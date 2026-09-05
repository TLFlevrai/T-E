# src/gui/controller/base_controller.py
from __future__ import annotations
import tkinter as tk
from typing import List, Optional
from src.services.extraction_service import ExtractionService
from src.logger import setup_logger
from src.i18n import _
from ..ui_builder.ui_widgets import UIWidgets

logger = setup_logger(__name__)


class BaseController:
    """Classe de base contenant les dépendances partagées."""

    def __init__(self, root, ui_widgets: UIWidgets, service: Optional[ExtractionService] = None):
        self.root = root
        self.ui = ui_widgets
        if service is None:
            logger.warning(
                "BaseController créé sans ExtractionService — "
                "le service sera créé proprement par le sous-contrôleur."
            )
            service = ExtractionService()
        self.service = service
        # Utiliser un attribut privé pour éviter les conflits avec les setters
        self._selected_folder = ""
        self.selected_files: List[str] = []
        self._is_extracting = False
        self.ui.controller = self

    @property
    def selected_folder(self) -> str:
        return self._selected_folder

    @selected_folder.setter
    def selected_folder(self, value: str):
        self._selected_folder = value

    @property
    def is_extracting(self) -> bool:
        return self._is_extracting

    @is_extracting.setter
    def is_extracting(self, value: bool):
        self._is_extracting = value

    def add_info(self, message: str):
        """Ajoute un message au journal via LogWidget."""
        if hasattr(self.ui, 'log_widget'):
            self.ui.log_widget.add_info(message)
        else:
            logger.warning("log_widget non disponible — message : %s", message)

    def clear_info(self):
        """Efface le journal via LogWidget."""
        if hasattr(self.ui, 'log_widget'):
            self.ui.log_widget.clear_info()
        else:
            logger.warning("log_widget non disponible — clear ignored")

    def update_status(self, message: str, detail: Optional[str] = None):
        """Met à jour la barre de statut via LogWidget."""
        if hasattr(self.ui, 'log_widget'):
            self.ui.log_widget.update_status(message, detail)
        else:
            logger.warning("log_widget non disponible — status : %s", message)

    def set_extracting(self, extracting: bool):
        """Active/désactive l'état d'extraction."""
        self._is_extracting = extracting
        state = 'disabled' if extracting else 'normal'
        self.ui.extract_btn.config(state=state)
        # Bouton Annuler : actif uniquement pendant l'extraction
        if hasattr(self.ui, 'cancel_btn') and self.ui.cancel_btn is not None:
            cancel_state = 'normal' if extracting else 'disabled'
            self.ui.cancel_btn.config(state=cancel_state)

    def get_include_options(self) -> dict:
        """Retourne les options d'inclusion (pour la boîte de dialogue de sélection)."""
        return {
            'include_json': self.ui.include_json.get(),
            'include_txt': self.ui.include_txt.get(),
            'include_po': self.ui.include_po.get(),
            'include_mo': self.ui.include_mo.get(),
            'include_html': self.ui.include_html.get(),
            'include_css': self.ui.include_css.get(),
            'include_js': self.ui.include_js.get(),
            'ignore_git': self.ui.ignore_git.get(),         # NOUVEAU
            'ignore_pycache': self.ui.ignore_pycache.get()  # NOUVEAU
        }

    def get_extraction_options(self) -> dict:
        """Retourne toutes les options d'extraction (pour le moteur d'extraction)."""
        return {
            'include_json': self.ui.include_json.get(),
            'include_subdirs': self.ui.include_subdirs.get(),
            'show_file_paths': self.ui.show_file_paths.get(),
            'include_structure': self.ui.include_structure.get(),
            'include_txt': self.ui.include_txt.get(),
            'include_po': self.ui.include_po.get(),
            'include_mo': self.ui.include_mo.get(),
            'include_html': self.ui.include_html.get(),
            'include_css': self.ui.include_css.get(),
            'include_js': self.ui.include_js.get(),
            'ignore_init': self.ui.ignore_init.get(),
            'ignore_git': self.ui.ignore_git.get(),
            'ignore_pycache': self.ui.ignore_pycache.get(),
            'include_statistics': self.ui.include_statistics.get(),
            'include_file_metadata': self.ui.include_file_metadata.get(),
            'archive_old': self.ui.archive_old.get()
        }

    def reset_selection(self):
        """Réinitialise la sélection de fichiers."""
        self.selected_files = []
        self.update_status(_("Prêt"))