# src/gui/selection/toolbar.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from src.i18n import _

class SelectionToolbar:
    def __init__(self, parent, controller, allowed_extensions):
        self.controller = controller
        self.allowed_extensions = allowed_extensions

        self.toolbar = ttk.Frame(parent)
        self.toolbar.pack(fill=tk.X, pady=5)

        # Boutons par extension avec icônes
        ext_buttons = [
            ('.py', "🐍", _("Tous les .py")),
            ('.json', "📄", _("Tous les .json")),
            ('.txt', "📝", _("Tous les .txt")),
            ('.po', "🌐", _("Tous les .po")),
            ('.mo', "📦", _("Tous les .mo")),
            ('.html', "🌍", _("Tous les .html")),
            ('.htm', "🌍", _("Tous les .htm")),
            ('.css', "🎨", _("Tous les .css")),
            ('.js', "⚡", _("Tous les .js"))
        ]

        # Stocker les boutons pour pouvoir les mettre à jour plus tard
        self.buttons = []

        for ext, icon, label in ext_buttons:
            if ext in allowed_extensions:
                btn = ttk.Button(self.toolbar, text=f"{icon} {label}")
                btn.pack(side=tk.LEFT, padx=2)
                self.buttons.append((btn, ext))

        # Boutons génériques
        self.select_all_btn = ttk.Button(self.toolbar, text=_("☑ Tout"))
        self.select_all_btn.pack(side=tk.LEFT, padx=2)

        self.deselect_all_btn = ttk.Button(self.toolbar, text=_("☐ Rien"))
        self.deselect_all_btn.pack(side=tk.LEFT, padx=2)

        self.invert_btn = ttk.Button(self.toolbar, text=_("⇄ Inverser"))
        self.invert_btn.pack(side=tk.LEFT, padx=2)

        # Si le contrôleur est déjà défini, configurer les commandes
        if controller:
            self.set_controller(controller)

    def set_controller(self, controller):
        """Définit le contrôleur et configure les commandes des boutons."""
        self.controller = controller

        # Configurer les boutons d'extension
        for btn, ext in self.buttons:
            btn.config(command=lambda e=ext: controller.select_by_extension(e))

        # Configurer les boutons génériques
        self.select_all_btn.config(command=controller.select_all)
        self.deselect_all_btn.config(command=controller.deselect_all)
        self.invert_btn.config(command=controller.invert_selection)