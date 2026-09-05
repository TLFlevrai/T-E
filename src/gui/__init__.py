# src/gui/__init__.py
"""Paquet GUI de TE.

Les consommateurs importent les sous-modules directement
(ex: `from src.gui.theme import apply_theme`) : ce paquet n'expose pas de
facade pour éviter des imports eagerly de dépendances lourdes (PIL,
ttkbootstrap) au démarrage.
"""

from __future__ import annotations