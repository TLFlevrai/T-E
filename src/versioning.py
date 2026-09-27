# versioning.py
from pathlib import Path
import threading
from src.logger import setup_logger
from src.paths import PathProvider, migrate_legacy_files, migrate_one_legacy_file

logger = setup_logger(__name__)

_provider = PathProvider()
_provider.ensure_dirs()
migrate_legacy_files(_provider)

_DEFAULT_VERSION_FILE = _provider.data_dir() / "extractor_version.txt"
if not _DEFAULT_VERSION_FILE.exists():
    migrate_one_legacy_file(_provider, "extractor_version.txt", _DEFAULT_VERSION_FILE, "versions")


class VersionManager:
    def __init__(self, version_file=None):
        if version_file is None:
            version_file = _DEFAULT_VERSION_FILE
        self.version_file = Path(version_file)
        self._lock = threading.Lock()
        self.mapping = self.load_mapping()

    def load_mapping(self):
        mapping = {}
        if self.version_file.exists():
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and ":" in line:
                            folder, ver = line.split(":", 1)
                            mapping[folder] = int(ver)
            except (IOError, OSError, ValueError) as e:
                logger.error("Erreur lors du chargement du fichier de versions : %s", e)
                mapping = {}
        return mapping

    def _save_mapping_locked(self):
        """Appelée uniquement lorsqu'on détient déjà le verrou."""
        try:
            tmp_file = self.version_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                for folder, ver in sorted(self.mapping.items()):
                    f.write(f"{folder}:{ver}\n")
            tmp_file.replace(self.version_file)
        except (IOError, OSError) as e:
            logger.error("Erreur lors de la sauvegarde du fichier de versions : %s", e)

    def save_mapping(self):
        with self._lock:
            self._save_mapping_locked()

    def get_next_version(self, folder_name, output_dir="."):
        with self._lock:
            output_dir = Path(output_dir)
            last_version = self.mapping.get(folder_name, 0)
            version = last_version + 1
            while (output_dir / f"{folder_name}v{version}.txt").exists():
                version += 1
            return version

    def use_version(self, folder_name, version):
        # Tout sous le même verrou pour éviter toute race
        with self._lock:
            self.mapping[folder_name] = version
            # Sauvegarde immédiate avant de libérer le verrou
            self._save_mapping_locked()

    def reset(self):
        with self._lock:
            self.mapping = {}
            if self.version_file.exists():
                try:
                    self.version_file.unlink()
                    logger.info("Fichier de versions supprimé.")
                except (IOError, OSError) as e:
                    logger.error("Erreur lors de la suppression du fichier de versions : %s", e)

    def reset_project(self, folder_name):
        """Réinitialise le compteur pour un projet spécifique."""
        with self._lock:
            if folder_name in self.mapping:
                del self.mapping[folder_name]
                self._save_mapping_locked()
                logger.info("Compteur réinitialisé pour %s", folder_name)

    # FIX BUG #1 : Race condition sur la numérotation de version
    def reserve_version(self, folder_name, output_dir="."):
        """
        Réserve une version de façon atomique sous verrou.
        Calcule la prochaine version, met à jour le mapping, crée un fichier sentinel,
        et retourne le numéro réservé. Évite la race condition entre get_next_version()
        et use_version() lors d'extractions simultanées.
        """
        with self._lock:
            output_dir = Path(output_dir)
            last_version = self.mapping.get(folder_name, 0)
            version = last_version + 1
            # Trouver la prochaine version libre (fichier inexistant)
            while (output_dir / f"{folder_name}v{version}.txt").exists():
                version += 1
            # Mettre à jour le mapping et sauvegarder
            self.mapping[folder_name] = version
            self._save_mapping_locked()
            # Créer le fichier sentinel pour marquer la réservation
            sentinel_path = output_dir / f"{folder_name}v{version}.txt.sentinel"
            try:
                sentinel_path.write_text("", encoding="utf-8")
            except (IOError, OSError) as e:
                logger.warning("Impossible de créer le fichier sentinel : %s", e)
            return version

    def release_version(self, folder_name, version, output_dir="."):
        """
        Libère une version réservée (annulation ou échec).
        Supprime le fichier sentinel et restaure l'ancien mapping.
        """
        with self._lock:
            output_dir = Path(output_dir)
            # Supprimer le fichier sentinel
            sentinel_path = output_dir / f"{folder_name}v{version}.txt.sentinel"
            try:
                if sentinel_path.exists():
                    sentinel_path.unlink()
            except Exception as e:
                logger.warning("Impossible de supprimer le fichier sentinel : %s", e)
            # Restaurer l'ancien mapping
            if version == 1:
                if folder_name in self.mapping:
                    del self.mapping[folder_name]
            else:
                self.mapping[folder_name] = version - 1
            self._save_mapping_locked()

    def load_version(self):
        """
        .. deprecated:: 2.1.0
            Utilisez :meth:`get_next_version` avec le nom du dossier.
        """
        import warnings
        warnings.warn(
            "load_version() est déprécié, utilisez get_next_version(folder_name)",
            DeprecationWarning,
            stacklevel=2
        )
        return 1

    def save_version(self, version):
        """
        .. deprecated:: 2.1.0
            Utilisez :meth:`use_version` avec le nom du dossier et la version.
        """
        import warnings
        warnings.warn(
            "save_version() est déprécié, utilisez use_version(folder_name, version)",
            DeprecationWarning,
            stacklevel=2
        )
        pass