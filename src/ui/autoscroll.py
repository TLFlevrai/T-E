# src/ui/autoscroll.py
"""Module de détection et gestion automatique des barres de défilement.

Ce module fournit un conteneur Tkinter (AutoScrollFrame) qui surveille
automatiquement les dimensions de ses composants enfants. Si les composants
dépassent la largeur ou la hauteur de la zone d'affichage, des barres de
défilement (verticale et/ou horizontale) sont ajoutées dynamiquement.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from src.gui.theme import get_color
from src.logger import setup_logger

logger = setup_logger(__name__)


class AutoScrollFrame(ttk.Frame):
    """Conteneur avec barres de défilement automatiques en cas de dépassement."""

    def __init__(
        self,
        parent: tk.Widget,
        fit_width: bool = True,
        fit_height: bool = False,
        auto_hide: bool = True,
        **kwargs: Any,
    ):
        """
        Args:
            parent: Widget parent.
            fit_width: Étirer le cadre intérieur en largeur si le canvas est plus large.
            fit_height: Étirer le cadre intérieur en hauteur si le canvas est plus haut.
            auto_hide: Masquer les barres de défilement quand le contenu tient dans la fenêtre.
        """
        super().__init__(parent, **kwargs)
        self.fit_width = fit_width
        self.fit_height = fit_height
        self.auto_hide = auto_hide

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Canvas principal
        bg_color = get_color('bg')
        self.canvas = tk.Canvas(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )

        # Barres de défilement (verticale et horizontale)
        self.v_scrollbar = ttk.Scrollbar(
            self, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.h_scrollbar = ttk.Scrollbar(
            self, orient=tk.HORIZONTAL, command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
        )

        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Conteneur intérieur pour les composants
        self.content = ttk.Frame(self.canvas)
        self._window_id = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )

        # Initalement masquer les scrollbars si auto_hide est activé
        if not self.auto_hide:
            self.v_scrollbar.grid(row=0, column=1, sticky="ns")
            self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Événements de dimensionnement
        self.content.bind("<Configure>", self._on_content_configure, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

        # Configuration de la molette
        self._setup_mousewheel()

    def _on_content_configure(self, event=None):
        """Mise à jour de la zone de défilement et vérification du dépassement."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.check_overflow()

    def _on_canvas_configure(self, event=None):
        """Ajustement du contenu lors du redimensionnement du canvas."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if self.fit_width:
            req_w = self.content.winfo_reqwidth()
            if canvas_w > req_w:
                self.canvas.itemconfig(self._window_id, width=canvas_w)
            else:
                self.canvas.itemconfig(self._window_id, width=req_w)

        if self.fit_height:
            req_h = self.content.winfo_reqheight()
            if canvas_h > req_h:
                self.canvas.itemconfig(self._window_id, height=canvas_h)
            else:
                self.canvas.itemconfig(self._window_id, height=req_h)

        self.check_overflow()

    def check_overflow(self):
        """Détecte si les composants dépassent en hauteur ou en largeur."""
        if not self.auto_hide:
            return

        self.update_idletasks()
        req_w = self.content.winfo_reqwidth()
        req_h = self.content.winfo_reqheight()

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        # Dépassement vertical (composants trop longs en hauteur)
        overflow_y = req_h > canvas_h and canvas_h > 1
        if overflow_y:
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            if self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.grid_remove()

        # Dépassement horizontal (composants trop larges)
        overflow_x = req_w > canvas_w and canvas_w > 1
        if overflow_x:
            if not self.h_scrollbar.winfo_ismapped():
                self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        else:
            if self.h_scrollbar.winfo_ismapped():
                self.h_scrollbar.grid_remove()

    def _setup_mousewheel(self):
        """Configure le défilement par molette de souris."""
        self.bind_mousewheel_recursive(self.canvas)
        self.bind_mousewheel_recursive(self.content)

    def bind_mousewheel_recursive(self, widget: tk.Widget):
        """Attache les gestionnaires de molette à un widget et à tous ses enfants."""
        try:
            widget.bind("<Enter>", self._on_mouse_enter, add="+")
            widget.bind("<Leave>", self._on_mouse_leave, add="+")
            for child in widget.winfo_children():
                self.bind_mousewheel_recursive(child)
        except Exception:
            logger.debug("Exception binding mousewheel to widget", exc_info=True)

    def _on_mouse_enter(self, event):
        if sys.platform == "darwin":
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        elif sys.platform.startswith("win"):
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        else:
            self.canvas.bind_all("<Button-4>", self._on_mousewheel)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mouse_leave(self, event):
        if sys.platform in ("darwin", "win32") or sys.platform.startswith("win"):
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Shift-MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if self.v_scrollbar.winfo_ismapped():
            if sys.platform == "darwin":
                self.canvas.yview_scroll(-1 * event.delta, "units")
            elif sys.platform.startswith("win"):
                self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
            else:
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")

    def _on_shift_mousewheel(self, event):
        if self.h_scrollbar.winfo_ismapped():
            if sys.platform.startswith("win"):
                self.canvas.xview_scroll(-1 * (event.delta // 120), "units")


def make_scrollable(
    parent: tk.Widget,
    builder_fn: Callable[[ttk.Frame], None],
    fit_width: bool = True,
    fit_height: bool = False,
) -> AutoScrollFrame:
    """Fonction utilitaire pour rendre un ensemble de composants défilant."""
    scroll_frame = AutoScrollFrame(
        parent, fit_width=fit_width, fit_height=fit_height
    )
    builder_fn(scroll_frame.content)
    scroll_frame.bind_mousewheel_recursive(scroll_frame.content)
    return scroll_frame
