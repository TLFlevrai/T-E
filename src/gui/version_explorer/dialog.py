# src/gui/version_explorer/dialog.py
from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, messagebox

from src.i18n import _, pgettext
from src.logger import setup_logger
from src.config import get_config
from src.services.version_service import VersionArchiveService
from ..base_dialog import BaseDialog
from .project_panel import ProjectPanel
from .version_tree import VersionTree
from .preview_pane import PreviewPane
from .toolbar import Toolbar
from .controller import VersionExplorerController

logger = setup_logger(__name__)


class VersionExplorerDialog(BaseDialog):
    """Fenetre de gestion des versions d'export."""

    def __init__(self, parent, service=None):
        super().__init__(
            parent,
            title=_("Gestionnaire de versions"),
            minsize=(800, 500),
        )

        self.config = get_config()
        self._setup_window_geometry()

        self.preview_entry = None

        self.controller = VersionExplorerController(
            service=service,
            on_status=self._marshal(self._set_status),
            on_projects_loaded=self._marshal(self._on_projects_loaded),
            on_error=self._marshal(self._show_error),
            on_info=self._marshal(self._show_info),
        )

        self._create_widgets()
        self.controller.start_scan()

        # Raccourci F5 pour rafraîchir
        self.bind("<F5>", lambda e: self.refresh())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window_geometry(self):
        """Restaure la géométrie de la fenêtre depuis la config."""
        gui = self.config.get_all().gui
        width = gui.version_window_width
        height = gui.version_window_height
        x = gui.version_window_x
        y = gui.version_window_y

        if x >= 0 and y >= 0:
            self.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.geometry(f"{width}x{height}")
            self.update_idletasks()
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")

    def _save_window_geometry(self):
        """Sauvegarde la géométrie actuelle de la fenêtre (valeurs bornées)."""
        try:
            width = max(600, min(1920, self.winfo_width()))
            height = max(400, min(1080, self.winfo_height()))
            x = max(-1, self.winfo_x())
            y = max(-1, self.winfo_y())
            self.config.update_gui(
                version_window_width=width,
                version_window_height=height,
                version_window_x=x,
                version_window_y=y,
            )
        except Exception:
            logger.debug("Erreur lors de la sauvegarde de la géométrie de la fenêtre", exc_info=True)
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.project_panel = ProjectPanel(main, self._on_project_selected)

        right_pane = ttk.Frame(main)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.version_tree = VersionTree(right_pane, self._on_versions_selected, self._on_version_double_click)

        self.preview_pane = PreviewPane(right_pane)

        self.toolbar = Toolbar(right_pane, self)

        self.status_var = tk.StringVar(value=_("Scan en cours..."))
        status_label = ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    # --- Callbacks du contrôleur ---

    def _marshal(self, func):
        """Exécute le callback sur le thread principal de Tkinter.

        La vérification d'existence se fait DANS le callback planifié (thread
        UI) : l'appeler depuis le thread worker puis faire after() laisse une
        fenêtre où le dialogue peut être détruit entre les deux.
        """
        def wrapper(*args):
            def run():
                if self.winfo_exists():
                    func(*args)
            try:
                self.after(0, run)
            except tk.TclError:
                pass
        return wrapper

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _show_info(self, title, msg):
        self.show_info(title, msg)

    def _show_error(self, title, msg):
        self.show_error(title, msg)

    def _on_projects_loaded(self, projects_data):
        self.controller.projects_data = projects_data
        self.project_panel.update_projects(projects_data)
        if self.controller.current_project in projects_data:
            self._on_project_selected(self.controller.current_project)
        else:
            if projects_data:
                first = list(projects_data.keys())[0]
                self._on_project_selected(first)
            else:
                self.version_tree.clear()
                self.preview_pane.show_entry(None)

    # --- Sélection ---

    def _on_project_selected(self, project_name):
        self.controller.current_project = project_name
        entries = self.controller.projects_data.get(project_name, [])
        self.version_tree.populate(entries)
        self.preview_pane.show_entry(None)
        self.status_var.set(_("Projet : {} ({} versions)").format(project_name, len(entries)))

    def _on_versions_selected(self, selected_entries):
        if selected_entries:
            self.preview_entry = selected_entries[0]
            self.preview_pane.show_entry(selected_entries[0])
        else:
            self.preview_entry = None
            self.preview_pane.show_entry(None)

    def _on_version_double_click(self, entry):
        try:
            os.startfile(str(entry.path))
        except Exception as e:
            logger.error("Impossible d'ouvrir %s : %s", entry.path, e)
            self.show_error(_("Erreur"), _("Impossible d'ouvrir le fichier : {}").format(e))

    # --- Actions ---

    def archive_selected(self):
        entries = self.version_tree.get_selected_entries()
        if not entries:
            self.show_info(_("Information"), _("Aucune version selectionnee."))
            return
        to_archive = [e for e in entries if e.status == 'active']
        if not to_archive:
            self.show_info(_("Information"), _("Les versions selectionnees sont deja archivees."))
            return
        if not self.confirm(_("Confirmation"),
                            pgettext("confirmation", "Archiver {} version(s) ?").format(len(to_archive))):
            return
        self.controller.archive_selected(to_archive)

    def restore_selected(self):
        entries = self.version_tree.get_selected_entries()
        if not entries:
            self.show_info(_("Information"), _("Aucune version selectionnee."))
            return
        to_restore = [e for e in entries if e.status == 'archived']
        if not to_restore:
            self.show_info(_("Information"), _("Les versions selectionnees sont deja actives."))
            return
        if not self.confirm(_("Confirmation"),
                            pgettext("confirmation", "Restaurer {} version(s) ?").format(len(to_restore))):
            return
        self.controller.restore_selected(to_restore)

    def delete_selected(self):
        entries = self.version_tree.get_selected_entries()
        if not entries:
            self.show_info(_("Information"), _("Aucune version selectionnee."))
            return
        if not self.confirm(_("Confirmation"),
                            pgettext("confirmation", "Supprimer definitivement {} version(s) ? Cette action est irreversible.").format(len(entries))):
            return
        self.controller.delete_selected(entries)

    def reset_counter(self):
        if not self.controller.current_project:
            self.show_info(_("Information"), _("Aucun projet selectionne."))
            return
        if not self.confirm(_("Confirmation"),
                            pgettext("confirmation", "Reinitialiser le compteur de versions pour le projet '{}' ?").format(self.controller.current_project)):
            return
        self.controller.reset_counter(self.controller.current_project)

    def open_folder(self):
        if not self.controller.current_project:
            self.show_info(_("Information"), _("Aucun projet selectionne."))
            return
        folder = self.controller.get_output_dir()
        if not folder.exists():
            self.show_error(_("Erreur"), _("Le dossier de sortie n'existe pas."))
            return
        try:
            os.startfile(str(folder))
        except Exception as e:
            logger.error("Impossible d'ouvrir %s : %s", folder, e)
            self.show_error(_("Erreur"), _("Impossible d'ouvrir le dossier : {}").format(e))

    def clean_all(self):
        """Supprime tout le contenu du dossier out/ y compris les archives."""
        if not self.confirm(
            _("Confirmation nettoyage complet"),
            _("ATTENTION : Cette action va supprimer TOUS les fichiers d'export dans le dossier 'out/' "
              "y compris les versions archivées.\n\nCette action est IRREVERSIBLE.\n\nContinuer ?"),
            icon=messagebox.WARNING,
        ):
            return

        if not self.confirm(
            _("Confirmation finale"),
            _("Êtes-vous ABSOLUMENT sûr de vouloir tout supprimer ?\n\n"
              "Tous les projets, toutes les versions, toutes les archives seront perdus."),
            icon=messagebox.WARNING,
        ):
            return

        self.controller.clean_all()

    def refresh(self):
        self.controller.refresh()

    def select_all(self):
        self.version_tree.select_all()

    def deselect_all(self):
        self.version_tree.deselect_all()

    def _on_close(self):
        self._save_window_geometry()
        self.destroy()