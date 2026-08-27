# src/core/__init__.py
"""Noyau de TE : app, tools, registres, événements, raccourcis.

Cette couche ne dépend d'aucun toolkit graphique et ne peut pas importer
les modules de src/ui ni src/tools (aucun cycle).
"""
from .command_registry import Command, CommandRegistry, commands
from .events import EventBus, events
from .tool import Tool
from .tool_registry import ToolRegistry, registry

__all__ = [
    'Command',
    'CommandRegistry',
    'EventBus',
    'Tool',
    'ToolRegistry',
    'commands',
    'events',
    'registry',
]
