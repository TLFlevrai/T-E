# src/tools/youtube.py
"""Outil YouTube : téléchargement de vidéos (MP4) ou d'audio (MP3)."""
from __future__ import annotations

import os
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
    ("Meilleure qualité disponible", 0),  # 0 = pas de limite
    ("1080p (Full HD)", 1080),
    ("720p (HD)", 720),
    ("480p", 480),
    ("360p", 360),
    ("240p", 240),
    ("144p", 144),
]


def build_youtube_view(shell) -> ttk.Frame:
    """Construit la vue YouTube intégrée au workspace."""
    from src.ui.tooltips import add_tooltip

    frame = ttk.Frame(shell.workspace, padding=12)

    ttk.Label(frame, text=_("URL de la vidéo YouTube")).grid(
        row=0, column=0, sticky=tk.W, pady=(0, 4))
    url_var = tk.StringVar()
    url_entry = ttk.Entry(frame, textvariable=url_var)
    url_entry.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))
    add_tooltip(url_entry, _("Collez l'URL d'une vidéo YouTube puis choisissez le format."))

    ttk.Label(frame, text=_("Format de téléchargement")).grid(
        row=2, column=0, sticky=tk.W, pady=(0, 4))
    format_var = tk.StringVar(value='video')

    radio_frame = ttk.Frame(frame)
    radio_frame.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
    ttk.Radiobutton(radio_frame, text=_("Vidéo (MP4)"), value='video',
                    variable=format_var).pack(side=tk.LEFT, padx=(0, 16))
    ttk.Radiobutton(radio_frame, text=_("Audio (MP3)"), value='audio',
                    variable=format_var).pack(side=tk.LEFT)

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
        os.startfile(path)
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

        opts = self._build_opts()

        self.progress.config(value=0)
        self._set_status(_("Analyse de la vidéo..."))
        self.download_btn.config(state='disabled')
        self._thread = threading.Thread(
            target=self._run, args=(url, opts), daemon=True)
        self._thread.start()

    def _build_opts(self) -> dict:
        quality_label = self.quality_var.get()
        max_height = 360
        for name, height in _VIDEO_QUALITIES:
            if name == quality_label:
                max_height = height
                break

        return {
            'format': self.format_var.get(),
            'dest': self.dest_var.get(),
            'max_height': max_height,
        }

    def _run(self, url: str, opts: dict) -> None:
        from src.youtube import (
            download_audio,
            download_video,
            FormatUnavailableError,
            InvalidYouTubeURLError,
            NetworkError,
            VideoUnavailableError,
            YouTubeError,
        )

        try:
            self._post(lambda: self._set_status(_("Récupération des informations...")))
            dest = opts['dest']
            fmt = opts['format']
            max_height = opts.get('max_height', 360)

            def _progress(downloaded: int, total: int, _speed: int) -> None:
                if total > 0:
                    percent = min(100.0, downloaded / total * 100.0)
                    self._post(lambda p=percent: self._update_progress(
                        p, _("Téléchargement : {p:.0f}%").format(p=p)))
                else:
                    self._post(lambda: self._set_status(
                        _("Téléchargement en cours...")))

            if fmt == 'audio':
                download_audio(
                    url=url,
                    output_dir=dest,
                    convert_mp3=True,
                    progress_cb=_progress,
                )
            else:
                download_video(
                    url=url,
                    output_dir=dest,
                    max_height=max_height,
                    progress_cb=_progress,
                )

            self._post(self._on_done)

        except InvalidYouTubeURLError as exc:
            self._post(lambda err=exc: self._fail(str(err)))
        except VideoUnavailableError as exc:
            self._post(lambda err=exc: self._fail(str(err)))
        except FormatUnavailableError as exc:
            self._post(lambda err=exc: self._fail(str(err)))
        except NetworkError as exc:
            self._post(lambda err=exc: self._fail(str(err)))
        except YouTubeError as exc:
            self._post(lambda err=exc: self._fail(str(err)))
        except Exception as exc:
            self._post(lambda err=exc: self._fail(str(err)))

    def _post(self, callback) -> None:
        safe_after(self.shell.root, 0, callback)

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
    name="TéléScope",
    description="Captandez des vidéos YouTube (MP4) ou extrayez l'audio (MP3).",
    category="Conversion",
    icon='🔭',
    shortcut='Ctrl+9',
    view=build_youtube_view,
    keywords=('youtube', 'video', 'audio', 'mp3', 'mp4', 'téléchargement', 'download'),
    order=2,
)


def register(reg, cmds) -> None:
    reg.register(TOOL)
    cmds.register(Command(
        id='tool.youtube',
        label="TéléScope",
        description="Captader des vidéos YouTube (MP4 ou MP3)",
        shortcut='Ctrl+9',
        icon='🔭',
        tool_id='youtube',
        keywords=('youtube', 'video', 'audio', 'mp3', 'mp4', 'download'),
    ))
