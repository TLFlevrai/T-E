# src/extractor/file_processor.py
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from src.i18n import _
from src.extractor.content_reader import ContentReader
from src.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class FileSectionResult:
    """Résultat du traitement d'un fichier, prêt à être écrit."""
    full_path: Path
    rel_path: Path
    ext: str
    file_type: str
    content: str
    num_lines: int
    file_size: int
    read_ok: bool
    show_file_paths: bool
    include_file_metadata: bool


class FileProcessor:
    """Traite un fichier (lecture, formatage, stats) sans écrire sur disque."""

    def __init__(self, context):
        self.context = context
        self.reader = ContentReader()
        self.last_read_ok = False

    def process(self, full_path: Path, rel_path: Path, ext: str) -> FileSectionResult:
        """
        Lit, formate, met à jour les stats internes.
        Retourne un DTO avec toutes les infos pour l'écriture.
        N'ÉCRIT PAS sur le disque.
        """
        file_type = self._get_file_type(ext)
        content, num_lines, file_size, read_ok = self.reader.read_file_content(full_path, ext)

        self.last_read_ok = read_ok

        if read_ok:
            self._update_stats(ext, num_lines, file_size)

        self.context.processed_files += 1

        return FileSectionResult(
            full_path=full_path,
            rel_path=rel_path,
            ext=ext,
            file_type=file_type,
            content=content,
            num_lines=num_lines,
            file_size=file_size,
            read_ok=read_ok,
            show_file_paths=self.context.options.show_file_paths,
            include_file_metadata=self.context.options.include_file_metadata
        )

    def _get_file_type(self, ext: str) -> str:
        return {
            '.py': _("Python"),
            '.json': "JSON",
            '.po': _("Traduction (PO)"),
            '.mo': _("Traduction compilée (MO)"),
            '.html': "HTML",
            '.htm': "HTML",
            '.css': "CSS",
            '.js': "JavaScript"
        }.get(ext, _("Texte"))

    def _update_stats(self, ext: str, num_lines: int, file_size: int):
        key = ext.lstrip('.')
        if key == 'htm':
            key = 'html'
        if key in self.context.stats:
            self.context.stats[key] += 1
            self.context.line_counts[key] += num_lines
            self.context.total_size += file_size