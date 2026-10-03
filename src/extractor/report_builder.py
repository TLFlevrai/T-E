# src/extractor/report_builder.py
from __future__ import annotations
from src.extractor.stats_writer import write_statistics_section

class ReportBuilder:
    def __init__(self, context):
        self.context = context

    def write_statistics(self, out_file):
        stats = self.context.stats
        lines = self.context.line_counts
        total_size = self.context.total_size
        # FIX BUG #12 : passer les compteurs précalculés depuis le contexte
        num_dirs = self.context.num_dirs
        num_packages = self.context.num_packages

        # Extensions supplémentaires : tout ce qui n'est pas une extension
        # classique (voir CLASSIC_STAT_KEYS). Ce sont les extensions issues
        # d'`extra_extensions` ; seules celles vues dans le dossier courant
        # sont listées, pour ne pas noyer le rapport de zéros.
        extra_keys = self.context.extra_stat_keys()
        extra_counts = {k: stats.get(k, 0) for k in extra_keys if stats.get(k, 0)}
        extra_line_counts = {k: lines.get(k, 0) for k in extra_keys if stats.get(k, 0)}

        write_statistics_section(
            out_file,
            self.context.folder_path,
            self.context.options.include_subdirs,
            stats.get('py', 0),
            stats.get('json', 0),
            stats.get('txt', 0),
            stats.get('po', 0),
            stats.get('mo', 0),
            stats.get('html', 0),
            stats.get('css', 0),
            stats.get('js', 0),
            lines.get('py', 0),
            lines.get('json', 0),
            lines.get('txt', 0),
            lines.get('po', 0),
            lines.get('mo', 0),
            lines.get('html', 0),
            lines.get('css', 0),
            lines.get('js', 0),
            total_size,
            num_dirs=num_dirs,
            num_packages=num_packages,
            md_count=stats.get('md', 0),
            total_lines_md=lines.get('md', 0),
            extra_counts=extra_counts,
            extra_line_counts=extra_line_counts,
        )
