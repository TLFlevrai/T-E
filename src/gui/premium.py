# src/gui/premium.py
"""
Améliorations de rendu : High-DPI, police moderne, thème ttkbootstrap.
Chaque fonction est un "best effort" : si une étape échoue, on continue.
"""
from __future__ import annotations
import sys
import tkinter as tk
import tkinter.font as tkfont

from src.logger import setup_logger

logger = setup_logger(__name__)

# Map nos thèmes logiques vers les thèmes ttkbootstrap
TTKBOOTSTRAP_THEMES = {
    'light': 'litera',   # clair moderne
    'dark': 'darkly',    # sombre moderne
    'default': 'litera',
}


def setup_dpi_awareness() -> bool:
    """Active le scaling High-DPI sur Windows (rendu net sur écrans 4K)."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        try:
            # Tenter le mode Per-Monitor DPI Aware v2 (meilleur)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            # Fallback : system DPI aware
            ctypes.windll.user32.SetProcessDPIAware()
        return True
    except Exception as e:
        logger.warning("Échec de l'activation High-DPI : %s", e)
        return False


def setup_default_font(root: tk.Tk):
    """Définit une police moderne par défaut (Segoe UI Variable si dispo)."""
    candidates = ['Segoe UI Variable Text', 'Segoe UI', 'TkDefaultFont', 'Helvetica']
    for family in candidates:
        try:
            if family == 'TkDefaultFont':
                # Garder la famille actuelle
                current = tkfont.nametofont('TkDefaultFont')
                current.configure(size=10)
                return
            families = set(tkfont.families(root))
            if family in families:
                tkfont.nametofont('TkDefaultFont').configure(
                    family=family, size=10
                )
                # Propager aux autres fonts Tk standard
                for name in ('TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkCaptionFont'):
                    try:
                        tkfont.nametofont(name).configure(family=family, size=10)
                    except Exception:
                        logger.debug("Échec de configuration de la police Tk secondaire", exc_info=True)
                return
        except Exception:
            continue


def premium_available() -> bool:
    """Vérifie si ttkbootstrap est disponible."""
    try:
        import ttkbootstrap  # noqa: F401
        return True
    except ImportError:
        return False


def apply_premium_theme(theme_name: str) -> bool:
    """
    Applique un thème ttkbootstrap. Retourne False si non disponible ou échec.
    """
    if not premium_available():
        return False
    try:
        import ttkbootstrap
        theme = TTKBOOTSTRAP_THEMES.get(theme_name, theme_name)
        style = ttkbootstrap.Style(theme=theme)
        return True
    except Exception as e:
        logger.warning("Échec d'application du thème ttkbootstrap '%s' : %s", theme_name, e)
        return False