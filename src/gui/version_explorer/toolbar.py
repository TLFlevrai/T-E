# src/gui/version_explorer/toolbar.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from src.i18n import _, pgettext
from src.ui.tooltips import add_lazy_tooltip


class Toolbar:
    """Barre d'outils avec les actions principales (défilement horizontal si nécessaire)."""

    def __init__(self, parent, controller):
        self.controller = controller

        # Conteneur principal avec scrollbar horizontal
        outer_frame = ttk.Frame(parent)
        outer_frame.pack(fill=tk.X, pady=5)

        canvas = tk.Canvas(outer_frame, height=40, highlightthickness=0)
        h_scroll = ttk.Scrollbar(outer_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        canvas.configure(xscrollcommand=h_scroll.set)

        canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame interne pour les boutons
        self.btn_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.btn_frame, anchor=tk.NW)

        # Mettre à jour la scrollregion quand la taille change
        self.btn_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Contexte "button" pour distinguer des messages de confirmation
        self.archive_btn = ttk.Button(self.btn_frame, text=pgettext("button", "Archiver"), command=self.controller.archive_selected)
        self.archive_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.archive_btn, "Archiver les versions sélectionnées (les déplace dans l'archive)")

        self.restore_btn = ttk.Button(self.btn_frame, text=pgettext("button", "Restaurer"), command=self.controller.restore_selected)
        self.restore_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.restore_btn, "Restaurer les versions archivées sélectionnées")

        self.delete_btn = ttk.Button(self.btn_frame, text=pgettext("button", "Supprimer"), command=self.controller.delete_selected)
        self.delete_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.delete_btn, "Supprimer définitivement les versions sélectionnées (irréversible)")

        self.open_folder_btn = ttk.Button(self.btn_frame, text=pgettext("button", "Ouvrir dossier"), command=self.controller.open_folder)
        self.open_folder_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.open_folder_btn, "Ouvrir le dossier de sortie dans l'explorateur de fichiers")

        self.refresh_btn = ttk.Button(self.btn_frame, text=_("Rafraîchir"), command=self.controller.refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.refresh_btn, "Recharger la liste des projets et versions")

        self.reset_btn = ttk.Button(self.btn_frame, text=_("Réinitialiser compteur"), command=self.controller.reset_counter)
        self.reset_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.reset_btn, "Remettre à zéro le compteur de versions du projet actuel")

        # Boutons de sélection
        self.select_all_btn = ttk.Button(self.btn_frame, text=_("Tout sélectionner"), command=self.controller.select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.select_all_btn, "Sélectionner toutes les versions de la liste")

        self.deselect_all_btn = ttk.Button(self.btn_frame, text=_("Tout désélectionner"), command=self.controller.deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.deselect_all_btn, "Désélectionner toutes les versions de la liste")

        # Bouton Nettoyer tout (avec séparateur visuel)
        sep = ttk.Separator(self.btn_frame, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)

        self.clean_all_btn = ttk.Button(self.btn_frame, text=_("Nettoyer tout"), command=self.controller.clean_all)
        self.clean_all_btn.pack(side=tk.LEFT, padx=4, pady=4)
        add_lazy_tooltip(self.clean_all_btn, "Supprimer TOUS les exports dans out/ (y compris archives) - IRREVERSIBLE")