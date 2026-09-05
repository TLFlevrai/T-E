# src/ui/shell.py
"""Shell de TE : fenêtre principale = sidebar + workspace + menus.

Le Shell est l'interface hôte de tous les outils. Il ne connaît pas les
outils individuellement : il navigue via le Tool Registry.
"""
from __future__ import annotations

import contextlib
import os
import tkinter as tk
from pathlib import Path

from src.config import get_config
from src.gui.theme import apply_theme, get_color
from src.i18n import _, register_reload_callback, unregister_reload_callback
from src.logger import setup_logger

logger = setup_logger(__name__)


class TEShell:
    """Interface principale de TE (sidebar, workspace, raccourcis, menus)."""

    def __init__(self, root, server, discovery, extraction_service):
        self.root: tk.Tk = root
        self.server = server
        self.discovery = discovery
        self.service = extraction_service
        self.config = get_config()

        # Thème + police moderne
        apply_theme()
        from src.gui.premium import setup_default_font
        setup_default_font(root)

        self._setup_window_geometry()
        self.root.resizable(True, True)

        # Enregistrer tous les outils (idempotent)
        from src.tools import register_all_tools
        register_all_tools()

        # Layout : sidebar | workspace
        root.columnconfigure(0, weight=0, minsize=210)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        from src.ui.sidebar import Sidebar
        from src.ui.workspace import Workspace
        self.sidebar = Sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        self.workspace = Workspace(self)
        self.workspace.grid(row=0, column=1, sticky='nsew')

        # État du toggle sidebar
        self._sidebar_visible = True

        # Bouton toggle toujours visible sur le workspace
        self._workspace_toggle = tk.Button(
            self.workspace,
            text="◀",
            font=('Segoe UI', 11),
            bg=get_color('surface'),
            fg=get_color('fg'),
            activebackground=get_color('surface_alt'),
            activeforeground=get_color('fg'),
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.toggle_sidebar,
            relief='flat',
        )
        self._workspace_toggle.place(relx=0.0, rely=0.0, x=4, y=4, anchor="nw")
        self._workspace_toggle.lift()

        # Outil par défaut : Extraction (construit vue + contrôleur + menus)
        self.show_tool('extract')
        from src.gui.ui_builder.menus import build_menus
        build_menus(root, self.extract_ui)
        self.extract_ui.quit_callback = self.on_close

        # Raccourcis clavier centralisés (Command Registry)
        from src.core.shortcuts import ShortcutManager
        self.shortcuts = ShortcutManager(self)
        self.shortcuts.bind_all()

        self._set_window_icon()
        self._register_i18n_callbacks()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._restore_session()
        self._setup_autosave()

        from src.core.events import events
        events.emit('app.started')

    # --- Sidebar toggle ---

    def toggle_sidebar(self):
        """Affiche/masque la barre latérale."""
        if self._sidebar_visible:
            self.sidebar.grid_forget()
            self.root.columnconfigure(0, weight=0, minsize=0)
            self._sidebar_visible = False
        else:
            self.root.columnconfigure(0, weight=0, minsize=210)
            self.sidebar.grid(row=0, column=0, sticky='ns')
            self._sidebar_visible = True
        # Mettre à jour les boutons toggle
        label = "▶" if not self._sidebar_visible else "◀"
        if hasattr(self, '_workspace_toggle'):
            self._workspace_toggle.config(text=label)
        if hasattr(self.sidebar, '_toggle_btn'):
            self.sidebar._toggle_btn.config(text=label)

    # --- Fenêtre ---

    def _setup_window_geometry(self):
        """Restaure la géométrie de la fenêtre depuis la config."""
        gui = self.config.get_all().gui
        width = gui.window_width
        height = gui.window_height
        x = gui.window_x
        y = gui.window_y

        if x >= 0 and y >= 0:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.root.geometry(f"{width}x{height}")
            self.root.update_idletasks()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _save_window_geometry(self):
        """Sauvegarde la géométrie actuelle de la fenêtre (valeurs bornées)."""
        try:
            width = max(400, min(1920, self.root.winfo_width()))
            height = max(300, min(1080, self.root.winfo_height()))
            x = max(-1, self.root.winfo_x())
            y = max(-1, self.root.winfo_y())
            self.config.update_gui(
                window_width=width,
                window_height=height,
                window_x=x,
                window_y=y,
            )
        except Exception as exc:
            logger.debug("Erreur sauvegarde géométrie fenêtre : %s", exc)

    def _set_window_icon(self):
        """Définit l'icône de la fenêtre depuis un SVG."""
        try:
            from PIL import ImageTk

            from src.gui.svg_utils import svg_to_pil
            icon_path = Path(__file__).parent.parent.parent / "assets" / "logo.svg"
            if icon_path.exists():
                img = svg_to_pil(str(icon_path), size=32)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self.root._icon_photo = photo
        except Exception as exc:
            logger.debug("Erreur icône fenêtre : %s", exc)

    def _restore_session(self):
        """Restaure le dernier dossier sélectionné au démarrage."""
        try:
            last_folder = self.config.get('gui.last_folder', '')
            controller = getattr(self, 'extract_controller', None)
            if last_folder and os.path.isdir(last_folder) and controller:
                controller.select_recent_folder(last_folder)
        except Exception as exc:
            logger.debug("Erreur restauration session : %s", exc)

    # --- Navigation entre outils ---

    def show_tool(self, tool_id: str):
        """Affiche un outil dans le workspace."""
        self.workspace.show(tool_id)

    def on_tool_opened(self, tool_id: str):
        """Appelé par le workspace après ouverture d'un outil."""
        self._update_window_title(tool_id)
        self.sidebar.set_active(tool_id)

    def _update_window_title(self, tool_id: str | None = None):
        tool_id = tool_id or (self.workspace.current_id if hasattr(self, 'workspace') else None)
        tool = None
        if tool_id:
            from src.core.tool_registry import registry
            tool = registry.get(tool_id)
        if tool:
            self.root.title(f"TE — {_(tool.name)}")
        else:
            self.root.title("TE")

    # --- Autosave ---

    def _setup_autosave(self):
        """Sauvegarde périodique de la config (toutes les 60s)."""
        self._autosave_after_id = None

        def _autosave_tick():
            with contextlib.suppress(Exception):
                self.config.save()
            with contextlib.suppress(Exception):
                self._autosave_after_id = self.root.after(60000, _autosave_tick)

        self._autosave_after_id = self.root.after(60000, _autosave_tick)

    # --- i18n ---

    def _register_i18n_callbacks(self):
        def refresh_window_title():
            self._update_window_title()
        register_reload_callback(refresh_window_title)
        self._i18n_window_title_callback = refresh_window_title

    def _unregister_i18n_callbacks(self):
        if hasattr(self, '_i18n_window_title_callback'):
            unregister_reload_callback(self._i18n_window_title_callback)
            delattr(self, '_i18n_window_title_callback')
        if hasattr(self, '_settings_reload_callback'):
            unregister_reload_callback(self._settings_reload_callback)
            delattr(self, '_settings_reload_callback')

    # --- Fermeture ---

    def on_close(self):
        """Nettoyage à la fermeture (geometry, callbacks, raccourcis)."""
        self._save_window_geometry()
        if getattr(self, '_autosave_after_id', None):
            with contextlib.suppress(Exception):
                self.root.after_cancel(self._autosave_after_id)
            self._autosave_after_id = None

        self._unregister_i18n_callbacks()

        ui = getattr(self, 'extract_ui', None)
        if ui is not None:
            from src.gui.ui_builder.menus import unregister_menu_refresh
            from src.gui.ui_builder.widgets import unregister_refresh_callback
            unregister_menu_refresh(ui)
            unregister_refresh_callback(ui)

        if hasattr(self, 'sidebar'):
            self.sidebar.unregister()

        if getattr(self, 'shortcuts', None):
            self.shortcuts.unbind_all()
