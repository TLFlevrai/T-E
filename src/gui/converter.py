# src/gui/converter.py
"""Convertisseur SVG vers ICO."""
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from src.i18n import _
from src.logger import setup_logger
from .base_dialog import BaseDialog

logger = setup_logger(__name__)


class SVGToICOConverter(BaseDialog):
    """Fenêtre de conversion SVG vers ICO."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Convertisseur SVG → ICO"),
            geometry="500x350",
            minsize=(450, 300),
        )

        self.svg_path = None
        self.ico_path = None

        self._create_widgets()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Titre
        title = ttk.Label(main, text=_("Convertisseur SVG vers ICO"), font=('Arial', 14, 'bold'))
        title.pack(pady=(0, 20))

        # Sélection fichier SVG
        svg_frame = ttk.LabelFrame(main, text=_("Fichier SVG source"), padding=10)
        svg_frame.pack(fill=tk.X, pady=(0, 15))
        svg_frame.columnconfigure(0, weight=1)

        self.svg_entry = ttk.Entry(svg_frame, state='readonly')
        self.svg_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        svg_btn = ttk.Button(svg_frame, text=_("Parcourir..."), command=self._select_svg)
        svg_btn.grid(row=0, column=1)

        # Options ICO
        options_frame = ttk.LabelFrame(main, text=_("Options de conversion"), padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        options_frame.columnconfigure(1, weight=1)

        # Tailles
        ttk.Label(options_frame, text=_("Tailles à inclure :")).grid(row=0, column=0, sticky=tk.W, pady=2)
        sizes_frame = ttk.Frame(options_frame)
        sizes_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

        self.size_vars = {}
        default_sizes = [16, 24, 32, 48, 64, 128, 256]
        for i, size in enumerate(default_sizes):
            var = tk.BooleanVar(value=True if size in (16, 32, 48, 64, 128, 256) else False)
            self.size_vars[size] = var
            cb = ttk.Checkbutton(sizes_frame, text=f"{size}x{size}", variable=var)
            cb.pack(side=tk.LEFT, padx=3)

        # Fichier de sortie
        output_frame = ttk.LabelFrame(main, text=_("Fichier ICO de sortie"), padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 15))
        output_frame.columnconfigure(0, weight=1)

        self.ico_entry = ttk.Entry(output_frame, state='readonly')
        self.ico_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ico_btn = ttk.Button(output_frame, text=_("Parcourir..."), command=self._select_ico)
        ico_btn.grid(row=0, column=1)

        # Barre de progression
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(main, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))

        self.status_var = tk.StringVar(value=_("Prêt"))
        status_label = ttk.Label(main, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(fill=tk.X)

        # Boutons d'action
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self.convert_btn = ttk.Button(btn_frame, text=_("Convertir"), command=self._convert, state='disabled')
        self.convert_btn.pack(side=tk.RIGHT, padx=5)

        close_btn = ttk.Button(btn_frame, text=_("Fermer"), command=self.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)

    def _select_svg(self):
        """Sélectionne le fichier SVG source."""
        path = filedialog.askopenfilename(
            title=_("Sélectionner un fichier SVG"),
            filetypes=[(_("Fichiers SVG"), "*.svg"), (_("Tous les fichiers"), "*.*")]
        )
        if path:
            self.svg_path = Path(path)
            self.svg_entry.config(state='normal')
            self.svg_entry.delete(0, tk.END)
            self.svg_entry.insert(0, str(self.svg_path))
            self.svg_entry.config(state='readonly')

            # Auto-générer le nom du fichier ICO
            ico_path = self.svg_path.with_suffix('.ico')
            self.ico_path = ico_path
            self.ico_entry.config(state='normal')
            self.ico_entry.delete(0, tk.END)
            self.ico_entry.insert(0, str(ico_path))
            self.ico_entry.config(state='readonly')

            self.convert_btn.config(state='normal')
            self.status_var.set(_("Fichier SVG sélectionné"))

    def _select_ico(self):
        """Sélectionne le fichier ICO de sortie."""
        path = filedialog.asksaveasfilename(
            title=_("Enregistrer le fichier ICO"),
            defaultextension=".ico",
            filetypes=[(_("Fichiers ICO"), "*.ico"), (_("Tous les fichiers"), "*.*")]
        )
        if path:
            self.ico_path = Path(path)
            self.ico_entry.config(state='normal')
            self.ico_entry.delete(0, tk.END)
            self.ico_entry.insert(0, str(self.ico_path))
            self.ico_entry.config(state='readonly')

    def _convert(self):
        """Lance la conversion SVG vers ICO."""
        if not self.svg_path or not self.svg_path.exists():
            self.show_error(_("Erreur"), _("Veuillez sélectionner un fichier SVG valide"))
            return

        if not self.ico_path:
            self.show_error(_("Erreur"), _("Veuillez spécifier un fichier de sortie"))
            return

        # Récupérer les tailles sélectionnées
        sizes = [size for size, var in self.size_vars.items() if var.get()]
        if not sizes:
            self.show_error(_("Erreur"), _("Veuillez sélectionner au moins une taille"))
            return

        self.convert_btn.config(state='disabled')
        self.progress_var.set(0)
        self.status_var.set(_("Conversion en cours..."))

        try:
            from .svg_utils import svg_to_ico

            # Rendre le SVG et l'enregistrer en ICO multi-tailles
            self.progress_var.set(30)
            self.status_var.set(_("Rendu du SVG..."))
            self.update_idletasks()

            svg_to_ico(self.svg_path, self.ico_path, sizes)

            self.progress_var.set(100)
            self.status_var.set(_("Conversion terminée avec succès !"))
            
            self.show_info(
                _("Succès"),
                _("Fichier ICO créé : {}").format(self.ico_path)
            )
            from .toast import show_toast
            show_toast(self, _("Conversion terminée avec succès"), 'success', parent=self)
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion : {e}")
            self.status_var.set(_("Erreur lors de la conversion"))
            self.show_error(_("Erreur"), _("Impossible de convertir : {}").format(str(e)))
        finally:
            self.convert_btn.config(state='normal')