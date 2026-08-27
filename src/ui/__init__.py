# src/ui/__init__.py
"""Couche interface de TE : shell, sidebar, workspace, palette, tooltips, autoscroll."""
from .autoscroll import AutoScrollFrame, make_scrollable
from .command_palette import CommandPaletteDialog, open_command_palette
from .tooltips import (
    LazyRichToolTip,
    RichToolTip,
    ToolTipContent,
    add_lazy_rich_tooltip,
    add_rich_tooltip,
)

__all__ = [
    'AutoScrollFrame',
    'CommandPaletteDialog',
    'LazyRichToolTip',
    'RichToolTip',
    'ToolTipContent',
    'add_lazy_rich_tooltip',
    'add_rich_tooltip',
    'make_scrollable',
    'open_command_palette',
]
