# src/ui/tooltips.py
"""Système de tooltips contextuels enrichis de TE.

Un tooltip peut contenir : titre, description, raccourci, catégorie,
avertissement, exemple et documentation. Le système i18n existant est
conservé : `LazyRichToolTip` re-traduit son contenu à chaque changement
de langue (via `refresh()`), tout comme l'ancien `LazyToolTip`.

`add_tooltip` / `add_lazy_tooltip` restent disponibles (réexportés depuis
src.gui.ui_builder.tooltip) pour préserver la compatibilité.
"""
from __future__ import annotations

import contextlib
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from src.gui.ui_builder.tooltip import LazyToolTip, ToolTip, add_lazy_tooltip, add_tooltip
from src.i18n import _

# Couleurs du tooltip (indépendantes du thème pour la lisibilité)
_TIP_BG = '#2b2b2b'
_TIP_FG = '#f0f0f0'
_TIP_TITLE = '#ffffff'
_TIP_ACCENT = '#4cc2ff'
_TIP_WARN = '#ffcc66'


@dataclass
class ToolTipContent:
    """Contenu d'un tooltip contextuel (textes déjà traduits ou msgids)."""

    title: str | None = None
    description: str | None = None
    shortcut: str | None = None
    category: str | None = None
    warning: str | None = None
    example: str | None = None
    docs: str | None = None

    def render(self) -> str:
        """Construit la représentation multi-lignes du tooltip."""
        lines: list[str] = []
        if self.title:
            lines.append(self.title)
        if self.description:
            lines.append(self.description)
        if self.shortcut:
            lines.append(f"{_('Raccourci')} : {self.shortcut}")
        if self.category:
            lines.append(f"{_('Catégorie')} : {self.category}")
        if self.warning:
            lines.append(f"⚠ {_('Attention')} : {self.warning}")
        if self.example:
            lines.append(f"{_('Exemple')} : {self.example}")
        if self.docs:
            lines.append(f"{_('Documentation')} : {self.docs}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return not any([
            self.title, self.description, self.shortcut,
            self.category, self.warning, self.example, self.docs,
        ])


class RichToolTip:
    """Infobulle enrichie (titre, description, raccourci, ...) au survol."""

    def __init__(self, widget, content: ToolTipContent, delay: int = 500):
        self.widget = widget
        self.content = content
        self.delay = delay
        self.tip_window: tk.Toplevel | None = None
        self.after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    # --- Cycle de vie ---

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
            with contextlib.suppress(Exception):
                self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _show(self):
        if self.tip_window or self.content.is_empty():
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        text = self.content.render()
        title = self.content.title or ''

        frame = ttk.Frame(tw)
        frame.pack()
        tk.Frame(frame, bg=_TIP_ACCENT, height=2).pack(fill=tk.X)
        if title:
            tk.Label(
                frame, text=title, bg=_TIP_BG, fg=_TIP_TITLE,
                font=('Segoe UI', 10, 'bold'), justify=tk.LEFT,
                anchor='w', padx=12, pady=8,
            ).pack(fill=tk.X)
        tk.Label(
            frame, text=text, bg=_TIP_BG, fg=_TIP_FG,
            font=('Segoe UI', 9), justify=tk.LEFT, anchor='w',
            padx=12, pady=6,
        ).pack(fill=tk.X)

    def _hide(self):
        if self.tip_window:
            with contextlib.suppress(Exception):
                self.tip_window.destroy()
            self.tip_window = None

    def update_content(self, content: ToolTipContent):
        """Met à jour le contenu du tooltip (utile pour i18n)."""
        self.content = content
        if self.tip_window:
            self._hide()
            self._show()


class LazyRichToolTip:
    """Infobulle enrichie dont le contenu est traduit à la volée."""

    def __init__(self, widget, content: ToolTipContent, delay: int = 500):
        self.widget = widget
        self.msgids = content
        self.delay = delay
        self.tooltip = RichToolTip(widget, self._translate(), delay)

    def _translate(self) -> ToolTipContent:
        return ToolTipContent(
            title=_(self.msgids.title) if self.msgids.title else None,
            description=_(self.msgids.description) if self.msgids.description else None,
            shortcut=self.msgids.shortcut,
            category=_(self.msgids.category) if self.msgids.category else None,
            warning=_(self.msgids.warning) if self.msgids.warning else None,
            example=_(self.msgids.example) if self.msgids.example else None,
            docs=_(self.msgids.docs) if self.msgids.docs else None,
        )

    def refresh(self):
        """Re-traduit le contenu (appelé au changement de langue)."""
        if self.tooltip:
            self.tooltip.update_content(self._translate())


def add_rich_tooltip(widget, content: ToolTipContent, delay: int = 500) -> RichToolTip:
    """Factory : infobulle enrichie avec contenu déjà traduit."""
    return RichToolTip(widget, content, delay)


def add_lazy_rich_tooltip(widget, content: ToolTipContent, delay: int = 500) -> LazyRichToolTip:
    """Factory : infobulle enrichie traduisible (msgids)."""
    return LazyRichToolTip(widget, content, delay)


__all__ = [
    'LazyRichToolTip',
    'LazyToolTip',
    'RichToolTip',
    'ToolTip',
    'ToolTipContent',
    'add_lazy_rich_tooltip',
    'add_lazy_tooltip',
    'add_rich_tooltip',
    'add_tooltip',
]
