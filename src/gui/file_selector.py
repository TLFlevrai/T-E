# src/gui/file_selector.py
from __future__ import annotations
from src.gui.selection import SelectionDialog

def select_files(parent, folder_path, options):
    """
    Ouvre le dialogue de sélection. Retourne la liste des chemins relatifs
    choisis (éventuellement vide si validé sans sélection), ou None si
    l'utilisateur a annulé / fermé la fenêtre.
    """
    dialog = SelectionDialog(parent, folder_path, options)
    parent.wait_window(dialog.window)
    return dialog.get_selected()