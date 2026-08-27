# src/gui/ui_builder/ui_widgets.py
"""Type-safe UI widgets container using dataclasses."""
from dataclasses import dataclass, field
from typing import Optional, Callable
import tkinter as tk
from tkinter import ttk


@dataclass
class UIWidgets:
    """Container for all UI widgets and variables with type safety."""
    
    # Variables
    folder_path_var: tk.StringVar = field(default_factory=tk.StringVar)
    progress_var: tk.DoubleVar = field(default_factory=tk.DoubleVar)
    status_var: tk.StringVar = field(default_factory=lambda: tk.StringVar(value="Prêt"))
    
    # Extraction options (BooleanVars)
    include_subdirs: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    show_file_paths: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_json: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    include_txt: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=False))
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


def create_ui_widgets(config_obj) -> UIWidgets:
    """Factory function to create UIWidgets with values from config."""
    cfg = config_obj.get_all()
    
    ui = UIWidgets(
        status_var=tk.StringVar(value="Prêt"),
        include_subdirs=tk.BooleanVar(value=cfg.extraction.include_subdirs),
        show_file_paths=tk.BooleanVar(value=cfg.extraction.show_file_paths),
        include_json=tk.BooleanVar(value=cfg.extraction.include_json),
        include_txt=tk.BooleanVar(value=cfg.extraction.include_txt),
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
    )
    
    return ui


def register_lazy_widget(ui: UIWidgets, widget, msgid: str):
    """Enregistre un widget avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((widget, msgid, 'text'))


def register_lazy_labelframe(ui: UIWidgets, labelframe, msgid: str):
    """Enregistre un LabelFrame avec son message pour mise à jour ultérieure."""
    ui._lazy_widgets.append((labelframe, msgid, 'label'))