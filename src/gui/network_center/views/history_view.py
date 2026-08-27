# src/gui/network_center/views/history_view.py
import tkinter as tk
from tkinter import ttk
from typing import List
from ..models import SendHistoryEntry
from src.i18n import _


class HistoryView(ttk.Frame):
    """Vue historique des envois."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.entries: List[SendHistoryEntry] = []
        self._create_widgets()
    
    def _create_widgets(self):
        ttk.Label(self, text=_("Historique des envois :")).grid(row=0, column=0, sticky=tk.W, pady=(10, 0))
        
        self.text = tk.Text(self, height=4, width=70, state=tk.DISABLED, wrap=tk.WORD)
        self.text.grid(row=1, column=0, columnspan=2, pady=5)
        
        self.columnconfigure(0, weight=1)
    
    def add_entry(self, entry: SendHistoryEntry):
        self.entries.insert(0, entry)  # Plus récent en haut
        if len(self.entries) > 20:
            self.entries.pop()
        self._refresh_display()
    
    def _refresh_display(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        for entry in self.entries:
            self.text.insert(tk.END, entry.format_line() + "\n")
        self.text.config(state=tk.DISABLED)
        # Les entrées les plus récentes sont insérées en haut : montrer le haut.
        self.text.see('1.0')
    
    def clear(self):
        self.entries.clear()
        self._refresh_display()