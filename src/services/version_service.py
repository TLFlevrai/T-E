# src/services/version_service.py
from __future__ import annotations
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import get_config
from src.logger import setup_logger
from src.versioning import VersionManager

logger = setup_logger(__name__)

# Regex pour extraire projet et version d'un nom de fichier
VERSION_FILE_PATTERN = re.compile(r'^(.+?)v(\d+)\.txt$')


@dataclass
class VersionEntry:
    """Métadonnées d'une version d'export."""
    project: str
    version: int
    date: str          # date extraite de l'en-tête
    size: int          # taille en octets
    file_count: int    # nombre total de fichiers extraits
    line_count: int    # nombre total de lignes
    status: str        # 'active' ou 'archived'
    path: Path         # chemin complet du fichier


class VersionArchiveService:
    """Service de gestion des versions d'export."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        archive_subdir: Optional[str] = None,
        version_manager: Optional[VersionManager] = None,
    ):
        cfg = get_config()
        self.output_dir = Path(output_dir or cfg.get('output_dir', 'out'))
        self.archive_subdir = archive_subdir or cfg.get('archive_subdir', 'old_out')
        self.archive_dir = self.output_dir / self.archive_subdir
        self.version_manager = version_manager or VersionManager(
            cfg.get('version_file', 'extractor_version.txt')
        )

    def scan_projects(self) -> Dict[str, List[VersionEntry]]:
        """
        Scanne les répertoires de sortie et d'archive pour construire
        la liste des versions par projet.
        Retourne un dictionnaire {nom_projet: [VersionEntry, ...]}.
        """
        projects: Dict[str, List[VersionEntry]] = {}

        # Parcours récursif des deux dossiers
        for root_dir in [self.output_dir, self.archive_dir]:
            if not root_dir.exists():
                continue
            for file_path in root_dir.rglob('*.txt'):
                # Ignorer les fichiers dans des sous-dossiers d'archive ?
                # On veut tous les fichiers .txt
                match = VERSION_FILE_PATTERN.match(file_path.name)
                if not match:
                    continue
                project = match.group(1)
                version = int(match.group(2))
                # Déterminer le statut : si le fichier est dans archive_dir (ou un sous-dossier)
                # mais attention: un fichier archivé peut être dans archive_dir/projet/ ou directement à la racine
                # On considère archivé si le chemin parent contient archive_dir
                if self.archive_dir in file_path.parents or file_path.parent == self.archive_dir:
                    status = 'archived'
                else:
                    status = 'active'

                # Métadonnées (lecture du fichier)
                meta = self._parse_metadata(file_path)
                entry = VersionEntry(
                    project=project,
                    version=version,
                    date=meta.get('date', ''),
                    size=file_path.stat().st_size,
                    file_count=meta.get('file_count', 0),
                    line_count=meta.get('line_count', 0),
                    status=status,
                    path=file_path,
                )
                projects.setdefault(project, []).append(entry)

        # Trier les versions par numéro décroissant pour chaque projet
        for project in projects:
            projects[project].sort(key=lambda e: e.version, reverse=True)

        return projects

    @staticmethod
    def _parse_metadata(file_path: Path) -> Dict[str, int | str]:
        """
        Extrait la date, le nombre total de fichiers et le nombre total de lignes
        depuis le fichier d'export.
        Retourne un dict avec les clés 'date', 'file_count', 'line_count'.
        """
        result = {'date': '', 'file_count': 0, 'line_count': 0}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(4096)  # lire les premiers 4K pour l'en-tête et les stats
        except Exception as e:
            logger.warning("Impossible de lire %s pour les métadonnées : %s", file_path, e)
            return result

        # Extraction de la date
        date_match = re.search(r'Date d\'extraction\s*:\s*(.+)', content)
        if date_match:
            result['date'] = date_match.group(1).strip()

        # Extraction du nombre total de fichiers
        file_match = re.search(r'Nombre total de fichiers\s*:\s*(\d+)', content)
        if file_match:
            result['file_count'] = int(file_match.group(1))

        # Extraction du nombre total de lignes
        line_match = re.search(r'Nombre total de lignes\s*:\s*(\d+)', content)
        if line_match:
            result['line_count'] = int(line_match.group(1))

        return result

    def archive(self, entry: VersionEntry) -> Path:
        """
        Archive une version active : déplace le fichier vers archive_dir/project/.
        Retourne le nouveau chemin.
        Lève une exception si le fichier n'existe pas ou si la destination existe.
        """
        if entry.status != 'active':
            raise ValueError(f"Seules les versions actives peuvent être archivées : {entry.path}")

        dest_dir = self.archive_dir / entry.project
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / entry.path.name

        # Gérer la collision : ajouter un suffixe _conflict si le fichier existe déjà
        if dest_path.exists():
            base = dest_path.stem
            ext = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_dir / f"{base}_conflict{counter}{ext}"
                counter += 1

        shutil.move(str(entry.path), str(dest_path))
        logger.info("Version archivée : %s -> %s", entry.path, dest_path)
        return dest_path

    def restore(self, entry: VersionEntry) -> Path:
        """
        Restaure une version archivée : déplace le fichier vers output_dir/.
        Retourne le nouveau chemin.
        Lève une exception si le fichier n'existe pas ou si la destination existe.
        """
        if entry.status != 'archived':
            raise ValueError(f"Seules les versions archivées peuvent être restaurées : {entry.path}")

        dest_path = self.output_dir / entry.path.name

        # Gérer la collision : ajouter _restored si le fichier existe déjà
        if dest_path.exists():
            base = dest_path.stem
            ext = dest_path.suffix
            # Vérifier si le fichier existe déjà en ajoutant _restored
            dest_path = self.output_dir / f"{base}_restored{ext}"
            if dest_path.exists():
                # Si _restored existe aussi, ajouter un compteur
                counter = 1
                while dest_path.exists():
                    dest_path = self.output_dir / f"{base}_restored{counter}{ext}"
                    counter += 1

        shutil.move(str(entry.path), str(dest_path))
        logger.info("Version restaurée : %s -> %s", entry.path, dest_path)
        return dest_path

    def delete(self, entry: VersionEntry) -> None:
        """Supprime définitivement le fichier de version."""
        if not entry.path.exists():
            logger.warning("Le fichier %s n'existe plus, suppression ignorée.", entry.path)
            return
        entry.path.unlink()
        logger.info("Version supprimée : %s", entry.path)

    def reset_project(self, project_name: str) -> None:
        """
        Réinitialise le compteur de version pour un projet donné.
        """
        self.version_manager.reset_project(project_name)
        logger.info("Compteur réinitialisé pour le projet '%s'", project_name)

    def reset_all(self) -> None:
        """Réinitialise tous les compteurs."""
        self.version_manager.reset()
        logger.info("Tous les compteurs réinitialisés.")

    def clean_all(self) -> int:
        """
        Supprime tout le contenu du dossier de sortie (out) y compris les archives.
        Retourne le nombre de fichiers supprimés.
        """
        count = 0
        if self.output_dir.exists():
            for file_path in self.output_dir.rglob('*'):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        count += 1
                    except Exception as e:
                        logger.error("Impossible de supprimer %s : %s", file_path, e)
        logger.info("Nettoyage complet : %d fichier(s) supprimé(s)", count)
        return count