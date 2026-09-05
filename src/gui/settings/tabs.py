# src/gui/settings/tabs.py
"""Onglets de la boîte de dialogue des paramètres."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from src.i18n import _
from src.gui.theme_editor import open_theme_editor


class FormatsTab:
    """Onglet Formats - quels types de fichiers inclure."""

    def __init__(self, parent, dialog):
        self.parent = parent
        self.dialog = dialog
        self.ui = dialog.ui
        self._create()

    def _create(self):
        formats = [
            ('include_json', _("Fichiers JSON (.json)"), True),
            ('include_html', _("Fichiers HTML (.html, .htm)"), True),
            ('include_css', _("Fichiers CSS (.css)"), True),
            ('include_js', _("Fichiers JavaScript (.js)"), True),
            ('include_txt', _("Fichiers texte (.txt)"), False),
            ('include_po', _("Fichiers traduction PO (.po)"), False),
            ('include_mo', _("Fichiers traduction MO (.mo)"), False),
        ]

        for i, (key, label, default) in enumerate(formats):
            var = getattr(self.ui, key, None)
            if var:
                cb = ttk.Checkbutton(self.parent, text=label, variable=var)
                cb.grid(row=i, column=0, sticky=tk.W, pady=4, padx=5)
                self.dialog._original_options[key] = var.get()


class FiltersTab:
    """Onglet Filtres - exclusions et inclusions de dossiers/fichiers."""

    def __init__(self, parent, dialog):
        self.parent = parent
        self.dialog = dialog
        self.ui = dialog.ui
        self._create()

    def _create(self):
        filters = [
            ('include_subdirs', _("Inclure les sous-dossiers"), True),
            ('show_file_paths', _("Afficher les chemins complets"), True),
            ('include_structure', _("Inclure la structure du projet"), True),
            ('ignore_init', _("Ignorer __init__.py"), False),
            ('ignore_git', _("Ignorer le dossier .git"), True),
            ('ignore_pycache', _("Ignorer __pycache__"), True),
        ]

        for i, (key, label, default) in enumerate(filters):
            var = getattr(self.ui, key, None)
            if var:
                cb = ttk.Checkbutton(self.parent, text=label, variable=var)
                cb.grid(row=i, column=0, sticky=tk.W, pady=4, padx=5)
                self.dialog._original_options[key] = var.get()


class OutputTab:
    """Onglet Sortie - options de sortie, métadonnées et dossier."""

    def __init__(self, parent, dialog):
        self.parent = parent
        self.dialog = dialog
        self.ui = dialog.ui
        self.config = dialog.config
        self.output_dir_var = tk.StringVar(value=self.config.get('output_dir', 'out'))
        self._create()

    def _create(self):
        outputs = [
            ('include_statistics', _("Inclure les statistiques globales"), True),
            ('include_file_metadata', _("Métadonnées par fichier (taille, lignes)"), False),
            ('archive_old', _("Archiver les anciennes versions"), False),
        ]

        for i, (key, label, default) in enumerate(outputs):
            var = getattr(self.ui, key, None)
            if var:
                cb = ttk.Checkbutton(self.parent, text=label, variable=var)
                cb.grid(row=i, column=0, sticky=tk.W, pady=4, padx=5)
                self.dialog._original_options[key] = var.get()

        # Dossier de sortie
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).grid(
            row=len(outputs), column=0, sticky=(tk.W, tk.E), pady=15)

        ttk.Label(self.parent, text=_("Dossier de sortie :"), font=('Arial', 9, 'bold')).grid(
            row=len(outputs)+1, column=0, sticky=tk.W, pady=2)

        output_dir_frame = ttk.Frame(self.parent)
        output_dir_frame.grid(row=len(outputs)+2, column=0, sticky=(tk.W, tk.E), pady=2)
        output_dir_frame.columnconfigure(0, weight=1)

        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, state='readonly').grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(output_dir_frame, text=_("Modifier..."), command=self._change_output_dir).grid(
            row=0, column=1)

    def _change_output_dir(self):
        """Change le dossier de sortie."""
        from tkinter import filedialog
        path = filedialog.askdirectory(title=_("Choisir le dossier de sortie"))
        if path:
            self.output_dir_var.set(path)


class AdvancedTab:
    """Onglet Avancé - options moins communes (journal, langue, thème, presets)."""

    def __init__(self, parent, dialog):
        self.parent = parent
        self.dialog = dialog
        self.config = dialog.config

        self.log_height_var = tk.IntVar(value=self.config.get('gui.log_height', 12))
        self.log_autoscroll_var = tk.BooleanVar(value=self.config.get('gui.log_autoscroll', True))
        self.lang_var = tk.StringVar(value=self.config.get('language', 'fr'))
        self.theme_var = tk.StringVar(value=self.config.get('gui.theme', 'system'))
        self.preset_var = tk.StringVar(value='custom')
        self._create()

    def _create(self):
        # Hauteur du journal
        ttk.Label(self.parent, text=_("Hauteur du journal (lignes) :")).grid(
            row=0, column=0, sticky=tk.W, pady=8)

        log_spin = ttk.Spinbox(self.parent, from_=4, to=50, textvariable=self.log_height_var, width=10)
        log_spin.grid(row=0, column=1, sticky=tk.W, padx=10, pady=8)

        # Auto-scroll
        ttk.Checkbutton(
            self.parent,
            text=_("Défilement automatique du journal"),
            variable=self.log_autoscroll_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=8)

        # Langue
        ttk.Label(self.parent, text=_("Langue :")).grid(row=2, column=0, sticky=tk.W, pady=8)
        lang_combo = ttk.Combobox(self.parent, textvariable=self.lang_var,
                                   values=['fr', 'en'], state='readonly', width=10)
        lang_combo.grid(row=2, column=1, sticky=tk.W, padx=10, pady=8)
        lang_combo.bind('<<ComboboxSelected>>', lambda e: self._on_language_change())

        # Thème
        ttk.Label(self.parent, text=_("Thème :")).grid(row=3, column=0, sticky=tk.W, pady=8)
        theme_combo = ttk.Combobox(self.parent, textvariable=self.theme_var,
                                    values=['system', 'light', 'dark', 'custom'], state='readonly', width=10)
        theme_combo.grid(row=3, column=1, sticky=tk.W, padx=10, pady=8)
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self._on_theme_change())

        # Bouton éditeur de thème
        ttk.Button(self.parent, text=_("Personnaliser le thème..."),
                   command=lambda: open_theme_editor(
                       getattr(self.dialog, 'parent_widget', self.dialog)
                   )).grid(row=3, column=2, padx=10, pady=8)

        # Presets d'export
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15)

        ttk.Label(self.parent, text=_("Preset d'export :"), font=('Arial', 9, 'bold')).grid(
            row=5, column=0, sticky=tk.W, pady=2)

        preset_frame = ttk.Frame(self.parent)
        preset_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        preset_frame.columnconfigure(1, weight=1)

        presets = [
            ('python_only', _("Python uniquement")),
            ('web_assets', _("Assets Web (HTML/CSS/JS)")),
            ('full', _("Complet (tout)")),
            ('minimal', _("Minimal (Python + structure)")),
            ('custom', _("Personnalisé")),
        ]
        for i, (val, label) in enumerate(presets):
            rb = ttk.Radiobutton(preset_frame, text=label, variable=self.preset_var, value=val,
                                  command=self._apply_preset)
            rb.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)

        ttk.Button(preset_frame, text=_("Enregistrer comme preset..."),
                   command=self._save_preset).grid(row=3, column=0, columnspan=2, pady=8)

    def _on_language_change(self):
        """Change la langue à chaud."""
        from src.i18n import change_language
        change_language(self.lang_var.get())

    def _on_theme_change(self):
        """Change le thème."""
        from src.gui.theme import apply_theme
        apply_theme(self.theme_var.get())

    def _apply_preset(self):
        """Applique un preset prédéfini."""
        preset = self.preset_var.get()
        ui = self.dialog.ui

        presets = {
            'python_only': {
                'include_json': False, 'include_html': False, 'include_css': False,
                'include_js': False, 'include_txt': False, 'include_po': False,
                'include_mo': False, 'include_structure': True,
            },
            'web_assets': {
                'include_json': True, 'include_html': True, 'include_css': True,
                'include_js': True, 'include_txt': False, 'include_po': False,
                'include_mo': False, 'include_structure': True,
            },
            'full': {
                'include_json': True, 'include_html': True, 'include_css': True,
                'include_js': True, 'include_txt': True, 'include_po': True,
                'include_mo': True, 'include_structure': True,
                'include_statistics': True, 'include_file_metadata': True,
            },
            'minimal': {
                'include_json': False, 'include_html': False, 'include_css': False,
                'include_js': False, 'include_txt': False, 'include_po': False,
                'include_mo': False, 'include_structure': True,
                'include_statistics': True,
            },
        }

        if preset in presets:
            for key, value in presets[preset].items():
                var = getattr(ui, key, None)
                if var:
                    var.set(value)

    def _save_preset(self):
        """Enregistre la config actuelle comme preset personnalisé."""
        # TODO: implémenter la sauvegarde de presets personnalisés
        messagebox.showinfo(_("Info"), _("Fonctionnalité à venir : sauvegarde de presets personnalisés"))