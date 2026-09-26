# src/gui/folder_scanner.py
from __future__ import annotations
from src.extractor.file_discovery import FileDiscoveryService
from src.config import ExtractionOptions

def scan_folder(folder, options: ExtractionOptions):
    """Scanne un dossier avec les options d'extraction données."""
    discovery = FileDiscoveryService(options)
    files = discovery.find_files(folder)

    types = {
        'py': 0, 'json': 0, 'txt': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    }

    for full_path, rel_path, ext in files:
        ext_clean = ext.lstrip('.')
        if ext_clean == 'htm':
            ext_clean = 'html'
        if ext_clean in types:
            types[ext_clean] += 1

    return {
        'total': len(files),
        'types': types
    }