# src/gui/theme.py
"""Système de design de TE : tokens, palettes clair/sombre et styles ttk.

Identité visuelle « Graphite & Cyan » :
- surfaces neutres graphite avec hiérarchie claire (bg → surface → alt) ;
- accent cyan/teal unique, utilisé avec parcimonie (action primaire,
  sélection, focus) ;
- rendu flat précis (base `clam`) : bordures fines 1px, pas de gradients ;
- typographie Segoe UI hiérarchisée (titres / corps / secondaire).

Toutes les couleurs passent par les tokens : aucun code hexadécimal
dispersé dans l'application (utiliser `get_color(key)`).
"""
import tkinter as tk
from tkinter import ttk

from src.config import get_config

# ---------------------------------------------------------------------------
# Tokens d'espacement / rayons / typographie
# ---------------------------------------------------------------------------

SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 24,
    'xxl': 32,
}

RADIUS = {
    'sm': 4,   # champs, petites pill
    'md': 8,   # cartes, boutons
    'lg': 12,  # dialogues, surfaces majeures
}

FONT = {
    'family': 'Segoe UI',
    'display': ('Segoe UI', 20, 'bold'),     # titre de page
    'h1': ('Segoe UI', 15, 'bold'),          # titre d'outil
    'h2': ('Segoe UI', 11, 'bold'),          # titre de carte
    'body': ('Segoe UI', 10),                # texte courant
    'small': ('Segoe UI', 9),                # secondaire
    'caption': ('Segoe UI', 8),              # hints, catégories
    'mono': ('Consolas', 9),                 # journal
}

# ---------------------------------------------------------------------------
# Palettes (tokens complets)
# ---------------------------------------------------------------------------

PALETTES = {
    'light': {
        # Surfaces (hiérarchie : bg < surface < surface_alt)
        'bg': '#F3F5F7',
        'surface': '#FFFFFF',
        'surface_alt': '#E9EDF1',
        'surface_active': '#DFE6EC',
        'frame_bg': '#F3F5F7',          # compat : arrière-plan générique
        # Bordures
        'border': '#D7DDE4',
        'border_strong': '#B9C2CC',
        # Texte
        'fg': '#191D23',
        'fg_muted': '#5D6875',
        'disabled_fg': '#9AA5B1',
        # Accent (cyan-teal profond)
        'accent': '#0E7490',
        'accent_hover': '#155E75',
        'accent_fg': '#FFFFFF',
        'accent_soft': '#D7EEF5',       # fond teinté (chips, icônes, actif)
        # Sémantiques
        'success': '#15803D',
        'warning': '#B45309',
        'error': '#B91C1C',
        # Sélection
        'select_bg': '#0E7490',
        'select_fg': '#FFFFFF',
        # Contrôles (compat anciennes clés)
        'entry_bg': '#FFFFFF',
        'entry_fg': '#191D23',
        'button_bg': '#FFFFFF',
        'button_fg': '#191D23',
        'text_bg': '#FFFFFF',
        'text_fg': '#191D23',
        # Toasts / overlays
        'overlay': '#232A33',
        'overlay_fg': '#ECF2F6',
    },
    'dark': {
        'bg': '#12151A',
        'surface': '#1B2027',
        'surface_alt': '#242B34',
        'surface_active': '#2E3743',
        'frame_bg': '#12151A',
        'border': '#2C343F',
        'border_strong': '#3D4855',
        'fg': '#E7EBF0',
        'fg_muted': '#94A0AE',
        'disabled_fg': '#5D6875',
        'accent': '#22D3EE',
        'accent_hover': '#67E3F4',
        'accent_fg': '#10151B',
        'accent_soft': '#17323C',
        'success': '#4ADE80',
        'warning': '#FBBF24',
        'error': '#F87171',
        'select_bg': '#155E75',
        'select_fg': '#ECFEFF',
        'entry_bg': '#1B2027',
        'entry_fg': '#E7EBF0',
        'button_bg': '#1B2027',
        'button_fg': '#E7EBF0',
        'text_bg': '#161B21',
        'text_fg': '#E7EBF0',
        'overlay': '#262E38',
        'overlay_fg': '#ECF2F6',
    },
}

# Thème neutre historique (éditeur de thème : "Réinitialiser")
THEMES = {
    'light': dict(PALETTES['light']),
    'dark': dict(PALETTES['dark']),
    'default': dict(PALETTES['light']),
}

_current_palette_name = 'light'
_current_palette: dict = dict(PALETTES['light'])


def get_color(key: str) -> str:
    """Retourne la valeur courante d'un token couleur."""
    return _current_palette.get(key, _current_palette['fg'])


def get_font(name: str):
    """Retourne une police du système de design."""
    return FONT.get(name, FONT['body'])


def get_system_theme() -> str:
    """Détecte le thème système (Windows 10/11)."""
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return 'light' if value == 1 else 'dark'
    except Exception:
        return 'light'


def get_current_theme() -> str:
    """Retourne le thème actuellement actif."""
    global _current_palette_name
    if _current_palette_name == 'system':
        return get_system_theme()
    return _current_palette_name


def resolve_palette(theme_name: str) -> dict:
    """Construit la palette effective.

    Thème 'custom' : palette système + surcharges de `gui.custom_theme`,
    puis surcharge éventuelle de `THEMES['custom']` (aperçu live de
    l'éditeur de thème, qui peut modifier le thème sans sauvegarder).
    """
    actual = theme_name if theme_name in PALETTES else get_system_theme()
    if actual == 'custom':
        palette = dict(PALETTES[get_system_theme()])
        try:
            custom = get_config().get_all().gui.custom_theme or {}
            palette.update({k: v for k, v in custom.items()
                            if isinstance(v, str) and v.startswith('#')})
        except Exception:
            pass
        palette.update({k: v for k, v in THEMES.get('custom', {}).items()
                        if isinstance(v, str) and v.startswith('#')})
        return palette
    return dict(PALETTES.get(actual, PALETTES['light']))


def apply_theme(theme_name: str = None):
    """Applique un thème à toute l'application."""
    global _current_palette_name, _current_palette

    if theme_name is None:
        config = get_config()
        theme_name = config.get('gui.theme', 'system')

    _current_palette_name = theme_name
    colors = resolve_palette(theme_name)
    _current_palette = colors

    # Base de rendu : clam donne le contrôle total des couleurs (bordures,
    # focus) pour un rendu flat cohérent, indépendant du thème Windows.
    style = ttk.Style()
    try:
        if style.theme_use() != 'clam':
            style.theme_use('clam')
    except Exception:
        pass

    _apply_base_styles(style, colors)
    _apply_component_styles(style, colors)

    # Widgets Tk natifs (Text, Menu, Listbox...)
    try:
        root = tk._default_root
        if root:
            _apply_to_tk_widgets(root, colors)
    except Exception:
        pass

    # Persistance
    try:
        config = get_config()
        config.update_gui(theme=theme_name)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Styles ttk
# ---------------------------------------------------------------------------

def _apply_base_styles(style: ttk.Style, c: dict):
    """Styles de base : chaque classe de widget reçoit les tokens."""
    style.configure('.',
                    background=c['bg'],
                    foreground=c['fg'],
                    fieldbackground=c['entry_bg'],
                    selectbackground=c['select_bg'],
                    selectforeground=c['select_fg'],
                    bordercolor=c['border'],
                    lightcolor=c['surface'],
                    darkcolor=c['border'],
                    troughcolor=c['surface_alt'],
                    focuscolor=c['accent'],
                )

    # Frames & labels
    style.configure('TFrame', background=c['bg'])
    style.configure('TLabel', background=c['bg'], foreground=c['fg'], font=FONT['body'])
    style.configure('Muted.TLabel', background=c['bg'], foreground=c['fg_muted'], font=FONT['small'])
    style.configure('Caption.TLabel', background=c['bg'], foreground=c['fg_muted'], font=FONT['caption'])

    # Bouton standard : discret, bordure fine
    style.configure('TButton', background=c['surface'], foreground=c['fg'],
                    bordercolor=c['border'], borderwidth=1, focalthickness=1,
                    padding=(14, 7), font=FONT['body'], relief='flat')
    style.map('TButton',
              background=[('active', c['surface_alt']), ('pressed', c['surface_active']),
                          ('disabled', c['surface_alt'])],
              foreground=[('disabled', c['disabled_fg'])],
              bordercolor=[('active', c['border_strong']), ('focus', c['accent'])],
              )

    # Champs
    style.configure('TEntry', fieldbackground=c['entry_bg'], foreground=c['entry_fg'],
                    bordercolor=c['border'], lightcolor=c['border'], darkcolor=c['border'],
                    insertcolor=c['fg'], padding=(8, 5))
    style.map('TEntry',
              bordercolor=[('focus', c['accent'])],
              lightcolor=[('focus', c['accent'])],
              darkcolor=[('focus', c['accent'])],
              fieldbackground=[('disabled', c['surface_alt'])],
              foreground=[('disabled', c['disabled_fg'])],
              )
    for w in ('TCombobox', 'TSpinbox'):
        style.configure(w, fieldbackground=c['entry_bg'], foreground=c['entry_fg'],
                        background=c['surface_alt'], bordercolor=c['border'],
                        lightcolor=c['border'], darkcolor=c['border'],
                        arrowcolor=c['fg_muted'], padding=(8, 4))
        style.map(w,
                  fieldbackground=[('readonly', c['entry_bg']), ('disabled', c['surface_alt'])],
                  bordercolor=[('focus', c['accent'])],
                  lightcolor=[('focus', c['accent'])],
                  darkcolor=[('focus', c['accent'])],
                  foreground=[('disabled', c['disabled_fg'])],
                  )
    # Liste déroulante des combobox
    try:
        style.configure('TCombobox.ListboxField', background=c['surface'])
        root = tk._default_root
        if root is not None:
            root.option_add('*TCombobox*Listbox.background', c['surface'])
            root.option_add('*TCombobox*Listbox.foreground', c['fg'])
            root.option_add('*TCombobox*Listbox.selectBackground', c['select_bg'])
            root.option_add('*TCombobox*Listbox.selectForeground', c['select_fg'])
    except Exception:
        pass

    # Checkboxes / radios : indicateur accentué
    style.configure('TCheckbutton', background=c['bg'], foreground=c['fg'],
                    focuscolor=c['accent'], font=FONT['body'], padding=(2, 3))
    style.map('TCheckbutton',
              background=[('active', c['bg'])],
              foreground=[('disabled', c['disabled_fg'])],
              indicatorcolor=[('selected', c['accent']), ('!selected', c['surface'])],
              bordercolor=[('active', c['border_strong'])],
              )
    style.configure('TRadiobutton', background=c['bg'], foreground=c['fg'],
                    focuscolor=c['accent'], font=FONT['body'], padding=(2, 3))
    style.map('TRadiobutton',
              background=[('active', c['bg'])],
              foreground=[('disabled', c['disabled_fg'])],
              indicatorcolor=[('selected', c['accent']), ('!selected', c['surface'])],
              )

    # Slider
    style.configure('TScale', background=c['bg'], troughcolor=c['surface_alt'],
                    bordercolor=c['border'], lightcolor=c['accent'], darkcolor=c['accent'])

    # Progression fine et discrète
    style.configure('TProgressbar', background=c['accent'], troughcolor=c['surface_alt'],
                    bordercolor=c['surface_alt'], lightcolor=c['accent'],
                    darkcolor=c['accent'], thickness=6)

    # Notebook : onglets plats, actif souligné par la couleur de surface
    style.configure('TNotebook', background=c['bg'], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure('TNotebook.Tab', background=c['bg'], foreground=c['fg_muted'],
                    padding=(16, 8), font=FONT['body'], borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', c['bg']), ('active', c['surface_alt'])],
              foreground=[('selected', c['accent']), ('active', c['fg'])],
              )

    # LabelFrame : carte légère
    style.configure('TLabelframe', background=c['bg'], bordercolor=c['border'], relief='flat')
    style.configure('TLabelframe.Label', background=c['bg'], foreground=c['fg_muted'],
                    font=FONT['small'])

    # Scrollbar fine et discrète
    style.configure('TScrollbar', background=c['surface_alt'], troughcolor=c['bg'],
                    bordercolor=c['bg'], arrowcolor=c['fg_muted'], relief='flat')
    style.map('TScrollbar',
              background=[('active', c['surface_active']), ('pressed', c['border_strong'])],
              )

    style.configure('TSeparator', background=c['border'])

    # Treeview : lignes aérées, sélection accent
    style.configure('Treeview', background=c['surface'], fieldbackground=c['surface'],
                    foreground=c['fg'], rowheight=28, bordercolor=c['border'],
                    font=FONT['body'])
    style.configure('Treeview.Heading', background=c['bg'], foreground=c['fg_muted'],
                    font=FONT['small'], borderwidth=0, padding=(8, 6))
    style.map('Treeview',
              background=[('selected', c['select_bg'])],
              foreground=[('selected', c['select_fg'])],
              )
    style.map('Treeview.Heading',
              background=[('active', c['surface_alt'])],
              )


def _apply_component_styles(style: ttk.Style, c: dict):
    """Styles applicatifs partagés par tous les outils."""

    def primary_button(name: str, bg: str, hover: str, fg: str):
        style.configure(name, background=bg, foreground=fg, borderwidth=0,
                        focalthickness=0, padding=(18, 8), font=FONT['h2'])
        style.map(name,
                  background=[('active', hover), ('pressed', hover),
                              ('disabled', c['surface_alt'])],
                  foreground=[('active', fg), ('pressed', fg),
                              ('disabled', c['disabled_fg'])],
                  )

    # Action primaire : accent plein
    primary_button('AppPrimary.TButton', c['accent'], c['accent_hover'], c['accent_fg'])
    # Alias historique (outil YouTube)
    primary_button('Accent.TButton', c['accent'], c['accent_hover'], c['accent_fg'])

    # Action secondaire : surface + bordure fine
    style.configure('AppGhost.TButton', background=c['surface'], foreground=c['fg'],
                    bordercolor=c['border'], borderwidth=1, focalthickness=1,
                    padding=(12, 6), font=FONT['body'])
    style.map('AppGhost.TButton',
              background=[('active', c['surface_alt']), ('pressed', c['surface_active']),
                          ('disabled', c['bg'])],
              foreground=[('active', c['fg']), ('pressed', c['fg']),
                          ('disabled', c['disabled_fg'])],
              bordercolor=[('active', c['border_strong']), ('focus', c['accent'])],
              )

    # Lien discret
    style.configure('AppLink.TButton', background=c['bg'], foreground=c['accent'],
                    borderwidth=0, focalthickness=0, padding=(6, 4), font=FONT['small'])
    style.map('AppLink.TButton',
              background=[('active', c['bg'])],
              foreground=[('active', c['accent_hover']), ('disabled', c['disabled_fg'])],
              )

    # Cartes : surface posée sur le fond, bordure 1px
    style.configure('Card.TFrame', background=c['surface'], bordercolor=c['border'],
                    borderwidth=1, relief='flat')
    style.configure('Card.TLabel', background=c['surface'], foreground=c['fg'])
    style.configure('CardMuted.TLabel', background=c['surface'], foreground=c['fg_muted'],
                    font=FONT['small'])
    # Variante survolée (élévation discrète)
    style.configure('CardHover.TFrame', background=c['surface_alt'],
                    bordercolor=c['accent'], borderwidth=1, relief='flat')

    # Chip : petit conteneur teinté accent (icônes, raccourcis)
    style.configure('Chip.TFrame', background=c['accent_soft'], borderwidth=0)
    style.configure('Chip.TLabel', background=c['accent_soft'], foreground=c['accent'])

    # Barre de statut plate (footer des outils)
    style.configure('Status.TLabel', background=c['bg'], foreground=c['fg_muted'],
                    font=FONT['small'], padding=(8, 4))

    # --- Sidebar ---
    style.configure('Sidebar.TFrame', background=c['surface'])
    style.configure('Sidebar.TLabel', background=c['surface'], foreground=c['fg'])
    style.configure('SidebarTitle.TLabel', background=c['surface'], foreground=c['fg'],
                    font=('Segoe UI', 16, 'bold'))
    style.configure('SidebarSubtitle.TLabel', background=c['surface'],
                    foreground=c['fg_muted'], font=FONT['caption'])
    style.configure('SidebarCategory.TLabel', background=c['surface'],
                    foreground=c['fg_muted'], font=('Segoe UI', 8, 'bold'))
    # Item normal : plat, hover discret
    style.configure('Sidebar.TButton', background=c['surface'], foreground=c['fg'],
                    anchor='w', borderwidth=0, focalthickness=0,
                    padding=(10, 8), font=FONT['body'])
    style.map('Sidebar.TButton',
              background=[('active', c['surface_alt']), ('pressed', c['surface_active'])],
              foreground=[('active', c['fg']), ('pressed', c['fg'])],
              )
    # Item actif : pastille accent à gauche (frame dédié) + fond teinté
    style.configure('SidebarActive.TButton', background=c['accent_soft'],
                    foreground=c['accent'], anchor='w', borderwidth=0,
                    focalthickness=0, padding=(10, 8), font=FONT['h2'])
    style.map('SidebarActive.TButton',
              background=[('active', c['accent_soft'])],
              foreground=[('active', c['accent'])],
              )
    # Champ de recherche sidebar
    style.configure('SidebarSearch.TEntry', fieldbackground=c['bg'],
                    bordercolor=c['border'], lightcolor=c['border'],
                    darkcolor=c['border'], insertcolor=c['fg'], padding=(8, 5))
    style.map('SidebarSearch.TEntry',
              bordercolor=[('focus', c['accent'])],
              lightcolor=[('focus', c['accent'])],
              darkcolor=[('focus', c['accent'])],
              )


def _apply_to_tk_widgets(widget, colors):
    """Applique les tokens aux widgets Tk natifs, récursivement."""
    try:
        widget_class = widget.winfo_class()

        if widget_class in ('Text', 'Listbox'):
            widget.configure(
                bg=colors['text_bg'],
                fg=colors['text_fg'],
                insertbackground=colors['fg'],
                selectbackground=colors['select_bg'],
                selectforeground=colors['select_fg'],
                highlightbackground=colors['border'],
                highlightcolor=colors['accent'],
            )
        elif widget_class == 'Entry':
            widget.configure(
                bg=colors['entry_bg'],
                fg=colors['entry_fg'],
                insertbackground=colors['fg'],
                selectbackground=colors['select_bg'],
                selectforeground=colors['select_fg'],
                highlightbackground=colors['border'],
                highlightcolor=colors['accent'],
                disabledbackground=colors['surface_alt'],
                disabledforeground=colors['disabled_fg'],
            )
        elif widget_class in ('Frame', 'Labelframe', 'Toplevel', 'Tk'):
            widget.configure(bg=colors['bg'])
        elif widget_class == 'Label':
            widget.configure(bg=colors['bg'], fg=colors['fg'])
        elif widget_class == 'Button':
            widget.configure(bg=colors['surface'], fg=colors['fg'],
                             activebackground=colors['surface_alt'],
                             activeforeground=colors['fg'],
                             relief='flat', borderwidth=1,
                             highlightthickness=0,
                             disabledforeground=colors['disabled_fg'])
        elif widget_class == 'Menu':
            widget.configure(bg=colors['surface'], fg=colors['fg'],
                             activebackground=colors['select_bg'],
                             activeforeground=colors['select_fg'],
                             bd=0, relief='flat')
        elif widget_class == 'Canvas':
            widget.configure(bg=colors['surface'], highlightbackground=colors['border'])
        elif widget_class == 'Checkbutton' or widget_class == 'Radiobutton':
            widget.configure(bg=colors['bg'], fg=colors['fg'],
                             activebackground=colors['bg'],
                             activeforeground=colors['fg'])
    except Exception:
        pass

    try:
        for child in widget.winfo_children():
            _apply_to_tk_widgets(child, colors)
    except Exception:
        pass


def refresh_theme():
    """Rafraîchit le thème actuel (après changement de langue par ex)."""
    apply_theme(_current_palette_name)
