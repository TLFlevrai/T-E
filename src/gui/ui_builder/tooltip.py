# src/gui/ui_builder/tooltip.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from src.i18n import _


class ToolTip:
    """Affiche une infobulle au survol d'un widget."""

    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event=None):
        self._schedule()

    def _on_leave(self, event=None):
        self._unschedule()
        self._hide()

    def _schedule(self):
        self._unschedule()
        self.after_id = self.widget.after(self.delay, self._show)

    def _unschedule(self):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _show(self):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(tw, text=self.text, background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                          padding=(6, 3), font=("Arial", 9))
        label.pack()

    def _hide(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def update_text(self, text: str):
        """Met à jour le texte de l'infobulle (utile pour i18n)."""
        self.text = text
        if self.tip_window:
            self._hide()
            self._show()


def add_tooltip(widget, text: str, delay: int = 500) -> ToolTip:
    """Factory pour ajouter une infobulle à un widget."""
    return ToolTip(widget, text, delay)


class LazyToolTip:
    """Infobulle qui supporte la traduction dynamique (i18n)."""

    def __init__(self, widget, msgid: str, delay: int = 500):
        self.widget = widget
        self.msgid = msgid
        self.delay = delay
        self.tooltip = None
        self._create()

    def _create(self):
        self.tooltip = ToolTip(self.widget, _(self.msgid), self.delay)

    def refresh(self):
        """Rafraîchit le texte traduit (appelé au changement de langue)."""
        if self.tooltip:
            self.tooltip.update_text(_(self.msgid))


def add_lazy_tooltip(widget, msgid: str, delay: int = 500) -> LazyToolTip:
    """Factory pour ajouter une infobulle traduisible à un widget."""
    return LazyToolTip(widget, msgid, delay)