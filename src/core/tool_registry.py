# src/core/tool_registry.py
"""Registre central des outils de TE.

Le registre permet à l'application de connaître automatiquement les
outils disponibles : l'ajout d'un nouvel outil consiste uniquement à
appeler `registry.register(Tool(...))`.
"""
from __future__ import annotations

import logging

from src.i18n import _

from .tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registre des outils, avec recherche par id et recherche textuelle."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Enregistre un outil (remplace silencieusement un doublon d'id)."""
        self._tools[tool.id] = tool
        logger.info("Outil enregistré : %s (%s)", tool.id, tool.name)

    def get(self, tool_id: str) -> Tool | None:
        """Retourne l'outil correspondant à l'id, ou None."""
        return self._tools.get(tool_id)

    def all(self) -> list[Tool]:
        """Retourne tous les outils (dans l'ordre d'enregistrement)."""
        return list(self._tools.values())

    def by_category(self) -> list[tuple[str, list[Tool]]]:
        """Retourne les outils groupés par catégorie, triés par order."""
        grouped: dict[str, list[Tool]] = {}
        order: list[str] = []
        for tool in self._tools.values():
            if tool.category not in grouped:
                grouped[tool.category] = []
                order.append(tool.category)
            grouped[tool.category].append(tool)
        # Trier chaque catégorie par order
        for cat in grouped:
            grouped[cat].sort(key=lambda t: t.order)
        return [(category, grouped[category]) for category in order]

    def search(self, query: str) -> list[Tool]:
        """Recherche textuelle sur le nom, la description et les mots-clés
        traduits (fonctionne en FR et en EN)."""
        q = query.strip().lower()
        if not q:
            return self.all()
        results = []
        for tool in self._tools.values():
            haystacks = [
                _(tool.name),
                _(tool.description),
                _(tool.category),
                *( _(kw) for kw in tool.keywords ),
                tool.id,
            ]
            if any(q in text.lower() for text in haystacks):
                results.append(tool)
        return results

    def clear(self) -> None:
        """Vide le registre (utile en test)."""
        self._tools.clear()


# Registre global unique
registry = ToolRegistry()
