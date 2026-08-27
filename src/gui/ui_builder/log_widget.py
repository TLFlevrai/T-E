# src/gui/ui_builder/log_widget.py
"""Widget de journal avec recherche, surbrillance et auto-scroll."""
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Optional

from src.config import get_config
from src.i18n import _, LazyString, register_reload_callback, unregister_reload_callback

from .tooltip import add_lazy_tooltip
from .ui_widgets import register_lazy_labelframe, register_lazy_widget

if TYPE_CHECKING:
    from .ui_widgets import UIWidgets


class LogWidget:
    """Widget de journal encapsulant Text, scrollbar, recherche et barre de statut."""

    # Garde-fou : sans limite, une extraction de plusieurs milliers de fichiers
    # ralentit progressivement le widget Text (rendu + mémoire).
    MAX_LINES = 2000

    def __init__(
        self,
        parent: ttk.Frame,
        ui: 'UIWidgets',
        status_var: tk.StringVar,
        log_visible_var: tk.BooleanVar,
        on_visibility_toggle: Optional[Callable[[bool], None]] = None,
    ):
        self.parent = parent
        self.ui = ui
        self.status_var = status_var
        self.log_visible_var = log_visible_var
        self.on_visibility_toggle = on_visibility_toggle
        self._line_count = 0

        self._create_widgets()
        self._setup_bindings()
        self._register_i18n()

    def _create_widgets(self):
        # LabelFrame conteneur
        self.info_frame = ttk.LabelFrame(self.parent, text=str(LazyString("Journal")), padding="8")
        self.info_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.ui.info_frame = self.info_frame
        # Note: lazy labelframe registration done by caller

        # Barre de recherche compacte
        search_frame = ttk.Frame(self.info_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        search_frame.columnconfigure(0, weight=1)

        self.ui.log_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.ui.log_search_var)
        search_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))
        search_entry.bind("<KeyRelease>", lambda e: self._on_log_search())
        search_entry.bind("<Return>", lambda e: self._on_log_search_next())

        self.ui.log_search_next_btn = ttk.Button(search_frame, text=_("Suivant"), command=self._on_log_search_next, width=7)
        self.ui.log_search_next_btn.grid(row=0, column=1, padx=2)

        self.ui.log_search_prev_btn = ttk.Button(search_frame, text=_("Précédent"), command=self._on_log_search_prev, width=8)
        self.ui.log_search_prev_btn.grid(row=0, column=2, padx=2)

        self.ui.clear_btn = ttk.Button(search_frame, text=str(LazyString("Effacer le journal")),
                                       style='AppLink.TButton', command=self.clear_info)
        self.ui.clear_btn.grid(row=0, column=3, padx=(8, 0))
        register_lazy_widget(self.ui, self.ui.clear_btn, "Effacer le journal")

        # Zone de texte
        log_height = get_config().get('gui.log_height', 12)
        self.info_text = tk.Text(self.info_frame, height=log_height, width=80, wrap=tk.WORD,
                                 font=('Consolas', 9))
        self.info_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.ui.info_text = self.info_text

        scrollbar = ttk.Scrollbar(self.info_frame, orient="vertical", command=self.info_text.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=lambda *args: self._on_scroll(scrollbar, *args))

        # Tag pour surbrillance
        self.info_text.tag_configure("search_highlight", background="yellow", foreground="black")
        
        # État recherche
        self.ui._log_search_matches = []
        self.ui._log_search_current = -1

        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.rowconfigure(1, weight=1)

        # Barre de statut plate (footer)
        status_frame = ttk.Frame(self.parent)
        status_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(8, 0))
        status_frame.columnconfigure(0, weight=1)

        status_bar = ttk.Label(status_frame, textvariable=self.status_var,
                               style='Status.TLabel', anchor=tk.W)
        status_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.ui.status_bar = status_bar

        self.ui.log_autoscroll_var = tk.BooleanVar(value=get_config().get('gui.log_autoscroll', True))
        autoscroll_cb = ttk.Checkbutton(
            status_frame,
            text=_("Auto-scroll"),
            variable=self.ui.log_autoscroll_var,
            command=self._save_autoscroll_pref
        )
        autoscroll_cb.grid(row=0, column=1, sticky=tk.E, padx=5)

    def _setup_bindings(self):
        """Configure les bindings de visibilité."""
        def toggle_log_visibility():
            if self.log_visible_var.get():
                self.info_frame.grid()
            else:
                self.info_frame.grid_remove()
            if self.on_visibility_toggle:
                self.on_visibility_toggle(self.log_visible_var.get())

        view_menu = self.ui.view_menu
        if view_menu:
            view_menu.entryconfig(0, command=toggle_log_visibility)

    def _register_i18n(self):
        """Enregistre les widgets pour traduction."""
        register_lazy_labelframe(self.ui, self.info_frame, "Journal")
        register_lazy_widget(self.ui, self.ui.log_search_next_btn, "Suivant")
        register_lazy_widget(self.ui, self.ui.log_search_prev_btn, "Précédent")

    def _on_scroll(self, scrollbar, *args):
        scrollbar.set(*args)

    def _save_autoscroll_pref(self):
        try:
            config = get_config()
            config.update_gui(log_autoscroll=self.ui.log_autoscroll_var.get())
        except Exception:
            pass

    # --- Méthodes publiques pour le contrôleur ---

    def add_info(self, message: str):
        """Ajoute un message au journal (avec limitation du nombre de lignes)."""
        self.info_text.insert(tk.END, message + "\n")
        self._line_count += message.count('\n') + 1
        if self._line_count > self.MAX_LINES:
            excess = self._line_count - self.MAX_LINES
            self.info_text.delete("1.0", f"{excess + 1}.0")
            self._line_count = self.MAX_LINES
            # Les indices des correspondances stockées pointent désormais
            # plus haut : on invalide (Suivant/Précédent relancera la recherche).
            if self.ui._log_search_matches:
                self.ui._log_search_matches.clear()
                self.ui._log_search_current = -1
                self.info_text.tag_remove("search_highlight", "1.0", tk.END)
        if self.ui.log_autoscroll_var.get():
            self.info_text.see(tk.END)

    def clear_info(self):
        """Efface le journal."""
        self.info_text.delete(1.0, tk.END)
        self._line_count = 0
        self._on_log_search_clear()

    def update_status(self, message: str, detail: Optional[str] = None):
        """Met à jour la barre de statut."""
        if detail:
            self.status_var.set(f"{message} | {detail}")
        else:
            self.status_var.set(message)

    def set_progress(self, value: float):
        """Met à jour la barre de progression (si disponible)."""
        if hasattr(self.ui, 'progress_var'):
            self.ui.progress_var.set(value)

    # --- Recherche ---

    def _on_log_search(self):
        """Recherche dans le journal et surligne les correspondances."""
        search_term = self.ui.log_search_var.get().strip()
        
        # Supprimer les surbrillances précédentes
        self.info_text.tag_remove("search_highlight", "1.0", tk.END)
        self.ui._log_search_matches = []
        self.ui._log_search_current = -1
        
        if not search_term:
            return
        
        # Rechercher toutes les occurrences
        start = "1.0"
        while True:
            pos = self.info_text.search(search_term, start, tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(search_term)}c"
            self.info_text.tag_add("search_highlight", pos, end)
            self.ui._log_search_matches.append(pos)
            start = end
        
        if self.ui._log_search_matches:
            self.ui._log_search_current = 0
            self._highlight_current_match()

    def _on_log_search_next(self):
        """Va à la correspondance suivante."""
        if not self.ui._log_search_matches:
            self._on_log_search()
            return
        
        self.ui._log_search_current = (self.ui._log_search_current + 1) % len(self.ui._log_search_matches)
        self._highlight_current_match()

    def _on_log_search_prev(self):
        """Va à la correspondance précédente."""
        if not self.ui._log_search_matches:
            self._on_log_search()
            return
        
        self.ui._log_search_current = (self.ui._log_search_current - 1) % len(self.ui._log_search_matches)
        self._highlight_current_match()

    def _on_log_search_clear(self):
        """Efface la recherche et les surbrillances."""
        self.ui.log_search_var.set("")
        self.info_text.tag_remove("search_highlight", "1.0", tk.END)
        self.ui._log_search_matches = []
        self.ui._log_search_current = -1

    def _highlight_current_match(self):
        """Surligne et fait défiler vers la correspondance courante."""
        if not self.ui._log_search_matches or self.ui._log_search_current < 0:
            return
        
        pos = self.ui._log_search_matches[self.ui._log_search_current]
        
        # Retirer la surbrillance de toutes, puis ajouter sur la courante
        self.info_text.tag_remove("search_highlight", "1.0", tk.END)
        search_term = self.ui.log_search_var.get().strip()
        end = f"{pos}+{len(search_term)}c"
        self.info_text.tag_add("search_highlight", pos, end)
        
        # S'assurer que la correspondance est visible
        self.info_text.see(pos)
        self.info_text.mark_set(tk.INSERT, pos)

    def get_text_widget(self) -> tk.Text:
        """Retourne le widget Text sous-jacent."""
        return self.info_text

    def get_frame(self) -> ttk.LabelFrame:
        """Retourne le LabelFrame conteneur."""
        return self.info_frame