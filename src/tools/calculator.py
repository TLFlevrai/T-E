# src/tools/calculator.py
"""Outil Calculatrice : calculatrice intégrée au workspace."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.core.command_registry import Command
from src.core.tool import Tool


def build_calculator_view(shell) -> ttk.Frame:
    """Construit la calculatrice embarquée dans le workspace."""
    from src.gui.calculator import CalculatorContent

    frame = ttk.Frame(shell.workspace)
    content = CalculatorContent(frame, global_keys=False)
    content.pack(fill=tk.BOTH, expand=True)
    return frame


TOOL = Tool(
    id='calculator',
    name="Calculatrice",
    description="Calculatrice simple et sécurisée.",
    category="Utilitaires",
    icon='🧮',
    shortcut='Ctrl+4',
    view=build_calculator_view,
    keywords=('calcul', 'calculator', 'math', 'calculette'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.calculator',
        label="Calculatrice",
        description="Calculatrice simple et sécurisée",
        shortcut='Ctrl+4',
        icon='🧮',
        tool_id='calculator',
        keywords=('calcul', 'calculator', 'math'),
    ))
