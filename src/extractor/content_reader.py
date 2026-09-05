# src/extractor/content_reader.py
from __future__ import annotations
import base64
from pathlib import Path
from typing import Tuple

from src.logger import setup_logger

logger = setup_logger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Mo limite par défaut


class ContentReader:
    """Responsable de la lecture du contenu des fichiers avec détection d'encodage."""

    @staticmethod
    def read_file_content(full_path: Path, ext: str) -> Tuple[str, int, int, bool]:
        """
        Lit le contenu d'un fichier selon son extension.
        Retourne (content, num_lines, file_size, read_ok).
        """
        try:
            file_size = full_path.stat().st_size

            if file_size > MAX_FILE_SIZE:
                logger.warning(
                    "Fichier trop volumineux (%s octets) : %s — ignoré",
                    file_size, full_path,
                )
                content = f"// ERREUR: Fichier trop volumineux ({file_size} octets)\n"
                return content, 0, file_size, False

            if ext == '.mo':
                with open(full_path, 'rb') as f:
                    raw = f.read()
                content = base64.b64encode(raw).decode('ascii')
                num_lines = len(content.splitlines())
                file_size = len(raw)
                read_ok = True
            else:
                content = ContentReader._read_text_with_fallback(full_path)
                if ext == '.json':
                    from .content_formatter import format_json_content
                    content = format_json_content(content, full_path)
                num_lines = len(content.splitlines())
                read_ok = True
        except Exception as e:
            logger.error("Erreur de lecture du fichier %s : %s", full_path, e)
            content = f"// ERREUR: Impossible de lire le fichier : {e}\n"
            num_lines = 0
            file_size = 0
            read_ok = False
        return content, num_lines, file_size, read_ok

    @staticmethod
    def _read_text_with_fallback(file_path: Path) -> str:
        """Tente plusieurs encodages pour lire un fichier texte."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-15', 'utf-16']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        # Dernier recours : latin-1 (ne lève jamais d'exception)
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()