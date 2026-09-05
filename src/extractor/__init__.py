# src/extractor/__init__.py
from __future__ import annotations
from .engine import ExtractionEngine
from .extractor import CodeExtractor
from .file_discovery import FileDiscoveryService
from .structure_generator import generate_project_structure
from .context import ExtractionContext
from .file_processor import FileProcessor, FileSectionResult  # <-- AJOUT FileSectionResult
from .content_reader import ContentReader
from .content_formatter import format_json_content
from .export_writer import write_header, write_file_section, write_statistics
from .report_builder import ReportBuilder
from .statistics_collector import StatisticsCollector
from .stats_writer import write_statistics_section

__all__ = [
    'ExtractionEngine',
    'CodeExtractor',
    'FileDiscoveryService',
    'generate_project_structure',
    'ExtractionContext',
    'FileProcessor',
    'FileSectionResult',  # <-- EXPORTÉ
    'ContentReader',
    'format_json_content',
    'write_header',
    'write_file_section',
    'write_statistics',
    'ReportBuilder',
    'StatisticsCollector',
    'write_statistics_section',
]