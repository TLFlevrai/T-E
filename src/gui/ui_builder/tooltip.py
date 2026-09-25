# src/gui/ui_builder/tooltip.py
"""
Ancien module d'infobulles — DÉPRÉCIÉ.

Ce module est conservé pour compatibilité.
Utilisez plutôt :mod:`src.ui.tooltips` qui consolide toutes les infobulles.
"""
from __future__ import annotations
import warnings

warnings.warn(
    "src.gui.ui_builder.tooltip est déprécié, utilisez src.ui.tooltips",
    DeprecationWarning,
    stacklevel=2
)

from src.ui.tooltips import (
    ToolTip,
    LazyToolTip,
    add_tooltip,
    add_lazy_tooltip,
)

__all__ = [
    'ToolTip',
    'LazyToolTip',
    'add_tooltip',
    'add_lazy_tooltip',
]