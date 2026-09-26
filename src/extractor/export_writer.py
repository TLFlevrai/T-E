# src/extractor/export_writer.py
from __future__ import annotations
from pathlib import Path

from src.i18n import _
from src.utils import get_current_date, human_size
from .stats_writer import write_statistics_section
from .file_processor import FileSectionResult  # Import du DTO


def write_header(output_file, folder):
    output_file.write(f"{_('Extraction du code du dossier')} : {folder}\n")
    date_label = _("Date d'extraction")
    output_file.write(f"{date_label} : {get_current_date()}\n")
    output_file.write("Format-Version: 1\n")
    output_file.write("=" * 80 + "\n\n")


def write_file_section(output_file, result: FileSectionResult):
    """
    Écrit une section fichier à partir du DTO FileSectionResult.
    N'effectue AUCUN traitement métier, seulement du formatage/sortie.
    """
    full_path = result.full_path
    rel_path = result.rel_path
    ext = result.ext

    output_file.write(f"\n{'=' * 80}\n")
    output_file.write(f"FICHIER {result.file_type} : ")
    if result.show_file_paths:
        output_file.write(f"{rel_path}\n")
    else:
        output_file.write(f"{full_path.name}\n")
    output_file.write(f"{_('Type')}: {result.file_type}\n")
    output_file.write(f"{_('Chemin complet')}: {full_path}\n")

    if result.include_file_metadata:
        parent_dir = rel_path.parent if result.show_file_paths else full_path.parent
        if not parent_dir or str(parent_dir) == '.':
            parent_dir = "."
        output_file.write(f"{_('Dossier parent')}: {parent_dir}\n")
        output_file.write(f"{_('Taille')}: {human_size(result.file_size)}\n")
        output_file.write(f"{_('Nombre de lignes')}: {result.num_lines}\n")

    output_file.write("-" * 80 + "\n")
    if ext == '.mo' and result.read_ok:
        output_file.write("// Fichier binaire (.mo) encodé en base64\n")
        output_file.write(result.content)
        if not result.content.endswith('\n'):
            output_file.write("\n")
    else:
        output_file.write(result.content)
        if not result.content.endswith('\n'):
            output_file.write("\n")
    output_file.write("\n--- FIN DU FICHIER ---\n")


def write_statistics(output_file, folder, include_subdirs,
                     py_count, json_count, txt_count, po_count, mo_count,
                     html_count, css_count, js_count,
                     total_lines_py, total_lines_json, total_lines_txt,
                     total_lines_po, total_lines_mo,
                     total_lines_html, total_lines_css, total_lines_js,
                     total_size,
                     include_statistics):
    if include_statistics:
        output_file.write("\n--- FIN DES FICHIERS ---\n\n")
        write_statistics_section(output_file, folder, include_subdirs,
                                 py_count, json_count, txt_count, po_count, mo_count,
                                 html_count, css_count, js_count,
                                 total_lines_py, total_lines_json, total_lines_txt,
                                 total_lines_po, total_lines_mo,
                                 total_lines_html, total_lines_css, total_lines_js,
                                 total_size)