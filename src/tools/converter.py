# src/tools/converter.py
"""Outil Conversion : convertisseurs de fichiers (TXT↔PDF, JSON→TXT)."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from threading import Thread

from src.core.command_registry import Command
from src.core.tool import Tool
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)

CONVERSION_MODES = [
    ("TXT → PDF", "txt_to_pdf"),
    ("PDF → TXT", "pdf_to_txt"),
    ("JSON → TXT", "json_to_txt"),
]


def build_convert_view(shell) -> ttk.Frame:
    """Construit la vue Conversion intégrée au workspace."""
    frame = ttk.Frame(shell.workspace, padding=16)
    frame.columnconfigure(0, weight=1)

    title = ttk.Label(frame, text=str(_("Convertisseur de fichiers")),
                      font=('Segoe UI', 15, 'bold'))
    title.grid(row=0, column=0, sticky=tk.W, pady=(0, 16))

    # --- Sélection du mode ---
    mode_frame = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    mode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
    mode_frame.columnconfigure(1, weight=1)

    ttk.Label(mode_frame, text=str(_("Mode :")),
              style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
        row=0, column=0, padx=(0, 10))

    mode_var = tk.StringVar(value="txt_to_pdf")
    mode_menu = ttk.OptionMenu(mode_frame, mode_var, "TXT → PDF",
                                *[label for label, _ in CONVERSION_MODES])
    mode_menu.grid(row=0, column=1, sticky=(tk.W, tk.E))

    # --- Fichier source ---
    src_frame = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    src_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
    src_frame.columnconfigure(1, weight=1)

    ttk.Label(src_frame, text=str(_("Source :")),
              style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
        row=0, column=0, padx=(0, 10))

    src_var = tk.StringVar()
    src_entry = ttk.Entry(src_frame, textvariable=src_var, state='readonly')
    src_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 8))

    src_btn = ttk.Button(src_frame, text=str(_("Parcourir")),
                          style='AppGhost.TButton')
    src_btn.grid(row=0, column=2)

    # --- Fichier destination ---
    dst_frame = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    dst_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
    dst_frame.columnconfigure(1, weight=1)

    ttk.Label(dst_frame, text=str(_("Destination :")),
              style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
        row=0, column=0, padx=(0, 10))

    dst_var = tk.StringVar()
    dst_entry = ttk.Entry(dst_frame, textvariable=dst_var, state='readonly')
    dst_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 8))

    dst_btn = ttk.Button(dst_frame, text=str(_("Parcourir")),
                          style='AppGhost.TButton')
    dst_btn.grid(row=0, column=2)

    # --- Options ---
    opts_frame = ttk.Frame(frame, style='Card.TFrame', padding=(14, 10))
    opts_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
    opts_frame.columnconfigure(1, weight=1)

    ttk.Label(opts_frame, text=str(_("Options :")),
              style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

    encoding_var = tk.StringVar(value="utf-8")
    ttk.Label(opts_frame, text=str(_("Encodage :")),
              style='Card.TLabel').grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.OptionMenu(opts_frame, encoding_var, "utf-8",
                    "utf-8", "latin-1", "cp1252", "ascii").grid(
        row=1, column=1, sticky=tk.W, pady=2)

    indent_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(opts_frame, text=str(_("Indentation JSON (2 espaces)")),
                     variable=indent_var).grid(
        row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

    # --- Barre de progression ---
    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(8, 4))

    status_var = tk.StringVar(value=_("Prêt"))
    status_label = ttk.Label(frame, textvariable=status_var,
                              style='Status.TLabel')
    status_label.grid(row=6, column=0, sticky=tk.W)

    # --- Boutons d'action ---
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(14, 0))

    convert_btn = ttk.Button(btn_frame, text=str(_("Convertir")),
                              style='AppPrimary.TButton', state='disabled')
    convert_btn.pack(side=tk.RIGHT, padx=(6, 0))

    # --- Log ---
    log_frame = ttk.Frame(frame, style='Card.TFrame', padding=(10, 6))
    log_frame.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(12, 0))
    frame.rowconfigure(8, weight=1)
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)

    log_text = tk.Text(log_frame, height=8, wrap=tk.WORD,
                       bg='#1B2027', fg='#E7EBF0', insertbackground='#E7EBF0',
                       font=('Consolas', 9), bd=0, highlightthickness=0)
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_text.configure(state='disabled')

    # --- État interne ---
    state = {
        'src_path': None,
        'dst_path': None,
    }

    def log(msg: str):
        log_text.configure(state='normal')
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
        log_text.configure(state='disabled')

    def _update_dst_from_mode(*_):
        src = state['src_path']
        if src is None:
            return
        mode = mode_var.get()
        if mode == "txt_to_pdf":
            dst = src.with_suffix('.pdf')
        elif mode == "pdf_to_txt":
            dst = src.with_suffix('.txt')
        elif mode == "json_to_txt":
            dst = src.with_suffix('.txt')
        else:
            dst = src.with_suffix('.out')
        state['dst_path'] = dst
        dst_var.set(str(dst))
        convert_btn.config(state='normal')

    def _select_src():
        mode = mode_var.get()
        if mode == "txt_to_pdf":
            ftypes = [("Fichiers TXT", "*.txt"), ("Tous les fichiers", "*.*")]
        elif mode == "pdf_to_txt":
            ftypes = [("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        elif mode == "json_to_txt":
            ftypes = [("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")]
        else:
            ftypes = [("Tous les fichiers", "*.*")]
        path = filedialog.askopenfilename(
            title=_("Sélectionner un fichier source"), filetypes=ftypes)
        if path:
            state['src_path'] = Path(path)
            src_var.set(str(state['src_path']))
            _update_dst_from_mode()

    def _select_dst():
        mode = mode_var.get()
        if mode == "txt_to_pdf":
            ext, ftypes = ".pdf", [("Fichiers PDF", "*.pdf")]
        elif mode == "pdf_to_txt":
            ext, ftypes = ".txt", [("Fichiers TXT", "*.txt")]
        elif mode == "json_to_txt":
            ext, ftypes = ".txt", [("Fichiers TXT", "*.txt")]
        else:
            ext, ftypes = ".out", []
        path = filedialog.asksaveasfilename(
            title=_("Enregistrer le fichier"),
            defaultextension=ext, filetypes=ftypes)
        if path:
            state['dst_path'] = Path(path)
            dst_var.set(str(state['dst_path']))

    def _do_convert():
        src = state['src_path']
        dst = state['dst_path']
        mode = mode_var.get()
        encoding = encoding_var.get()
        indent = indent_var.get()

        if not src or not src.exists():
            messagebox.showerror(_("Erreur"), _("Fichier source invalide."))
            return
        if not dst:
            messagebox.showerror(_("Erreur"), _("Spécifiez un fichier de destination."))
            return

        convert_btn.config(state='disabled')
        progress_var.set(0)
        status_var.set(_("Conversion en cours..."))
        log(f"→ {mode.replace('_', ' ').upper()} : {src.name} → {dst.name}")

        def run():
            try:
                progress_var.set(20)
                if mode == "txt_to_pdf":
                    _convert_txt_to_pdf(src, dst, encoding, log)
                elif mode == "pdf_to_txt":
                    _convert_pdf_to_txt(src, dst, encoding, log)
                elif mode == "json_to_txt":
                    _convert_json_to_txt(src, dst, encoding, indent, log)
                progress_var.set(100)
                status_var.set(_("Conversion terminée !"))
                log(f"✓ Fichier créé : {dst.name}")
            except Exception as e:
                logger.error(f"Erreur conversion : {e}")
                status_var.set(_("Erreur lors de la conversion"))
                log(f"✗ Erreur : {e}")
                messagebox.showerror(_("Erreur"), str(e))
            finally:
                convert_btn.config(state='normal')

        Thread(target=run, daemon=True).start()

    src_btn.config(command=_select_src)
    dst_btn.config(command=_select_dst)
    convert_btn.config(command=_do_convert)
    mode_var.trace_add('write', _update_dst_from_mode)

    return frame


# --- Fonctions de conversion ---


def _convert_txt_to_pdf(src: Path, dst: Path, encoding: str, log):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    text = src.read_text(encoding=encoding, errors='replace')
    for line in text.split('\n'):
        pdf.cell(0, 5, txt=line, ln=True)
    pdf.output(str(dst))


def _convert_pdf_to_txt(src: Path, dst: Path, encoding: str, log):
    from PyPDF2 import PdfReader
    reader = PdfReader(str(src))
    parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            parts.append(f"--- Page {i + 1} ---\n{text}")
        log(f"  Page {i + 1}/{len(reader.pages)} lue")
    result = "\n\n".join(parts)
    dst.write_text(result, encoding=encoding)


def _convert_json_to_txt(src: Path, dst: Path, encoding: str, indent: bool, log):
    raw = src.read_text(encoding=encoding, errors='replace')
    data = json.loads(raw)
    if indent:
        formatted = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    else:
        formatted = json.dumps(data, ensure_ascii=False, default=str)
    dst.write_text(formatted, encoding=encoding)


# --- Registration ---


TOOL = Tool(
    id='convert',
    name="Conversion",
    description="Convertir des fichiers : TXT↔PDF, JSON→TXT.",
    category="Utilitaires",
    icon='🔄',
    shortcut='Ctrl+2',
    view=build_convert_view,
    keywords=('convertir', 'convert', 'pdf', 'txt', 'json', 'fichier'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.convert',
        label="Conversion",
        description="Convertir des fichiers TXT, PDF, JSON",
        shortcut='Ctrl+2',
        icon='🔄',
        tool_id='convert',
        keywords=('convertir', 'convert', 'pdf', 'txt', 'json'),
    ))
