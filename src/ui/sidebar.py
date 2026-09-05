# src/ui/sidebar.py
"""Barre latérale de TE : identité, recherche et navigation entre outils.

Design : surface distincte du workspace, en-tête applicatif, recherche
filtrante, catégories muettes et item actif marqué par une pastille
d'accent à gauche du libellé.
"""
from __future__ import annotations

import contextlib
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any

from src.core.tool_registry import registry
from src.gui.theme import get_color, get_font
from src.i18n import _, register_reload_callback, unregister_reload_callback
from src.logger import setup_logger
from src.ui.tooltips import ToolTipContent, add_lazy_rich_tooltip

logger = setup_logger(__name__)

# Délai (ms) avant reconstruction de la liste après une frappe : la sidebar
# détruit/recrée tous ses boutons + tooltips ; le faire à chaque caractère
# est inutilement coûteux.
_SEARCH_DEBOUNCE_MS = 150

_INDICATOR_WIDTH = 3


class Sidebar(ttk.Frame):
    """Liste des outils avec recherche, groupés par catégorie."""

    def __init__(self, shell: Any):
        self.shell = shell
        super().__init__(shell.root, style='Sidebar.TFrame', width=230,
                         padding=(0, 0))
        self.pack_propagate(False)

        self._buttons: dict[str, ttk.Button] = {}
        self._indicators: dict[str, ttk.Frame] = {}
        self._tooltips: list[Any] = []
        self._search_var = tk.StringVar()
        self._search_var.trace_add('write', self._on_search)
        self._search_entry: ttk.Entry | None = None
        self._body: ttk.Frame | None = None
        self._debounce_after_id: str | None = None
        self._placeholder_active = False

        self._build()
        self._reload_callback = self._rebuild
        register_reload_callback(self._reload_callback)

    # --- Construction ---

    def _build(self):
        # En-tête applicatif
        header = ttk.Frame(self, style='Sidebar.TFrame', padding=(14, 14, 14, 10))
        header.pack(fill=tk.X)

        title_row = ttk.Frame(header, style='Sidebar.TFrame')
        title_row.pack(fill=tk.X)

        title = ttk.Label(title_row, text="TE", style='SidebarTitle.TLabel')
        title.pack(side=tk.LEFT)

        # Bouton toggle sidebar dans l'en-tête
        self._toggle_btn = tk.Button(
            title_row,
            text="◀",
            font=('Segoe UI', 10),
            bg=get_color('surface'),
            fg=get_color('fg'),
            activebackground=get_color('surface_alt'),
            activeforeground=get_color('fg'),
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._on_toggle_click,
            relief='flat',
        )
        self._toggle_btn.pack(side=tk.RIGHT)

        subtitle = ttk.Label(header, text=_("Toolkit multi-outils"),
                             style='SidebarSubtitle.TLabel')
        subtitle.pack(anchor=tk.W)

        # Recherche
        search_frame = ttk.Frame(self, style='Sidebar.TFrame', padding=(12, 0, 12, 10))
        search_frame.pack(fill=tk.X)
        self._search_entry = ttk.Entry(search_frame, textvariable=self._search_var,
                                       style='SidebarSearch.TEntry',
                                       font=get_font('small'))
        self._search_entry.pack(fill=tk.X)
        self._bind_placeholder()

        # Corps défilant : canvas + scrollbar pour la liste d'outils
        canvas_frame = ttk.Frame(self, style='Sidebar.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(canvas_frame, bg=get_color('surface'),
                                  bd=0, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                         command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = ttk.Frame(self._canvas, style='Sidebar.TFrame', padding=(8, 0, 8, 10))
        self._canvas_window = self._canvas.create_window((0, 0), window=body, anchor="nw")
        self._body = body

        self._canvas.bind("<Configure>", self._on_canvas_resize)
        body.bind("<Configure>", self._on_body_resize)

        self._bind_mousewheel(self._canvas)
        self._bind_mousewheel(body)

        self._populate(body)

    def _bind_placeholder(self):
        """Placeholder léger sur le champ de recherche."""
        entry = self._search_entry
        if entry is None:
            return
        self._placeholder = _("Rechercher un outil…")

        def show_placeholder():
            if not self._search_var.get():
                self._placeholder_active = True
                self._search_var.set(self._placeholder)
                entry.configure(foreground=get_color('fg_muted'))

        def clear_placeholder(_event=None):
            if self._placeholder_active:
                self._placeholder_active = False
                entry.configure(foreground=get_color('fg'))
                with contextlib.suppress(Exception):
                    self._search_var.set('')

        entry.bind('<FocusIn>', clear_placeholder)

        def on_focus_out(_event=None):
            if not self._search_var.get():
                show_placeholder()
            elif not self._placeholder_active:
                entry.configure(foreground=get_color('fg'))

        entry.bind('<FocusOut>', on_focus_out)
        show_placeholder()

    def _on_canvas_resize(self, event):
        """Ajuste la largeur du cadre interne à la largeur du canvas."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_body_resize(self, event):
        """Met à jour la scrollregion quand le contenu change de taille."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _bind_mousewheel(self, widget):
        """Attache le défilement à la molette de souris."""
        widget.bind("<Enter>", self._on_mouse_enter, add="+")
        widget.bind("<Leave>", self._on_mouse_leave, add="+")

    def _on_mouse_enter(self, _event):
        if sys.platform == "darwin":
            self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        elif sys.platform.startswith("win"):
            self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else:
            self._canvas.bind_all("<Button-4>", self._on_mousewheel)
            self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mouse_leave(self, _event):
        if sys.platform in ("darwin", "win32") or sys.platform.startswith("win"):
            self._canvas.unbind_all("<MouseWheel>")
        else:
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if sys.platform == "darwin":
            self._canvas.yview_scroll(-1 * event.delta, "units")
        elif sys.platform.startswith("win"):
            self._canvas.yview_scroll(-1 * (event.delta // 120), "units")
        else:
            if event.num == 4:
                self._canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._canvas.yview_scroll(1, "units")

    def _populate(self, parent: ttk.Frame):
        query = '' if self._placeholder_active else self._search_var.get().strip().lower()
        try:
            tools = registry.search(query) if query else None
            grouped = registry.by_category() if tools is None else [("", tools)]
        except Exception as exc:
            logger.error("Erreur chargement outils : %s", exc)
            grouped = []

        for category, tool_list in grouped:
            if category:
                label = ttk.Label(parent, text=_(category).upper(),
                                  style='SidebarCategory.TLabel')
                label.pack(anchor=tk.W, padx=8, pady=(12, 4))
            for tool in tool_list:
                self._make_tool_row(parent, tool)

    def _make_tool_row(self, parent: ttk.Frame, tool):
        """Ligne outil : pastille d'accent + bouton plat."""
        row = ttk.Frame(parent, style='Sidebar.TFrame')
        row.pack(fill=tk.X, pady=1)

        indicator = ttk.Frame(row, style='Chip.TFrame', width=_INDICATOR_WIDTH, height=22)
        indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2))
        indicator.pack_propagate(False)
        indicator.pack_forget()  # visible uniquement pour l'outil actif

        button = ttk.Button(
            row,
            text=f"{tool.icon}  {_(tool.name)}",
            style='Sidebar.TButton',
            command=lambda tid=tool.id: self.shell.show_tool(tid),
        )
        button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._buttons[tool.id] = button
        self._indicators[tool.id] = indicator

        tooltip = add_lazy_rich_tooltip(button, ToolTipContent(
            title=tool.name,
            description=tool.description,
            shortcut=tool.shortcut,
            category=tool.category,
        ))
        self._tooltips.append(tooltip)

    # --- Recherche ---

    def _on_search(self, *_):
        # Le placeholder modifie la variable programmatiquement : ignorer.
        if self._placeholder_active:
            return
        if self._debounce_after_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._debounce_after_id)
        self._debounce_after_id = self.after(_SEARCH_DEBOUNCE_MS, self._apply_search)

    def _apply_search(self):
        self._debounce_after_id = None
        if self._body is None or not self.winfo_exists():
            return
        for child in self._body.winfo_children():
            child.destroy()
        self._buttons.clear()
        self._indicators.clear()
        self._tooltips.clear()
        self._populate(self._body)
        current = getattr(self.shell.workspace, 'current_id', None)
        self._apply_active(current if current in self._buttons else None)

    # --- État actif ---

    def set_active(self, tool_id: str | None):
        """Met en évidence l'outil actuellement affiché."""
        self._apply_active(tool_id)

    def _apply_active(self, tool_id: str | None):
        active_style = 'SidebarActive.TButton'
        normal_style = 'Sidebar.TButton'
        for tid, button in list(self._buttons.items()):
            is_active = (tid == tool_id)
            button.configure(style=active_style if is_active else normal_style)
            indicator = self._indicators.get(tid)
            if indicator is not None:
                if is_active:
                    indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2))
                else:
                    indicator.pack_forget()

    # --- i18n ---

    def _rebuild(self):
        """Reconstruit la sidebar avec la langue courante."""
        current = None
        try:
            current = self.shell.workspace.current_id if hasattr(self.shell, 'workspace') else None
        except Exception:
            logger.debug("Exception reading current workspace ID during rebuild", exc_info=True)

        try:
            for child in self.winfo_children():
                child.destroy()
            self._buttons.clear()
            self._indicators.clear()
            self._tooltips.clear()
            self._body = None
            self._canvas = None
            self._scrollbar = None
            self._placeholder_active = False
            self._build()
            self._apply_active(current)
            # Mettre à jour le bouton toggle après rebuild
            self._update_toggle_button()
        except Exception as exc:
            logger.error("Erreur reconstruction sidebar : %s", exc)
            try:
                if not self._buttons:
                    self._build()
                    self._update_toggle_button()
            except Exception:
                logger.debug("Exception rebuilding sidebar body", exc_info=True)

    def _update_toggle_button(self):
        """Met à jour le texte du bouton toggle selon l'état."""
        if hasattr(self, '_toggle_btn') and hasattr(self.shell, '_sidebar_visible'):
            self._toggle_btn.config(text="▶" if not self.shell._sidebar_visible else "◀")

    def unregister(self):
        """Désenregistre les callbacks i18n."""
        if hasattr(self, '_reload_callback'):
            unregister_reload_callback(self._reload_callback)

    def _on_toggle_click(self):
        """Callback du bouton toggle sidebar."""
        if hasattr(self.shell, 'toggle_sidebar'):
            self.shell.toggle_sidebar()
