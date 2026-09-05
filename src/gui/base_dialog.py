# src/gui/base_dialog.py
"""Classe de base pour les fenêtres de dialogue (Toplevel)."""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from src.i18n import _
from src.logger import setup_logger
from .errors import show_error, show_info, confirm, run_and_handle, center_window

logger = setup_logger(__name__)


class BaseDialog(tk.Toplevel):
    """
    Fenêtre de dialogue modale : centrage, gestion d'erreurs centralisée.
    Les sous-classes doivent appeler super().__init__(parent, title, geometry, minsize).
    """

    def __init__(
        self,
        parent,
        title: str,
        geometry: Optional[str] = None,
        minsize: Optional[tuple] = None,
        modal: bool = True,
    ):
        super().__init__(parent)
        self.title(title)
        if geometry:
            self.geometry(geometry)
        if minsize:
            self.minsize(*minsize)
        if modal:
            self.transient(parent)
            self.grab_set()

        self._center_window()

    # --- Positionnement ---

    def _center_window(self):
        """Centre la fenêtre par rapport au parent."""
        center_window(self)

    # --- Gestion d'erreurs centralisée ---

    def show_error(self, title: str, message: str):
        """Affiche une erreur (log + messagebox)."""
        show_error(title, message, parent=self)

    def show_info(self, title: str, message: str):
        """Affiche une information."""
        show_info(title, message, parent=self)

    def confirm(self, title: str, message: str, icon: str = messagebox.QUESTION) -> bool:
        """Demande une confirmation."""
        return confirm(title, message, parent=self, icon=icon)

    def run_operation(
        self,
        func,
        error_title: str,
        *,
        on_error_message=None,
    ):
        """
        Exécute une opération en interceptant les exceptions.
        Retourne le résultat de func, ou None si erreur.
        """
        return run_and_handle(
            func, error_title, parent=self, on_error_message=on_error_message
        )