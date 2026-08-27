# src/ui/command_palette.py
"""Command Palette de TE (Ctrl+K) : recherche et lancement des outils/actions.

Alimentée par le Command Registry partagé (mêmes commandes que les
raccourcis clavier et les menus).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.core.command_registry import commands
from src.core.tool_registry import registry
from src.i18n import _


class _PaletteItem:
    """Élément de la palette : navigation vers un outil ou commande."""

    __slots__ = ('command_id', 'detail', 'icon', 'kind', 'label', 'shortcut', 'tool_id')

    def __init__(self, kind: str, label: str, detail: str, icon: str,
                 shortcut: str | None, tool_id: str | None = None,
                 command_id: str | None = None):
        self.kind = kind
        self.label = label
        self.detail = detail
        self.icon = icon
        self.shortcut = shortcut
        self.tool_id = tool_id
        self.command_id = command_id

    def display(self) -> str:
        base = f"{self.icon}  {self.label}"
        if self.detail:
            base += f"  —  {self.detail}"
        return base

    def match(self, query: str) -> bool:
        if not query:
            return True
        haystacks = [self.label, self.detail, self.icon,
                     self.tool_id or '', self.command_id or '']
        return any(query in text.lower() for text in haystacks)


class CommandPaletteDialog(tk.Toplevel):
    """Fenêtre de recherche rapide des outils et commandes."""

    def __init__(self, shell: Any):
        super().__init__(shell.root)
        self.shell = shell
        self.title(_("Commandes"))
        self.transient(shell.root)
        self.resizable(False, False)

        self._all_items: list[_PaletteItem] = []
        self._visible_items: list[_PaletteItem] = []
        self._selected = 0

        self._build_index()
        self._create_widgets()
        self._refresh()

        width, height = 580, 440
        x = shell.root.winfo_rootx() + (shell.root.winfo_width() - width) // 2
        y = shell.root.winfo_rooty() + (shell.root.winfo_height() - height) // 3
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Up>", lambda e: self._move(-1))
        self.bind("<Down>", lambda e: self._move(1))
        self.bind("<Return>", lambda e: self._execute())
        self.after(10, self._focus_entry)

    # --- Index ---

    def _build_index(self):
        items: list[_PaletteItem] = []
        for tool in registry.all():
            shortcut = f"{tool.shortcut}" if tool.shortcut else None
            items.append(_PaletteItem(
                kind='tool',
                label=_(tool.name),
                detail=_(tool.description),
                icon=tool.icon,
                shortcut=shortcut,
                tool_id=tool.id,
            ))
        for command in commands.all():
            items.append(_PaletteItem(
                kind='command',
                label=_(command.label),
                detail=_(command.description) if command.description else '',
                icon=command.icon or '⚡',
                shortcut=command.shortcut,
                command_id=command.id,
            ))
        self._all_items = items

    # --- UI ---

    def _create_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text=_("Rechercher une commande ou un outil..."),
                  font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(0, 6))

        search_frame = ttk.Frame(main)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._refresh())
        self.entry = ttk.Entry(search_frame, textvariable=self.search_var,
                               font=('Segoe UI', 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, "")

        self.list_frame = ttk.Frame(main)
        self.list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            self.list_frame,
            activestyle='dotbox',
            font=('Segoe UI', 10),
            selectmode=tk.BROWSE,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<Double-Button-1>", lambda e: self._execute())

        hint = ttk.Label(main, text=f"↑↓ {_('Naviguer')}   ·   Enter {_('Lancer')}   ·   Esc {_('Fermer')}",
                         font=('Segoe UI', 8), foreground='#888888')
        hint.pack(anchor=tk.E, pady=(6, 0))

    # --- Filtrage ---

    def _refresh(self):
        query = self.search_var.get().strip().lower()
        self._visible_items = [item for item in self._all_items if item.match(query)]
        self.listbox.delete(0, tk.END)
        if not self._visible_items:
            self.listbox.insert(tk.END, _("Aucun résultat"))
            self.listbox.itemconfig(tk.END, foreground='#888888')
            self._selected = -1
            return
        for item in self._visible_items:
            text = item.display()
            if item.shortcut:
                text += f"    {item.shortcut}"
            self.listbox.insert(tk.END, text)
        self._selected = 0
        self._highlight()

    def _highlight(self):
        if self._selected >= 0 and self._selected < self.listbox.size():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self._selected)
            self.listbox.activate(self._selected)
            self.listbox.see(self._selected)

    def _move(self, delta: int):
        if not self._visible_items:
            return
        self._selected = (self._selected + delta) % len(self._visible_items)
        self._highlight()
        return "break"

    def _execute(self):
        if not self._visible_items or self._selected < 0:
            return
        item = self._visible_items[self._selected]
        self.destroy()
        if item.kind == 'tool' and item.tool_id:
            self.shell.show_tool(item.tool_id)
        elif item.command_id:
            commands.execute(item.command_id, self.shell)

    def _focus_entry(self):
        self.entry.focus_set()


def open_command_palette(shell: Any):
    """Ouvre la palette de commandes (Ctrl+K)."""
    CommandPaletteDialog(shell)
