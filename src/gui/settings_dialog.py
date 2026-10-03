# src/gui/settings_dialog.py
"""Boîte de dialogue des paramètres avec onglets."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from src.i18n import _
from src.config import get_config
from .base_dialog import BaseDialog
from .settings import FormatsTab, FiltersTab, ExtensionsTab, OutputTab, AdvancedTab


class SettingsDialog(BaseDialog):
    """Dialogue des paramètres : Formats, Extensions, Filtres, Sortie, Avancé."""

    def __init__(self, parent, ui_widgets):
        super().__init__(
            parent,
            title=_("Paramètres"),
            geometry="550x500",
            minsize=(500, 450),
        )

        self.ui = ui_widgets
        self.config = get_config()
        self._original_options = {}

        self._create_widgets()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Notebook (onglets)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # --- Onglet Formats ---
        self.formats_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.formats_frame, text=_("Formats"))
        self.formats_tab = FormatsTab(self.formats_frame, self)

        # --- Onglet Extensions avancées ---
        self.extensions_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.extensions_frame, text=_("Extensions"))
        self.extensions_tab = ExtensionsTab(self.extensions_frame, self)

        # --- Onglet Filtres ---
        self.filters_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.filters_frame, text=_("Filtres"))
        self.filters_tab = FiltersTab(self.filters_frame, self)

        # --- Onglet Sortie ---
        self.output_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.output_frame, text=_("Sortie"))
        self.output_tab = OutputTab(self.output_frame, self)

        # --- Onglet Avancé (après Extensions : il pilote ces cases) ---
        self.advanced_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.advanced_frame, text=_("Avancé"))
        self.advanced_tab = AdvancedTab(self.advanced_frame, self)

        # Boutons bas
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text=_("Restaurer défauts"), command=self._reset_defaults).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text=_("Annuler"), command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_("OK"), command=self._on_ok).pack(side=tk.RIGHT, padx=5)

    def _reset_defaults(self):
        """Restaure les valeurs par défaut."""
        if messagebox.askyesno(_("Confirmation"), _("Restaurer tous les paramètres par défaut ?")):
            cfg = self.config.get_all()
            extraction = cfg.extraction

            defaults = {
                'include_json': extraction.include_json,
                'include_subdirs': extraction.include_subdirs,
                'show_file_paths': extraction.show_file_paths,
                'include_structure': extraction.include_structure,
                'include_txt': extraction.include_txt,
                'include_md': extraction.include_md,
                'include_po': extraction.include_po,
                'include_mo': extraction.include_mo,
                'include_html': extraction.include_html,
                'include_css': extraction.include_css,
                'include_js': extraction.include_js,
                'ignore_init': extraction.ignore_init,
                'ignore_git': extraction.ignore_git,
                'ignore_pycache': extraction.ignore_pycache,
                'include_statistics': extraction.include_statistics,
                'include_file_metadata': extraction.include_file_metadata,
                'archive_old': cfg.gui.archive_old if hasattr(cfg.gui, 'archive_old') else False,
            }

            for key, value in defaults.items():
                var = getattr(self.ui, key, None)
                if var:
                    var.set(value)

            self.advanced_tab.log_height_var.set(12)
            self.advanced_tab.log_autoscroll_var.set(True)
            self.advanced_tab.preset_var.set('custom')

            # Extensions avancées : « Restaurer défauts » doit aussi
            # décocher les cases, sinon la config sauvegardée garderait des
            # extensions que l'onglet affiche comme désactivées.
            self._reset_extraction_defaults()

    def _reset_extraction_defaults(self):
        """Décoche les cases d'extensions avancées (défaut : liste vide)."""
        from src.gui.ui_builder.ui_widgets import apply_extra_extensions

        apply_extra_extensions(self.ui, [])

    def _on_ok(self):
        """Sauvegarde et ferme."""
        # Sauvegarder les options GUI
        self.config.update_gui(
            log_height=self.advanced_tab.log_height_var.get(),
            log_autoscroll=self.advanced_tab.log_autoscroll_var.get(),
            theme=self.advanced_tab.theme_var.get(),
        )

        # Sauvegarder le dossier de sortie et la langue en une seule fois
        self.config._config.output_dir = self.output_tab.output_dir_var.get()
        self.config._config.language = self.advanced_tab.lang_var.get()

        # Persiste les cases d'extraction (include_md, extra_extensions, ...)
        # dans la config : sans cela, cocher une extension n'aurait aucun
        # effet au redémarrage.
        self._save_extraction_options()

        self.config.save()

        self.destroy()

    def _save_extraction_options(self):
        """Recopie les cases d'extraction vers la config persistée.

        `model_validate` repasse par le validateur de `extra_extensions` :
        la liste blanche est donc appliquée au moment de la sauvegarde, et
        non seulement à l'extraction.
        """
        from src.gui.ui_builder.ui_widgets import apply_extraction_flags

        extraction = self.config._config.extraction
        apply_extraction_flags(self.ui, extraction)
        self.config._config.extraction = type(extraction).model_validate(
            extraction.model_dump()
        )


def open_settings_dialog(parent, ui_widgets):
    """Ouvre la boîte de dialogue des paramètres."""
    SettingsDialog(parent, ui_widgets)