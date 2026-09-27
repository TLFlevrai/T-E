# src/extractor/engine.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Callable
from src.extractor.file_discovery import FileDiscoveryService
from src.extractor.structure_generator import generate_project_structure
from src.extractor.report_builder import ReportBuilder
from src.extractor.file_processor import FileProcessor
from src.extractor.export_writer import write_file_section
from src.extractor.context import ExtractionContext
from src.logger import setup_logger

logger = setup_logger(__name__)

# Signature de callback de progression : (octets traités, total octets, nom relatif)
# FIX BUG #9 : progression pondérée par la taille (octets) au lieu du nombre de fichiers
ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]

# Résultats d'extraction
SUCCESS = 'success'
FAILED = 'failed'
CANCELLED = 'cancelled'
NO_SELECTION = 'no_selection'  # FIX BUG #7 : sélection vide (aucun fichier ne matche)


class ExtractionEngine:
    def __init__(self, context: ExtractionContext):
        self.context = context
        self.discovery = FileDiscoveryService(context.options)
        self.processor = FileProcessor(context)
        self.report_builder = ReportBuilder(context)
        self.cancel_event = None  # threading.Event optionnel pour annulation

    def set_cancel_event(self, cancel_event):
        """Permet d'annuler l'extraction entre deux fichiers."""
        self.cancel_event = cancel_event

    def run(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ) -> str:
        folder = self.context.folder_path
        output_path = self.context.output_path

        # 1) Découverte unique
        all_files = self.discovery.find_files(folder)
        if not all_files:
            self._warn("Aucun fichier trouvé", log_callback)
            return FAILED

        # 2) Filtrage sélection
        files = self._filter_selected(all_files, log_callback)
        if files is NO_SELECTION:
            return NO_SELECTION

        total_files = len(files)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, 'w', encoding='utf-8') as out_file:
                self._write_header(out_file, folder)
                self._write_structure(out_file, folder, log_callback)
                result = self._process_files(out_file, files, progress_callback, log_callback)
                if result == CANCELLED:
                    cancelled = True
                else:
                    cancelled = False
                    self._write_stats(out_file, log_callback)

            if cancelled:
                # Après fermeture du fichier : suppression du fichier partiel
                self._cleanup_partial_output(output_path)
                return CANCELLED

            logger.info("Extraction terminée avec succès : %s", output_path)
            return SUCCESS

        except Exception as e:
            logger.error("Erreur lors de l'extraction globale : %s", e)
            self._log(f"Erreur critique : {e}", log_callback)
            return FAILED

    def _cleanup_partial_output(self, output_path):
        """Supprime le fichier de sortie partiel après une annulation."""
        try:
            if output_path.exists():
                output_path.unlink()
                logger.info("Fichier partiel supprimé après annulation : %s", output_path)
        except Exception as e:
            logger.warning("Impossible de supprimer le fichier partiel : %s", e)

    @staticmethod
    def _normalize_rel_path(p: str) -> str:
        """Normalise un chemin relatif pour la comparaison (POSIX, sans ./ initial)."""
        return Path(p).as_posix().lstrip('./')

    # --- Sous-étapes de l'extraction ---

    def _filter_selected(self, all_files, log_callback: Optional[LogCallback]):
        """Filtre les fichiers selon la sélection. Retourne NO_SELECTION si rien ne correspond."""
        if self.context.selected_files is not None:
            # FIX BUG #7 : normaliser les deux côtés pour la comparaison
            selected_set = {self._normalize_rel_path(f) for f in self.context.selected_files}
            files = [(full, rel, ext) for full, rel, ext in all_files
                     if self._normalize_rel_path(rel.as_posix()) in selected_set]
            if not files:
                self._warn("Aucun fichier sélectionné ne correspond aux fichiers trouvés", log_callback)
                return NO_SELECTION
            return files
        return all_files

    def _write_header(self, out_file, folder):
        """Écrit l'en-tête du fichier d'export."""
        from src.utils import get_current_date
        out_file.write(f"Extraction du code du dossier : {folder}\n")
        out_file.write(f"Date d'extraction : {get_current_date()}\n")
        out_file.write("=" * 80 + "\n\n")

    def _write_structure(self, out_file, folder, log_callback: Optional[LogCallback]):
        """Écrit la structure du projet si l'option est activée."""
        if not self.context.options.include_structure:
            return
        structure = generate_project_structure(folder, self.context.options, self.context)
        out_file.write(structure)
        out_file.write("\n--- FIN DE LA STRUCTURE ---\n\n")
        self._log("✓ Structure du projet générée", log_callback)
        logger.info("Structure du projet générée")

    def _process_files(
        self,
        out_file,
        files,
        progress_callback: Optional[ProgressCallback],
        log_callback: Optional[LogCallback],
    ) -> str:
        """Boucle : TRAITER → ÉCRIRE (séparation des responsabilités).

        Retourne CANCELLED si l'annulation a été demandée.
        FIX BUG #9 : progression pondérée par la taille des fichiers (octets).
        """
        # FIX BUG #9 : précalculer les tailles pour éviter double I/O et permettre progression pondérée
        file_sizes = []
        total_size = 0
        for full_path, rel_path, ext in files:
            try:
                size = full_path.stat().st_size
            except OSError:
                size = 0
            file_sizes.append(size)
            total_size += size

        processed_size = 0
        for i, (full_path, rel_path, ext) in enumerate(files):
            # Vérifier l'annulation avant chaque fichier
            if self.cancel_event is not None and self.cancel_event.is_set():
                self._log("Extraction annulée par l'utilisateur", log_callback)
                logger.info("Extraction annulée par l'utilisateur")
                return CANCELLED

            if progress_callback:
                # FIX BUG #9 : passer les octets traités au lieu du nombre de fichiers
                progress_callback(processed_size, total_size, str(rel_path))

            # TRAITEMENT pur (testable sans I/O)
            result = self.processor.process(full_path, rel_path, ext)

            # ÉCRITURE (déléguée à export_writer)
            write_file_section(out_file, result)

            # Mettre à jour la taille traitée APRÈS le traitement réussi
            processed_size += file_sizes[i]

            if log_callback:
                if result.read_ok:
                    log_callback(f"✓ {rel_path} extrait")
                else:
                    log_callback(f"✗ Erreur sur {rel_path}")

        # Progression finale à 100%
        if progress_callback and total_size > 0:
            progress_callback(total_size, total_size, "")

        return SUCCESS

    def _write_stats(self, out_file, log_callback: Optional[LogCallback]):
        """Écrit les statistiques globales si l'option est activée."""
        if not self.context.options.include_statistics:
            return
        out_file.write("\n--- FIN DES FICHIERS ---\n\n")
        self.report_builder.write_statistics(out_file)

    @staticmethod
    def _warn(msg: str, log_callback: Optional[LogCallback]):
        if log_callback:
            log_callback(msg)
        logger.warning(msg)

    @staticmethod
    def _log(msg: str, log_callback: Optional[LogCallback]):
        if log_callback:
            log_callback(msg)