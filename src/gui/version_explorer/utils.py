# src/gui/version_explorer/utils.py
from __future__ import annotations
import re
from pathlib import Path
from src.utils import human_size
from src.logger import setup_logger

logger = setup_logger(__name__)


def parse_date_from_header(file_path: Path) -> str:
    """Extrait la date d'extraction depuis l'en-tête du fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Date d\'extraction'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        return parts[1].strip()
    except Exception:
        logger.debug("Erreur lors de la lecture de la date d'extraction", exc_info=True)
    return ""


def format_size(size_bytes: int) -> str:
    """Utilise la fonction human_size existante."""
    return human_size(size_bytes)


def get_file_stats(file_path: Path) -> dict:
    """Extrait les statistiques depuis le bloc STATISTIQUES."""
    stats = {'file_count': 0, 'line_count': 0, 'total_size': 0}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Recherche du bloc STATISTIQUES (après le marqueur)
        match = re.search(r'STATISTIQUES\n=+.*?\n(.*?)(?=\n--- FIN DES FICHIERS|---|\Z)', content, re.DOTALL)
        if match:
            block = match.group(1)
            # Extraire les valeurs
            fc = re.search(r'Nombre total de fichiers\s*:\s*(\d+)', block)
            if fc:
                stats['file_count'] = int(fc.group(1))
            lc = re.search(r'Nombre total de lignes\s*:\s*(\d+)', block)
            if lc:
                stats['line_count'] = int(lc.group(1))
            # Taille : "Volume total extrait : 123.45 Ko" ou "... Mo"
            size_match = re.search(r'Volume total extrait\s*:\s*([\d.]+)\s*([KMG]o)?', block)
            if size_match:
                val = float(size_match.group(1))
                unit = size_match.group(2) or 'octets'
                if unit.startswith('K'):
                    stats['total_size'] = int(val * 1024)
                elif unit.startswith('M'):
                    stats['total_size'] = int(val * 1024 * 1024)
                else:
                    stats['total_size'] = int(val)
    except Exception:
        logger.debug("Erreur lors de l'extraction des statistiques du fichier", exc_info=True)
    return stats