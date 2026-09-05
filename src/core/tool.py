# src/core/tool.py
"""Abstraction commune d'un outil (Tool) de TE.

Chaque outil déclare ses métadonnées (id, nom, description, catégorie,
icône, raccourci), une vue à intégrer au workspace ou un lanceur de
dialogue, ainsi que les commandes qu'il fournit.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Le shell n'est référencé qu'en tant qu'objet opaque pour éviter tout
# cycle d'import : les builders reçoivent le shell au moment de l'exécution.
ShellType = Any


@dataclass(frozen=True)
class Tool:
    """Métadonnées d'un outil enregistré dans le Tool Registry."""

    id: str
    name: str                       # msgid (chaîne i18n)
    description: str                # msgid
    category: str                   # msgid
    icon: str = '🔧'                # glyphe/emoji affiché dans la sidebar
    shortcut: str | None = None  # accélérateur de navigation (ex: Ctrl+1)
    view: Callable[[ShellType], Any] | None = None   # construit la vue embarquée
    open: Callable[[ShellType], None] | None = None  # ouvre un dialogue dédié
    commands: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()  # termes de recherche supplémentaires (msgids)
    order: int = 100                # position within category (lower = higher)

    def __post_init__(self) -> None:
        if self.view is None and self.open is None:
            raise ValueError(f"Le tool '{self.id}' doit définir une vue ou un lanceur")

    @property
    def embeds_view(self) -> bool:
        """True si l'outil fournit une vue intégrée au workspace."""
        return self.view is not None
