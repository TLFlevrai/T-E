# versioning.py
from pathlib import Path
import threading
from src.logger import setup_logger

logger = setup_logger(__name__)

class VersionManager:
    def __init__(self, version_file="extractor_version.txt"):
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

    def save_mapping(self):
        # Sauvegarde atomique via fichier temporaire
        try:
            tmp_file = self.version_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                for folder, ver in sorted(self.mapping.items()):
                    f.write(f"{folder}:{ver}\n")
            tmp_file.replace(self.version_file)
        except (IOError, OSError) as e:
            logger.error("Erreur lors de la sauvegarde du fichier de versions : %s", e)

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
            self._save_mapping_locked()   # méthode interne sans verrou

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

    # On garde save_mapping pour d'autres usages éventuels, mais on le réécrit
    # pour qu'il utilise le verrou (appel externe)
    def save_mapping(self):
        with self._lock:
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

    # Anciennes méthodes conservées pour compatibilité
    def load_version(self):
        return 1

    def save_version(self, version):
        pass