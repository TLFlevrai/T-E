# src/gui/ui_builder/menus.py
import os
import tkinter as tk
from src.i18n import _, pgettext, change_language as i18n_change_language, register_reload_callback, unregister_reload_callback
from src.gui.recent_files import load_recent_folders, clear_recent_folders
from src.gui.settings_dialog import open_settings_dialog
from src.gui.theme_editor import open_theme_editor
from .ui_widgets import UIWidgets


def build_menus(parent, ui: UIWidgets):
    """Construit la barre de menus et enregistre le callback de rechargement i18n."""
    menubar = tk.Menu(parent)
    parent.config(menu=menubar)
    ui.menubar = menubar
    ui._menu_items = {}

    _rebuild_all_menus(parent, ui)

    # Enregistrer callback pour rechargement à chaud
    def refresh_menus():
        _rebuild_all_menus(parent, ui)
    
    register_reload_callback(refresh_menus)
    ui._i18n_menu_refresh_callback = refresh_menus


def _rebuild_all_menus(parent, ui: UIWidgets):
    """Reconstruit tous les menus avec la langue actuelle."""
    menubar = ui.menubar
    menubar.delete(0, tk.END)
    menu_items = ui._menu_items

    # --- Menu Fichier ---
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=pgettext("menu", "Fichier"), menu=file_menu)
    menu_items['file_menu'] = file_menu
    menu_items['file_cascade_index'] = 0

    file_menu.add_command(label=_("Exporter en PDF"),
        command=lambda: _export_to_pdf(parent, ui)
    )
    file_menu.add_separator()

    file_menu.add_command(
        label=_("Quitter"),
        # Résolu à l'appel : quit_callback est assigné APRÈS build_menus
        # (shell.py) ; une liaison anticipée binderait bare destroy et
        # sauterait toute la sauvegarde à la fermeture.
        command=lambda: ui.quit_callback() if ui.quit_callback else parent.destroy(),
        accelerator="Ctrl+Q",
    )

    # Sous-menu "Emplacements récents"
    recent_menu = tk.Menu(file_menu, tearoff=0)
    file_menu.add_cascade(label=_("Emplacements récents"), menu=recent_menu)
    menu_items['recent_menu'] = recent_menu
    menu_items['recent_cascade_index'] = 1

    # Fonction pour mettre à jour le sous-menu
    def update_recent_menu():
        recent_menu.delete(0, tk.END)
        folders = load_recent_folders()
        if not folders:
            recent_menu.add_command(label=_("Aucun"), state='disabled')
        else:
            for f in folders:
                label = f"{os.path.basename(f)} ({f})"
                recent_menu.add_command(
                    label=label,
                    command=lambda path=f: _select_recent_folder(parent, ui, path)
                )
            recent_menu.add_separator()
            recent_menu.add_command(label=_("Effacer la liste"), command=_clear_recent)
    ui.update_recent_menu = update_recent_menu

    def _clear_recent():
        clear_recent_folders()
        if ui.update_recent_menu:
            ui.update_recent_menu()

    update_recent_menu()

    # --- Menu Options (remplacé par boîte de dialogue Paramètres) ---
    options_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=_("Options"), menu=options_menu)
    menu_items['options_menu'] = options_menu
    menu_items['options_cascade_index'] = 1

    options_menu.add_command(label=_("Paramètres..."), command=lambda: open_settings_dialog(parent, ui))
    options_menu.add_separator()
    
    # Thème
    options_menu.add_command(label=_("Éditeur de thème..."), command=lambda: open_theme_editor(parent))
    options_menu.add_separator()
    
    # Accès rapide aux presets
    options_menu.add_command(label=_("Preset : Python uniquement"), command=lambda: apply_preset(ui, 'python_only'))
    options_menu.add_command(label=_("Preset : Assets Web"), command=lambda: apply_preset(ui, 'web_assets'))
    options_menu.add_command(label=_("Preset : Complet"), command=lambda: apply_preset(ui, 'full'))
    options_menu.add_command(label=_("Preset : Minimal"), command=lambda: apply_preset(ui, 'minimal'))

    # --- Menu Langue ---
    lang_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=_("Langue"), menu=lang_menu)
    menu_items['lang_menu'] = lang_menu
    menu_items['lang_cascade_index'] = 2
    
    lang_menu.add_command(label="Français", command=lambda: _change_language_hot(ui, "fr"))
    lang_menu.add_command(label="English", command=lambda: _change_language_hot(ui, "en"))

    # --- Menu Outils (navigation dans le workspace, dialogue en repli) ---
    tools_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=_("Outils"), menu=tools_menu)
    menu_items['tools_menu'] = tools_menu
    menu_items['tools_cascade_index'] = 3
    tools_menu.add_command(label=_("Extraction"), command=lambda: _navigate(ui, 'extract'))
    tools_menu.add_command(label=_("Conversion"), command=lambda: _navigate(ui, 'convert'))
    tools_menu.add_command(label=_("Vidéo"), command=lambda: _navigate(ui, 'video'))
    tools_menu.add_command(label=_("Calculatrice"), command=lambda: _navigate(ui, 'calculator'))
    tools_menu.add_separator()
    tools_menu.add_command(label=_("Centre réseau"), command=lambda: _navigate(ui, 'network'))
    tools_menu.add_command(label=_("Gestionnaire de versions"), command=lambda: _navigate(ui, 'versions'))
    tools_menu.add_separator()
    tools_menu.add_command(label=_("Outils"), command=lambda: _navigate(ui, 'tools'))
    tools_menu.add_command(label=_("Paramètres"), command=lambda: _navigate(ui, 'settings'))
    ui.open_version_explorer_index = 0

    # --- Menu Vue ---
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label=_("Vue"), menu=view_menu)
    menu_items['view_menu'] = view_menu
    menu_items['view_cascade_index'] = 4
    view_menu.add_checkbutton(label=_("Afficher le journal"), variable=ui.log_visible)
    ui.view_menu = view_menu


def _navigate(ui: UIWidgets, tool_id: str):
    """Navigue vers un outil du workspace (repli : dialogue dédié)."""
    navigator = getattr(ui, 'navigate_to', None)
    if navigator:
        navigator(tool_id)
        return
    # Repli : ouvrir le dialogue classique si le Shell n'est pas disponible
    if tool_id == 'versions':
        _open_version_explorer(None, ui)
    elif tool_id == 'network':
        _open_network_center(None, ui)
    elif tool_id == 'convert':
        _open_svg_converter(None, ui)
    elif tool_id == 'video':
        from src.gui.video_converter import open_video_converter
        import tkinter as tk
        root = tk._default_root
        if root:
            open_video_converter(root)
    elif tool_id == 'calculator':
        _open_calculator(None)


def _change_language_hot(ui: UIWidgets, lang_code):
    """Change la langue à chaud sans redémarrer l'application."""
    success = i18n_change_language(lang_code)
    if success:
        # Les callbacks register_reload_callback s'occupent du rafraîchissement
        pass


def _export_to_pdf(parent, ui: UIWidgets):
    """Exporte le code du projet sélectionné en PDF."""
    controller = ui.controller
    if controller:
        controller.export_to_pdf()
    else:
        from ..errors import show_warning, show_error
        folder = ui.folder_path_var.get()
        if not folder:
            show_warning(_("Attention"), _("Veuillez d'abord sélectionner un dossier"), parent=parent)
            return
        show_error(_("Erreur"), _("Contrôleur non disponible pour l'export PDF"), parent=parent)


def _select_recent_folder(parent, ui: UIWidgets, folder_path):
    """Sélectionne un dossier récent via le contrôleur."""
    controller = ui.controller
    if controller:
        controller.select_recent_folder(folder_path)
    else:
        ui.folder_path_var.set(folder_path)
        ui.extract_btn.config(state='normal')


def _open_version_explorer(parent, ui: UIWidgets):
    """Ouvre le gestionnaire de versions via le contrôleur (repli du Shell)."""
    controller = ui.controller if ui else None
    if controller:
        controller.open_version_explorer()
    else:
        from src.gui.version_explorer import VersionExplorerDialog
        VersionExplorerDialog(parent)


def _open_network_center(parent, ui: UIWidgets):
    """Ouvre le centre réseau via le contrôleur (repli du Shell)."""
    controller = ui.controller if ui else None
    if controller:
        controller.open_network_center()
    else:
        import tkinter as tk
        from src.gui.network_center import NetworkCenterDialog
        root = parent or tk._default_root
        if root:
            NetworkCenterDialog(root, None, None, None)


def _open_svg_converter(parent, ui: UIWidgets):
    """Ouvre le convertisseur SVG vers ICO."""
    import tkinter as tk
    from src.gui.converter import SVGToICOConverter
    root = parent or tk._default_root
    if root:
        SVGToICOConverter(root)


def _open_calculator(parent):
    """Ouvre la calculatrice."""
    import tkinter as tk
    from src.gui.calculator import open_calculator
    root = parent or tk._default_root
    if root:
        open_calculator(root)


def apply_preset(ui: UIWidgets, preset: str):
    """Applique un preset d'export rapide (fonction publique)."""
    presets = {
        'python_only': {
            'include_json': False, 'include_html': False, 'include_css': False,
            'include_js': False, 'include_txt': False, 'include_po': False,
            'include_mo': False, 'include_structure': True,
        },
        'web_assets': {
            'include_json': True, 'include_html': True, 'include_css': True,
            'include_js': True, 'include_txt': False, 'include_po': False,
            'include_mo': False, 'include_structure': True,
        },
        'full': {
            'include_json': True, 'include_html': True, 'include_css': True,
            'include_js': True, 'include_txt': True, 'include_po': True,
            'include_mo': True, 'include_structure': True,
            'include_statistics': True, 'include_file_metadata': True,
        },
        'minimal': {
            'include_json': False, 'include_html': False, 'include_css': False,
            'include_js': False, 'include_txt': False, 'include_po': False,
            'include_mo': False, 'include_structure': True,
            'include_statistics': True,
        },
    }
    if preset in presets:
        for key, value in presets[preset].items():
            var = getattr(ui, key, None)
            if var:
                var.set(value)


def unregister_menu_refresh(ui: UIWidgets):
    """Désenregistre le callback de rafraîchissement des menus."""
    callback = ui._i18n_menu_refresh_callback
    if callback:
        unregister_reload_callback(callback)
        ui._i18n_menu_refresh_callback = None