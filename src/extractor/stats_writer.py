# src/extractor/stats_writer.py
from __future__ import annotations
from pathlib import Path

from src.i18n import _
from .file_processor import file_type_for_ext

# Largeur de la colonne des libellés (alignement historique conservé).
# Les lignes classiques écrivent "Fichiers Python (.py)        : ", soit
# 21 caractères + 8 espaces, d'où 29. Les libellés générés
# dynamiquement doivent reprendre exactement cette même colonne.
_COL_LABEL = 29


def write_statistics_section(output_file, folder, include_subdirs,
                             py_count, json_count, txt_count, po_count, mo_count,
                             html_count, css_count, js_count,
                             total_lines_py, total_lines_json, total_lines_txt,
                             total_lines_po, total_lines_mo,
                             total_lines_html, total_lines_css, total_lines_js,
                             total_size,
                             num_dirs: int = 0,
                             num_packages: int = 0,
                             md_count: int = 0,
                             total_lines_md: int = 0,
                             extra_counts: dict[str, int] | None = None,
                             extra_line_counts: dict[str, int] | None = None):
    # FIX BUG #12 : utiliser les compteurs précalculés au lieu de rglob sur le thread UI
    # num_dirs et num_packages sont fournis par le contexte (calculés dans structure_generator)
    # NOTE : la longue liste d'arguments est celle du format de rapport
    # historique ; la refactorer en dataclass changerait l'API publique
    # consommée par ReportBuilder.write_statistics.

    output_file.write("\n" + "=" * 80 + "\n")
    output_file.write("STATISTIQUES\n")
    output_file.write("=" * 80 + "\n")
    output_file.write(f"Nombre de dossiers          : {num_dirs}\n")
    output_file.write(f"Dossiers 'Python package'    : {num_packages}\n")
    output_file.write(f"Fichiers Python (.py)        : {py_count}\n")
    output_file.write(f"Fichiers JSON (.json)        : {json_count}\n")
    output_file.write(f"Fichiers Texte (.txt)        : {txt_count}\n")
    output_file.write(f"Fichiers PO (.po)            : {po_count}\n")
    output_file.write(f"Fichiers MO (.mo)            : {mo_count}\n")
    output_file.write(f"Fichiers HTML (.html/.htm)   : {html_count}\n")
    output_file.write(f"Fichiers CSS (.css)          : {css_count}\n")
    output_file.write(f"Fichiers JavaScript (.js)    : {js_count}\n")

    # --- Markdown et extensions supplémentaires ---
    # Ces lignes n'apparaissent QUE si le dossier contenait réellement des
    # fichiers de ces types : un export classique (défauts) produit ainsi
    # exactement le même rapport qu'avant l'ajout de ces extensions.
    if md_count:
        output_file.write(f"Fichiers Markdown (.md)      : {md_count}\n")

    extra_total = 0
    if extra_counts:
        output_file.write(_("Autres extensions") + "\n")
        for ext_key, count in extra_counts.items():
            if not count:
                continue
            label = f"Fichiers {file_type_for_ext('.' + ext_key)}"
            output_file.write(f"{label.ljust(_COL_LABEL)}: {count}\n")
            extra_total += count

    total_files = (py_count + json_count + txt_count + po_count + mo_count
                   + html_count + css_count + js_count + md_count + extra_total)
    output_file.write(f"Nombre total de fichiers     : {total_files}\n")
    output_file.write(f"Nombre de lignes (Python)    : {total_lines_py}\n")
    output_file.write(f"Nombre de lignes (JSON)      : {total_lines_json}\n")
    output_file.write(f"Nombre de lignes (Texte)     : {total_lines_txt}\n")
    output_file.write(f"Nombre de lignes (PO)        : {total_lines_po}\n")
    output_file.write(f"Nombre de lignes (MO)        : {total_lines_mo}\n")
    output_file.write(f"Nombre de lignes (HTML)      : {total_lines_html}\n")
    output_file.write(f"Nombre de lignes (CSS)       : {total_lines_css}\n")
    output_file.write(f"Nombre de lignes (JS)        : {total_lines_js}\n")
    if md_count:
        output_file.write(f"Nombre de lignes (Markdown)  : {total_lines_md}\n")

    extra_lines_total = 0
    if extra_counts and extra_line_counts:
        for ext_key, count in extra_counts.items():
            if not count:
                continue
            label = f"Nombre de lignes ({file_type_for_ext('.' + ext_key)})"
            output_file.write(f"{label.ljust(_COL_LABEL)}: {extra_line_counts.get(ext_key, 0)}\n")
            extra_lines_total += extra_line_counts.get(ext_key, 0)

    total_lines = (total_lines_py + total_lines_json + total_lines_txt
                   + total_lines_po + total_lines_mo + total_lines_html
                   + total_lines_css + total_lines_js + total_lines_md
                   + extra_lines_total)
    output_file.write(f"Nombre total de lignes       : {total_lines}\n")

    if total_size < 1024:
        size_str = f"{total_size} octets"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.2f} Ko"
    else:
        size_str = f"{total_size / (1024 * 1024):.2f} Mo"
    output_file.write(f"Volume total extrait         : {size_str}\n")
