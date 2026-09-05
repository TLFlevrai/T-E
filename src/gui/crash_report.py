# src/gui/crash_report.py
"""Dialogue propre de signalement d'erreur en cas de crash."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)


def show_crash_dialog(root: tk.Tk, details: str):
    """Affiche un dialogue de crash propre (ne doit jamais lever)."""
    try:
        _CrashDialog(root, details)
    except Exception:
        # Dernier recours : messagebox standard
        try:
            messagebox.showerror(
                _("Erreur inattendue"),
                _("Une erreur inattendue est survenue. Consultez les logs.")
            )
        except Exception:
            logger.debug("Erreur lors de l'affichage du messagebox de secours", exc_info=True)


class _CrashDialog(tk.Toplevel):
    """Fenêtre de signalement d'erreur avec détails copiables."""

    def __init__(self, parent, details: str):
        super().__init__(parent)
        self.title(_("Erreur inattendue"))
        self.geometry("560x420")
        self.minsize(480, 320)
        self.transient(parent)

        self._create_widgets(details)

    def _create_widgets(self, details: str):
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main,
            text=_("⚠ Une erreur inattendue est survenue."),
            font=('Arial', 12, 'bold'),
        ).pack(anchor=tk.W)

        ttk.Label(
            main,
            text=_("L'application va tenter de continuer. "
                   "Les détails ont été enregistrés dans le journal."),
            wraplength=500,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 10))

        # Zone de détails
        ttk.Label(main, text=_("Détails :")).pack(anchor=tk.W)
        self.text = tk.Text(main, height=14, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True, pady=(2, 8))
        self.text.insert(tk.END, details)
        self.text.config(state=tk.DISABLED)

        # Scrollbar
        scroll = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.place(relx=1.0, rely=1.0, anchor=tk.SE, relheight=1.0)

        # Boutons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text=_("Copier les détails"), command=lambda: self._copy(details)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text=_("Continuer"), command=self.destroy).pack(side=tk.RIGHT)

    def _copy(self, details: str):
        self.clipboard_clear()
        self.clipboard_append(details)