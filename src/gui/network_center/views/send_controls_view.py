# src/gui/network_center/views/send_controls_view.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable
from src.i18n import _


class SendControlsView(ttk.Frame):
    """Vue contrôles d'envoi : boutons, progression, statut."""
    
    def __init__(
        self,
        parent,
        on_send: Callable[[], None],
        on_refresh_files: Callable[[], None],
        on_scan_network: Callable[[], None]
    ):
        super().__init__(parent)
        self._create_widgets(on_send, on_refresh_files, on_scan_network)
    
    def _create_widgets(self, on_send, on_refresh_files, on_scan_network):
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=10)
        
        self.send_btn = ttk.Button(btn_frame, text=_("Envoyer"), command=on_send, state='disabled')
        self.send_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text=_("Rafraîchir la liste"), command=on_refresh_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=_("Scanner le réseau"), command=on_scan_network).pack(side=tk.LEFT, padx=5)
        
        # Progression
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Statut
        self.status_var = tk.StringVar(value=_("Prêt"))
        ttk.Label(self, textvariable=self.status_var).grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        self.columnconfigure(0, weight=1)
    
    def set_send_enabled(self, enabled: bool):
        self.send_btn.config(state='normal' if enabled else 'disabled')
    
    def set_progress(self, value: float):
        self.progress_var.set(value)
    
    def set_status(self, text: str):
        self.status_var.set(text)
    
    def reset(self):
        self.progress_var.set(0)
        self.status_var.set(_("Prêt"))
        self.set_send_enabled(False)