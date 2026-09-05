# src/gui/recent_files.py
from __future__ import annotations
import json
import os
from pathlib import Path

from src.logger import setup_logger

logger = setup_logger(__name__)

RECENT_FILE = Path(__file__).parent.parent.parent / "recent_folders.json"
MAX_RECENT = 10


def load_recent_folders():
    """Charge la liste des dossiers récents depuis le fichier JSON."""
    if RECENT_FILE.exists():
        try:
            with open(RECENT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                folders = data.get('folders', [])
                # Filtrer les dossiers qui n'existent plus
                return [f for f in folders if os.path.exists(f)]
        except Exception as exc:
            logger.debug("Erreur chargement dossiers récents : %s", exc)
            return []
    return []


def save_recent_folders(folders):
    """Sauvegarde la liste des dossiers récents."""
    try:
        with open(RECENT_FILE, 'w', encoding='utf-8') as f:
            json.dump({'folders': folders[:MAX_RECENT]}, f, indent=2)
    except Exception as exc:
        logger.debug("Erreur sauvegarde dossiers récents : %s", exc)


def add_recent_folder(folder_path):
    """Ajoute un dossier en tête de liste et sauvegarde."""
    folders = load_recent_folders()
    # Supprimer l'entrée si déjà présente
    if folder_path in folders:
        folders.remove(folder_path)
    # Insérer en tête
    folders.insert(0, folder_path)
    # Tronquer
    folders = folders[:MAX_RECENT]
    save_recent_folders(folders)
    return folders


def remove_recent_folder(folder_path):
    """Supprime un dossier de la liste (si inexistant par exemple)."""
    folders = load_recent_folders()
    if folder_path in folders:
        folders.remove(folder_path)
        save_recent_folders(folders)
    return folders


def clear_recent_folders():
    """Supprime tous les dossiers récents."""
    save_recent_folders([])