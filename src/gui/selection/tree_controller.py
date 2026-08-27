# src/gui/selection/tree_controller.py

class TreeController:
    def __init__(self, tree, file_nodes, folder_nodes, folder_children):
        self.tree = tree
        self.file_nodes = file_nodes          # chemin_relatif -> iid
        self.folder_nodes = folder_nodes      # chemin_relatif -> iid
        self.folder_children = folder_children  # iid_parent -> [iid_enfant]
        self.file_iids = set(file_nodes.values())      # ensemble des iid de fichiers
        self.folder_iids = set(folder_nodes.values())  # ensemble des iid de dossiers
        self.items_state = {}  # iid -> bool (True = sélectionné)

    def toggle_item(self, item):
        """Bascule l'état d'un fichier ou dossier."""
        if item in self.file_iids:
            current = self.tree.set(item, "select")
            if current == "•":   # fichier non extractible (ignoré)
                return
            new_state = not self.items_state.get(item, False)
            self.set_item_state(item, new_state)
        elif item in self.folder_iids:
            total, selected = self._count_files_in_subtree(item)
            if total > 0:
                # Si tous les fichiers sont sélectionnés, on les désélectionne,
                # sinon on les sélectionne tous.
                new_state = (selected != total)
                self.set_folder_state(item, new_state)
        return self.items_state

    def set_item_state(self, item, state):
        """Change l'état d'un fichier."""
        if item not in self.file_iids:
            return
        self.items_state[item] = state
        self.tree.set(item, "select", "☑" if state else "☐")
        self._update_parent_state(item)

    def set_folder_state(self, folder_item, state):
        """Applique l'état à tous les fichiers extractibles du dossier (itératif).

        Les indicateurs sont rafraîchis une seule fois à la fin : appliquer
        l'état fichier par fichier avec mise à jour des ancêtres serait
        quadratique sur les grands arborescences.
        """
        stack = [folder_item]
        glyph = "☑" if state else "☐"
        while stack:
            current = stack.pop()
            if current in self.file_iids:
                # Ne pas toucher les fichiers non extractibles ('•')
                if self.tree.set(current, "select") == "•":
                    continue
                self.items_state[current] = state
                self.tree.set(current, "select", glyph)
            elif current in self.folder_iids:
                stack.extend(self.folder_children.get(current, []))
        self._update_folder_indicator(folder_item)
        self._update_parent_state(folder_item)

    def select_by_extension(self, ext):
        """Sélectionne tous les fichiers avec une extension donnée."""
        def _filter(iid):
            tags = self.tree.item(iid, "tags")
            return ext in tags
        self._bulk_apply(_filter, lambda iid: True)

    def select_all(self):
        """Sélectionne tous les fichiers extractibles."""
        self._bulk_apply(lambda iid: True, lambda iid: True)

    def deselect_all(self):
        """Désélectionne tous les fichiers."""
        self._bulk_apply(lambda iid: True, lambda iid: False)

    def invert_selection(self):
        """Inverse la sélection."""
        self._bulk_apply(lambda iid: True,
                         lambda iid: not self.items_state.get(iid, False))

    def get_selected_files(self):
        """Retourne la liste des chemins relatifs sélectionnés."""
        return [rel_str for rel_str, iid in self.file_nodes.items()
                if self.items_state.get(iid, False)]

    def count_selected(self):
        """Retourne le nombre de fichiers sélectionnés."""
        return sum(1 for state in self.items_state.values() if state)

    # --- Méthodes privées ---

    def _bulk_apply(self, include_fn, state_fn):
        """Applique state_fn aux fichiers acceptés par include_fn en un seul
        passage, puis rafraîchit chaque indicateur de dossier une seule fois.
        Complexité : O(fichiers + somme des sous-arbres une fois), au lieu de
        O(fichiers × profondeur × sous-arbre) avec la version par fichier.
        """
        for iid in self.file_nodes.values():
            if self.tree.set(iid, "select") == "•":
                continue
            if not include_fn(iid):
                continue
            state = state_fn(iid)
            self.items_state[iid] = state
            self.tree.set(iid, "select", "☑" if state else "☐")
        self._refresh_all_folder_indicators()

    def _refresh_all_folder_indicators(self):
        """Met à jour l'indicateur de tous les dossiers, du plus profond au
        plus haut (un seul passage)."""
        folders = list(self.folder_nodes.values())
        folders.sort(key=self._depth, reverse=True)
        for folder in folders:
            self._update_folder_indicator(folder)

    def _depth(self, iid):
        depth = 0
        parent = self.tree.parent(iid)
        while parent:
            depth += 1
            parent = self.tree.parent(parent)
        return depth

    def _count_files_in_subtree(self, iid):
        """
        Retourne (total_fichiers, fichiers_selectionnes) pour tout le sous‑arbre.
        Parcourt récursivement les dossiers enfants.
        """
        total = 0
        selected = 0
        stack = [iid]
        while stack:
            current = stack.pop()
            if current in self.file_iids:
                total += 1
                if self.items_state.get(current, False):
                    selected += 1
            elif current in self.folder_iids:
                for child in self.folder_children.get(current, []):
                    stack.append(child)
        return total, selected

    def _update_parent_state(self, item):
        parent = self.tree.parent(item)
        if parent:
            self._update_folder_indicator(parent)
            self._update_parent_state(parent)

    def _update_folder_indicator(self, folder_item):
        """
        Met à jour l'indicateur (☐/☑/◐) d'un dossier en fonction de l'état
        de tous les fichiers de son sous‑arbre.
        """
        total, selected = self._count_files_in_subtree(folder_item)
        if total == 0:
            return  # pas de fichiers extractibles, on ne change rien
        if selected == 0:
            indicator = "☐"
        elif selected == total:
            indicator = "☑"
        else:
            indicator = "◐"
        self.tree.set(folder_item, "select", indicator)
