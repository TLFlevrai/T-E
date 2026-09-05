# src/gui/selection/search.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from src.i18n import _

class SearchBar:
    def __init__(self, parent, tree, all_items):
        self.tree = tree
        self.all_items = list(all_items)
        # Hiérarchie d'origine capturée AVANT tout détachement : une fois un
        # item détaché, tree.parent(item) renvoie '' et une restauration basée
        # sur cet appel aplatirait toute l'arborescence au niveau racine.
        self._original_parent = {}
        if tree is not None:
            for item in self.all_items:
                try:
                    self._original_parent[item] = tree.parent(item)
                except tk.TclError:
                    pass
        self.var = tk.StringVar()
        # Utilisation de trace_add (moderne) au lieu de trace
        self.var.trace_add('write', self._on_search_change)

        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(frame, text=_("Rechercher :")).pack(side=tk.LEFT, padx=(0, 5))
        entry = ttk.Entry(frame, textvariable=self.var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.focus_set()

        self.entry = entry

    def _on_search_change(self, *args):
        if self.tree is None:
            return
        pattern = self.var.get().strip().lower()
        if not pattern:
            # Restaure la hiérarchie d'origine (parent capturé avant détachement)
            for item in self.all_items:
                parent = self._original_parent.get(item, '')
                try:
                    self.tree.reattach(item, parent, 'end')
                except tk.TclError:
                    pass
            return
        for item in self.all_items:
            try:
                text = self.tree.item(item, "text").lower()
            except tk.TclError:
                continue
            parent = self._original_parent.get(item, '')
            try:
                if pattern in text:
                    self.tree.reattach(item, parent, 'end')
                else:
                    self.tree.detach(item)
            except tk.TclError:
                pass