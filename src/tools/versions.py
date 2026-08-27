# src/tools/versions.py
"""Outil Versions : gestionnaire de versions d'export (dialogue spécialisé conservé)."""
from __future__ import annotations

from src.core.command_registry import Command
from src.core.tool import Tool


def _open_versions(shell) -> None:
    from src.gui.version_explorer import VersionExplorerDialog
    VersionExplorerDialog(shell.root)


TOOL = Tool(
    id='versions',
    name="Versions",
    description="Gérer les versions d'export des projets.",
    category="Données",
    icon='🗂️',
    shortcut='Ctrl+6',
    open=_open_versions,
    keywords=('versions', 'archive', 'restaurer', 'history', 'backup'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.versions',
        label="Versions",
        description="Ouvrir le gestionnaire de versions d'export",
        shortcut='Ctrl+6',
        icon='🗂️',
        tool_id='versions',
        keywords=('versions', 'archive', 'restaurer', 'history'),
    ))
