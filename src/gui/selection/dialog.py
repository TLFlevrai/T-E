# src/gui/selection/dialog.py
import tkinter as tk
from tkinter import ttk
from src.i18n import _
from .utils import get_allowed_extensions
from .tree_builder import TreeBuilder
from .tree_controller import TreeController
from .search import SearchBar
from .toolbar import SelectionToolbar

class SelectionDialog:
    def __init__(self, parent, root_path, options):
        self.parent = parent
        self.root_path = root_path
        self.options = options
        self.allowed_extensions = get_allowed_extensions(options)

        # Fenêtre principale
        self.window = tk.Toplevel(parent)
        self.window.title(_("Sélectionner les fichiers à extraire"))
        self.window.geometry("850x600")
        self.window.minsize(700, 400)
        self.window.transient(parent)
        self.window.grab_set()

        self._create_widgets()
        self._build_tree()
        self._update_selected_count()

        # Raccourcis clavier
        self.window.bind('<Control-a>', lambda e: self.controller.select_all())
        self.window.bind('<Control-d>', lambda e: self.controller.deselect_all())
        self.window.bind('<space>', self._on_space)

    def _create_widgets(self):
        main = ttk.Frame(self.window, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Barre de recherche (sans tree pour l'instant)
        self.search = SearchBar(main, None, [])

        # Treeview avec 3 colonnes
        columns = ("select", "name", "size")
        self.tree = ttk.Treeview(main, columns=columns, show="tree headings")
        self.tree.heading("select", text=_("Sélection"))
        self.tree.heading("name", text=_("Nom"))
        self.tree.heading("size", text=_("Taille"))
        self.tree.column("select", width=80, anchor="center")
        self.tree.column("name", anchor="w", width=300)
        self.tree.column("size", width=100, anchor="e")

        v_scroll = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(main, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind des événements
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # Frame pour la toolbar (sera rempli après construction de l'arbre)
        self.toolbar_frame = ttk.Frame(main)
        self.toolbar_frame.pack(fill=tk.X, pady=5)

        # Compteur
        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        self.selected_count_var = tk.StringVar(value="0 fichier sélectionné")
        ttk.Label(status_frame, textvariable=self.selected_count_var).pack(side=tk.LEFT)
        ttk.Label(status_frame, text=_("(fichiers extractibles)")).pack(side=tk.LEFT, padx=(5, 0))

        # Boutons Valider / Annuler
        action_frame = ttk.Frame(main)
        action_frame.pack(fill=tk.X, pady=10)
        ttk.Button(action_frame, text=_("Valider"), 
                   command=self._validate).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text=_("Annuler"), 
                   command=self.window.destroy).pack(side=tk.RIGHT, padx=5)

        # Stocker les références (utile pour la toolbar)
        self.main = main

    def _build_tree(self):
        """Construit l'arborescence via TreeBuilder."""
        builder = TreeBuilder(self.tree, self.root_path, self.options)
        data = builder.build()

        # Créer le contrôleur APRÈS avoir les données
        self.controller = TreeController(
            self.tree,
            data['file_nodes'],
            data['folder_nodes'],
            data['folder_children']
        )

        # Mettre à jour la recherche avec les items
        self.search.tree = self.tree
        self.search.all_items = data['all_items']

        # Créer la barre d'outils dans le frame dédié
        self.toolbar = SelectionToolbar(self.toolbar_frame, self.controller, self.allowed_extensions)

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col == "#1":
                self.controller.toggle_item(item)
                self._update_selected_count()
                return
        if item in self.controller.file_nodes or item in self.controller.folder_nodes:
            self.controller.toggle_item(item)
            self._update_selected_count()

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item and item in self.controller.folder_nodes:
            current = self.tree.item(item, "open")
            self.tree.item(item, open=not current)

    def _on_space(self, event):
        item = self.tree.focus()
        if item:
            self.controller.toggle_item(item)
            self._update_selected_count()
        return "break"

    def _update_selected_count(self):
        total = len(self.controller.file_nodes)
        selected = self.controller.count_selected()
        self.selected_count_var.set(f"{selected} / {total} fichier(s) sélectionné(s)")

    def _validate(self):
        self.selected_files = self.controller.get_selected_files()
        self.window.destroy()

    def get_selected(self):
        """Retourne la liste sélectionnée, ou None si annulé (bouton Annuler
        ou fermeture de la fenêtre) : permet au contrôleur de distinguer
        « validation sans fichier » d'une véritable annulation."""
        return self.selected_files if hasattr(self, 'selected_files') else None