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
    name="Chronologie",
    description="Naviguez dans l'historique des versions d'export.",
    category="Extraction",
    icon='⏳',
    shortcut='Ctrl+6',
    open=_open_versions,
    keywords=('versions', 'archive', 'restaurer', 'history', 'backup', 'chronologie'),
    order=3,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.versions',
        label="Chronologie",
        description="Ouvrir le gestionnaire de versions d'export",
        shortcut='Ctrl+6',
        icon='⏳',
        tool_id='versions',
        keywords=('versions', 'archive', 'restaurer', 'history', 'chronologie'),
    ))
