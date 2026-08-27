# src/tools/youtube.py
"""Outil YouTube : téléchargement de vidéos (MP4) ou d'audio (MP3).

L'utilisateur choisit le format (vidéo ou audio) avant le lancement du
téléchargement. Le téléchargement s'exécute dans un thread de travail et
met à jour la barre de progression via `safe_after` (thread-safe).
"""
from __future__ import annotations

import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from src.config import get_config
from src.core.command_registry import Command
from src.core.tool import Tool
from src.gui.app_guard import safe_after
from src.i18n import _

_VIDEO_QUALITIES = [
    ("Meilleure qualité", None),
    ("2160p (4K)", 2160),
    ("1080p", 1080),
    ("720p", 720),
    ("480p", 480),
    ("360p", 360),
]


def build_youtube_view(shell) -> ttk.Frame:
    """Construit la vue YouTube intégrée au workspace."""
    from src.gui.ui_builder.tooltip import add_tooltip

    frame = ttk.Frame(shell.workspace, padding=12)

    # --- URL ---
    ttk.Label(frame, text=_("URL de la vidéo YouTube")).grid(
        row=0, column=0, sticky=tk.W, pady=(0, 4))
    url_var = tk.StringVar()
    url_entry = ttk.Entry(frame, textvariable=url_var)
    url_entry.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))
    add_tooltip(url_entry, _("Collez l'URL d'une vidéo YouTube puis choisissez le format."))

    # --- Format ---
    ttk.Label(frame, text=_("Format de téléchargement")).grid(
        row=2, column=0, sticky=tk.W, pady=(0, 4))
    format_var = tk.StringVar(value='video')

    radio_frame = ttk.Frame(frame)
    radio_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
    ttk.Radiobutton(radio_frame, text=_("Vidéo (MP4)"), value='video',
                    variable=format_var).pack(side=tk.LEFT, padx=(0, 16))
    ttk.Radiobutton(radio_frame, text=_("Audio (MP3)"), value='audio',
                    variable=format_var).pack(side=tk.LEFT)

    # --- Qualité vidéo ---
    ttk.Label(frame, text=_("Qualité vidéo")).grid(
        row=4, column=0, sticky=tk.W, pady=(0, 4))
    quality_var = tk.StringVar(value=_VIDEO_QUALITIES[0][0])
    quality_combo = ttk.Combobox(
        frame, textvariable=quality_var, state='readonly',
        values=[label for label, _ in _VIDEO_QUALITIES], width=22)
    quality_combo.grid(row=5, column=0, sticky=tk.W, pady=(0, 8))

    def _on_format_change(*_args):
        state = 'normal' if format_var.get() == 'video' else 'disabled'
        quality_combo.config(state=state)
    format_var.trace_add('write', _on_format_change)

    # --- Destination ---
    ttk.Label(frame, text=_("Dossier de destination")).grid(
        row=6, column=0, sticky=tk.W, pady=(0, 4))
    dest_var = tk.StringVar(value=_default_dest())
    dest_entry = ttk.Entry(frame, textvariable=dest_var, state='readonly')
    dest_entry.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
    dest_buttons = ttk.Frame(frame)
    dest_buttons.grid(row=8, column=0, sticky=tk.W, pady=(0, 10))
    ttk.Button(dest_buttons, text=_("Parcourir..."),
               command=lambda: _browse_dest(shell, dest_var)).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(dest_buttons, text=_("Ouvrir le dossier"),
               command=lambda: _open_dest(dest_var.get())).pack(side=tk.LEFT)

    # --- Actions ---
    progress = ttk.Progressbar(frame, mode='determinate', maximum=100)
    progress.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 6))
    status_var = tk.StringVar(value="")
    status_label = ttk.Label(frame, textvariable=status_var, wraplength=560, justify=tk.LEFT)
    status_label.grid(row=10, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))

    download_btn = ttk.Button(frame, text=_("Télécharger"), style='Accent.TButton')
    download_btn.grid(row=11, column=0, sticky=tk.W)

    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(12, weight=1)

    view = _YouTubeView(
        shell=shell,
        url_var=url_var,
        format_var=format_var,
        quality_var=quality_var,
        dest_var=dest_var,
        progress=progress,
        status_var=status_var,
        download_btn=download_btn,
    )
    download_btn.config(command=view.start_download)

    shell.youtube_ui = view
    return frame


def _default_dest() -> str:
    folder = get_config().get('gui.youtube_dir', 'downloads')
    return str(Path(folder).resolve())


def _browse_dest(shell, dest_var: tk.StringVar) -> None:
    folder = filedialog.askdirectory(title=_("Dossier de destination"), initialdir=dest_var.get())
    if folder:
        dest_var.set(folder)
        get_config().update_gui(youtube_dir=folder)


def _open_dest(path: str) -> None:
    if not os.path.isdir(path):
        messagebox.showinfo(_("Dossier"), _("Le dossier n'existe pas encore."))
        return
    try:
        os.startfile(path)  # noqa: S606
    except OSError:
        pass


class _YouTubeView:
    """Logique du téléchargement YouTube (thread de travail + i18n)."""

    def __init__(self, shell, url_var, format_var, quality_var, dest_var,
                 progress, status_var, download_btn) -> None:
        self.shell = shell
        self.url_var = url_var
        self.format_var = format_var
        self.quality_var = quality_var
        self.dest_var = dest_var
        self.progress = progress
        self.status_var = status_var
        self.download_btn = download_btn
        self._thread: threading.Thread | None = None

    def start_download(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        url = self.url_var.get().strip()
        if not url:
            self._set_status(_("Veuillez saisir une URL YouTube."))
            return
        if not url.startswith(('http://', 'https://')):
            self._set_status(_("URL invalide : elle doit commencer par http(s)://"))
            return

        # Snapshot des options ICI (thread UI) : les tk.StringVar ne doivent
        # jamais être lues depuis le thread de travail.
        opts = self._build_opts()

        self.progress.config(value=0)
        self._set_status(_("Analyse de la vidéo..."))
        self.download_btn.config(state='disabled')
        self._thread = threading.Thread(
            target=self._run, args=(url, opts), daemon=True)
        self._thread.start()

    # --- Thread de travail ---

    def _run(self, url: str, opts: dict) -> None:
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            self._post(lambda: self._fail(_(
                "yt-dlp n'est pas installé. Lancez : pip install yt-dlp")))
            return

        try:
            with YoutubeDL(opts) as ydl:
                self._post(lambda: self._set_status(_("Récupération des informations...")))
                ydl.download([url])
            self._post(self._on_done)
        except Exception as exc:  # noqa: BLE001 - erreur utilisateur lisible
            self._post(lambda err=exc: self._fail(str(err)))

    def _build_opts(self) -> dict:
        quality = self._selected_quality()
        ffmpeg = shutil.which('ffmpeg') is not None
        if self.format_var.get() == 'audio':
            if ffmpeg:
                return {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(self.dest_var.get(), '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'progress_hooks': [self._hook],
                    'noplaylist': True,
                }
            # Sans ffmpeg : audio natif (m4a/webm/opus)
            return {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.dest_var.get(), '%(title)s.%(ext)s'),
                'progress_hooks': [self._hook],
                'noplaylist': True,
            }
        # Vidéo MP4
        fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        if quality:
            fmt = (f'bestvideo[height<={quality}][ext=mp4]'
                   f'+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]'
                   f'/best[height<={quality}]')
        opts = {
            'format': fmt,
            'outtmpl': os.path.join(self.dest_var.get(), '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [self._hook],
            'noplaylist': True,
        }
        if not ffmpeg:
            opts.pop('merge_output_format', None)
        return opts

    def _selected_quality(self) -> int | None:
        label = self.quality_var.get()
        for name, height in _VIDEO_QUALITIES:
            if name == label:
                return height
        return None

    # --- Hooks ---

    def _hook(self, d: dict) -> None:
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes') or 0
            percent = min(100.0, (done / total * 100.0)) if total else 0.0
            speed = d.get('speed')
            eta = d.get('eta')
            text = _("Téléchargement : {percent:.0f}%").format(percent=percent)
            if speed:
                text += " — " + _("{speed} Mo/s").format(speed=speed / 1_000_000)
            if eta:
                text += " — " + _("{eta} s restantes").format(eta=int(eta))
            self._post(lambda: self._update_progress(percent, text))
        elif status == 'finished':
            self._post(lambda: self._set_status(_("Finalisation du fichier...")))

    def _post(self, callback) -> None:
        safe_after(self.shell.root, 0, callback)

    # --- Callbacks UI (thread principal) ---

    def _update_progress(self, percent: float, text: str) -> None:
        self.progress.config(value=percent)
        self._set_status(text)

    def _on_done(self) -> None:
        self.progress.config(value=100)
        folder = self.dest_var.get()
        if os.path.isdir(folder):
            self._set_status(_("Téléchargement terminé ! Le fichier est dans : {folder}").format(folder=folder))
        else:
            self._set_status(_("Téléchargement terminé !"))
        self.download_btn.config(state='normal')

    def _fail(self, message: str) -> None:
        self.download_btn.config(state='normal')
        self.progress.config(value=0)
        self._set_status(_("Erreur de téléchargement : {message}").format(message=message))

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)


TOOL = Tool(
    id='youtube',
    name="YouTube",
    description="Télécharger des vidéos YouTube (MP4 ou MP3).",
    category="Réseau",
    icon='▶️',
    shortcut='Ctrl+9',
    view=build_youtube_view,
    keywords=('youtube', 'video', 'audio', 'mp3', 'mp4', 'téléchargement', 'download'),
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.youtube',
        label="YouTube",
        description="Télécharger des vidéos YouTube (MP4 ou MP3)",
        shortcut='Ctrl+9',
        icon='▶️',
        tool_id='youtube',
        keywords=('youtube', 'video', 'audio', 'mp3', 'mp4', 'download'),
    ))