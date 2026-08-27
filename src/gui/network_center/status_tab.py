# src/gui/network_center/status_tab.py
import tkinter as tk
from tkinter import ttk
from src.i18n import _
from src.network.utils import get_local_ip


class StatusTab(ttk.Frame):
    def __init__(self, parent, dialog, controller):
        super().__init__(parent)
        self.dialog = dialog
        self.controller = controller  # MainController (a get_server/get_discovery)
        self.server = controller.get_server() if hasattr(controller, 'get_server') else None
        self.received_count = 0
        self.last_received = ""

        self._create_widgets()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # État
        self.status_label = ttk.Label(main, text=_("État : Inconnu"))
        self.status_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.host_label = ttk.Label(main, text=_("Hôte : -"))
        self.host_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        self.port_label = ttk.Label(main, text=_("Port : -"))
        self.port_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        self.ip_label = ttk.Label(main, text=_("IP locale : {}").format(get_local_ip()))
        self.ip_label.grid(row=3, column=0, sticky=tk.W, pady=2)

        # BOUTONS START/STOP SUPPRIMÉS - Cycle de vie géré par l'application
        # Affichage info seulement

        # Compteur
        ttk.Label(main, text=_("Fichiers reçus depuis le lancement :")).grid(row=5, column=0, sticky=tk.W, pady=(15, 0))
        self.count_var = tk.StringVar(value="0")
        ttk.Label(main, textvariable=self.count_var).grid(row=6, column=0, sticky=tk.W)

        ttk.Label(main, text=_("Dernier reçu :")).grid(row=7, column=0, sticky=tk.W, pady=(10, 0))
        self.last_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.last_var).grid(row=8, column=0, sticky=tk.W)

        # Separator
        ttk.Separator(main, orient='horizontal').grid(row=9, column=0, sticky=tk.EW, pady=15)

        # Info sur les fichiers reçus
        ttk.Label(main, text=_("Les fichiers reçus sont stockés dans out/received/")).grid(row=10, column=0, sticky=tk.W)

        # Mise à jour initiale
        self._update_status()

    def _update_status(self):
        """Met à jour l'affichage de l'état du serveur (lecture seule)."""
        server = self.controller.get_server() if hasattr(self.controller, 'get_server') else None
        is_running = server and server.is_alive()
        
        if is_running:
            host = getattr(server, 'host', '?')
            port = getattr(server, 'port', '?')
            self.status_label.config(text=_("État : Démarré"))
            self.host_label.config(text=_("Hôte : {}").format(host))
            self.port_label.config(text=_("Port : {}").format(port))
        else:
            self.status_label.config(text=_("État : Arrêté"))
            self.host_label.config(text=_("Hôte : -"))
            self.port_label.config(text=_("Port : -"))

    # MÉTHODES SUPPRIMÉES : _update_buttons, _start_server, _stop_server

    def on_event(self, event_type, data):
        """Reçoit les événements du serveur."""
        if event_type == 'started':
            self._update_status()
        elif event_type == 'stopped':
            self._update_status()
        elif event_type == 'file_received':
            self.received_count += 1
            self.count_var.set(str(self.received_count))
            filename = data.get('filename', '')
            if filename:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.last_var.set(f"{timestamp} - {filename}")