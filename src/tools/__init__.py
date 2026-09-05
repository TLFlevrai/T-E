# src/tools/__init__.py
"""Registre des outils de TE.

`register_all_tools()` enregistre dans le Tool Registry et le Command
Registry tous les outils disponibles. L'ajout d'un futur outil consiste
à créer un module `src/tools/<nom>.py` avec une fonction
`register(registry, commands)` puis à l'ajouter à la liste ci-dessous.
"""
from __future__ import annotations

from src.core.command_registry import Command
from src.core.command_registry import commands as _commands
from src.core.tool_registry import registry as _registry

_registered = False


def register_all_tools() -> None:
    """Enregistre tous les outils (idempotent)."""
    global _registered
    if _registered:
        return

    from . import (builder, calculator, color_picker, converter, diff,
                   extractor, network, notepad, settings, text_analyzer,
                   tools_hub, versions, youtube)

    # Extraction -> Conversion -> Édition -> Système
    for module in (extractor, builder, versions,
                   converter, youtube,
                   diff, color_picker, text_analyzer, notepad,
                   calculator, network, settings, tools_hub):
        module.register(_registry, _commands)

    _register_app_commands(_commands)
    _registered = True


def _register_app_commands(cmds) -> None:
    """Commandes globales de TE (palette, quitter, éditeur de thème)."""
    from src.ui.command_palette import open_command_palette

    def _quit(shell):
        shell.on_close()
        shell.root.destroy()

    cmds.register(Command(
        id='app.command_palette',
        label="Palette de commandes",
        description="Rechercher et lancer un outil ou une action",
        shortcut='Ctrl+K',
        icon='⌘',
        keywords=('recherche', 'commandes', 'palette', 'tools'),
        handler=lambda shell: open_command_palette(shell),
    ))
    cmds.register(Command(
        id='app.quit',
        label="Quitter TE",
        description="Fermer l'application",
        shortcut='Ctrl+Q',
        icon='✖',
        keywords=('quitter', 'fermer', 'quit', 'exit'),
        handler=_quit,
    ))
    cmds.register(Command(
        id='app.open_theme_editor',
        label="Éditeur de thème",
        description="Personnaliser les couleurs du thème",
        icon='🎨',
        keywords=('theme', 'couleurs', 'colors', 'personnaliser'),
        handler=lambda shell: _open_theme_editor(shell),
    ))
    cmds.register(Command(
        id='app.export_pdf',
        label="Exporter en PDF",
        description="Extraire le projet sélectionné au format PDF",
        icon='📄',
        keywords=('pdf', 'exporter', 'export'),
        handler=lambda shell: _export_pdf(shell),
    ))


def _open_theme_editor(shell) -> None:
    from src.gui.theme_editor import open_theme_editor
    open_theme_editor(shell.root)


def _export_pdf(shell) -> None:
    controller = getattr(shell, 'extract_controller', None)
    if controller is not None:
        controller.export_to_pdf()
