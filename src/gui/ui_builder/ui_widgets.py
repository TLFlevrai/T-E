# src/gui/ui_builder/ui_widgets.py
from __future__ import annotations
"""Type-safe UI widgets container using dataclasses."""
from dataclasses import dataclass, field
from typing import Optional, Callable
import tkinter as tk
from tkinter import ttk

# Extensions proposées dans l'onglet « Extensions avancées ».
# Format : (attribut_var, extensions, msgid_libellé). Une même case peut
# couvrir plusieurs extensions synonymes (.yaml/.yml, .ini/.cfg).
# Les libellés sont des msgid NON traduits ici : la traduction est appliquée
# à la création des widgets, pour suivre le changement de langue à chaud.
# La validation (liste blanche ALLOWED_EXTRA_EXTENSIONS) reste en amont,
# dans le schéma Pydantic.
EXTRA_EXT_CHOICES = (
    ('extra_ext_toml', ('.toml',), "TOML (.toml)"),
    ('extra_ext_yaml', ('.yaml', '.yml'), "YAML (.yaml, .yml)"),
    ('extra_ext_ini', ('.ini', '.cfg'), "INI (.ini, .cfg)"),
    ('extra_ext_xml', ('.xml',), "XML (.xml)"),
    ('extra_ext_sh', ('.sh',), "Shell (.sh)"),
    ('extra_ext_ps1', ('.ps1',), "PowerShell (.ps1)"),
    ('extra_ext_sql', ('.sql',), "SQL (.sql)"),
    ('extra_ext_ts', ('.ts',), "TypeScript (.ts)"),
    ('extra_ext_vue', ('.vue',), "Vue (.vue)"),
    ('extra_ext_rst', ('.rst',), "reStructuredText (.rst)"),
)


@dataclass
class UIWidgets:
    """Container for all UI widgets and variables with type safety."""
    
    # Variables
    folder_path_var: tk.StringVar = field(default_factory=tk.StringVar)
    progress_var: tk.DoubleVar = field(default_factory=tk.DoubleVar)
    status_var: tk.StringVar = field(default_factory=lambda: tk.StringVar(value="Prêt"))
    
    # Custom output directory (optional override)
    custom_output_dir: tk.StringVar = field(default_factory=tk.StringVar)
    
    # Extraction options (BooleanVars)
    include_subdirs: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    show_file_paths: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_json: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_txt: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    include_md: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    include_po: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    include_mo: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    include_html: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_css: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_js: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_structure: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    ignore_init: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    ignore_git: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    ignore_pycache: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_statistics: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_file_metadata: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))

    # Other options
    archive_old: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
    log_visible: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    sidebar_visible: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    
    # Widgets (populated by build_widgets)
    browse_btn: ttk.Button = None
    extract_btn: ttk.Button = None
    cancel_btn: ttk.Button = None
    select_btn: ttk.Button = None
    version_btn: ttk.Button = None
    network_btn: ttk.Button = None
    clear_btn: ttk.Button = None
    progress_bar: ttk.Progressbar = None
    info_frame: ttk.LabelFrame = None
    info_text: tk.Text = None
    status_bar: ttk.Label = None
    main_frame: ttk.Frame = None
    
    # Menus (populated by build_menus)
    menubar: tk.Menu = None
    recent_menu: tk.Menu = None
    tools_menu: tk.Menu = None
    view_menu: tk.Menu = None
    open_version_explorer_index: int = 0
    update_recent_menu: Optional[Callable[[], None]] = None
    
    # Controller reference
    controller: object = None
    
    # Navigation entre outils (fournie par le Shell TE)
    navigate_to: Optional[Callable[[str], None]] = None
    quit_callback: Optional[Callable[[], None]] = None
    
    # Internal: lazy widgets for i18n refresh
    _lazy_widgets: list = field(default_factory=list)
    _lazy_tooltips: list = field(default_factory=list)
    _i18n_refresh_callback: Optional[Callable[[], None]] = None
    _i18n_menu_refresh_callback: Optional[Callable[[], None]] = None


def apply_extra_extensions(ui, extensions) -> None:
    """Alimente les cases à cocher d'extensions avancées.

    Sens inverse de `collect_extra_extensions` : une liste d'extensions
    positionne les cases. Utilisé par `create_ui_widgets` (restauration
    depuis la config) et par les presets.
    """
    requested = {
        ext.strip().lower()
        for ext in (extensions or [])
        if isinstance(ext, str) and ext.strip()
    }
    for attr, exts, _label in EXTRA_EXT_CHOICES:
        var = getattr(ui, attr, None)
        if var is not None:
            var.set(any(ext in requested for ext in exts))


def collect_extra_extensions(ui) -> list[str]:
    """Reconstruit `extra_extensions` depuis les cases à cocher de l'UI.

    Une case cochée active toutes les extensions qu'elle couvre (ex. .yaml
    et .yml ensemble). L'ordre suit EXTRA_EXT_CHOICES, donc le résultat est
    stable et indépendant de l'ordre de parcours des cases.
    La liste blanche reste vérifiée plus bas, par le schéma Pydantic.
    """
    result: list[str] = []
    for attr, exts, _label in EXTRA_EXT_CHOICES:
        var = getattr(ui, attr, None)
        if var is not None and var.get():
            for ext in exts:
                if ext not in result:
                    result.append(ext)
    return result


# Flags d'extraction pilotés par des cases à cocher dans les paramètres.
# `include_md` est listé ici (et non dans les onglets) car il vit dans
# l'onglet Formats ; les extensions supplémentaires sont traitées à part,
# via EXTRA_EXT_CHOICES, pour rester une source unique de vérité.
EXTRACTION_FLAG_KEYS = (
    'include_json', 'include_html', 'include_css', 'include_js',
    'include_txt', 'include_md', 'include_po', 'include_mo',
    'include_subdirs', 'show_file_paths', 'include_structure',
    'ignore_init', 'ignore_git', 'ignore_pycache',
    'include_statistics', 'include_file_metadata',
)


def apply_extraction_flags(ui, extraction) -> list[str]:
    """Recopie les cases à cocher de l'UI vers un objet ExtractionOptions.

    Retourne la liste des clés réellement écrites. Les cases d'extensions
    avancées sont résolues via EXTRA_EXT_CHOICES puis validées par le schéma
    (liste blanche), ce qui évite toute liste d'attributs dupliquée ici.
    """
    written = []
    for key in EXTRACTION_FLAG_KEYS:
        var = getattr(ui, key, None)
        if var is None:
            continue
        setattr(extraction, key, bool(var.get()))
        written.append(key)

    extra = collect_extra_extensions(ui)
    # La liste blanche est appliquée par le modèle : la validation est faite
    # au chargement de la config et lors de l'extraction, pas ici.
    extraction.extra_extensions = extra
    written.append('extra_extensions')
    return written


def create_ui_widgets(config_obj) -> UIWidgets:
    """Factory function to create UIWidgets with values from config."""
    cfg = config_obj.get_all()
    
    ui = UIWidgets(
        status_var=tk.StringVar(value="Prêt"),
        include_subdirs=tk.BooleanVar(value=cfg.extraction.include_subdirs),
        show_file_paths=tk.BooleanVar(value=cfg.extraction.show_file_paths),
        include_json=tk.BooleanVar(value=cfg.extraction.include_json),
        include_txt=tk.BooleanVar(value=cfg.extraction.include_txt),
        include_md=tk.BooleanVar(value=cfg.extraction.include_md),
        include_po=tk.BooleanVar(value=cfg.extraction.include_po),
        include_mo=tk.BooleanVar(value=cfg.extraction.include_mo),
        include_html=tk.BooleanVar(value=cfg.extraction.include_html),
        include_css=tk.BooleanVar(value=cfg.extraction.include_css),
        include_js=tk.BooleanVar(value=cfg.extraction.include_js),
        include_structure=tk.BooleanVar(value=cfg.extraction.include_structure),
        ignore_init=tk.BooleanVar(value=cfg.extraction.ignore_init),
        ignore_git=tk.BooleanVar(value=cfg.extraction.ignore_git),
        ignore_pycache=tk.BooleanVar(value=cfg.extraction.ignore_pycache),
        include_statistics=tk.BooleanVar(value=cfg.extraction.include_statistics),
        include_file_metadata=tk.BooleanVar(value=cfg.extraction.include_file_metadata),
        sidebar_visible=tk.BooleanVar(value=True),
    )

    # Extensions avancées : une BooleanVar par case, positionnée d'après la
    # config persistée (les cases non décrites restent à False).
    for attr, _exts, _label in EXTRA_EXT_CHOICES:
        setattr(ui, attr, tk.BooleanVar(value=False))
    apply_extra_extensions(ui, getattr(cfg.extraction, 'extra_extensions', None))

    return ui


def register_lazy_widget(ui: UIWidgets, widget, msgid: str):
    """Enregistre un widget avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((widget, msgid, 'text'))


def register_lazy_labelframe(ui: UIWidgets, labelframe, msgid: str):
    """Enregistre un LabelFrame avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((labelframe, msgid, 'label'))