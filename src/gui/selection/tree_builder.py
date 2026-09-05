# src/gui/selection/tree_builder.py
from __future__ import annotations
from pathlib import Path
from .utils import get_allowed_extensions, format_size

class TreeBuilder:
    def __init__(self, tree, root_path, options):
        self.tree = tree
        self.root_path = Path(root_path).resolve()
        self.options = options
        self.allowed_extensions = get_allowed_extensions(options)
        self.file_nodes = {}
        self.folder_nodes = {}
        self.folder_children = {}
        self.all_items = []

    def build(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.file_nodes.clear()
        self.folder_nodes.clear()
        self.folder_children.clear()
        self.all_items.clear()

        root_name = self.root_path.name
        root_iid = self.tree.insert("", "end", text=root_name, 
                                    values=("", root_name, ""), open=True)
        self.folder_nodes[str(self.root_path)] = root_iid
        self.folder_children[root_iid] = []
        self.all_items.append(root_iid)

        self._walk_directory(self.root_path, root_iid)

        for iid in self.folder_nodes.values():
            self.tree.item(iid, open=True)

        return {
            'file_nodes': self.file_nodes,
            'folder_nodes': self.folder_nodes,
            'folder_children': self.folder_children,
            'all_items': self.all_items
        }

    def _walk_directory(self, dir_path, parent_iid):
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return

        # NOUVEAU : Filtrer les dossiers ignorés selon les options
        ignored_names = set()
        if self.options.get('ignore_git', False):
            ignored_names.add('.git')
        if self.options.get('ignore_pycache', True):
            ignored_names.add('__pycache__')
        
        entries = [e for e in entries if not (e.is_dir() and e.name in ignored_names)]

        for path in entries:
            rel_path = path.relative_to(self.root_path)
            rel_str = str(rel_path).replace('\\', '/')

            if path.is_dir():
                iid = self.tree.insert(parent_iid, "end", text=path.name, 
                                       values=("", path.name, ""), open=False)
                self.folder_nodes[rel_str] = iid
                self.folder_children.setdefault(parent_iid, []).append(iid)
                self.folder_children[iid] = []
                self.all_items.append(iid)
                self._walk_directory(path, iid)
            else:
                ext = path.suffix.lower()
                is_extractable = ext in self.allowed_extensions
                select_char = "☐" if is_extractable else "•"
                size_str = format_size(path.stat().st_size) if path.exists() else "?"
                iid = self.tree.insert(parent_iid, "end", text=path.name,
                                       values=(select_char, path.name, size_str))
                self.file_nodes[rel_str] = iid
                self.folder_children.setdefault(parent_iid, []).append(iid)
                self.tree.item(iid, tags=(ext,))
                self.all_items.append(iid)