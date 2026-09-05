# src/gui/network_center/views/file_list_view.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional
from ..models import FileItem
from src.i18n import _


class FileListView(ttk.Frame):
    """Vue liste des fichiers envoyables."""
    
    def __init__(self, parent, on_selection_change: Callable[[Optional[FileItem]], None]):
        super().__init__(parent)
        self.on_selection_change = on_selection_change
        self.items_map: List[FileItem] = []
        self._create_widgets()
    
    def _create_widgets(self):
        ttk.Label(self, text=_("Fichiers disponibles dans out/ :")).grid(row=0, column=0, sticky=tk.W)
        
        self.listbox = tk.Listbox(self, height=8, width=70)
        self.listbox.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.listbox.yview)
        scroll.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.listbox.config(yscrollcommand=scroll.set)
        
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        self.columnconfigure(0, weight=1)
    
    def populate(self, items: List[FileItem]):
        self.listbox.delete(0, tk.END)
        self.items_map = items
        for item in items:
            self.listbox.insert(tk.END, item.display_name)
    
    def _on_select(self, event):
        sel = self.listbox.curselection()
        item = self.items_map[sel[0]] if sel else None
        self.on_selection_change(item)
    
    def get_selected(self) -> Optional[FileItem]:
        sel = self.listbox.curselection()
        return self.items_map[sel[0]] if sel else None
    
    def refresh(self):
        self.listbox.selection_clear(0, tk.END)
        self.on_selection_change(None)