# src/gui/version_explorer/project_panel.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List
from src.i18n import _
from src.services.version_service import VersionEntry


class ProjectPanel:
    """Panneau gauche affichant la liste des projets avec compteurs."""

    def __init__(self, parent, on_project_select: Callable[[str], None]):
        self.on_project_select = on_project_select
        self.projects: Dict[str, List[VersionEntry]] = {}  # nom_projet -> entrées

        frame = ttk.LabelFrame(parent, text=_("Projets"), padding=5)
        frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Listbox avec scrollbar
        self.listbox = tk.Listbox(frame, height=20, width=25)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.listbox.bind('<<ListboxSelect>>', self._on_select)

    def update_projects(self, projects: Dict[str, List[VersionEntry]]):
        """Met à jour la liste des projets."""
        self.projects = projects
        self.listbox.delete(0, tk.END)
        for project, entries in projects.items():
            count = len(entries)
            display = f"{project} ({count})"
            self.listbox.insert(tk.END, display)

    def _on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            project_name = list(self.projects.keys())[index]
            self.on_project_select(project_name)

    def get_selected_project(self):
        """Retourne le nom du projet sélectionné, ou None."""
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            return list(self.projects.keys())[idx]
        return None