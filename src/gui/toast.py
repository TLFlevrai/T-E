# src/gui/toast.py
"""Notifications non-bloquantes en bas de fenêtre (toasts)."""
from __future__ import annotations
import tkinter as tk
from typing import Optional

from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

# Types de toast -> couleurs
_TYPE_COLORS = {
    'info': ('#2b7de9', '#ffffff'),
    'success': ('#28a745', '#ffffff'),
    'warning': ('#ffc107', '#1f1f1f'),
    'error': ('#dc3545', '#ffffff'),
}

_STOCK = []  # toasts actifs, pour les empiler


def show_toast(
    root: tk.Misc,
    message: str,
    type_: str = 'info',
    duration_ms: int = 4000,
    parent: Optional[tk.Tk] = None,
):
    """
    Affiche une notification discrète en bas de la fenêtre principale.
    Non bloquant : disparaît automatiquement après duration_ms.
    """
    try:
        _Toast(root, message, type_, duration_ms, parent)
    except Exception as exc:
        logger.debug("Erreur affichage toast : %s", exc)


def _reposition_all():
    """Empile les toasts en remontant."""
    offset = 0
    for toast in _STOCK:
        toast._place_with_offset(offset)
        offset += toast.win.winfo_height() + 8


class _Toast:
    """Fenêtre sans bordure affichée en bas à droite, avec fondu."""

    def __init__(self, root, message, type_, duration_ms, parent):
        self.root = root
        self.duration_ms = duration_ms

        bg, fg = _TYPE_COLORS.get(type_, _TYPE_COLORS['info'])

        # Fenêtre sans bordure, au-dessus des autres
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.configure(bg=bg)

        # Contenu
        label = tk.Label(
            self.win,
            text=message,
            bg=bg,
            fg=fg,
            font=('Segoe UI', 9),
            padx=18,
            pady=10,
            justify=tk.LEFT,
            wraplength=320,
        )
        label.pack()

        # Positionner en bas de la fenêtre principale
        self._place()
        self.win.bind('<Button-1>', lambda e: self.close())
        label.bind('<Button-1>', lambda e: self.close())

        # Empiler au-dessus des toasts précédents
        _STOCK.append(self)
        _reposition_all()

        # Fermeture automatique avec fondu
        self.win.after(duration_ms, self._fade_out)

    def _place(self):
        self.win.update_idletasks()
        x = self.root.winfo_rootx() + self.root.winfo_width() - self.win.winfo_width() - 20
        y = self.root.winfo_rooty() + self.root.winfo_height() - self.win.winfo_height() - 20
        self.win.geometry(f"+{x}+{y}")

    def _place_with_offset(self, offset: int):
        x = self.root.winfo_rootx() + self.root.winfo_width() - self.win.winfo_width() - 20
        y = self.root.winfo_rooty() + self.root.winfo_height() - self.win.winfo_height() - 20 - offset
        self.win.geometry(f"+{x}+{y}")

    def _fade_out(self, step: int = 0):
        """Fondu de sortie progressif."""
        try:
            alpha = 1.0 - step * 0.1
            if alpha <= 0:
                self.close()
                return
            self.win.attributes('-alpha', alpha)
            self.win.after(40, lambda: self._fade_out(step + 1))
        except Exception:
            logger.debug("Erreur lors du fondu de sortie", exc_info=True)
            self.close()

    def close(self):
        try:
            if self in _STOCK:
                _STOCK.remove(self)
            self.win.destroy()
            # Ré-aligner les toasts restants
            _reposition_all()
        except Exception as exc:
            logger.debug("Erreur fermeture toast : %s", exc, exc_info=True)