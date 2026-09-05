# src/gui/video_converter.py
"""Convertisseur vidéo vers MP3 (UI)."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import webbrowser
from src.i18n import _
from src.logger import setup_logger
from .app_guard import safe_after
from .base_dialog import BaseDialog
from .video_converter_core import VideoConverterCore, VideoConversionOptions

logger = setup_logger(__name__)


class VideoToMP3Converter(BaseDialog):
    """Fenêtre de conversion vidéo vers MP3."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Convertisseur Vidéo → MP3"),
            geometry="600x450",
            minsize=(550, 400),
        )

        self.video_path = None
        self.output_path = None
        self.converter = VideoConverterCore()
        self.ffmpeg_available = self.converter.check_ffmpeg()

        self._create_widgets()

        # Gérer la fermeture pendant conversion
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Titre
        title = ttk.Label(main, text=_("Convertisseur Vidéo vers MP3"), font=('Arial', 14, 'bold'))
        title.pack(pady=(0, 10))

        # Avertissement ffmpeg
        if not self.ffmpeg_available:
            warning_frame = ttk.Frame(main)
            warning_frame.pack(fill=tk.X, pady=(0, 15))
            warning_label = ttk.Label(
                warning_frame,
                text=_("⚠ FFmpeg non détecté. La conversion ne fonctionnera pas.\n"
                       "Installez FFmpeg et assurez-vous qu'il est dans le PATH."),
                foreground='red',
                wraplength=500,
                justify=tk.CENTER
            )
            warning_label.pack()
            ttk.Button(warning_frame, text=_("Télécharger FFmpeg"), 
                      command=self._open_ffmpeg_download).pack(pady=5)

        # Sélection fichier vidéo
        video_frame = ttk.LabelFrame(main, text=_("Fichier vidéo source"), padding=10)
        video_frame.pack(fill=tk.X, pady=(0, 15))
        video_frame.columnconfigure(0, weight=1)

        self.video_entry = ttk.Entry(video_frame, state='readonly')
        self.video_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        video_btn = ttk.Button(video_frame, text=_("Parcourir..."), command=self._select_video)
        video_btn.grid(row=0, column=1)

        # Formats supportés
        formats = self.converter.get_supported_formats()
        formats_label = ttk.Label(video_frame, 
            text=_("Formats supportés : {}").format(", ".join(f.upper() for f in formats)),
            font=('Arial', 8), foreground='gray')
        formats_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Options de conversion
        options_frame = ttk.LabelFrame(main, text=_("Options de conversion"), padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        options_frame.columnconfigure(1, weight=1)

        # Qualité audio
        ttk.Label(options_frame, text=_("Qualité audio :")).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.quality_var = tk.StringVar(value='192k')
        quality_combo = ttk.Combobox(options_frame, textvariable=self.quality_var,
                                      values=['64k', '128k', '192k', '256k', '320k'], 
                                      state='readonly', width=10)
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=4)

        # Taux d'échantillonnage
        ttk.Label(options_frame, text=_("Taux d'échantillonnage :")).grid(row=1, column=0, sticky=tk.W, pady=4)
        self.sample_rate_var = tk.StringVar(value='44100')
        sample_combo = ttk.Combobox(options_frame, textvariable=self.sample_rate_var,
                                     values=['22050', '44100', '48000'], 
                                     state='readonly', width=10)
        sample_combo.grid(row=1, column=1, sticky=tk.W, padx=10, pady=4)

        # Canaux
        ttk.Label(options_frame, text=_("Canaux :")).grid(row=2, column=0, sticky=tk.W, pady=4)
        self.channels_var = tk.StringVar(value='stereo')
        channels_combo = ttk.Combobox(options_frame, textvariable=self.channels_var,
                                       values=['mono', 'stereo'], 
                                       state='readonly', width=10)
        channels_combo.grid(row=2, column=1, sticky=tk.W, padx=10, pady=4)

        # Volume
        ttk.Label(options_frame, text=_("Volume :")).grid(row=3, column=0, sticky=tk.W, pady=4)
        self.volume_var = tk.DoubleVar(value=1.0)
        volume_frame = ttk.Frame(options_frame)
        volume_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=10, pady=4)
        volume_frame.columnconfigure(0, weight=1)
        volume_scale = ttk.Scale(volume_frame, from_=0.5, to=2.0, variable=self.volume_var, 
                                  orient=tk.HORIZONTAL, length=200)
        volume_scale.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.volume_label = ttk.Label(volume_frame, text="100%")
        self.volume_label.grid(row=0, column=1, padx=5)
        volume_scale.bind('<Motion>', lambda e: self.volume_label.config(
            text=f"{int(self.volume_var.get() * 100)}%"))

        # Fichier de sortie
        output_frame = ttk.LabelFrame(main, text=_("Fichier MP3 de sortie"), padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 15))
        output_frame.columnconfigure(0, weight=1)

        self.output_entry = ttk.Entry(output_frame, state='readonly')
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        output_btn = ttk.Button(output_frame, text=_("Parcourir..."), command=self._select_output)
        output_btn.grid(row=0, column=1)

        # Barre de progression
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main, variable=self.progress_var, maximum=100, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))

        self.status_var = tk.StringVar(value=_("Prêt") if self.ffmpeg_available else _("FFmpeg requis"))
        status_label = ttk.Label(main, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(fill=tk.X)

        # Boutons d'action
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self.convert_btn = ttk.Button(btn_frame, text=_("Convertir en MP3"), 
                                       command=self._start_conversion, 
                                       state='normal' if self.ffmpeg_available else 'disabled')
        self.convert_btn.pack(side=tk.RIGHT, padx=5)

        close_btn = ttk.Button(btn_frame, text=_("Fermer"), command=self.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)

    def _open_ffmpeg_download(self):
        """Ouvre la page de téléchargement FFmpeg."""
        webbrowser.open("https://ffmpeg.org/download.html")

    def _select_video(self):
        """Sélectionne le fichier vidéo source."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title=_("Sélectionner un fichier vidéo"),
            filetypes=[
                (_("Fichiers vidéo"), " ".join(f"*{ext}" for ext in self.converter.get_supported_formats())),
                (_("Tous les fichiers"), "*.*")
            ]
        )
        if path:
            from pathlib import Path
            self.video_path = Path(path)
            self.video_entry.config(state='normal')
            self.video_entry.delete(0, tk.END)
            self.video_entry.insert(0, str(self.video_path))
            self.video_entry.config(state='readonly')

            # Auto-générer le nom du fichier MP3
            mp3_path = self.video_path.with_suffix('.mp3')
            self.output_path = mp3_path
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(mp3_path))
            self.output_entry.config(state='readonly')

            self.status_var.set(_("Fichier vidéo sélectionné"))

    def _select_output(self):
        """Sélectionne le fichier MP3 de sortie."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title=_("Enregistrer le fichier MP3"),
            defaultextension=".mp3",
            filetypes=[(_("Fichiers MP3"), "*.mp3"), (_("Tous les fichiers"), "*.*")]
        )
        if path:
            from pathlib import Path
            self.output_path = Path(path)
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(self.output_path))
            self.output_entry.config(state='readonly')

    def _start_conversion(self):
        """Lance la conversion dans un thread séparé."""
        if not self.video_path or not self.video_path.exists():
            self.show_error(_("Erreur"), _("Veuillez sélectionner un fichier vidéo valide"))
            return

        if not self.output_path:
            self.show_error(_("Erreur"), _("Veuillez spécifier un fichier de sortie"))
            return

        if not self.ffmpeg_available:
            self.show_error(_("Erreur"), _("FFmpeg n'est pas installé ou pas dans le PATH"))
            return

        self.convert_btn.config(state='disabled')
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.status_var.set(_("Conversion en cours..."))

        options = VideoConversionOptions(
            quality=self.quality_var.get(),
            sample_rate=self.sample_rate_var.get(),
            channels=self.channels_var.get(),
            volume=self.volume_var.get(),
        )

        # Les callbacks sont invoqués depuis le thread de travail du
        # convertisseur : passer par safe_after (jamais de widget depuis un
        # thread worker).
        def _on_progress_thread(msg: str):
            safe_after(self, 0, lambda: self._set_status_if_alive(msg))

        self.converter.convert(
            input_path=self.video_path,
            output_path=self.output_path,
            options=options,
            on_progress=_on_progress_thread,
            on_complete=self._on_conversion_complete,
        )

    def _set_status_if_alive(self, msg: str):
        try:
            if self.winfo_exists():
                self.status_var.set(msg)
        except tk.TclError:
            pass

    def _on_conversion_complete(self, success: bool, error_msg: str | None):
        """Callback appelé à la fin de la conversion (thread de travail)."""
        if success:
            safe_after(self, 0, self._conversion_success)
        else:
            safe_after(self, 0, lambda: self._conversion_error(error_msg or "Erreur inconnue"))

    def _conversion_success(self):
        """Appelé quand la conversion réussit."""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=100)
        self.status_var.set(_("Conversion terminée avec succès !"))
        self.convert_btn.config(state='normal')
        
        self.show_info(
            _("Succès"),
            _("Fichier MP3 créé : {}").format(self.output_path)
        )
        from .toast import show_toast
        show_toast(self, _("Conversion terminée avec succès"), 'success', parent=self)

    def _conversion_error(self, error_msg: str):
        """Appelé en cas d'erreur de conversion."""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=0)
        self.status_var.set(_("Erreur lors de la conversion"))
        self.convert_btn.config(state='normal')
        
        self.show_error(_("Erreur"), _("Impossible de convertir : {}").format(error_msg))

    def _on_close(self):
        """Gère la fermeture de la fenêtre."""
        if self.converter.is_running():
            # Conversion en cours, demander confirmation
            if self.confirm(
                _("Confirmation"),
                _("Une conversion est en cours. Voulez-vous l'annuler et fermer ?")
            ):
                self.converter.cancel()
                self.destroy()
        else:
            self.destroy()


def open_video_converter(parent):
    """Ouvre le convertisseur vidéo vers MP3."""
    VideoToMP3Converter(parent)