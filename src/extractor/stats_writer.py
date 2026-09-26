# src/extractor/stats_writer.py
from __future__ import annotations
from pathlib import Path

def write_statistics_section(output_file, folder, include_subdirs,
                             py_count, json_count, txt_count, po_count, mo_count,
                             html_count, css_count, js_count,
                             total_lines_py, total_lines_json, total_lines_txt,
                             total_lines_po, total_lines_mo,
                             total_lines_html, total_lines_css, total_lines_js,
                             total_size,
                             num_dirs: int = 0,
                             num_packages: int = 0):
    # FIX BUG #12 : utiliser les compteurs précalculés au lieu de rglob sur le thread UI
    # num_dirs et num_packages sont fournis par le contexte (calculés dans structure_generator)

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
    output_file.write(f"Nombre total de fichiers     : {py_count + json_count + txt_count + po_count + mo_count + html_count + css_count + js_count}\n")
    output_file.write(f"Nombre de lignes (Python)    : {total_lines_py}\n")
    output_file.write(f"Nombre de lignes (JSON)      : {total_lines_json}\n")
    output_file.write(f"Nombre de lignes (Texte)     : {total_lines_txt}\n")
    output_file.write(f"Nombre de lignes (PO)        : {total_lines_po}\n")
    output_file.write(f"Nombre de lignes (MO)        : {total_lines_mo}\n")
    output_file.write(f"Nombre de lignes (HTML)      : {total_lines_html}\n")
    output_file.write(f"Nombre de lignes (CSS)       : {total_lines_css}\n")
    output_file.write(f"Nombre de lignes (JS)        : {total_lines_js}\n")
    output_file.write(f"Nombre total de lignes       : {total_lines_py + total_lines_json + total_lines_txt + total_lines_po + total_lines_mo + total_lines_html + total_lines_css + total_lines_js}\n")

    if total_size < 1024:
        size_str = f"{total_size} octets"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.2f} Ko"
    else:
        size_str = f"{total_size / (1024 * 1024):.2f} Mo"
    output_file.write(f"Volume total extrait         : {size_str}\n")