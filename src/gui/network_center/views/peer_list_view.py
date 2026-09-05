# src/gui/network_center/views/peer_list_view.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional
from ..models import Peer
from src.i18n import _


class PeerListView(ttk.Frame):
    """Vue liste des pairs découverts."""
    
    def __init__(self, parent, on_selection_change: Callable[[Optional[Peer]], None]):
        super().__init__(parent)
        self.on_selection_change = on_selection_change
        self.items_map: List[Peer] = []
        self._create_widgets()
    
    def _create_widgets(self):
        ttk.Label(self, text=_("PC disponibles sur le réseau :")).grid(row=0, column=0, sticky=tk.W, pady=(10, 0))
        
        self.listbox = tk.Listbox(self, height=6, width=70)
        self.listbox.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.listbox.yview)
        scroll.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.listbox.config(yscrollcommand=scroll.set)
        
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        self.columnconfigure(0, weight=1)
    
    def populate(self, peers: List[Peer]):
        self.listbox.delete(0, tk.END)
        self.items_map = peers
        for peer in peers:
            self.listbox.insert(tk.END, peer.display_name)
    
    def _on_select(self, event):
        sel = self.listbox.curselection()
        peer = self.items_map[sel[0]] if sel else None
        self.on_selection_change(peer)
    
    def get_selected(self) -> Optional[Peer]:
        sel = self.listbox.curselection()
        return self.items_map[sel[0]] if sel else None