# src/core/command_registry.py
"""Registre central des commandes de TE.

Le Command Registry est la source unique des actions disponibles :
il alimente à la fois la Command Palette (Ctrl+K), les raccourcis
clavier centralisés et les menus.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.i18n import _

logger = logging.getLogger(__name__)

# Handler reçoit le shell comme unique argument (lazy : résolu à l'exécution).
HandlerType = Callable[['Any'], None]


@dataclass(frozen=True)
class Command:
    """Métadonnées d'une commande enregistrée."""

    id: str
    label: str                          # msgid
    description: str | None = None   # msgid
    shortcut: str | None = None      # accélérateur par défaut (ex: Ctrl+K)
    icon: str | None = None
    tool_id: str | None = None       # outil associé (navigation)
    keywords: tuple[str, ...] = ()
    handler: HandlerType | None = None

    @property
    def navigates(self) -> bool:
        """True si la commande ouvre un outil du workspace."""
        return self.tool_id is not None


class CommandRegistry:
    """Registre des commandes, avec recherche et exécution."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """Enregistre une commande (remplace un doublon d'id)."""
        self._commands[command.id] = command
        logger.info("Commande enregistrée : %s", command.id)

    def get(self, command_id: str) -> Command | None:
        """Retourne la commande correspondant à l'id, ou None."""
        return self._commands.get(command_id)

    def all(self) -> list[Command]:
        """Retourne toutes les commandes (ordre d'enregistrement)."""
        return list(self._commands.values())

    def search(self, query: str) -> list[Command]:
        """Recherche textuelle sur le libellé, la description et les
        mots-clés traduits."""
        q = query.strip().lower()
        if not q:
            return self.all()
        results = []
        for command in self._commands.values():
            haystacks = [
                _(command.label),
                _(command.description) if command.description else '',
                command.id,
                *( _(kw) for kw in command.keywords ),
            ]
            if any(q in text.lower() for text in haystacks):
                results.append(command)
        return results

    def execute(self, command_id: str, shell: Any) -> None:
        """Exécute une commande avec le shell comme contexte."""
        command = self._commands.get(command_id)
        if command is None:
            logger.warning("Commande inconnue : %s", command_id)
            return
        if command.navigates and command.tool_id:
            if hasattr(shell, 'show_tool'):
                shell.show_tool(command.tool_id)
            return
        if command.handler:
            command.handler(shell)

    def clear(self) -> None:
        """Vide le registre (utile en test)."""
        self._commands.clear()


# Registre global unique
commands = CommandRegistry()
