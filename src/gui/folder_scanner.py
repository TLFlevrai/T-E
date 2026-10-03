# src/gui/folder_scanner.py
from __future__ import annotations
from src.extractor.file_discovery import FileDiscoveryService
from src.extractor.context import stat_key_for_ext
from src.config import ExtractionOptions

def scan_folder(folder, options: ExtractionOptions):
    """Scanne un dossier avec les options d'extraction données."""
    discovery = FileDiscoveryService(options)
    files = discovery.find_files(folder)

    types = {
        'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    }

    for full_path, rel_path, ext in files:
        ext_clean = stat_key_for_ext(ext)
        if not ext_clean:
            continue
        if ext_clean not in types:
            # Extension supplémentaire (extra_extensions) : compteur
            # déclaré à la volée pour rester aligné sur l'export.
            # `stat_key_for_ext` fusionne les synonymes, donc un dossier
            # avec .yml ET .yaml affiche « YAML : 2 », comme le rapport.
            types[ext_clean] = 0
        types[ext_clean] += 1

    return {
        'total': len(files),
        'types': types
    }