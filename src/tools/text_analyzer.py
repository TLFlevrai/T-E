# src/tools/text_analyzer.py
"""Outil Analyseur de texte : statistiques, fréquence, encodage, minification, comparaison."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.theme import get_color
from src.i18n import _
from src.logger import setup_logger
from ._text_stats import (
    compute_stats, word_frequency, detect_encoding, minify, quick_compare,
)

logger = setup_logger(__name__)


def build_analyzer_view(shell) -> ttk.Frame:
    """Construit la vue Analyseur de texte."""
    frame = ttk.Frame(shell.workspace, padding=12)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text=str(_("Analyseur de texte")),
              font=('Segoe UI', 15, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 12))

    state = {'text': ''}

    # ── Zone de saisie ──
    input_frame = ttk.LabelFrame(frame, text=str(_("Source")), padding=8)
    input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
    input_frame.columnconfigure(1, weight=1)

    file_var = tk.StringVar()
    ttk.Label(input_frame, text=str(_("Fichier :"))).grid(row=0, column=0, padx=(0, 6))
    ttk.Entry(input_frame, textvariable=file_var, state='readonly').grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6))

    def _browse():
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner un fichier texte")),
            filetypes=[("Texte", "*.txt *.py *.js *.css *.html *.json *.md *.csv"),
                       ("Tous", "*.*")])
        if path:
            file_var.set(path)
            try:
                text = Path(path).read_text(encoding='utf-8', errors='replace')
                text_input.delete('1.0', tk.END)
                text_input.insert('1.0', text)
                _analyze()
            except Exception as exc:
                messagebox.showerror(str(_("Erreur")), str(exc))

    ttk.Button(input_frame, text=str(_("Parcourir...")), command=_browse).grid(row=0, column=2)

    ttk.Label(input_frame, text=str(_("Ou collez du texte :"))).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(6, 2))

    text_input = tk.Text(input_frame, height=4, wrap=tk.WORD,
                         font=('Consolas', 10), bg=get_color('text_bg'), fg=get_color('text_fg'),
                         insertbackground=get_color('fg'), bd=0, highlightthickness=0)
    text_input.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E))
    text_input.bind('<KeyRelease>', lambda e: _analyze())

    input_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=text_input.yview)
    text_input.configure(yscrollcommand=input_scroll.set)
    input_scroll.grid(row=2, column=3, sticky=tk.NS)

    # ── Boutons d'action ──
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

    ttk.Button(btn_frame, text=str(_("Analyser")), command=lambda: _analyze(),
               style='AppPrimary.TButton').pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(btn_frame, text=str(_("Effacer")), command=lambda: _clear()).pack(side=tk.LEFT)

    # ── Résultats (notebook à onglets) ──
    notebook = ttk.Notebook(frame)
    notebook.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 8))
    frame.rowconfigure(3, weight=1)

    # Onglet 1 : Statistiques
    stats_frame = ttk.Frame(notebook, padding=8)
    notebook.add(stats_frame, text=str(_("📈 Statistiques")))

    stats_vars = {}
    stats_labels = [
        ('lines', _("Lignes")),
        ('words', _("Mots")),
        ('chars_with_spaces', _("Caractères (avec espaces)")),
        ('chars_without_spaces', _("Caractères (sans espaces)")),
        ('sentences', _("Phrases")),
        ('paragraphs', _("Paragraphes")),
        ('avg_words_per_sentence', _("Mots moyens/phrase")),
        ('empty_lines', _("Lignes vides")),
        ('max_line_length', _("Plus longue ligne")),
    ]
    for i, (key, label) in enumerate(stats_labels):
        ttk.Label(stats_frame, text=f"{label} :", font=('Segoe UI', 10)).grid(row=i, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar(value="—")
        ttk.Label(stats_frame, textvariable=var, font=('Consolas', 10, 'bold')).grid(row=i, column=1, sticky=tk.W, padx=(12, 0), pady=2)
        stats_vars[key] = var

    # Onglet 2 : Fréquence
    freq_frame = ttk.Frame(notebook, padding=8)
    notebook.add(freq_frame, text=str(_("📊 Fréquence")))

    freq_text = tk.Text(freq_frame, height=10, wrap=tk.NONE,
                        font=('Consolas', 10), bg=get_color('text_bg'), fg=get_color('text_fg'),
                        insertbackground=get_color('fg'), bd=0, highlightthickness=0,
                        state='disabled')
    freq_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    freq_frame.columnconfigure(0, weight=1)
    freq_frame.rowconfigure(0, weight=1)
    freq_scroll = ttk.Scrollbar(freq_frame, orient=tk.VERTICAL, command=freq_text.yview)
    freq_text.configure(yscrollcommand=freq_scroll.set)
    freq_scroll.grid(row=0, column=1, sticky=tk.NS)

    # Onglet 3 : Encodage
    enc_frame = ttk.Frame(notebook, padding=8)
    notebook.add(enc_frame, text=str(_("🔍 Encodage")))

    enc_vars = {}
    enc_labels = [
        ('encoding', _("Encodage")),
        ('confidence', _("Confiance")),
        ('bom', _("BOM")),
        ('line_ending', _("Fin de ligne")),
    ]
    for i, (key, label) in enumerate(enc_labels):
        ttk.Label(enc_frame, text=f"{label} :", font=('Segoe UI', 10)).grid(row=i, column=0, sticky=tk.W, pady=4)
        var = tk.StringVar(value="—")
        ttk.Label(enc_frame, textvariable=var, font=('Consolas', 10, 'bold')).grid(row=i, column=1, sticky=tk.W, padx=(12, 0), pady=4)
        enc_vars[key] = var

    # Onglet 4 : Minification
    min_frame = ttk.Frame(notebook, padding=8)
    notebook.add(min_frame, text=str(_("📦 Minification")))

    ttk.Label(min_frame, text=str(_("Format :")), font=('Segoe UI', 10)).grid(row=0, column=0, sticky=tk.W)
    min_fmt_var = tk.StringVar(value="auto")
    fmt_menu = ttk.OptionMenu(min_frame, min_fmt_var, "auto", "auto", "JS", "CSS", "HTML")
    fmt_menu.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))

    min_result_var = tk.StringVar(value="")
    ttk.Label(min_frame, textvariable=min_result_var, font=('Consolas', 10)).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

    min_text = tk.Text(min_frame, height=6, wrap=tk.WORD,
                       font=('Consolas', 9), bg=get_color('text_bg'), fg=get_color('text_fg'),
                       insertbackground=get_color('fg'), bd=0, highlightthickness=0,
                       state='disabled')
    min_text.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(8, 0))
    min_frame.columnconfigure(0, weight=1)
    min_frame.rowconfigure(2, weight=1)

    min_scroll = ttk.Scrollbar(min_frame, orient=tk.VERTICAL, command=min_text.yview)
    min_text.configure(yscrollcommand=min_scroll.set)
    min_scroll.grid(row=2, column=2, sticky=tk.NS)

    ttk.Button(min_frame, text=str(_("Minifier")), command=lambda: _do_minify()).grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))

    # Onglet 5 : Comparaison
    cmp_frame = ttk.Frame(notebook, padding=8)
    notebook.add(cmp_frame, text=str(_("🪞 Comparaison")))

    cmp_frame.columnconfigure(1, weight=1)

    ttk.Label(cmp_frame, text=str(_("Texte A :")), font=('Segoe UI', 10)).grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
    cmp_text_a = tk.Text(cmp_frame, height=4, wrap=tk.WORD,
                         font=('Consolas', 9), bg=get_color('text_bg'), fg=get_color('text_fg'),
                         insertbackground=get_color('fg'), bd=0, highlightthickness=0)
    cmp_text_a.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 4))

    ttk.Label(cmp_frame, text=str(_("Texte B :")), font=('Segoe UI', 10)).grid(row=2, column=0, sticky=tk.W, pady=(0, 2))
    cmp_text_b = tk.Text(cmp_frame, height=4, wrap=tk.WORD,
                         font=('Consolas', 9), bg=get_color('text_bg'), fg=get_color('text_fg'),
                         insertbackground=get_color('fg'), bd=0, highlightthickness=0)
    cmp_text_b.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 4))

    cmp_result_var = tk.StringVar(value="")
    ttk.Label(cmp_frame, textvariable=cmp_result_var, font=('Consolas', 10, 'bold')).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

    ttk.Button(cmp_frame, text=str(_("Comparer")), command=lambda: _do_compare()).grid(row=5, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))

    # ── Logique ──

    def _analyze():
        text = text_input.get('1.0', tk.END).rstrip('\n')
        state['text'] = text

        # Stats
        stats = compute_stats(text)
        for key, var in stats_vars.items():
            val = stats.get(key, '—')
            if isinstance(val, float):
                val = f"{val:.1f}"
            var.set(str(val))

        # Fréquence
        freq = word_frequency(text, top_n=10)
        freq_text.configure(state='normal')
        freq_text.delete('1.0', tk.END)
        if freq:
            max_count = freq[0][1] if freq else 1
            for word, count, pct in freq:
                bar_len = int(count / max_count * 20)
                bar = '█' * bar_len
                line = f"{word:<15} {bar:<20} {count:>5} ({pct}%)\n"
                freq_text.insert(tk.END, line)
        else:
            freq_text.insert(tk.END, str(_("Aucun mot détecté.")))
        freq_text.configure(state='disabled')

        # Encodage (si fichier chargé)
        fpath = file_var.get()
        if fpath and Path(fpath).exists():
            enc = detect_encoding(Path(fpath))
        else:
            enc = detect_encoding_bytes(text.encode('utf-8'))
        for key, var in enc_vars.items():
            var.set(str(enc.get(key, '—')))

    def _clear():
        text_input.delete('1.0', tk.END)
        file_var.set('')
        state['text'] = ''
        for var in stats_vars.values():
            var.set('—')
        for var in enc_vars.values():
            var.set('—')
        freq_text.configure(state='normal')
        freq_text.delete('1.0', tk.END)
        freq_text.configure(state='disabled')
        min_result_var.set('')
        min_text.configure(state='normal')
        min_text.delete('1.0', tk.END)
        min_text.configure(state='disabled')
        cmp_result_var.set('')
        cmp_text_a.delete('1.0', tk.END)
        cmp_text_b.delete('1.0', tk.END)

    def _do_minify():
        text = text_input.get('1.0', tk.END).rstrip('\n')
        if not text.strip():
            messagebox.showerror(str(_("Erreur")), str(_("Entrez du texte à minifier.")))
            return
        fmt = min_fmt_var.get().lower()
        result = minify(text, fmt)
        min_result_var.set(
            f"{result['format'].upper()} — "
            f"{result['original_size']} → {result['minified_size']} octets "
            f"(−{result['gain_pct']}%)"
        )
        min_text.configure(state='normal')
        min_text.delete('1.0', tk.END)
        min_text.insert('1.0', result['minified'])
        min_text.configure(state='disabled')

    def _do_compare():
        a = cmp_text_a.get('1.0', tk.END).rstrip('\n')
        b = cmp_text_b.get('1.0', tk.END).rstrip('\n')
        if not a and not b:
            messagebox.showerror(str(_("Erreur")), str(_("Entrez au moins un texte.")))
            return
        result = quick_compare(a, b)
        cmp_result_var.set(
            f"{str(_('Identiques'))} : {result['identical_pct']}% | "
            f"{str(_('Ajoutées'))} : {result['added']} | "
            f"{str(_('Supprimées'))} : {result['removed']}"
        )

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════════

TOOL = Tool(
    id='text_analyzer',
    name="Analyseur de texte",
    description="Statistiques, fréquence, encodage, minification et comparaison.",
    category="Édition",
    icon='📊',
    shortcut='Ctrl+Shift+A',
    view=build_analyzer_view,
    keywords=('analyse', 'stats', 'fréquence', 'minifier', 'comparer', 'encodage', 'texte'),
    order=3,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.text_analyzer',
        label="Analyseur de texte",
        description="Analyser un texte : stats, fréquence, encodage, minification",
        shortcut='Ctrl+Shift+A',
        icon='📊',
        tool_id='text_analyzer',
        keywords=('analyse', 'stats', 'fréquence', 'minifier', 'comparer', 'texte'),
    ))
