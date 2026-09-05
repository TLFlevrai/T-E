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
            total_size
        )