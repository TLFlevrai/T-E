# src/tools/diff.py
"""Outil Text Diff : comparaison de fichiers côte à côte."""
from __future__ import annotations

import difflib
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.theme import get_color
from src.i18n import _

# Tags de couleur pour les différences
_TAG_ADDED = "diff_added"
_TAG_REMOVED = "diff_removed"
_TAG_MODIFIED = "diff_modified"
_TAG_INFO = "diff_info"


def build_diff_view(shell) -> ttk.Frame:
    """Construit la vue comparaison de fichiers dans le workspace."""
    frame = ttk.Frame(shell.workspace, padding=12)
    frame.columnconfigure(0, weight=1)

    # --- Sélection des fichiers ---
    file_frame = ttk.Frame(frame)
    file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
    file_frame.columnconfigure(1, weight=1)

    ttk.Label(file_frame, text=str(_("Fichier A :"))).grid(
        row=0, column=0, sticky=tk.W, padx=(0, 6))
    file_a_var = tk.StringVar()
    entry_a = ttk.Entry(file_frame, textvariable=file_a_var, state='readonly')
    entry_a.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))
    ttk.Button(file_frame, text="...", width=3,
               command=lambda: _browse_file(file_a_var)).grid(row=0, column=2)

    ttk.Label(file_frame, text=str(_("Fichier B :"))).grid(
        row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(4, 0))
    file_b_var = tk.StringVar()
    entry_b = ttk.Entry(file_frame, textvariable=file_b_var, state='readonly')
    entry_b.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 6), pady=(4, 0))
    ttk.Button(file_frame, text="...", width=3,
               command=lambda: _browse_file(file_b_var)).grid(row=1, column=2, pady=(4, 0))

    # --- Boutons d'action ---
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

    compare_btn = ttk.Button(btn_frame, text=str(_("Comparer")),
                              style='Accent.TButton')
    compare_btn.pack(side=tk.LEFT, padx=(0, 6))

    clear_btn = ttk.Button(btn_frame, text=str(_("Effacer")))
    clear_btn.pack(side=tk.LEFT)

    # --- Barre de statuts ---
    status_var = tk.StringVar(value=str(_("Sélectionnez deux fichiers à comparer.")))
    status_label = ttk.Label(frame, textvariable=status_var, wraplength=600)
    status_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 6))

    # --- Zone de comparaison ---
    paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
    paned.grid(row=3, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    frame.rowconfigure(3, weight=1)

    # Panneau gauche (Fichier A)
    left_frame = ttk.Frame(paned)
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(1, weight=1)
    ttk.Label(left_frame, text=str(_("Fichier A")), font=('Segoe UI', 9, 'bold')).grid(
        row=0, column=0, sticky=tk.W, pady=(0, 2))
    text_a = tk.Text(left_frame, wrap=tk.NONE, font=('Consolas', 10),
                      bg=get_color('text_bg'), fg=get_color('text_fg'), insertbackground=get_color('fg'),
                      selectbackground=get_color('select_bg'), bd=0, highlightthickness=0)
    scroll_a_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=text_a.yview)
    scroll_a_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=text_a.xview)
    text_a.configure(yscrollcommand=scroll_a_y.set, xscrollcommand=scroll_a_x.set)
    scroll_a_y.grid(row=1, column=1, sticky=(tk.N, tk.S))
    scroll_a_x.grid(row=2, column=0, sticky=(tk.E, tk.W))
    text_a.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    paned.add(left_frame, weight=1)

    # Panneau droit (Fichier B)
    right_frame = ttk.Frame(paned)
    right_frame.columnconfigure(0, weight=1)
    right_frame.rowconfigure(1, weight=1)
    ttk.Label(right_frame, text=str(_("Fichier B")), font=('Segoe UI', 9, 'bold')).grid(
        row=0, column=0, sticky=tk.W, pady=(0, 2))
    text_b = tk.Text(right_frame, wrap=tk.NONE, font=('Consolas', 10),
                      bg=get_color('text_bg'), fg=get_color('text_fg'), insertbackground=get_color('fg'),
                      selectbackground=get_color('select_bg'), bd=0, highlightthickness=0)
    scroll_b_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=text_b.yview)
    scroll_b_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=text_b.xview)
    text_b.configure(yscrollcommand=scroll_b_y.set, xscrollcommand=scroll_b_x.set)
    scroll_b_y.grid(row=1, column=1, sticky=(tk.N, tk.S))
    scroll_b_x.grid(row=2, column=0, sticky=(tk.E, tk.W))
    text_b.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    paned.add(right_frame, weight=1)

    # Configurer les tags de couleur
    text_a.tag_configure(_TAG_ADDED, background=get_color('accent_soft'), foreground=get_color('success'))
    text_a.tag_configure(_TAG_REMOVED, background=get_color('surface_alt'), foreground=get_color('error'))
    text_a.tag_configure(_TAG_MODIFIED, background=get_color('surface_alt'), foreground=get_color('warning'))
    text_a.tag_configure(_TAG_INFO, foreground=get_color('accent'))
    text_b.tag_configure(_TAG_ADDED, background=get_color('accent_soft'), foreground=get_color('success'))
    text_b.tag_configure(_TAG_REMOVED, background=get_color('surface_alt'), foreground=get_color('error'))
    text_b.tag_configure(_TAG_MODIFIED, background=get_color('surface_alt'), foreground=get_color('warning'))
    text_b.tag_configure(_TAG_INFO, foreground=get_color('accent'))

    # Synchronisation du défilement vertical
    def _sync_scroll(*args):
        text_a.yview(*args)
        text_b.yview(*args)

    scroll_a_y.configure(command=_sync_scroll)
    scroll_b_y.configure(command=_sync_scroll)

    def _on_mousewheel(event):
        text_a.yview_scroll(int(-1 * (event.delta / 120)), "units")
        text_b.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    text_a.bind("<MouseWheel>", _on_mousewheel)
    text_b.bind("<MouseWheel>", _on_mousewheel)

    # --- État interne ---
    state = {
        'file_a': None,
        'file_b': None,
    }

    def _browse_file(var):
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner un fichier")),
            filetypes=[("Tous les fichiers", "*.*"), ("Fichiers texte", "*.txt *.py *.json")])
        if path:
            var.set(path)

    def _compare():
        path_a = file_a_var.get()
        path_b = file_b_var.get()
        if not path_a or not path_b:
            messagebox.showwarning(
                str(_("Fichiers requis")),
                str(_("Veuillez sélectionner les deux fichiers à comparer.")))
            return
        if not Path(path_a).exists() or not Path(path_b).exists():
            messagebox.showerror(
                str(_("Fichier introuvable")),
                str(_("Un des fichiers sélectionnés n'existe pas.")))
            return

        try:
            lines_a = Path(path_a).read_text(encoding='utf-8', errors='replace').splitlines()
            lines_b = Path(path_b).read_text(encoding='utf-8', errors='replace').splitlines()
        except Exception as exc:
            messagebox.showerror(str(_("Erreur")), str(exc))
            return

        state['file_a'] = path_a
        state['file_b'] = path_b

        text_a.configure(state='normal')
        text_b.configure(state='normal')
        text_a.delete('1.0', tk.END)
        text_b.delete('1.0', tk.END)

        # Générer le diff
        differ = difflib.unified_diff(
            lines_a, lines_b,
            fromfile=Path(path_a).name,
            tofile=Path(path_b).name,
            lineterm='',
        )

        diff_lines = list(differ)

        # Parser le diff pour l'affichage côte à côte
        _display_diff(text_a, text_b, lines_a, lines_b)

        text_a.configure(state='disabled')
        text_b.configure(state='disabled')

        # Statistiques
        added = sum(
            1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        removed = sum(
            1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        modified = max(0, min(added, removed))

        status_var.set(
            str(_("{added} ajouts, {removed} suppressions, {modified} modifications")).format(
                added=added, removed=removed, modified=modified))

    def _clear():
        text_a.configure(state='normal')
        text_b.configure(state='normal')
        text_a.delete('1.0', tk.END)
        text_b.delete('1.0', tk.END)
        text_a.configure(state='disabled')
        text_b.configure(state='disabled')
        file_a_var.set('')
        file_b_var.set('')
        state['file_a'] = None
        state['file_b'] = None
        status_var.set(str(_("Sélectionnez deux fichiers à comparer.")))

    compare_btn.config(command=_compare)
    clear_btn.config(command=_clear)

    return frame


def _display_diff(text_a: tk.Text, text_b: tk.Text,
                  lines_a: list[str], lines_b: list[str]) -> None:
    """Affiche le diff côte à côte dans les deux widgets Text."""
    # Utiliser SequenceMatcher pour une comparaison ligne par ligne
    sm = difflib.SequenceMatcher(None, lines_a, lines_b)

    line_num_a = 1
    line_num_b = 1

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for idx in range(i1, i2):
                line = lines_a[idx]
                text_a.insert(tk.END, f"{line}\n")
                text_b.insert(tk.END, f"{lines_b[j1 + (idx - i1)]}\n")
            line_num_a += (i2 - i1)
            line_num_b += (j2 - j1)
        elif tag == 'replace':
            # Lignes modifiées
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                if i1 + k < i2:
                    line = lines_a[i1 + k]
                    text_a.insert(tk.END, f"{line}\n", _TAG_MODIFIED)
                else:
                    text_a.insert(tk.END, "\n", _TAG_INFO)
                if j1 + k < j2:
                    line = lines_b[j1 + k]
                    text_b.insert(tk.END, f"{line}\n", _TAG_MODIFIED)
                else:
                    text_b.insert(tk.END, "\n", _TAG_INFO)
            line_num_a += max_len
            line_num_b += max_len
        elif tag == 'delete':
            for idx in range(i1, i2):
                line = lines_a[idx]
                text_a.insert(tk.END, f"{line}\n", _TAG_REMOVED)
                text_b.insert(tk.END, "\n", _TAG_INFO)
            line_num_a += (i2 - i1)
            line_num_b += (i2 - i1)
        elif tag == 'insert':
            for idx in range(j1, j2):
                line = lines_b[idx]
                text_a.insert(tk.END, "\n", _TAG_INFO)
                text_b.insert(tk.END, f"{line}\n", _TAG_ADDED)
            line_num_a += (j2 - j1)
            line_num_b += (j2 - j1)


TOOL = Tool(
    id='diff',
    name="DualiS",
    description="Miroir comparatif de deux fichiers texte.",
    category="Édition",
    icon='🪞',
    shortcut='Ctrl+0',
    view=build_diff_view,
    keywords=('diff', 'comparer', 'compare', 'différences', 'differences', 'fichier', 'duo'),
    order=1,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.diff',
        label="DualiS",
        description="Comparer deux fichiers texte côte à côte",
        shortcut='Ctrl+0',
        icon='🪞',
        tool_id='diff',
        keywords=('diff', 'comparer', 'compare', 'différences', 'duo'),
    ))
