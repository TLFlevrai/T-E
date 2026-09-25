# src/paths.py
"""Fournisseur de chemins multi-plateforme pour données utilisateur."""
from __future__ import annotations
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PathProvider:
    """Résout les répertoires de config/data/cache selon la plateforme."""

    def __init__(self, app_name: str = "TE"):
        self.app_name = app_name

    def config_dir(self) -> Path:
        """Répertoire de configuration utilisateur."""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / self.app_name
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / self.app_name
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            return base / self.app_name.lower()

    def data_dir(self) -> Path:
        """Répertoire de données persistantes (exports, versions, reçus)."""
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / self.app_name
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / self.app_name
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            return base / self.app_name.lower()

    def cache_dir(self) -> Path:
        """Répertoire de cache (téléchargements temporaires, etc.)."""
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / self.app_name / "Cache"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Caches" / self.app_name
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            return base / self.app_name.lower()

    def ensure_dirs(self) -> None:
        """Crée les répertoires s'ils n'existent pas."""
        for dir_path in (self.config_dir(), self.data_dir(), self.cache_dir()):
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("Impossible de créer le répertoire %s : %s", dir_path, e)


def migrate_legacy_files(provider: PathProvider) -> None:
    """Migre les fichiers legacy (racine projet) vers les nouveaux emplacements.

    Copie (pas déplace) les fichiers s'ils existent à l'ancien emplacement
    et que le nouvel emplacement est vide. Log chaque migration.
    """
    for legacy_name, new_path in _legacy_migrations(provider):
        _migrate_one_legacy_file(provider, legacy_name, new_path)


def _legacy_migrations(provider: PathProvider):
    """Retourne la liste des migrations (legacy_name, new_path)."""
    return [
        ("config.json", provider.config_dir() / "config.json"),
        ("recent_folders.json", provider.config_dir() / "recent_folders.json"),
        ("extractor_version.txt", provider.data_dir() / "extractor_version.txt"),
    ]


def _migrate_one_legacy_file(provider: PathProvider, legacy_name: str, new_path: Path, description: str = "") -> bool:
    """Migre un seul fichier legacy s'il existe et que la destination n'existe pas.

    Args:
        provider: PathProvider instance
        legacy_name: Nom du fichier à la racine du projet (ex: "config.json")
        new_path: Chemin de destination complet
        description: Description optionnelle pour les logs

    Returns:
        True si la migration a eu lieu, False sinon
    """
    project_root = Path(__file__).parent.parent.parent
    legacy_path = project_root / legacy_name

    if legacy_path.exists() and not new_path.exists():
        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_bytes(legacy_path.read_bytes())
            desc = f" ({description})" if description else ""
            logger.info("Migration %s → %s%s", legacy_path, new_path, desc)
            return True
        except OSError as e:
            logger.warning("Échec migration %s : %s", legacy_path, e)
    return False


# Alias public pour compatibilité
migrate_one_legacy_file = _migrate_one_legacy_file


def get_legacy_fallback_path(filename: str) -> Path:
    """Retourne le chemin legacy (racine projet) en fallback."""
    return Path(__file__).parent.parent.parent / filename