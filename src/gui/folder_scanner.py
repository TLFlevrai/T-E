# src/gui/folder_scanner.py
from __future__ import annotations
from src.extractor.file_discovery import FileDiscoveryService
from src.config import ExtractionOptions

def scan_folder(folder, ui):
    options = ExtractionOptions(
        include_json=ui.include_json.get(),
        include_subdirs=ui.include_subdirs.get(),
        include_txt=ui.include_txt.get(),
        include_po=ui.include_po.get(),
        include_mo=ui.include_mo.get(),
        include_html=ui.include_html.get(),
        include_css=ui.include_css.get(),
        include_js=ui.include_js.get(),
        ignore_init=ui.ignore_init.get(),
        ignore_git=ui.ignore_git.get(),
        ignore_pycache=ui.ignore_pycache.get()
    )

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