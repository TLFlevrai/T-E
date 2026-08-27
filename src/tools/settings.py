# src/tools/settings.py
"""Outil Paramètres : configuration de TE intégrée au workspace.

Réutilise les onglets existants (Formats, Filtres, Sortie, Avancé) à
travers un adaptateur compatible avec l'ancien dialogue.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.config import get_config
from src.core.command_registry import Command
from src.core.tool import Tool
from src.i18n import _, register_reload_callback


class _SettingsAdapter:
    """Adaptateur 'dialogue' pour les onglets de paramètres existants."""

    def __init__(self, ui, root):
        self.ui = ui
        self.config = get_config()
        self._original_options = {}
        self.parent_widget = root


def build_settings_view(shell) -> ttk.Frame:
    """Construit la vue Paramètres embarquée dans le workspace."""
    frame = ttk.Frame(shell.workspace, padding=15)

    ui = getattr(shell, 'extract_ui', None)
    if ui is None:
        from src.gui.ui_builder.ui_widgets import create_ui_widgets
        ui = create_ui_widgets(get_config())

    adapter = _SettingsAdapter(ui, shell.root)

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

    from src.gui.settings import AdvancedTab, FiltersTab, FormatsTab, OutputTab

    formats_frame = ttk.Frame(notebook, padding=10)
    notebook.add(formats_frame, text=_("Formats"))
    adapter.formats_tab = FormatsTab(formats_frame, adapter)

    filters_frame = ttk.Frame(notebook, padding=10)
    notebook.add(filters_frame, text=_("Filtres"))
    adapter.filters_tab = FiltersTab(filters_frame, adapter)

    output_frame = ttk.Frame(notebook, padding=10)
    notebook.add(output_frame, text=_("Sortie"))
    adapter.output_tab = OutputTab(output_frame, adapter)

    advanced_frame = ttk.Frame(notebook, padding=10)
    notebook.add(advanced_frame, text=_("Avancé"))
    adapter.advanced_tab = AdvancedTab(advanced_frame, adapter)

    # Boutons bas
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X)

    ttk.Button(btn_frame, text=_("Restaurer défauts"),
               command=lambda: _reset_defaults(ui, adapter)).pack(side=tk.LEFT)
    ttk.Button(btn_frame, text=_("Sauvegarder"),
               style='AppPrimary.TButton',
               command=lambda: _save(adapter)).pack(side=tk.RIGHT, padx=5)

    # Reconstruire la vue à chaque changement de langue (libellés des onglets)
    def _reload():
        if frame.winfo_exists():
            _rebuild_notebook(frame, adapter)

    shell._settings_reload_callback = _reload
    register_reload_callback(_reload)

    return frame


def _rebuild_notebook(frame, adapter):
    """Reconstruit le notebook des paramètres (après changement de langue)."""
    for child in frame.winfo_children():
        child.destroy()

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

    from src.gui.settings import AdvancedTab, FiltersTab, FormatsTab, OutputTab

    formats_frame = ttk.Frame(notebook, padding=10)
    notebook.add(formats_frame, text=_("Formats"))
    adapter.formats_tab = FormatsTab(formats_frame, adapter)

    filters_frame = ttk.Frame(notebook, padding=10)
    notebook.add(filters_frame, text=_("Filtres"))
    adapter.filters_tab = FiltersTab(filters_frame, adapter)

    output_frame = ttk.Frame(notebook, padding=10)
    notebook.add(output_frame, text=_("Sortie"))
    adapter.output_tab = OutputTab(output_frame, adapter)

    advanced_frame = ttk.Frame(notebook, padding=10)
    notebook.add(advanced_frame, text=_("Avancé"))
    adapter.advanced_tab = AdvancedTab(advanced_frame, adapter)

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X)
    ttk.Button(btn_frame, text=_("Restaurer défauts"),
               command=lambda: _reset_defaults(adapter.ui, adapter)).pack(side=tk.LEFT)
    ttk.Button(btn_frame, text=_("Sauvegarder"),
               style='AppPrimary.TButton',
               command=lambda: _save(adapter)).pack(side=tk.RIGHT, padx=5)


def _reset_defaults(ui, adapter) -> None:
    """Restaure les valeurs par défaut (schéma AppConfig), pas les dernières
    valeurs sauvegardées : `config.get_all()` renvoie la config persistée,
    pas les défauts."""
    if not messagebox.askyesno(_("Confirmation"),
                               _("Restaurer tous les paramètres par défaut ?")):
        return
    from src.config.schema import ExtractionOptions

    defaults = ExtractionOptions().model_dump()
    for key, value in defaults.items():
        var = getattr(ui, key, None)
        if var:
            var.set(value)

    if adapter.advanced_tab:
        adapter.advanced_tab.log_height_var.set(12)
        adapter.advanced_tab.log_autoscroll_var.set(True)
        adapter.advanced_tab.preset_var.set('custom')


def _save(adapter) -> None:
    """Persiste la configuration actuelle."""
    from src.gui.toast import show_toast
    try:
        adapter.config.save()
        show_toast(adapter.parent_widget, _("Paramètres enregistrés"),
                   type_='info', parent=adapter.parent_widget)
    except Exception:
        from src.gui.errors import show_error
        show_error(_("Erreur"), _("Impossible de sauvegarder la configuration."),
                   parent=adapter.parent_widget)


TOOL = Tool(
    id='settings',
    name="Paramètres",
    description="Configurer TE : langue, thème, formats, sortie.",
    category="Personnalisation",
    icon='⚙️',
    shortcut='Ctrl+8',
    view=build_settings_view,
    keywords=('parametres', 'settings', 'configuration', 'options', 'preferences'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.settings',
        label="Paramètres",
        description="Configurer TE : langue, thème, formats, sortie",
        shortcut='Ctrl+8',
        icon='⚙️',
        tool_id='settings',
        keywords=('parametres', 'settings', 'configuration', 'options'),
    ))
