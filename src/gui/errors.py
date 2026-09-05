# src/gui/errors.py
"""Helpers centralisés pour la gestion d'erreurs et les boîtes de dialogue."""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional, TypeVar

from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

T = TypeVar('T')


def show_error(title: str, message: str, parent: Optional[tk.Misc] = None, log: bool = True):
    """
    Affiche une erreur et la journalise.
    Le titre et le message doivent être déjà traduits.
    """
    if log:
        logger.error(message)
    messagebox.showerror(title, message, parent=parent)


def show_info(title: str, message: str, parent: Optional[tk.Misc] = None):
    """Affiche une boîte d'information."""
    messagebox.showinfo(title, message, parent=parent)


def show_warning(title: str, message: str, parent: Optional[tk.Misc] = None):
    """Affiche un avertissement."""
    messagebox.showwarning(title, message, parent=parent)


def confirm(
    title: str,
    message: str,
    parent: Optional[tk.Misc] = None,
    icon: str = messagebox.QUESTION,
) -> bool:
    """Demande une confirmation oui/non."""
    return messagebox.askyesno(title, message, parent=parent, icon=icon)


def log_and_show_error(title: str, message: str, parent: Optional[tk.Misc] = None):
    """Log l'erreur et l'affiche (sans exposer la trace)."""
    show_error(title, message, parent=parent, log=True)


def run_and_handle(
    func: Callable[[], T],
    error_title: str,
    parent: Optional[tk.Misc] = None,
    *,
    on_error_message: Optional[Callable[[Exception], str]] = None,
) -> Optional[T]:
    """
    Exécute func en interceptant les exceptions : log + messagebox.
    Retourne le résultat de func, ou None si une exception est survenue.
    """
    try:
        return func()
    except Exception as e:
        message = on_error_message(e) if on_error_message else str(e)
        log_and_show_error(error_title, message, parent=parent)
        return None


def center_window(window: tk.Toplevel):
    """Centre une fenêtre par rapport à son parent."""
    window.update_idletasks()
    parent = window.master
    if parent:
        x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 2
        window.geometry(f"+{x}+{y}")