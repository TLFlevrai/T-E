# src/tools/converter.py
"""Outil Conversion : convertisseurs de fichiers multi-formats.

Modes :
- TXT ↔ PDF, JSON → TXT
- Vidéo → MP3 (via yt-dlp)
- Images : PNG ↔ JPG ↔ BMP ↔ WEBP (+ redimensionnement)
- CSV → JSON
- Audio : MP3 → WAV, WAV → MP3
- Conversion par lot (plusieurs fichiers)
"""
from __future__ import annotations

import csv
import io
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.app_guard import safe_after
from src.gui.theme import get_color
from src.i18n import _
from src.logger import setup_logger

logger = setup_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Vue principale
# ═══════════════════════════════════════════════════════════════════════════

def build_convert_view(shell) -> ttk.Frame:
    """Construit la vue Conversion avec onglets."""
    frame = ttk.Frame(shell.workspace, padding=12)

    title = ttk.Label(frame, text=str(_("Convertisseur de fichiers")),
                      font=('Segoe UI', 15, 'bold'))
    title.pack(anchor=tk.W, pady=(0, 10))

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    notebook.add(_build_document_tab(notebook), text=str(_("Documents")))
    notebook.add(_build_video_tab(notebook), text=str(_("Vidéo → MP3")))
    notebook.add(_build_image_tab(notebook), text=str(_("Images")))
    notebook.add(_build_csv_tab(notebook), text=str(_("CSV → JSON")))
    notebook.add(_build_audio_tab(notebook), text=str(_("Audio")))
    notebook.add(_build_batch_tab(notebook), text=str(_("Par lot")))

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet Documents (TXT↔PDF, JSON→TXT) — conservé de l'ancien code
# ═══════════════════════════════════════════════════════════════════════════

def _build_document_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    mode_var = tk.StringVar(value="txt_to_pdf")
    modes = [("TXT → PDF", "txt_to_pdf"), ("PDF → TXT", "pdf_to_txt"), ("JSON → TXT", "json_to_txt")]
    ttk.Label(frame, text=str(_("Mode :")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
    ttk.OptionMenu(frame, mode_var, "TXT → PDF", *[l for l, _ in modes]).pack(fill=tk.X, pady=(0, 8))

    src_var, dst_var = tk.StringVar(), tk.StringVar()
    state = {'src': None, 'dst': None}

    file_frame = ttk.Frame(frame)
    file_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(file_frame, text=str(_("Source :"))).pack(anchor=tk.W)
    src_entry = ttk.Entry(file_frame, textvariable=src_var, state='readonly')
    src_entry.pack(fill=tk.X)
    ttk.Button(file_frame, text=str(_("Parcourir...")),
               command=lambda: _browse_file(state, src_var, mode_var, dst_var)).pack(anchor=tk.W, pady=2)

    ttk.Label(file_frame, text=str(_("Destination :"))).pack(anchor=tk.W)
    dst_entry = ttk.Entry(file_frame, textvariable=dst_var, state='readonly')
    dst_entry.pack(fill=tk.X)
    ttk.Button(file_frame, text=str(_("Enregistrer...")),
               command=lambda: _save_file(state, dst_var, mode_var)).pack(anchor=tk.W, pady=2)

    encoding_var = tk.StringVar(value="utf-8")
    ttk.Label(frame, text=str(_("Encodage :"))).pack(anchor=tk.W)
    ttk.OptionMenu(frame, encoding_var, "utf-8", "utf-8", "latin-1", "cp1252").pack(fill=tk.X, pady=(0, 8))

    indent_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text=str(_("Indentation JSON")), variable=indent_var).pack(anchor=tk.W)

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert():
        src, dst = state['src'], state['dst']
        if not src or not src.exists():
            messagebox.showerror(str(_("Erreur")), str(_("Fichier source invalide.")))
            return
        if not dst:
            messagebox.showerror(str(_("Erreur")), str(_("Choisissez la destination.")))
            return
        mode = mode_var.get()
        encoding = encoding_var.get()

        def run():
            try:
                progress['value'] = 20
                if mode == "txt_to_pdf":
                    _convert_txt_to_pdf(src, dst, encoding, log_text)
                elif mode == "pdf_to_txt":
                    _convert_pdf_to_txt(src, dst, encoding, log_text)
                elif mode == "json_to_txt":
                    _convert_json_to_txt(src, dst, encoding, indent_var.get(), log_text)
                progress['value'] = 100
                _log(log_text, f"✓ {dst.name}")
            except Exception as exc:
                _log(log_text, f"✗ {exc}")
                messagebox.showerror(str(_("Erreur")), str(exc))
            finally:
                progress['value'] = 0

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir")), command=_convert,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet Vidéo → MP3
# ═══════════════════════════════════════════════════════════════════════════

_VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv', '.mpeg', '.mpg']

def _build_video_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    from src.gui.video_converter_core import VideoConverterCore, VideoConversionOptions
    converter = VideoConverterCore()
    ffmpeg_ok = converter.check_ffmpeg()

    if not ffmpeg_ok:
        ttk.Label(frame, text=str(_("⚠ FFmpeg non détecté. Installez FFmpeg pour utiliser cet outil.")),
                  foreground='red', wraplength=400).pack(anchor=tk.W, pady=(0, 8))

    ttk.Label(frame, text=str(_("Fichier vidéo :")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
    src_var = tk.StringVar()
    state = {'src': None, 'dst': None}

    src_entry = ttk.Entry(frame, textvariable=src_var, state='readonly')
    src_entry.pack(fill=tk.X, pady=(0, 4))

    def _browse_video():
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner une vidéo")),
            filetypes=[("Vidéos", " ".join(f"*{ext}" for ext in _VIDEO_FORMATS)), ("Tous", "*.*")])
        if path:
            state['src'] = Path(path)
            src_var.set(path)
            state['dst'] = Path(path).with_suffix('.mp3')
            dst_var.set(str(state['dst']))

    ttk.Button(frame, text=str(_("Parcourir...")), command=_browse_video).pack(anchor=tk.W, pady=(0, 8))

    ttk.Label(frame, text=str(_("Fichier MP3 de sortie :"))).pack(anchor=tk.W)
    dst_var = tk.StringVar()
    ttk.Entry(frame, textvariable=dst_var, state='readonly').pack(fill=tk.X, pady=(0, 4))

    def _browse_dst():
        path = filedialog.asksaveasfilename(
            title=str(_("Enregistrer le MP3")),
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("Tous", "*.*")])
        if path:
            state['dst'] = Path(path)
            dst_var.set(path)

    ttk.Button(frame, text=str(_("Enregistrer sous...")), command=_browse_dst).pack(anchor=tk.W, pady=(0, 8))

    opts_frame = ttk.Frame(frame)
    opts_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(opts_frame, text=str(_("Qualité :"))).pack(side=tk.LEFT)
    quality_var = tk.StringVar(value='192k')
    ttk.OptionMenu(opts_frame, quality_var, '192k', '64k', '128k', '192k', '256k', '320k').pack(side=tk.LEFT, padx=4)
    ttk.Label(opts_frame, text=str(_("Canaux :"))).pack(side=tk.LEFT, padx=(8, 0))
    channels_var = tk.StringVar(value='stereo')
    ttk.OptionMenu(opts_frame, channels_var, 'stereo', 'mono', 'stereo').pack(side=tk.LEFT, padx=4)

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert_video():
        src = state['src']
        dst = state['dst']
        if not src or not src.exists():
            messagebox.showerror(str(_("Erreur")), str(_("Sélectionnez une vidéo.")))
            return
        if not dst:
            messagebox.showerror(str(_("Erreur")), str(_("Choisissez la destination.")))
            return
        if not ffmpeg_ok:
            messagebox.showerror(str(_("Erreur")), str(_("FFmpeg non installé.")))
            return

        opts = VideoConversionOptions(
            quality=quality_var.get(),
            channels=channels_var.get(),
        )

        def run():
            try:
                _log(log_text, f"→ {src.name}")
                progress['value'] = 10

                def _on_progress(msg):
                    _log(log_text, f"  {msg}")

                def _on_complete(success, error):
                    if success:
                        progress['value'] = 100
                        _log(log_text, f"✓ {dst.name}")
                    else:
                        _log(log_text, f"✗ {error}")
                    progress['value'] = 0

                converter.convert(src, dst, opts, on_progress=_on_progress, on_complete=_on_complete)
            except Exception as exc:
                _log(log_text, f"✗ {exc}")

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir en MP3")), command=_convert_video,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet Images
# ═══════════════════════════════════════════════════════════════════════════

_IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']

def _build_image_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    ttk.Label(frame, text=str(_("Conversion d'images")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

    src_var = tk.StringVar()
    state = {'src': None}

    ttk.Label(frame, text=str(_("Image source :"))).pack(anchor=tk.W)
    src_entry = ttk.Entry(frame, textvariable=src_var, state='readonly')
    src_entry.pack(fill=tk.X, pady=(0, 4))

    def _browse():
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner une image")),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("Tous", "*.*")])
        if path:
            state['src'] = Path(path)
            src_var.set(path)

    ttk.Button(frame, text=str(_("Parcourir...")), command=_browse).pack(anchor=tk.W, pady=(0, 8))

    fmt_frame = ttk.Frame(frame)
    fmt_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(fmt_frame, text=str(_("Format cible :"))).pack(side=tk.LEFT)
    fmt_var = tk.StringVar(value=".png")
    ttk.OptionMenu(fmt_frame, fmt_var, ".png", *_IMAGE_FORMATS).pack(side=tk.LEFT, padx=8)

    resize_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text=str(_("Redimensionner")), variable=resize_var).pack(anchor=tk.W)

    size_frame = ttk.Frame(frame)
    size_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(size_frame, text="W:").pack(side=tk.LEFT)
    width_var = tk.StringVar(value="800")
    ttk.Entry(size_frame, textvariable=width_var, width=6).pack(side=tk.LEFT, padx=(2, 8))
    ttk.Label(size_frame, text="H:").pack(side=tk.LEFT)
    height_var = tk.StringVar(value="600")
    ttk.Entry(size_frame, textvariable=height_var, width=6).pack(side=tk.LEFT, padx=2)

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert_image():
        src = state['src']
        if not src or not src.exists():
            messagebox.showerror(str(_("Erreur")), str(_("Sélectionnez une image.")))
            return
        fmt = fmt_var.get()
        dst = src.with_suffix(fmt)
        resize = resize_var.get()
        w, h = int(width_var.get()), int(height_var.get()) if resize else None

        def run():
            try:
                from PIL import Image
                progress['value'] = 30
                img = Image.open(src)
                if resize and w and h:
                    img = img.resize((w, h), Image.LANCZOS)
                if fmt in ('.jpg', '.jpeg'):
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                img.save(dst)
                progress['value'] = 100
                _log(log_text, f"✓ {src.name} → {dst.name}")
            except Exception as exc:
                _log(log_text, f"✗ {exc}")
                messagebox.showerror(str(_("Erreur")), str(exc))
            finally:
                progress['value'] = 0

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir")), command=_convert_image,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet CSV → JSON
# ═══════════════════════════════════════════════════════════════════════════

def _build_csv_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    ttk.Label(frame, text=str(_("CSV → JSON")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

    src_var, dst_var = tk.StringVar(), tk.StringVar()
    state = {'src': None, 'dst': None}

    ttk.Label(frame, text=str(_("Fichier CSV :"))).pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=src_var, state='readonly').pack(fill=tk.X, pady=(0, 4))
    ttk.Button(frame, text=str(_("Parcourir...")), command=lambda: _browse_csv(state, src_var, dst_var)).pack(anchor=tk.W, pady=(0, 8))

    ttk.Label(frame, text=str(_("Destination :"))).pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=dst_var, state='readonly').pack(fill=tk.X, pady=(0, 4))

    delim_frame = ttk.Frame(frame)
    delim_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(delim_frame, text=str(_("Délimiteur :"))).pack(side=tk.LEFT)
    delim_var = tk.StringVar(value=",")
    ttk.Entry(delim_frame, textvariable=delim_var, width=3).pack(side=tk.LEFT, padx=8)
    ttk.Label(delim_frame, text=str(_("Encodage :"))).pack(side=tk.LEFT, padx=(8, 0))
    enc_var = tk.StringVar(value="utf-8")
    ttk.OptionMenu(delim_frame, enc_var, "utf-8", "utf-8", "latin-1", "cp1252").pack(side=tk.LEFT, padx=4)

    indent_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text=str(_("Indentation JSON")), variable=indent_var).pack(anchor=tk.W)

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert_csv():
        src = state['src']
        if not src or not src.exists():
            messagebox.showerror(str(_("Erreur")), str(_("Sélectionnez un CSV.")))
            return
        dst = src.with_suffix('.json')
        state['dst'] = dst
        dst_var.set(str(dst))
        delimiter = delim_var.get() or ","
        encoding = enc_var.get()

        def run():
            try:
                progress['value'] = 30
                rows = []
                with open(src, 'r', encoding=encoding, errors='replace') as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    for row in reader:
                        rows.append(dict(row))
                formatted = json.dumps(rows, indent=2 if indent_var.get() else None, ensure_ascii=False)
                dst.write_text(formatted, encoding=encoding)
                progress['value'] = 100
                _log(log_text, f"✓ {src.name} → {dst.name} ({len(rows)} lignes)")
            except Exception as exc:
                _log(log_text, f"✗ {exc}")
                messagebox.showerror(str(_("Erreur")), str(exc))
            finally:
                progress['value'] = 0

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir")), command=_convert_csv,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet Audio (MP3 ↔ WAV)
# ═══════════════════════════════════════════════════════════════════════════

def _build_audio_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    ttk.Label(frame, text=str(_("Conversion audio")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

    src_var = tk.StringVar()
    state = {'src': None}

    ttk.Label(frame, text=str(_("Fichier source :"))).pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=src_var, state='readonly').pack(fill=tk.X, pady=(0, 4))

    def _browse_audio():
        path = filedialog.askopenfilename(
            title=str(_("Sélectionner un fichier audio")),
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac"), ("Tous", "*.*")])
        if path:
            state['src'] = Path(path)
            src_var.set(path)

    ttk.Button(frame, text=str(_("Parcourir...")), command=_browse_audio).pack(anchor=tk.W, pady=(0, 8))

    fmt_frame = ttk.Frame(frame)
    fmt_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(fmt_frame, text=str(_("Format cible :"))).pack(side=tk.LEFT)
    fmt_var = tk.StringVar(value=".wav")
    ttk.OptionMenu(fmt_frame, fmt_var, ".wav", ".mp3", ".wav", ".ogg").pack(side=tk.LEFT, padx=8)

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert_audio():
        src = state['src']
        if not src or not src.exists():
            messagebox.showerror(str(_("Erreur")), str(_("Sélectionnez un fichier audio.")))
            return
        fmt = fmt_var.get()
        dst = src.with_suffix(fmt)

        def run():
            try:
                progress['value'] = 30
                _convert_audio_file(src, dst, log_text)
                progress['value'] = 100
                _log(log_text, f"✓ {src.name} → {dst.name}")
            except Exception as exc:
                _log(log_text, f"✗ {exc}")
                messagebox.showerror(str(_("Erreur")), str(exc))
            finally:
                progress['value'] = 0

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir")), command=_convert_audio,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Onglet Conversion par lot
# ═══════════════════════════════════════════════════════════════════════════

def _build_batch_tab(parent) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=12)

    ttk.Label(frame, text=str(_("Conversion par lot")), font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
    ttk.Label(frame, text=str(_("Sélectionnez plusieurs fichiers d'un même type")),
              font=('Segoe UI', 9)).pack(anchor=tk.W, pady=(0, 8))

    mode_var = tk.StringVar(value="image")
    mode_frame = ttk.Frame(frame)
    mode_frame.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(mode_frame, text=str(_("Type :"))).pack(side=tk.LEFT)
    ttk.OptionMenu(mode_frame, mode_var, "image", "image", "txt_to_pdf", "audio").pack(side=tk.LEFT, padx=8)

    files_var = tk.StringVar(value="0 fichiers sélectionnés")
    state = {'files': []}

    def _browse_batch():
        mode = mode_var.get()
        if mode == "image":
            ftypes = [("Images", "*.png *.jpg *.jpeg *.bmp *.webp")]
        elif mode == "txt_to_pdf":
            ftypes = [("Texte", "*.txt")]
        else:
            ftypes = [("Audio", "*.mp3 *.wav")]
        paths = filedialog.askopenfilenames(title=str(_("Sélectionner les fichiers")), filetypes=ftypes)
        if paths:
            state['files'] = [Path(p) for p in paths]
            files_var.set(f"{len(paths)} fichiers sélectionnés")

    ttk.Button(frame, text=str(_("Sélectionner des fichiers...")), command=_browse_batch).pack(anchor=tk.W, pady=(0, 8))
    ttk.Label(frame, textvariable=files_var, foreground=get_color('fg_muted')).pack(anchor=tk.W, pady=(0, 8))

    fmt_var = tk.StringVar(value=".png")
    ttk.Label(frame, text=str(_("Format cible :"))).pack(anchor=tk.W)
    ttk.OptionMenu(frame, fmt_var, ".png", *_IMAGE_FORMATS).pack(fill=tk.X, pady=(0, 8))

    progress, status_var, log_text = _add_progress_and_log(frame)

    def _convert_batch():
        files = state['files']
        if not files:
            messagebox.showerror(str(_("Erreur")), str(_("Sélectionnez des fichiers.")))
            return
        fmt = fmt_var.get()
        mode = mode_var.get()
        total = len(files)

        def run():
            try:
                ok, fail = 0, 0
                for i, src in enumerate(files):
                    safe_after(frame, 0, lambda v=(i + 1) / total * 100: progress.config(value=v))
                    try:
                        if mode == "image":
                            _convert_single_image(src, src.with_suffix(fmt))
                        elif mode == "txt_to_pdf":
                            _convert_txt_to_pdf(src, src.with_suffix('.pdf'), 'utf-8', log_text)
                        elif mode == "audio":
                            _convert_audio_file(src, src.with_suffix('.wav'), log_text)
                        ok += 1
                        _log(log_text, f"  ✓ {src.name}")
                    except Exception as exc:
                        fail += 1
                        _log(log_text, f"  ✗ {src.name}: {exc}")
                progress['value'] = 100
                _log(log_text, f"Terminé : {ok} OK, {fail} erreurs")
            except Exception as exc:
                _log(log_text, f"✗ {exc}")
            finally:
                progress['value'] = 0

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(frame, text=str(_("Convertir tout")), command=_convert_batch,
               style='AppPrimary.TButton').pack(anchor=tk.E, pady=(8, 0))
    return frame


# ═══════════════════════════════════════════════════════════════════════════
# Helpers UI
# ═══════════════════════════════════════════════════════════════════════════

def _add_progress_and_log(parent):
    progress = ttk.Progressbar(parent, mode='determinate', maximum=100)
    progress.pack(fill=tk.X, pady=(8, 4))
    status_var = tk.StringVar(value=str(_("Prêt")))
    ttk.Label(parent, textvariable=status_var, foreground=get_color('fg_muted')).pack(anchor=tk.W)
    log_frame = ttk.Frame(parent, style='Card.TFrame', padding=(6, 4))
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    log_text = tk.Text(log_frame, height=6, wrap=tk.WORD,
                       bg=get_color('text_bg'), fg=get_color('text_fg'), font=('Consolas', 9),
                       bd=0, highlightthickness=0, state='disabled')
    log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return progress, status_var, log_text


def _log(log_text: tk.Text, msg: str):
    safe_after(log_text, 0, lambda: _do_log(log_text, msg))


def _do_log(log_text: tk.Text, msg: str):
    log_text.configure(state='normal')
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.configure(state='disabled')


# ═══════════════════════════════════════════════════════════════════════════
# Helpers fichiers
# ═══════════════════════════════════════════════════════════════════════════

def _browse_file(state, src_var, mode_var, dst_var):
    mode = mode_var.get()
    if mode == "txt_to_pdf":
        ftypes = [("TXT", "*.txt"), ("Tous", "*.*")]
    elif mode == "pdf_to_txt":
        ftypes = [("PDF", "*.pdf"), ("Tous", "*.*")]
    else:
        ftypes = [("JSON", "*.json"), ("Tous", "*.*")]
    path = filedialog.askopenfilename(title=str(_("Sélectionner")), filetypes=ftypes)
    if path:
        state['src'] = Path(path)
        src_var.set(path)
        s = state['src']
        ext_map = {"txt_to_pdf": ".pdf", "pdf_to_txt": ".txt", "json_to_txt": ".txt"}
        dst = s.with_suffix(ext_map.get(mode_var.get(), ".out"))
        state['dst'] = dst
        dst_var.set(str(dst))


def _save_file(state, dst_var, mode_var):
    ext_map = {"txt_to_pdf": ".pdf", "pdf_to_txt": ".txt", "json_to_txt": ".txt"}
    ext = ext_map.get(mode_var.get(), ".out")
    path = filedialog.asksaveasfilename(title=str(_("Enregistrer")), defaultextension=ext)
    if path:
        state['dst'] = Path(path)
        dst_var.set(path)


def _browse_csv(state, src_var, dst_var):
    path = filedialog.askopenfilename(
        title=str(_("Sélectionner un CSV")),
        filetypes=[("CSV", "*.csv"), ("Tous", "*.*")])
    if path:
        state['src'] = Path(path)
        src_var.set(path)
        dst = Path(path).with_suffix('.json')
        state['dst'] = dst
        dst_var.set(str(dst))


# ═══════════════════════════════════════════════════════════════════════════
# Fonctions de conversion
# ═══════════════════════════════════════════════════════════════════════════

def _convert_txt_to_pdf(src: Path, dst: Path, encoding: str, log_text):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    text = src.read_text(encoding=encoding, errors='replace')
    for line in text.split('\n'):
        pdf.cell(0, 5, txt=line, ln=True)
    pdf.output(str(dst))


def _convert_pdf_to_txt(src: Path, dst: Path, encoding: str, log_text):
    from PyPDF2 import PdfReader
    reader = PdfReader(str(src))
    parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            parts.append(f"--- Page {i + 1} ---\n{text}")
        _log(log_text, f"  Page {i + 1}/{len(reader.pages)}")
    dst.write_text("\n\n".join(parts), encoding=encoding)


def _convert_json_to_txt(src: Path, dst: Path, encoding: str, indent: bool, log_text):
    raw = src.read_text(encoding=encoding, errors='replace')
    data = json.loads(raw)
    formatted = json.dumps(data, indent=2 if indent else None, ensure_ascii=False, default=str)
    dst.write_text(formatted, encoding=encoding)


def _convert_single_image(src: Path, dst: Path, resize=None):
    from PIL import Image
    img = Image.open(src)
    if resize:
        img = img.resize(resize, Image.LANCZOS)
    if dst.suffix in ('.jpg', '.jpeg') and img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.save(dst)


def _convert_audio_file(src: Path, dst: Path, log_text):
    """Convertit entre MP3, WAV, OGG via pydub (ffmpeg requis en arrière-plan)."""
    try:
        from pydub import AudioSegment
        fmt = dst.suffix.lstrip('.')
        audio = AudioSegment.from_file(str(src))
        audio.export(str(dst), format=fmt)
    except ImportError:
        import subprocess
        cmd = ['ffmpeg', '-y', '-i', str(src), str(dst)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Erreur ffmpeg inconnue")


# ═══════════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════════

TOOL = Tool(
    id='convert',
    name="Alchimiste",
    description="Transmutez vos fichiers : documents, vidéos, images, audio, CSV.",
    category="Conversion",
    icon='🧬',
    shortcut='Ctrl+2',
    view=build_convert_view,
    keywords=('convertir', 'convert', 'transmuter', 'pdf', 'txt', 'json', 'image', 'csv', 'audio', 'video', 'mp3'),
    order=1,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.convert',
        label="Alchimiste",
        description="Transmuter des fichiers (documents, vidéos, images, audio, CSV)",
        shortcut='Ctrl+2',
        icon='🧬',
        tool_id='convert',
        keywords=('convertir', 'transmuter', 'pdf', 'txt', 'json', 'image', 'csv', 'audio', 'video', 'mp3'),
    ))
