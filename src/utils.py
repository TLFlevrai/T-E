# src/utils.py
from datetime import datetime

from src.i18n import _


def get_current_date():
    """Retourne la date actuelle formatée"""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def human_size(size_bytes):
    """
    Retourne une taille lisible en octets, Ko ou Mo.
    Utilisée pour l'affichage des métadonnées (structure, statistiques, GUI).
    """
    if size_bytes < 1024:
        return f"{size_bytes} {_('octets')}"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} Ko"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} Mo"
