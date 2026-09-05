# src/tools/network.py
"""Outil Réseau : centre réseau (dialogue spécialisé conservé)."""
from __future__ import annotations

from src.core.command_registry import Command
from src.core.tool import Tool


class _DummyController:
    """Repli minimal si le contrôleur d'extraction n'est pas encore créé."""

    def __init__(self, service):
        self.service = service


def _open_network(shell) -> None:
    from src.gui.network_center import NetworkCenterDialog

    controller = getattr(shell, 'extract_controller', None)
    if controller is None:
        controller = _DummyController(shell.service)
    NetworkCenterDialog(shell.root, controller, shell.server, shell.discovery)


TOOL = Tool(
    id='network',
    name="Nexus",
    description="Transférez des fichiers sur le réseau local.",
    category="Système",
    icon='🔗',
    shortcut='Ctrl+5',
    open=_open_network,
    keywords=('reseau', 'network', 'transfert', 'fichiers', 'transfer', 'wifi', 'nexus'),
    order=2,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.network',
        label="Nexus",
        description="Ouvrir le centre réseau",
        shortcut='Ctrl+5',
        icon='🔗',
        tool_id='network',
        keywords=('reseau', 'network', 'transfert', 'transfer', 'nexus'),
    ))
