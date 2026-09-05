# src/tools/notepad.py
"""Outil Bloc-notes amélioré : éditeur multi-onglets avec surlignage syntaxique."""
from __future__ import annotations

import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.theme import get_color
from src.i18n import _
from src.logger import setup_logger
from ._syntax import SyntaxHighlighter, detect_language

logger = setup_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════════════════════════

_UNSAVED_COUNTER = [0]


def _new_unsaved_name():
    _UNSAVED_COUNTER[0] += 1
    return f"Sans titre {_UNSAVED_COUNTER[0]}"


# ═══════════════════════════════════════════════════════════════════════════
# Vue principale
# ═══════════════════════════════════════════════════════════════════════════

def build_notepad_view(shell) -> ttk.Frame:
    """Construit la vue Bloc-notes amélioré."""
    frame = ttk.Frame(shell.workspace, padding=8)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(2, weight=1)

    # ── Titre ──
    ttk.Label(frame, text=str(_("Bloc-notes amélioré")),
              font=('Segoe UI', 15, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 8))

    # ── Barre de recherche (initialement cachée) ──
    search_frame = ttk.Frame(frame)
    search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
    search_frame.columnconfigure(1, weight=1)

    search_var = tk.StringVar()
    replace_var = tk.StringVar()

    # ── Notebook (onglets) ──
    notebook = ttk.Notebook(frame)
    notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # ── Barre de statut ──
    status_frame = ttk.Frame(frame)
    status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(4, 0))

    status_vars = {}
    status_labels = [
        ('cursor', "Ln 1, Col 1"),
        ('words', str(_("Mots: 0"))),
        ('lines', str(_("Lignes: 0"))),
        ('chars', str(_("Caractères: 0"))),
        ('encoding', "UTF-8"),
        ('lang', "Text"),
    ]
    for key, default in status_labels:
        var = tk.StringVar(value=default)
        ttk.Label(status_frame, textvariable=var, font=('Consolas', 9),
                  foreground=get_color('fg_muted')).pack(side=tk.LEFT, padx=(0, 12))
        status_vars[key] = var

    # ── État interne ──
    state = {
        'tabs': {},           # {tab_id: {'frame': ..., 'text': ..., 'file': Path|None, 'highlighter': ..., 'modified': bool}}
        'current_tab': None,
        'search_visible': False,
        'search_regex': tk.BooleanVar(value=False),
        'search_case': tk.BooleanVar(value=False),
    }

    # ── Boutons d'action ──
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(4, 0))

    ttk.Button(btn_frame, text=str(_("Nouveau")), command=lambda: _new_tab()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text=str(_("Ouvrir")), command=lambda: _open_file()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text=str(_("Sauvegarder")), command=lambda: _save_file()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text=str(_("Sauvegarder sous")), command=lambda: _save_as()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text=str(_("Exporter")), command=lambda: _export_menu()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
    ttk.Button(btn_frame, text=str(_("Rechercher")), command=lambda: _toggle_search()).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text=str(_("Fermer onglet")), command=lambda: _close_tab()).pack(side=tk.LEFT)

    # ═══════════════════════════════════════════════════════════════════
    # Fonctions internes
    # ═══════════════════════════════════════════════════════════════════

    def _new_tab(file_path=None, content=None):
        """Crée un nouvel onglet."""
        tab_id = str(id(object()))
        name = file_path.name if file_path else _new_unsaved_name()

        tab_frame = ttk.Frame(notebook, padding=0)
        notebook.add(tab_frame, text=f" {name} ")
        notebook.select(tab_frame)

        # Text widget avec undo
        text = tk.Text(
            tab_frame,
            undo=True,
            maxundo=100,
            autoseparators=True,
            wrap=tk.WORD,
            font=('Consolas', 11),
            bg=get_color('text_bg'),
            fg=get_color('text_fg'),
            insertbackground=get_color('fg'),
            selectbackground=get_color('select_bg'),
            selectforeground=get_color('select_fg'),
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        scroll_y = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text.yview)
        scroll_x = ttk.Scrollbar(tab_frame, orient=tk.HORIZONTAL, command=text.xview)
        text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Insérer le contenu
        if content:
            text.insert('1.0', content)
            text.edit_reset()  # Pas d'historique pour le contenu initial

        # Surlignage syntaxique
        lang = detect_language(str(file_path) if file_path else None, content or '')
        highlighter = SyntaxHighlighter(text)
        if lang != 'text':
            highlighter.highlight_range('1.0', tk.END, lang)

        # État
        state['tabs'][tab_id] = {
            'frame': tab_frame,
            'text': text,
            'file': file_path,
            'highlighter': highlighter,
            'lang': lang,
            'modified': False,
        }

        # Bindings
        text.bind('<KeyRelease>', lambda e: _on_text_change(tab_id))
        text.bind('<ButtonRelease-1>', lambda e: _update_cursor(tab_id))
        text.bind('<Control-z>', lambda e: _undo(text))
        text.bind('<Control-y>', lambda e: _redo(text))
        text.bind('<Control-a>', lambda e: _select_all(text))
        text.bind('<Control-s>', lambda e: _save_file())
        text.bind('<Control-o>', lambda e: _open_file())
        text.bind('<Control-n>', lambda e: _new_tab())
        text.bind('<Control-w>', lambda e: _close_tab())
        text.bind('<Control-f>', lambda e: _toggle_search())
        text.bind('<Control-h>', lambda e: _toggle_search())
        text.bind('<Tab>', lambda e: _indent(text))
        text.bind('<Shift-Tab>', lambda e: _dedent(text))
        text.bind('<F3>', lambda e: _find_next())
        text.bind('<Return>', lambda e: _auto_indent(text))

        state['current_tab'] = tab_id
        _on_text_change(tab_id)
        return tab_id

    def _on_text_change(tab_id):
        """Met à jour les stats quand le texte change."""
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        text = tab['text']
        content = text.get('1.0', tk.END).rstrip('\n')

        # Stats
        words = len(content.split()) if content.strip() else 0
        lines = content.count('\n') + 1
        chars = len(content)

        status_vars['words'].set(f"{str(_('Mots:'))} {words}")
        status_vars['lines'].set(f"{str(_('Lignes:'))} {lines}")
        status_vars['chars'].set(f"{str(_('Caractères:'))} {chars}")

        # Marquer comme modifié
        if not tab['modified']:
            tab['modified'] = True
            _update_tab_title(tab_id)

        # Re-surligner si changement de langage
        new_lang = detect_language(str(tab['file']) if tab['file'] else None, content)
        if new_lang != tab['lang']:
            tab['lang'] = new_lang
            status_vars['lang'].set(new_lang.title())
            tab['highlighter'].highlight_range('1.0', tk.END, new_lang)

    def _update_cursor(tab_id):
        """Met à jour la position du curseur."""
        tab = state['tabs'].get(tab_id)
        if not tab:
            return
        text = tab['text']
        pos = text.index(tk.INSERT)
        line, col = pos.split('.')
        status_vars['cursor'].set(f"Ln {line}, Col {int(col) + 1}")

    def _update_tab_title(tab_id):
        """Met à jour le titre de l'onglet (avec * si modifié)."""
        tab = state['tabs'].get(tab_id)
        if not tab:
            return
        name = tab['file'].name if tab['file'] else _get_tab_name(tab_id)
        modified = " *" if tab['modified'] else ""
        try:
            idx = notebook.index(tab['frame'])
            notebook.tab(idx, text=f" {name}{modified} ")
        except Exception:
            logger.debug("Exception updating tab title", exc_info=True)

    def _get_tab_name(tab_id):
        """Retourne le nom de l'onglet depuis le titre du notebook."""
        tab = state['tabs'].get(tab_id)
        if not tab:
            return "Sans titre"
        try:
            idx = notebook.index(tab['frame'])
            return notebook.tab(idx, 'text').strip().replace(' *', '')
        except Exception:
            return "Sans titre"

    def _close_tab():
        """Ferme l'onglet courant."""
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        if tab['modified']:
            name = _get_tab_name(tab_id)
            if not messagebox.askyesno(str(_("Fermer")),
                                       str(_("Le fichier '{name}' a été modifié. Fermer sans sauvegarder ?")).format(name=name)):
                return

        notebook.forget(tab['frame'])
        tab['text'].destroy()
        del state['tabs'][tab_id]

        if notebook.index('end') > 0:
            state['current_tab'] = _get_current_tab_id()
        else:
            state['current_tab'] = None
            _new_tab()

    def _get_current_tab_id():
        """Retourne l'id de l'onglet sélectionné."""
        try:
            current_frame = notebook.select()
            for tab_id, tab in state['tabs'].items():
                if str(tab['frame']) == str(current_frame):
                    return tab_id
        except Exception:
            logger.debug("Exception getting current tab ID", exc_info=True)
        return None

    def _on_tab_change(_event):
        """Appelé quand l'onglet change."""
        tab_id = _get_current_tab_id()
        if tab_id:
            state['current_tab'] = tab_id
            tab = state['tabs'].get(tab_id)
            if tab:
                status_vars['lang'].set(tab['lang'].title())
                _update_cursor(tab_id)

    notebook.bind('<<NotebookTabChanged>>', _on_tab_change)

    # ── Fichier ──

    def _open_file():
        path = filedialog.askopenfilename(
            title=str(_("Ouvrir un fichier")),
            filetypes=[
                ("Tous les fichiers", "*.*"),
                ("Texte", "*.txt *.md"),
                ("Python", "*.py"),
                ("JavaScript", "*.js"),
                ("JSON", "*.json"),
                ("HTML", "*.html *.htm"),
                ("CSS", "*.css"),
            ])
        if path:
            p = Path(path)
            try:
                content = p.read_text(encoding='utf-8', errors='replace')
                _new_tab(file_path=p, content=content)
                tab_id = state['current_tab']
                if tab_id:
                    state['tabs'][tab_id]['modified'] = False
                    _update_tab_title(tab_id)
            except Exception as exc:
                messagebox.showerror(str(_("Erreur")), str(exc))

    def _save_file():
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return
        if tab['file']:
            _write_file(tab['file'], tab['text'])
            tab['modified'] = False
            _update_tab_title(tab_id)
        else:
            _save_as()

    def _save_as():
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return
        path = filedialog.asksaveasfilename(
            title=str(_("Sauvegarder sous")),
            defaultextension=".txt",
            filetypes=[
                ("Texte", "*.txt"),
                ("Markdown", "*.md"),
                ("Python", "*.py"),
                ("JSON", "*.json"),
                ("HTML", "*.html"),
                ("CSS", "*.css"),
                ("Tous", "*.*"),
            ])
        if path:
            p = Path(path)
            _write_file(p, tab['text'])
            tab['file'] = p
            tab['modified'] = False
            _update_tab_title(tab_id)

    def _write_file(path, text):
        try:
            content = text.get('1.0', tk.END).rstrip('\n')
            path.write_text(content, encoding='utf-8')
        except Exception as exc:
            messagebox.showerror(str(_("Erreur")), str(exc))

    def _export_menu():
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        path = filedialog.asksaveasfilename(
            title=str(_("Exporter en...")),
            filetypes=[
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("HTML", "*.html"),
                ("Tous", "*.*"),
            ])
        if not path:
            return

        p = Path(path)
        content = tab['text'].get('1.0', tk.END).rstrip('\n')

        try:
            if p.suffix.lower() == '.json':
                data = {"content": content, "language": tab['lang']}
                p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            elif p.suffix.lower() == '.html':
                html = _export_html(content, tab['lang'])
                p.write_text(html, encoding='utf-8')
            else:
                p.write_text(content, encoding='utf-8')
        except Exception as exc:
            messagebox.showerror(str(_("Erreur")), str(exc))

    def _export_html(content, lang):
        """Exporte le texte en HTML avec surlignage basique."""
        import html
        escaped = html.escape(content)
        lines = escaped.split('\n')
        numbered = '\n'.join(f'<span class="line-num">{i+1:>4}</span>  {l}'
                            for i, l in enumerate(lines, 1))
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Export TE</title>
<style>
body {{ background: #1E1E1E; color: #D4D4D4; font-family: Consolas, monospace; padding: 20px; }}
.line-num {{ color: #858585; user-select: none; }}
pre {{ white-space: pre-wrap; word-wrap: break-word; }}
</style>
</head>
<body>
<pre>{numbered}</pre>
</body>
</html>"""

    # ── Recherche ──

    def _toggle_search():
        state['search_visible'] = not state['search_visible']
        if state['search_visible']:
            search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
            search_entry.focus_set()
        else:
            search_frame.grid_forget()

    def _do_search(event=None):
        """Recherche la prochaine occurrence."""
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        query = search_var.get()
        if not query:
            return

        text = tab['text']
        text.tag_remove('search_highlight', '1.0', tk.END)

        try:
            if state['search_regex'].get():
                pattern = re.compile(query, 0 if not state['search_case'].get() else re.IGNORECASE)
            else:
                flags = 0 if state['search_case'].get() else re.IGNORECASE
                pattern = re.compile(re.escape(query), flags)
        except re.error:
            return

        content = text.get('1.0', tk.END)
        count = 0
        for match in pattern.finditer(content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            text.tag_add('search_highlight', start, end)
            count += 1

        text.tag_configure('search_highlight', background=get_color('warning'), foreground=get_color('select_fg'))

    def _find_next():
        _do_search()

    def _replace_one():
        """Remplace l'occurrence suivante."""
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        text = tab['text']
        query = search_var.get()
        replace = replace_var.get()
        if not query:
            return

        # Trouver et sélectionner l'occurrence suivante
        sel = text.tag_ranges('search_highlight')
        if sel:
            text.mark_set(tk.INSERT, sel[0])
            text.delete(sel[0], sel[1])
            text.insert(tk.INSERT, replace)
            _do_search()

    def _replace_all():
        """Remplace toutes les occurrences."""
        tab_id = state['current_tab']
        if not tab_id:
            return
        tab = state['tabs'].get(tab_id)
        if not tab:
            return

        text = tab['text']
        query = search_var.get()
        replace = replace_var.get()
        if not query:
            return

        content = text.get('1.0', tk.END).rstrip('\n')
        try:
            if state['search_regex'].get():
                pattern = re.compile(query, 0 if not state['search_case'].get() else re.IGNORECASE)
            else:
                flags = 0 if state['search_case'].get() else re.IGNORECASE
                pattern = re.compile(re.escape(query), flags)
            new_content = pattern.sub(replace, content)
            text.delete('1.0', tk.END)
            text.insert('1.0', new_content)
            _do_search()
        except re.error:
            pass

    # ── Édition ──

    def _undo(text):
        try:
            text.edit_undo()
        except tk.TclError:
            pass

    def _redo(text):
        try:
            text.edit_redo()
        except tk.TclError:
            pass

    def _select_all(text):
        text.tag_add(tk.SEL, '1.0', tk.END)
        return "break"

    def _indent(text):
        """Indentation de 2 espaces."""
        try:
            sel = text.tag_ranges(tk.SEL)
            if sel:
                start = sel[0].string
                end = sel[1].string
                lines = text.get(start, end).split('\n')
                indented = '\n'.join('  ' + l for l in lines)
                text.delete(start, end)
                text.insert(start, indented)
            else:
                text.insert(tk.INSERT, '  ')
        except Exception:
            text.insert(tk.INSERT, '  ')
        return "break"

    def _dedent(text):
        """Désindentation."""
        try:
            pos = tk.INSERT
            line_start = text.index(f"{pos} linestart")
            line_end = text.index(f"{pos} lineend")
            line = text.get(line_start, line_end)
            if line.startswith('  '):
                text.delete(line_start, line_end)
                text.insert(line_start, line[2:])
            elif line.startswith('\t'):
                text.delete(line_start, line_end)
                text.insert(line_start, line[1:])
        except Exception:
            logger.debug("Exception dedenting line", exc_info=True)
        return "break"

    def _auto_indent(text):
        """Indentation automatique après Entrée."""
        try:
            pos = tk.INSERT
            line_start = text.index(f"{pos} linestart")
            line = text.get(line_start, pos)
            indent = ''
            for ch in line:
                if ch in ' \t':
                    indent += ch
                else:
                    break
            text.insert(tk.INSERT, '\n' + indent)
        except Exception:
            text.insert(tk.INSERT, '\n')
        return "break"

    # ── Construction barre de recherche ──

    def _build_search_bar(parent, main_frame):
        ttk.Label(parent, text=str(_("Rechercher :"))).grid(row=0, column=0, padx=(0, 4))
        search_entry = ttk.Entry(parent, textvariable=search_var, width=25)
        search_entry.grid(row=0, column=1, padx=(0, 4))
        search_entry.bind('<Return>', _do_search)

        ttk.Checkbutton(parent, text="Regex", variable=state['search_regex']).grid(row=0, column=2, padx=4)
        ttk.Checkbutton(parent, text=str(_("Casse")), variable=state['search_case']).grid(row=0, column=3, padx=4)

        ttk.Button(parent, text="▶", width=3, command=_do_search).grid(row=0, column=4, padx=2)

        ttk.Label(parent, text=str(_("Remplacer :"))).grid(row=0, column=5, padx=(8, 4))
        ttk.Entry(parent, textvariable=replace_var, width=25).grid(row=0, column=6, padx=(0, 4))
        ttk.Button(parent, text=str(_("1")), width=3, command=_replace_one).grid(row=0, column=7, padx=2)
        ttk.Button(parent, text=str(_("Tout")), width=3, command=_replace_all).grid(row=0, column=8, padx=2)

    _build_search_bar(search_frame, frame)

    # ── Créer le premier onglet ──
    _new_tab()

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════════

TOOL = Tool(
    id='notepad',
    name="Bloc-notes amélioré",
    description="Éditeur multi-onglets avec surlignage syntaxique.",
    category="Édition",
    icon='📝',
    shortcut='Ctrl+Shift+N',
    view=build_notepad_view,
    keywords=('bloc-notes', 'editeur', 'texte', 'code', 'syntaxique', 'onglets'),
    order=4,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.notepad',
        label="Bloc-notes amélioré",
        description="Éditeur multi-onglets avec surlignage syntaxique",
        shortcut='Ctrl+Shift+N',
        icon='📝',
        tool_id='notepad',
        keywords=('bloc-notes', 'editeur', 'texte', 'code', 'syntaxique'),
    ))
