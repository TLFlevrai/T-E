# src/tools/extractor.py
"""Outil Extraction : extrait le code et la structure d'un projet.

Réutilise l'interface d'extraction existante (UIWidgets, contrôleurs,
services) en l'intégrant comme vue du workspace de TE.
"""
from __future__ import annotations

from tkinter import ttk

from src.config import get_config
from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.controller.main_controller import MainController
from src.gui.ui_builder.ui_widgets import create_ui_widgets
from src.gui.ui_builder.widgets import build_widgets


def build_extract_view(shell) -> ttk.Frame:
    """Construit la vue Extraction intégrée au workspace."""
    frame = ttk.Frame(shell.workspace)

    ui = create_ui_widgets(get_config())

    # Créer le contrôleur AVANT build_widgets pour que ui.controller soit disponible
    controller = MainController(shell.root, ui, service=shell.service)
    ui.controller = controller
    controller.set_server(shell.server)
    controller.set_discovery(shell.discovery)

    # Maintenant build_widgets peut utiliser ui.controller
    build_widgets(frame, ui)

    ui.browse_btn.config(command=controller.browse_folder)
    ui.clear_btn.config(command=controller.clear_info)
    ui.extract_btn.config(command=controller.extract_code)
    ui.cancel_btn.config(command=controller.cancel_extraction)
    ui.select_btn.config(command=controller.open_selection_dialog)
    ui.version_btn.config(command=lambda: shell.show_tool('versions'))
    ui.network_btn.config(command=lambda: shell.show_tool('network'))
    ui.navigate_to = shell.show_tool

    # Drag & drop : double-clic sur le champ dossier
    entry = getattr(ui, 'folder_entry', None)
    if entry is not None:
        entry.config(cursor="hand2")
        entry.bind("<Double-Button-1>", lambda e: controller.browse_folder())

    shell.extract_ui = ui
    shell.extract_controller = controller
    return frame


# --- Handlers de commandes (reçoivent le shell au moment de l'exécution) ---

def _cmd_extract(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is None:
        return
    ui = getattr(shell, 'extract_ui', None)
    if ui is not None and str(ui.extract_btn['state']) != 'normal':
        return
    controller.extract_code()


def _cmd_browse(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is not None:
        controller.browse_folder()


def _cmd_clear_log(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is not None:
        controller.clear_info()


def _cmd_toggle_sidebar(shell) -> None:
    """Toggle la visibilité de la barre latérale."""
    if hasattr(shell, 'toggle_sidebar'):
        shell.toggle_sidebar()


TOOL = Tool(
    id='extract',
    name="Archiviste",
    description="Extrayez et archivez le code de vos projets.",
    category="Extraction",
    icon='📦',
    shortcut='Ctrl+1',
    view=build_extract_view,
    commands=('extract.run', 'extract.browse', 'extract.clear_log'),
    keywords=('code', 'projet', 'project', 'structure', 'extraire', 'export', 'archive'),
    order=1,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='extract.run',
        label="Archiviste",
        description="Lancer l'extraction du code du projet sélectionné",
        shortcut='Ctrl+E',
        icon='📦',
        tool_id='extract',
        keywords=('extraire', 'extraction', 'extract', 'lancer', 'archiver'),
        handler=_cmd_extract,
    ))
    cmds.register(Command(
        id='extract.browse',
        label="Parcourir un dossier",
        description="Ouvrir un dossier de projet",
        shortcut='Ctrl+O',
        icon='📂',
        tool_id='extract',
        keywords=('parcourir', 'dossier', 'ouvrir', 'browse', 'folder'),
        handler=_cmd_browse,
    ))
    cmds.register(Command(
        id='extract.clear_log',
        label="Effacer le journal",
        description="Effacer le journal d'extraction",
        shortcut='Ctrl+L',
        icon='🧹',
        tool_id='extract',
        keywords=('journal', 'log', 'effacer', 'clear', 'vider'),
        handler=_cmd_clear_log,
    ))
    cmds.register(Command(
        id='extract.toggle_sidebar',
        label="Basculer la barre latérale",
        description="Afficher ou masquer la barre latérale de sélection des outils",
        shortcut='Ctrl+B',
        icon='☰',
        keywords=('sidebar', 'barre', 'latérale', 'outils', 'toggle', 'masquer', 'afficher'),
        handler=_cmd_toggle_sidebar,
    ))
