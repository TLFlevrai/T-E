# src/gui/controller/main_controller.py
"""
Contrôleur principal qui compose tous les sous-contrôleurs.
Utilise la composition plutôt que l'héritage pour combiner les fonctionnalités.
"""
from __future__ import annotations
from .base_controller import BaseController
from .folder_controller import FolderController
from .extraction_controller import ExtractionController
from .server_controller import ServerController
from .navigation_controller import NavigationController


class MainController(BaseController):
    """
    Contrôleur principal qui orchestre tous les sous-contrôleurs.
    
    Hérite de BaseController pour les méthodes communes,
    et délègue les responsabilités spécifiques aux sous-contrôleurs.
    """
    
    def __init__(self, root, ui_widgets, service=None):
        # Créer les sous-contrôleurs
        self._folder = FolderController(root, ui_widgets, service)
        self._extraction = ExtractionController(root, ui_widgets, service)
        self._server = ServerController(root, ui_widgets, service)
        self._navigation = NavigationController(root, ui_widgets, service)
        
        # Appeler super() pour initialiser BaseController
        super().__init__(root, ui_widgets, service)

    # --- Propriétés avec délégation ---
    
    @property
    def selected_folder(self):
        return self._folder.selected_folder
    
    @selected_folder.setter
    def selected_folder(self, value):
        self._folder.selected_folder = value
        self._extraction.selected_folder = value
    
    @property
    def selected_files(self):
        return self._extraction.selected_files
    
    @selected_files.setter
    def selected_files(self, value):
        self._extraction.selected_files = value
    
    @property
    def is_extracting(self):
        return self._extraction.is_extracting
    
    @is_extracting.setter
    def is_extracting(self, value):
        self._extraction.is_extracting = value
    
    # --- Délégation FolderController ---
    def browse_folder(self):
        self._folder.browse_folder()
        # Synchroniser avec extraction
        self._extraction.selected_folder = self._folder.selected_folder
    
    def select_recent_folder(self, folder_path):
        self._folder.select_recent_folder(folder_path)
        self._extraction.selected_folder = self._folder.selected_folder
    
    # --- Délégation ExtractionController ---
    def open_selection_dialog(self):
        self._extraction.open_selection_dialog()
        # Synchroniser les fichiers sélectionnés
        self.selected_files = self._extraction.selected_files
    
    def extract_code(self):
        self._extraction.extract_code()

    def cancel_extraction(self):
        """Demande l'annulation de l'extraction en cours."""
        self._extraction.cancel_extraction()
    
    def export_to_pdf(self):
        """Lance l'extraction et génère un PDF."""
        self._extraction.export_to_pdf()
    
    def set_extracting(self, extracting):
        """Active/désactive l'état d'extraction."""
        self._extraction.set_extracting(extracting)
    
    # --- Délégation ServerController ---
    def set_server(self, server):
        """Définit l'instance du serveur partagé."""
        self._server.set_server(server)
        self._navigation.set_server(server)  # Navigation en reçoit aussi une copie
    
    def set_discovery(self, discovery):
        """Définit l'instance du service de découverte partagé."""
        self._server.set_discovery(discovery)
        self._navigation.set_discovery(discovery)  # Navigation en reçoit aussi une copie
    
    def start_server(self):
        self._server.start_server()
    
    def stop_server(self):
        self._server.stop_server()
    
    def get_server(self):
        return self._server.get_server()
    
    def get_discovery(self):
        return self._server.get_discovery()
    
    # --- Délégation NavigationController ---
    def open_version_explorer(self):
        self._navigation.open_version_explorer()
    
    def open_network_center(self):
        self._navigation.open_network_center()