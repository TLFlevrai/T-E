# src/services/extraction_service.py
from __future__ import annotations
import shutil
from pathlib import Path
from typing import Optional, List, Callable, Tuple
from src.config import ExtractionOptions, get_config
from src.i18n import _
from src.versioning import VersionManager
from src.logger import setup_logger
from src.services.interfaces import ICodeExtractor, IVersionManager
from src.extractor.engine import ExtractionEngine, SUCCESS, FAILED, CANCELLED
from src.extractor.context import ExtractionContext

logger = setup_logger(__name__)


class ExtractionService:
    """
    Service d'extraction (couche Use-Case).
    
    Ne connaît que les interfaces (protocoles), pas les implémentations concrètes.
    L'injection de dépendances se fait via le constructeur.
    """
    
    def __init__(
        self,
        extractor: ICodeExtractor,
        version_manager: IVersionManager,
        output_dir: Path
    ):
        self.extractor = extractor
        self.version_manager = version_manager
        self.output_dir = output_dir

    def extract_folder(
        self,
        folder_path: str | Path,
        options: dict,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        selected_files: Optional[List[str]] = None,
        cancel_event=None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        selected_files : liste de chemins relatifs (str) à extraire.
        Si None ou vide, on extrait tous les fichiers trouvés.
        cancel_event : threading.Event optionnel pour annuler l'extraction.
        output_dir : dossier de sortie personnalisé (optionnel). Si fourni, 
                     un sous-dossier 'out' sera créé dedans.
        
        Retourne : (success, output_filename, stats_dict)
        success peut être True (ok), False (échec) ou None (annulé).
        """
        folder_path = Path(folder_path)
        
        # Fusionner options par défaut + options UI
        default_options = ExtractionOptions()
        merged_dict = default_options.model_dump()
        merged_dict.update(options)
        extractor_options = ExtractionOptions(**merged_dict)

        folder_name = folder_path.name
        
        # Déterminer le dossier de sortie effectif
        effective_output_dir = output_dir if output_dir is not None else self.output_dir
        if output_dir is not None:
            # Créer le sous-dossier 'out' dans le dossier personnalisé
            effective_output_dir = effective_output_dir / "out"
        
        effective_output_dir.mkdir(parents=True, exist_ok=True)
        next_version = self.version_manager.get_next_version(folder_name, output_dir=effective_output_dir)
        output_filename = effective_output_dir / f"{folder_name}v{next_version}.txt"

        # Construire le contexte avec les options fusionnées
        selected_set = None
        if selected_files is not None:
            selected_set = set(Path(f).as_posix() for f in selected_files)

        context = ExtractionContext(
            folder_path=folder_path,
            options=extractor_options,
            output_path=output_filename,
            selected_files=selected_set
        )

        # Utiliser ExtractionEngine directement (le contexte porte déjà les options)
        engine = ExtractionEngine(context)
        if cancel_event is not None:
            engine.set_cancel_event(cancel_event)
        result = engine.run(progress_callback, log_callback)

        if result == CANCELLED:
            # Extraction annulée : on ne consomme pas la version
            logger.info("Extraction annulée : %s", folder_name)
            return None, None, None

        if result == SUCCESS:
            self.version_manager.use_version(folder_name, next_version)
            stats = context.stats
            stats_dict = {
                'py_count': stats.get('py', 0),
                'json_count': stats.get('json', 0),
                'txt_count': stats.get('txt', 0),
                'po_count': stats.get('po', 0),
                'mo_count': stats.get('mo', 0),
                'html_count': stats.get('html', 0),
                'css_count': stats.get('css', 0),
                'js_count': stats.get('js', 0),
                'total_files': stats.get('total', 0),
                'output_filename': str(output_filename)
            }

            # Option « Archiver les anciennes versions » : déplace les
            # versions actives précédentes du même projet vers le dossier
            # d'archive. Best-effort : ne fait jamais échouer l'extraction.
            if merged_dict.get('archive_old'):
                self._archive_previous_versions(
                    folder_name, Path(output_filename), log_callback)

            logger.info("Extraction réussie : %s", output_filename)
            return True, str(output_filename), stats_dict
        else:
            logger.error("Échec de l'extraction")
            return False, None, None

    def _archive_previous_versions(self, project_name: str, new_file: Path,
                                   log_callback=None) -> int:
        """Archive les anciennes versions actives du projet (sauf la nouvelle)."""
        try:
            from src.services.version_service import VersionArchiveService
            archive_service = VersionArchiveService()
            archived = 0
            for entries in archive_service.scan_projects().values():
                for entry in entries:
                    if entry.project != project_name or entry.status != 'active':
                        continue
                    if entry.path.resolve() == new_file.resolve():
                        continue
                    try:
                        archive_service.archive(entry)
                        archived += 1
                        if log_callback:
                            log_callback(_("Ancienne version archivée : {}").format(entry.path.name))
                    except Exception as e:
                        logger.warning("Archivage impossible de %s : %s", entry.path, e)
            if archived and log_callback:
                log_callback(_("{} ancienne(s) version(s) archivée(s)").format(archived))
            return archived
        except Exception as e:
            logger.error("Erreur pendant l'archivage des anciennes versions : %s", e)
            return 0

    def clean_versions(self, archive: bool = False) -> str:
        if archive:
            archive_dir = self.output_dir / get_config().get('archive_subdir', 'old_out')
            archive_dir.mkdir(parents=True, exist_ok=True)
            moved_files = []
            for item in self.output_dir.iterdir():
                if item.is_file() and item.suffix == '.txt':
                    try:
                        shutil.move(str(item), str(archive_dir / item.name))
                        moved_files.append(item.name)
                    except Exception as e:
                        logger.error("Erreur archivage %s : %s", item, e)
                        raise
            logger.info("Archivés : %s", ', '.join(moved_files))

        self.version_manager.reset()
        logger.info("Historique des versions réinitialisé.")
        return "Nettoyage terminé" + (" (fichiers archivés)" if archive else "")