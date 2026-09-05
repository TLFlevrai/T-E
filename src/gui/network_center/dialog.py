# src/gui/network_center/dialog.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from src.i18n import _
from src.logger import setup_logger
from ..base_dialog import BaseDialog
from .status_tab import StatusTab
from .send_tab import SendTab
from .received_tab import ReceivedTab
from .log_tab import LogTab

logger = setup_logger(__name__)


class NetworkCenterDialog(BaseDialog):
    def __init__(self, parent, controller, server=None, discovery=None):
        super().__init__(
            parent,
            title=_("Centre réseau"),
            geometry="850x650",
            minsize=(750, 550),
        )

        self.controller = controller  # MainController (a get_server/start_server)
        self.server = server
        self.discovery = discovery
        self.output_dir = controller.service.output_dir if controller and hasattr(controller, 'service') else None

        self._create_widgets()
        self._subscribe_to_server()

        # Chargements paresseux : ne scanner le réseau / lister les fichiers
        # que lorsqu'un onglet concerné est réellement affiché (l'ouverture
        # du centre réseau ne doit pas déclencher de broadcast inutile).
        self._lazy_loaded_tabs = set()
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        self._on_tab_changed()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Passer self.controller (MainController) qui a get_server()
        self.status_tab = StatusTab(notebook, self, self.controller)
        self.send_tab = SendTab(notebook, self, self.discovery, self.output_dir, lazy=True)
        self.received_tab = ReceivedTab(notebook, self, self.output_dir)
        self.log_tab = LogTab(notebook, self)

        notebook.add(self.status_tab, text=_("État du serveur"))
        notebook.add(self.send_tab, text=_("Envoyer"))
        notebook.add(self.received_tab, text=_("Fichiers reçus"))
        notebook.add(self.log_tab, text=_("Journal réseau"))

        self.notebook = notebook

    def _on_tab_changed(self, _event=None):
        try:
            current = self.notebook.nametowidget(self.notebook.select())
        except Exception:
            return
        if current is self.send_tab and 'send' not in self._lazy_loaded_tabs:
            self._lazy_loaded_tabs.add('send')
            self.send_tab.initial_load()

    def _subscribe_to_server(self):
        if self.server:
            self.server.add_observer(self._on_server_event)

    def _on_server_event(self, event_type, data):
        """Appelé dans le thread du serveur → rediriger vers l'UI via after."""
        self.after(0, lambda: self._dispatch_event(event_type, data))

    def _dispatch_event(self, event_type, data):
        # Statut
        if hasattr(self, 'status_tab'):
            self.status_tab.on_event(event_type, data)
        # Journal
        if hasattr(self, 'log_tab'):
            self.log_tab.on_event(event_type, data)
        # Received tab peut aussi réagir (rafraîchir)
        if event_type == 'file_received' and hasattr(self, 'received_tab'):
            self.received_tab.on_file_received(data)

    def _on_close(self):
        if self.server:
            self.server.remove_observer(self._on_server_event)
        self.destroy()