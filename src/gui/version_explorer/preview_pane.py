# src/gui/version_explorer/preview_pane.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Optional
from src.i18n import _
from src.services.version_service import VersionEntry

# L'aperçu n'affiche que l'en-tête + le bloc STATISTIQUES (≈ 50 lignes) :
# lire tout le fichier (parfois plusieurs Mo) sur le thread UI à chaque
# sélection est inutile. 64 Ko couvrent largement ces sections.
PREVIEW_READ_BYTES = 64 * 1024


class PreviewPane:
    """Panneau d'aperçu (en-tête + statistiques)."""

    def __init__(self, parent):
        frame = ttk.LabelFrame(parent, text=_("Aperçu"), padding=5)
        frame.pack(fill=tk.BOTH, expand=True, padx=(5, 0))

        self.text = tk.Text(frame, wrap=tk.WORD, height=10, width=40)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=scroll.set)
        self.text.config(state=tk.DISABLED)

    def show_entry(self, entry: Optional[VersionEntry]):
        """Affiche l'aperçu de l'entrée."""
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        if not entry:
            self.text.insert(tk.END, _("Aucune version sélectionnée"))
            self.text.config(state=tk.DISABLED)
            return

        # Lire seulement le début du fichier : l'en-tête et les statistiques
        # se trouvent dans les premiers kilo-octets.
        try:
            with open(entry.path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(PREVIEW_READ_BYTES)
        except Exception as e:
            self.text.insert(tk.END, f"Erreur de lecture : {e}")
            self.text.config(state=tk.DISABLED)
            return

        # Extraire l'en-tête (jusqu'à la première ligne "--- FIN DE LA STRUCTURE ---" ou "--- FIN DES FICHIERS ---")
        lines = content.splitlines()
        preview_lines = []
        in_stats = False
        for line in lines:
            if line.startswith('--- FIN DE LA STRUCTURE ---') or line.startswith('--- FIN DES FICHIERS ---'):
                # On s'arrête après avoir ajouté les lignes précédentes
                break
            if line.startswith('STATISTIQUES'):
                in_stats = True
            preview_lines.append(line)
            # On garde aussi quelques lignes après les stats
            if in_stats and line.startswith('Volume total extrait'):
                # On peut ajouter encore quelques lignes mais on s'arrête là
                break

        preview = '\n'.join(preview_lines[:50])  # limiter à 50 lignes
        if len(preview_lines) > 50:
            preview += '\n... (tronqué)'
        self.text.insert(tk.END, preview)
        self.text.config(state=tk.DISABLED)