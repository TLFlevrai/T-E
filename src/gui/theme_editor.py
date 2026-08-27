# src/gui/theme_editor.py
"""Éditeur de thème personnalisé."""
import tkinter as tk
from tkinter import ttk, colorchooser
from src.i18n import _
from src.config import get_config
from src.gui.theme import THEMES, apply_theme, refresh_theme
from .base_dialog import BaseDialog


class ThemeEditorDialog(BaseDialog):
    """Dialogue pour personnaliser le thème."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Éditeur de thème personnalisé"),
            geometry="700x550",
            minsize=(650, 500),
        )

        self.config = get_config()
        self.color_vars = {}
        self.color_previews = {}

        # État à restaurer si l'utilisateur quitte sans sauvegarder :
        # l'aperçu modifie le thème global, "Annuler"/fermeture doivent
        # rétablir exactement ce qui était appliqué à l'ouverture.
        gui_config = self.config.get_all().gui
        self._previous_theme_name = getattr(gui_config, 'theme', 'system')
        self._previous_custom_theme = dict(getattr(gui_config, 'custom_theme', {}) or {})

        # Charger le thème personnalisé actuel ou créer à partir du thème par défaut
        self._load_custom_theme()

        self._create_widgets()
        # Fermeture par la croix = annulation : restaurer l'aperçu
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _load_custom_theme(self):
        """Charge le thème personnalisé depuis la config."""
        gui_config = self.config.get_all().gui
        custom = getattr(gui_config, 'custom_theme', {})
        
        # Si pas de thème custom, copier depuis 'default'
        if not custom:
            self.custom_theme = THEMES['default'].copy()
        else:
            # Fusionner avec default pour avoir toutes les clés
            self.custom_theme = THEMES['default'].copy()
            self.custom_theme.update(custom)

    def _create_widgets(self):
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Titre
        title = ttk.Label(main, text=_("Personnalisation du thème"), font=('Arial', 14, 'bold'))
        title.pack(pady=(0, 15))

        # Notebook pour organiser les catégories
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # --- Onglet Général ---
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text=_("Général"))
        self._create_color_section(general_frame, [
            ('bg', _("Arrière-plan principal")),
            ('fg', _("Texte principal")),
            ('frame_bg', _("Arrière-plan des cadres")),
            ('border', _("Bordures")),
            ('disabled_fg', _("Texte désactivé")),
        ])

        # --- Onglet Widgets ---
        widgets_frame = ttk.Frame(notebook, padding=10)
        notebook.add(widgets_frame, text=_("Widgets"))
        self._create_color_section(widgets_frame, [
            ('button_bg', _("Arrière-plan boutons")),
            ('button_fg', _("Texte boutons")),
            ('entry_bg', _("Arrière-plan champs")),
            ('entry_fg', _("Texte champs")),
            ('select_bg', _("Sélection (arrière-plan)")),
            ('select_fg', _("Sélection (texte)")),
        ])

        # --- Onglet Zones de texte ---
        text_frame = ttk.Frame(notebook, padding=10)
        notebook.add(text_frame, text=_("Zones de texte"))
        self._create_color_section(text_frame, [
            ('text_bg', _("Arrière-plan journal/texte")),
            ('text_fg', _("Texte journal/texte")),
        ])

        # Boutons d'action
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text=_("Aperçu"), command=self._preview_theme).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=_("Réinitialiser (défaut)"), command=self._reset_to_default).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=_("Annuler"), command=self._cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_("Appliquer et sauvegarder"), command=self._apply_and_save).pack(side=tk.RIGHT, padx=5)

    def _create_color_section(self, parent, color_items):
        """Crée une section avec sélecteurs de couleur."""
        for i, (key, label) in enumerate(color_items):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=6)
            
            ttk.Label(row, text=label, width=30).pack(side=tk.LEFT)
            
            # Variable pour la couleur
            var = tk.StringVar(value=self.custom_theme.get(key, '#000000'))
            self.color_vars[key] = var
            
            # Entry pour le code hex
            entry = ttk.Entry(row, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<FocusOut>', lambda e, k=key: self._on_color_change(k))
            
            # Aperçu couleur (canvas)
            preview = tk.Canvas(row, width=30, height=22, highlightthickness=1, highlightbackground='#999')
            preview.pack(side=tk.LEFT, padx=5)
            self.color_previews[key] = preview
            self._update_preview(preview, var.get())
            
            # Bouton choisir couleur
            ttk.Button(row, text=_("Choisir..."), width=10,
                       command=lambda k=key: self._choose_color(k)).pack(side=tk.LEFT, padx=5)

    def _update_preview(self, canvas, color):
        """Met à jour l'aperçu de couleur."""
        try:
            canvas.delete("all")
            canvas.create_rectangle(0, 0, 30, 22, fill=color, outline='')
        except Exception:
            pass

    def _on_color_change(self, key):
        """Appelé quand la couleur change via l'entry."""
        var = self.color_vars[key]
        color = var.get()
        if color.startswith('#') and len(color) == 7:
            self._update_preview(self.color_previews[key], color)
            self.custom_theme[key] = color

    def _choose_color(self, key):
        """Ouvre le sélecteur de couleur."""
        current = self.color_vars[key].get()
        color = colorchooser.askcolor(initialcolor=current, title=_("Choisir une couleur"))
        if color[1]:  # color[1] est le hex
            self.color_vars[key].set(color[1])
            self._on_color_change(key)

    def _preview_theme(self):
        """Applique le thème temporairement pour aperçu."""
        # Créer un thème temporaire
        temp_theme = self.custom_theme.copy()
        THEMES['custom'] = temp_theme
        apply_theme('custom')

    def _cancel(self):
        """Ferme l'éditeur en restaurant le thème appliqué avant l'aperçu."""
        THEMES['custom'] = dict(self._previous_custom_theme)
        apply_theme(self._previous_theme_name)
        self.destroy()

    def _reset_to_default(self):
        """Réinitialise au thème par défaut (blanc neutre)."""
        if self.confirm(_("Confirmation"), _("Réinitialiser toutes les couleurs au thème par défaut ?")):
            self.custom_theme = THEMES['default'].copy()
            for key, var in self.color_vars.items():
                var.set(self.custom_theme[key])
                self._update_preview(self.color_previews[key], self.custom_theme[key])
            # Appliquer immédiatement
            THEMES['custom'] = self.custom_theme.copy()
            apply_theme('custom')

    def _apply_and_save(self):
        """Sauvegarde le thème personnalisé et l'applique."""
        # Mettre à jour depuis les variables
        for key, var in self.color_vars.items():
            color = var.get()
            if color.startswith('#') and len(color) == 7:
                self.custom_theme[key] = color
        
        # Sauvegarder dans la config
        try:
            gui = self.config._config.gui
            gui.custom_theme = self.custom_theme
            gui.theme = 'custom'
            self.config.save()
        except Exception as e:
            self.show_error(_("Erreur"), _("Impossible de sauvegarder : {}").format(e))
            return
        
        # Enregistrer et appliquer
        THEMES['custom'] = self.custom_theme.copy()
        apply_theme('custom')
        
        self.show_info(_("Succès"), _("Thème personnalisé appliqué et sauvegardé"))
        self.destroy()


def open_theme_editor(parent):
    """Ouvre l'éditeur de thème."""
    ThemeEditorDialog(parent)