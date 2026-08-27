# src/gui/version_explorer/version_tree.py
import tkinter as tk
from tkinter import ttk
from typing import Callable, List
from src.i18n import _
from src.utils import human_size
from src.services.version_service import VersionEntry


class VersionTree:
    """Table des versions avec colonnes et sélection multiple."""

    def __init__(
        self,
        parent,
        on_version_select: Callable[[List[VersionEntry]], None],
        on_version_double_click: Callable[[VersionEntry], None],
    ):
        self.on_version_select = on_version_select
        self.on_version_double_click = on_version_double_click
        self.current_entries = []
        self.selected_items = set()  # pour suivre les IID sélectionnés
        self._entry_map = {}  # iid -> VersionEntry

        self.tree = ttk.Treeview(
            parent,
            columns=('version', 'date', 'size', 'files', 'lines', 'status'),
            show='tree headings',
            selectmode='extended'  # sélection multiple
        )
        self.tree.heading('#0', text=_('Sélection'))
        self.tree.heading('version', text=_('Version'))
        self.tree.heading('date', text=_('Date'))
        self.tree.heading('size', text=_('Taille'))
        self.tree.heading('files', text=_('Fichiers'))
        self.tree.heading('lines', text=_('Lignes'))
        self.tree.heading('status', text=_('Statut'))

        self.tree.column('#0', width=80, anchor='center')
        self.tree.column('version', width=80, anchor='center')
        self.tree.column('date', width=150, anchor='w')
        self.tree.column('size', width=100, anchor='e')
        self.tree.column('files', width=80, anchor='center')
        self.tree.column('lines', width=80, anchor='center')
        self.tree.column('status', width=100, anchor='w')

        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)

        # Scrollbar
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        # Pack
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def populate(self, entries):
        """Remplit le treeview avec les entrées d'un projet."""
        self.clear()
        self.current_entries = sorted(entries, key=lambda e: e.version, reverse=True)
        for entry in self.current_entries:
            # Sélection par défaut (non sélectionné)
            select_char = '☐'
            item = self.tree.insert(
                '', 
                'end', 
                text=select_char,  # La colonne #0 est définie par 'text'
                values=(
                    f"v{entry.version}",
                    entry.date,
                    human_size(entry.size),
                    entry.file_count,
                    entry.line_count,
                    _(entry.status.capitalize())
                )
            )
            # Stocker l'entry associée à l'item
            self._entry_map[item] = entry

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_entries = []
        self.selected_items.clear()
        self._entry_map.clear()

    def _on_select(self, event):
        selected_iids = set(self.tree.selection())
        # Mettre à jour les glyphes : on garde les sélectionnés avec ☑
        self._sync_glyphs(selected_iids)
        # Appeler le callback avec la liste des entrées sélectionnées
        self.on_version_select(self._entries_for(self.tree.selection()))

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            entry = self._entry_map.get(item)
            if entry:
                self.on_version_double_click(entry)

    def get_selected_entries(self):
        """Retourne la liste des VersionEntry sélectionnés (cochés)."""
        selected = []
        for iid in self.selected_items: 
            entry = self._entry_map.get(iid)
            if entry:
                selected.append(entry)
        return selected

    def get_all_entries(self):
        return self.current_entries

    def select_all(self):
        """Sélectionne toutes les versions en une seule opération.

        selection_set avec tous les iids génère un seul événement
        <<TreeviewSelect>> : les glyphes et le callback sont donc mis à jour
        une seule fois (au lieu de n×mises à jour avec selection_add par item).
        """
        all_items = list(self.tree.get_children())
        if not all_items:
            self.on_version_select([])
            return
        self.tree.selection_set(all_items)
        # _on_select est déclenché par l'événement ; on force quand même
        # l'état cohérent si l'événement ne s'est pas propagé.
        if self.tree.selection() != tuple(all_items):
            self._sync_glyphs(set(all_items))
            self.on_version_select(self._entries_for(all_items))

    def deselect_all(self):
        all_items = list(self.tree.get_children())
        self.tree.selection_remove(all_items)
        if self.tree.selection():
            self._sync_glyphs(set())
            self.on_version_select([])

    # --- Helpers internes ---

    def _sync_glyphs(self, selected_iids: set):
        """Met à jour les glyphes ☑/☐ de toutes les lignes en un passage."""
        for item in self.tree.get_children():
            if item in selected_iids:
                self.tree.item(item, text='☑')
                self.selected_items.add(item)
            else:
                self.tree.item(item, text='☐')
                self.selected_items.discard(item)

    def _entries_for(self, iids):
        return [self._entry_map[iid] for iid in iids if iid in self._entry_map]

    def refresh(self):
        # Repeupler avec les mêmes entrées (les métadonnées peuvent avoir changé)
        entries = self.current_entries
        self.populate(entries)