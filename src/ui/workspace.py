# src/ui/workspace.py
"""Workspace central de TE : affiche la vue de l'outil actif.

Les vues sont construites une seule fois puis mises en cache et enveloppées
dans un conteneur AutoScrollFrame, assurant l'ajout automatique de barres
de défilement si les composants dépassent la hauteur ou la largeur disponible.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.core.events import events
from src.core.tool_registry import registry
from src.i18n import _
from src.ui.autoscroll import AutoScrollFrame
from src.ui.tooltips import ToolTipContent, add_lazy_rich_tooltip


class Workspace(ttk.Frame):
    """Conteneur central qui bascule d'un outil à l'autre."""

    def __init__(self, shell: Any):
        self.shell = shell
        super().__init__(shell.root, padding=0)
        self._views: dict[str, tk.Widget] = {}
        self._containers: dict[str, AutoScrollFrame] = {}
        self._tips: list = []
        self.current_id: str | None = None
        self.current_widget: tk.Widget | None = None

    # --- Navigation ---

    def show(self, tool_id: str):
        """Affiche l'outil demandé (construction + cache avec défilement automatique, puis pack)."""
        tool = registry.get(tool_id)
        if tool is None:
            return
        if tool_id == self.current_id and self.current_widget is not None:
            return

        if self.current_widget is not None:
            self.current_widget.pack_forget()

        container = self._containers.get(tool_id)
        if container is None:
            scroll_frame = AutoScrollFrame(self, fit_width=True, fit_height=False, auto_hide=True)
            if tool.view is not None:
                view_widget = tool.view(self.shell)
            else:
                view_widget = self._build_launcher_card(scroll_frame.content, tool)

            if view_widget.master != scroll_frame.content:
                view_widget.pack(in_=scroll_frame.content, fill=tk.BOTH, expand=True)
            else:
                view_widget.pack(fill=tk.BOTH, expand=True)

            scroll_frame.bind_mousewheel_recursive(view_widget)
            container = scroll_frame
            self._containers[tool_id] = container
            self._views[tool_id] = view_widget

        container.pack(fill=tk.BOTH, expand=True)
        container.check_overflow()
        self.current_id = tool_id
        self.current_widget = container
        events.emit('tool.opened', tool_id)
        self.shell.on_tool_opened(tool_id)

    # --- Carte de lancement pour les outils en dialogue ---

    def _build_launcher_card(self, parent_widget, tool):
        """Carte d'accueil affichée quand l'outil ouvre un dialogue dédié."""
        card = ttk.Frame(parent_widget, style='Card.TFrame', padding=30)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        inner = ttk.Frame(card, style='Card.TFrame')
        inner.grid(row=0, column=0)
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text=f"{tool.icon}  {_(tool.name)}",
                  style='Card.TLabel', font=('Segoe UI', 20, 'bold')).grid(
            row=0, column=0, pady=(0, 12))

        ttk.Label(inner, text=_(tool.description),
                  style='Card.TLabel', font=('Segoe UI', 11), justify=tk.CENTER).grid(
            row=1, column=0, pady=(0, 8))

        if tool.shortcut:
            ttk.Label(inner, text=f"{_('Raccourci')} : {tool.shortcut}",
                      style='Card.TLabel', font=('Segoe UI', 9)).grid(
                row=2, column=0, pady=(0, 16))

        open_btn = ttk.Button(inner, text=f"{_('Ouvrir')} {_(tool.name)}",
                              style='AppPrimary.TButton',
                              command=lambda: self._invoke_open(tool))
        open_btn.grid(row=3, column=0, pady=(8, 0))
        tip = add_lazy_rich_tooltip(open_btn, ToolTipContent(
            title=tool.name,
            description=tool.description,
            shortcut=tool.shortcut,
            category=tool.category,
        ))
        self._attach_launcher_tip(tip)

        return card

    def _attach_launcher_tip(self, tip):
        """Conserve une référence au tooltip pour éviter le garbage collection."""
        self._tips.append(tip)

    def _invoke_open(self, tool):
        if tool.open is not None:
            tool.open(self.shell)

    # --- État ---

    @property
    def current_tool(self):
        if self.current_id is None:
            return None
        return registry.get(self.current_id)
