# src/extractor/statistics_collector.py
from __future__ import annotations


class StatisticsCollector:
    """Agrège les statistiques d'extraction."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.py_count = 0
        self.json_count = 0
        self.txt_count = 0
        self.po_count = 0
        self.mo_count = 0
        self.html_count = 0
        self.css_count = 0
        self.js_count = 0

        self.total_lines_py = 0
        self.total_lines_json = 0
        self.total_lines_txt = 0
        self.total_lines_po = 0
        self.total_lines_mo = 0
        self.total_lines_html = 0
        self.total_lines_css = 0
        self.total_lines_js = 0
        self.total_size = 0

        self.processed_files = 0  # nombre de fichiers traités (même en erreur)

    def count_file(self, ext: str, num_lines: int, file_size: int, read_ok: bool):
        """Met à jour les compteurs pour un fichier donné."""
        if not read_ok:
            self.processed_files += 1
            return

        self.processed_files += 1
        self.total_size += file_size

        if ext == '.py':
            self.py_count += 1
            self.total_lines_py += num_lines
        elif ext == '.json':
            self.json_count += 1
            self.total_lines_json += num_lines
        elif ext == '.po':
            self.po_count += 1
            self.total_lines_po += num_lines
        elif ext == '.mo':
            self.mo_count += 1
            self.total_lines_mo += num_lines
        elif ext in ('.html', '.htm'):
            self.html_count += 1
            self.total_lines_html += num_lines
        elif ext == '.css':
            self.css_count += 1
            self.total_lines_css += num_lines
        elif ext == '.js':
            self.js_count += 1
            self.total_lines_js += num_lines
        else:
            self.txt_count += 1
            self.total_lines_txt += num_lines

    def get_counts(self):
        """Retourne un tuple (py_count, json_count, txt_count, po_count, mo_count, html_count, css_count, js_count)."""
        return (self.py_count, self.json_count, self.txt_count, self.po_count, self.mo_count,
                self.html_count, self.css_count, self.js_count)

    def get_line_counts(self):
        """Retourne un tuple (total_lines_py, total_lines_json, total_lines_txt, total_lines_po, total_lines_mo, total_lines_html, total_lines_css, total_lines_js)."""
        return (self.total_lines_py, self.total_lines_json, self.total_lines_txt,
                self.total_lines_po, self.total_lines_mo,
                self.total_lines_html, self.total_lines_css, self.total_lines_js)

    def get_total_size(self):
        return self.total_size