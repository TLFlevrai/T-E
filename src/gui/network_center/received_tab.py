# src/gui/network_center/received_tab.py
from __future__ import annotations
import os
import shutil
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from src.i18n import _, pgettext
from src.logger import setup_logger
from ..errors import show_error, show_info, confirm

logger = setup_logger(__name__)

class ReceivedTab(ttk.Frame):
    def __init__(self, parent, dialog, output_dir):
        super().__init__(parent)
        self.dialog = dialog
        self.output_dir = output_dir
        self.received_dir = output_dir / "received" if output_dir else None
        self.selected_file = None

        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Liste
        columns = ('name', 'size', 'date')
        self.tree = ttk.Treeview(main, columns=columns, show='headings')
        self.tree.heading('name', text=_('Nom'))
        self.tree.heading('size', text=_('Taille'))
        self.tree.heading('date', text=_('Date'))
        self.tree.column('name', width=300)
        self.tree.column('size', width=100)
        self.tree.column('date', width=150)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scroll.set)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # Boutons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=5)

        # Contexte "button" pour distinguer des messages de confirmation
        ttk.Button(btn_frame, text=pgettext("button", "Ouvrir"), command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=pgettext("button", "Ouvrir le dossier"), command=self._open_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=pgettext("button", "Supprimer"), command=self._delete_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=_("Déplacer vers out/"), command=self._move_to_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=_("Rafraîchir"), command=self._refresh_list).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.status_var).pack(fill=tk.X, pady=5)

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.received_dir or not self.received_dir.exists():
            self.status_var.set(_("Dossier received/ introuvable"))
            return

        try:
            files = sorted(self.received_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in files:
                if f.is_file():
                    size = f.stat().st_size
                    size_str = self._human_size(size)
                    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    self.tree.insert('', 'end', values=(f.name, size_str, mtime), tags=(str(f),))
            self.status_var.set(_("{} fichier(s)").format(len(files)))
        except Exception as e:
            logger.error(f"Erreur lecture received : {e}")
            self.status_var.set(_("Erreur de lecture"))

    def _human_size(self, size):
        for unit in ['o', 'Ko', 'Mo']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} Go"

    def _on_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.selected_file = Path(self.tree.item(selection[0], 'tags')[0])
        else:
            self.selected_file = None

    def _open_file(self):
        if self.selected_file and self.selected_file.exists():
            try:
                os.startfile(str(self.selected_file))
            except Exception as e:
                show_error(_("Erreur"), _("Impossible d'ouvrir : {}").format(e), parent=self)
        else:
            show_info(_("Information"), _("Aucun fichier sélectionné"), parent=self)

    def _open_folder(self):
        if self.received_dir and self.received_dir.exists():
            try:
                os.startfile(str(self.received_dir))
            except Exception as e:
                show_error(_("Erreur"), _("Impossible d'ouvrir le dossier : {}").format(e), parent=self)

    def _delete_file(self):
        if not self.selected_file or not self.selected_file.exists():
            show_info(_("Information"), _("Aucun fichier sélectionné"), parent=self)
            return
        if confirm(_("Confirmation"), pgettext("confirmation", "Supprimer définitivement {} ?").format(self.selected_file.name), parent=self):
            try:
                self.selected_file.unlink()
                self._refresh_list()
                self.status_var.set(_("Fichier supprimé"))
            except Exception as e:
                show_error(_("Erreur"), _("Suppression échouée : {}").format(e), parent=self)

    def _move_to_out(self):
        if not self.selected_file or not self.selected_file.exists():
            show_info(_("Information"), _("Aucun fichier sélectionné"), parent=self)
            return
        dest = self.output_dir / self.selected_file.name
        if dest.exists():
            # Ajouter un suffixe
            base = dest.stem
            ext = dest.suffix
            counter = 1
            while dest.exists():
                dest = self.output_dir / f"{base}_{counter}{ext}"
                counter += 1
        try:
            shutil.move(str(self.selected_file), str(dest))
            self._refresh_list()
            self.status_var.set(_("Fichier déplacé vers out/"))
        except Exception as e:
            show_error(_("Erreur"), _("Déplacement échoué : {}").format(e), parent=self)

    def on_file_received(self, data):
        # Nouveau fichier reçu → rafraîchir la liste
        self._refresh_list()
        self.status_var.set(_("Nouveau fichier reçu : {}").format(data.get('filename', '')))