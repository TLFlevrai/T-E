# src/gui/controller/navigation_controller.py
from __future__ import annotations
from .base_controller import BaseController
from ..errors import show_error
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

class NavigationController(BaseController):
    """Ouverture des dialogues (version explorer, réseau center)."""
    
    def __init__(self, root, ui_widgets, service=None):
        super().__init__(root, ui_widgets, service)
        self.server = None
        self.discovery = None

    def set_server(self, server):
        """Définit l'instance du serveur partagé."""
        self.server = server

    def set_discovery(self, discovery):
        """Définit l'instance du service de découverte partagé."""
        self.discovery = discovery

    def open_version_explorer(self):
        """Ouvre le gestionnaire de versions."""
        try:
            from src.gui.version_explorer import VersionExplorerDialog
            VersionExplorerDialog(self.root)
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture du gestionnaire de versions : {e}")
            show_error(_("Erreur"), _("Impossible d'ouvrir le gestionnaire de versions : {}").format(e), parent=self.root)

    def open_network_center(self):
        """Ouvre le tableau de bord réseau."""
        try:
            from src.gui.network_center import NetworkCenterDialog
            # Passer self comme contrôleur (pour que les onglets puissent appeler)
            # MAIS il faut passer le MainController qui a start_server()
            # On va chercher le contrôleur parent via self.ui.controller
            main_controller = getattr(self.ui, 'controller', None)
            if main_controller:
                NetworkCenterDialog(self.root, main_controller, self.server, self.discovery)
            else:
                # Fallback: passer self (mais start_server ne sera pas disponible)
                NetworkCenterDialog(self.root, self, self.server, self.discovery)
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture du centre réseau : {e}")
            show_error(_("Erreur"), _("Impossible d'ouvrir le centre réseau : {}").format(e), parent=self.root)