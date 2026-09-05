# src/gui/controller/server_controller.py
from __future__ import annotations
from .base_controller import BaseController
from src.logger import setup_logger

logger = setup_logger(__name__)


class ServerController(BaseController):
    """Gestion du serveur réseau (démarrage/arrêt) - Utilise instance injectée."""
    
    def __init__(self, root, ui_widgets, service=None):
        super().__init__(root, ui_widgets, service)
        self.server = None
        self.discovery = None

    def set_server(self, server):
        """Définit l'instance du serveur partagé (injectée par l'application)."""
        self.server = server

    def set_discovery(self, discovery):
        """Définit l'instance du service de découverte partagé."""
        self.discovery = discovery

    # MÉTHODES SUPPRIMÉES : start_server(), stop_server()
    # Le cycle de vie est géré par main.py / Application

    def get_server(self):
        """Retourne l'instance du serveur."""
        return self.server

    def get_discovery(self):
        """Retourne l'instance du service de découverte."""
        return self.discovery