# src/core/shortcuts.py
"""Système centralisé de raccourcis clavier.

Les raccourcis sont déclarés sur les commandes du Command Registry et
peuvent être surchargés par l'utilisateur via la configuration
(`gui.shortcuts` dans config.json). Chaque raccourci est mappé une seule
fois sur la fenêtre racine, ce qui évite les câblages en dur dans les
interfaces.
"""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from src.config import get_config

from .command_registry import commands

logger = logging.getLogger(__name__)

_MOD_MAP = {'Ctrl': 'Control', 'Alt': 'Alt', 'Shift': 'Shift', 'Cmd': 'Command'}


def to_tk_binding(accelerator: str) -> str:
    """Convertit un accélérateur type 'Ctrl+K' ou 'Ctrl+Shift+S' ou 'F5'
    en séquence Tkinter ('<Control-k>', '<Control-Shift-s>', '<F5>')."""
    parts = accelerator.split('+')
    key = parts[-1]
    mods = [_MOD_MAP.get(m, m) for m in parts[:-1]]
    # Les lettres uniques sont insensibles à la casse côté Tk
    if len(key) == 1:
        key = key.lower()
    if mods:
        return f"<{'-'.join(mods)}-{key}>"
    return f"<{key}>"


class ShortcutManager:
    """Lie les raccourcis du registre de commandes à la fenêtre racine."""

    def __init__(self, shell: Any) -> None:
        self.shell = shell
        self._bound: dict[str, str] = {}  # binding tk -> command id

    def bind_all(self) -> None:
        """(Re)lie tous les raccourcis effectifs des commandes."""
        self.unbind_all()
        config_shortcuts = get_config().get('gui.shortcuts', {})
        if not isinstance(config_shortcuts, dict):
            config_shortcuts = {}

        for command in commands.all():
            accelerator = config_shortcuts.get(command.id, command.shortcut)
            if not accelerator:
                continue
            binding = to_tk_binding(accelerator)
            if binding in self._bound:
                continue
            try:
                self.shell.root.bind_all(
                    binding,
                    lambda event, cid=command.id: self._dispatch(cid, event),
                )
                self._bound[binding] = command.id
                logger.debug("Raccourci lié : %s -> %s", accelerator, command.id)
            except Exception:
                logger.exception("Impossible de lier le raccourci %s", accelerator)

    def unbind_all(self) -> None:
        """Délie tous les raccourcis précédemment enregistrés."""
        for binding, _command_id in list(self._bound.items()):
            with contextlib.suppress(Exception):
                self.shell.root.unbind_all(binding)
        self._bound.clear()

    def _dispatch(self, command_id: str, _event: Any) -> str | None:
        commands.execute(command_id, self.shell)
        return 'break'
