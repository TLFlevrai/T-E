# src/gui/controller/folder_controller.py
from __future__ import annotations
import os
from tkinter import filedialog
from .base_controller import BaseController
from ..errors import show_error
from src.gui.folder_scanner import scan_folder
from src.gui.recent_files import add_recent_folder, remove_recent_folder
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

class FolderController(BaseController):
    """Gestion du dossier sélectionné et des emplacements récents."""
    
    def browse_folder(self):
        """Ouvre un dialogue pour sélectionner un dossier."""
        folder = filedialog.askdirectory(
            title=_("Sélectionner un dossier contenant des fichiers Python/JSON/TXT/PO/MO/HTML/CSS/JS")
        )
        if not folder:
            return

        self._set_folder(folder)
        self.reset_selection()
        self._log_folder_stats()

    def choose_output_dir(self):
        """Ouvre un dialogue pour choisir le dossier de sortie personnalisé."""
        folder = filedialog.askdirectory(
            title=_("Choisir le dossier où créer le sous-dossier 'out' pour les extractions")
        )
        if not folder:
            return
        
        self.ui.custom_output_dir.set(folder)
        self._update_output_dir_label()
        self.add_info(_("Dossier de sortie personnalisé : {}").format(folder))

    def clear_output_dir(self):
        """Efface le dossier de sortie personnalisé (retour au dossier par défaut)."""
        self.ui.custom_output_dir.set("")
        self._update_output_dir_label()
        self.add_info(_("Dossier de sortie personnalisé effacé (retour au dossier par défaut)"))

    def _update_output_dir_label(self):
        """Met à jour l'affichage du dossier de sortie personnalisé."""
        custom = self.ui.custom_output_dir.get().strip()
        if custom:
            self.ui.output_dir_label.config(text=_("Sortie : {}/out").format(custom))
        else:
            self.ui.output_dir_label.config(text=_("Sortie : dossier par défaut (projet/out)"))

    def select_recent_folder(self, folder_path):
        """Sélectionne un dossier depuis les emplacements récents."""
        if not os.path.exists(folder_path):
            show_error(_("Erreur"), _("Le dossier n'existe plus : {}").format(folder_path), parent=self.root)
            remove_recent_folder(folder_path)
            if self.ui.update_recent_menu:
                self.ui.update_recent_menu()
            return

        self._set_folder(folder_path)
        self.reset_selection()
        self._log_folder_stats()
        self.add_info(_("Dossier récent sélectionné : {}").format(folder_path))

    def _set_folder(self, folder):
        """Définit le dossier sélectionné et met à jour l'UI."""
        self._selected_folder = folder
        self.ui.folder_path_var.set(folder)
        self.ui.extract_btn.config(state='normal')
        self.clear_info()
        # Session restore : mémoriser le dernier dossier
        try:
            from src.config import get_config
            get_config().update_gui(last_folder=folder)
        except Exception:
            logger.debug("Erreur lors de la sauvegarde du dernier dossier", exc_info=True)

    def _log_folder_stats(self):
        """Affiche les statistiques du dossier dans le journal."""
        self.add_info(_("Dossier sélectionné : {}").format(self._selected_folder))

        stats = scan_folder(self._selected_folder, self.ui)
        self.add_info(_("Fichiers trouvés : {}").format(stats['total']))
        for ext, count in stats['types'].items():
            if count > 0:
                self.add_info(_("  - Fichiers {} : {}").format(ext.upper(), count))