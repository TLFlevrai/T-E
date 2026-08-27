# src/extractor/structure_generator.py
from pathlib import Path
from typing import List, Tuple, Set
from src.utils import human_size
from src.config import ExtractionOptions
from src.extractor.file_discovery import FileDiscoveryService


def generate_project_structure(folder: str, options: ExtractionOptions) -> str:
    """
    Génère la structure du projet en s'appuyant sur FileDiscoveryService.
    Inclut TOUS les fichiers trouvés dans le dossier (code, images, vidéos,
    archives, ...) tout en respectant les règles de parcours (.git, __pycache__,
    include_subdirs) : la structure reflète fidèlement le projet réel.
    """
    folder_path = Path(folder)
    discovery = FileDiscoveryService(options)
    # all_files=True : vidéos et images incluses, sans filtre d'extension
    files, dirs = discovery.find_all_paths(folder, all_files=True)

    lines = []
    lines.append("STRUCTURE DU PROJET")
    lines.append("=" * 80)

    root_name = folder_path.name
    lines.append(f"📁 {root_name}/")

    # Icônes par extension
    icon_map = {
        # Code
        '.py': "🐍", '.json': "📄", '.txt': "📝", '.po': "🌐",
        '.mo': "📦", '.html': "🌍", '.htm': "🌍", '.css': "🎨", '.js': "⚡",
        # Images
        '.png': "🖼️", '.jpg': "🖼️", '.jpeg': "🖼️", '.gif': "🖼️",
        '.bmp': "🖼️", '.webp': "🖼️", '.tiff': "🖼️", '.ico': "🖼️",
        '.svg': "🎨",
        # Vidéos
        '.mp4': "🎬", '.avi': "🎬", '.mkv': "🎬", '.mov': "🎬",
        '.webm': "🎬", '.wmv': "🎬", '.flv': "🎬", '.m4v': "🎬",
        '.mpg': "🎬", '.mpeg': "🎬",
        # Audio
        '.mp3': "🎵", '.wav': "🎵", '.ogg': "🎵", '.flac': "🎵",
        '.m4a': "🎵", '.aac': "🎵",
        # Documents
        '.pdf': "📕", '.doc': "📘", '.docx': "📘", '.xls': "📗",
        '.xlsx': "📗", '.ppt': "📙", '.pptx': "📙",
        # Archives
        '.zip': "🗜️", '.rar': "🗜️", '.7z': "🗜️", '.tar': "🗜️",
        '.gz': "🗜️", '.bz2': "🗜️",
    }

    # Construire l'arbre complet (dossiers + fichiers) trié
    # Structure: {parent_path: {dirs: [names], files: [(name, ext, size)]}}
    from collections import defaultdict
    tree = defaultdict(lambda: {'dirs': [], 'files': []})

    # Ajouter les dossiers
    for d in sorted(dirs):
        parent = d.parent
        parent_str = str(parent)
        if parent_str == '.':
            parent_str = ''
        tree[parent_str]['dirs'].append(d.name)

    # Ajouter les fichiers
    for full_path, rel_path, ext in files:
        parent = str(rel_path.parent)
        if parent == '.':
            parent = ''
        try:
            size_str = human_size(full_path.stat().st_size)
        except Exception:
            size_str = "?"
        tree[parent]['files'].append((rel_path.name, ext, size_str))

    # Trier les entrées
    for parent in tree:
        tree[parent]['dirs'].sort()
        tree[parent]['files'].sort(key=lambda x: x[0])

    # Parcours récursif pour affichage
    def walk_display(current_path: str, prefix: str, is_last: bool):
        node = tree.get(current_path, {'dirs': [], 'files': []})
        entries = []

        # Dossiers d'abord
        for d in node['dirs']:
            entries.append(('dir', d))

        # Puis fichiers
        for f in node['files']:
            entries.append(('file', f))

        for i, (typ, entry) in enumerate(entries):
            is_last_entry = (i == len(entries) - 1)
            connector = "└── " if is_last_entry else "├── "
            new_prefix = prefix + ("    " if is_last_entry else "│   ")

            if typ == 'dir':
                lines.append(f"{prefix}{connector}📁 {entry}/")
                walk_display(
                    str(Path(current_path) / entry) if current_path else entry,
                    new_prefix,
                    is_last_entry
                )
            else:
                name, ext, size_str = entry
                icon = icon_map.get(ext.lower(), "📄")
                lines.append(f"{prefix}{connector} {icon} {name} ({size_str})")

    # Démarrer depuis la racine
    walk_display('', '', True)

    lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(lines)


# Ancienne fonction gardée pour compatibilité (dépréciée)
def generate_project_structure_legacy(folder, include_json=True, include_subdirs=True,
                               include_txt=False, include_po=False, include_mo=False,
                               include_html=True, include_css=True, include_js=True,
                               ignore_init=False, ignore_git=False, ignore_pycache=True):
    """@deprecated Utilisez generate_project_structure(folder, options)"""
    from src.config import ExtractionOptions
    options = ExtractionOptions(
        include_json=include_json,
        include_subdirs=include_subdirs,
        include_txt=include_txt,
        include_po=include_po,
        include_mo=include_mo,
        include_html=include_html,
        include_css=include_css,
        include_js=include_js,
        ignore_init=ignore_init,
        ignore_git=ignore_git,
        ignore_pycache=ignore_pycache
    )
    return generate_project_structure(folder, options)