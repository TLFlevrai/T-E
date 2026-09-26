# src/extractor/content_reader.py
from __future__ import annotations
import base64
from pathlib import Path
from typing import Tuple, Optional

from src.logger import setup_logger

logger = setup_logger(__name__)

# Seuil pour activer le streaming (1 Mo)
STREAMING_THRESHOLD = 1024 * 1024
# Taille de chunk pour le streaming (aligné sur FileTransferService.CHUNK_SIZE)
CHUNK_SIZE = 64 * 1024
# Taille lue pour la détection binaire (8 Ko)
BINARY_DETECTION_SIZE = 8 * 1024


class ContentReader:
    """Responsable de la lecture du contenu des fichiers avec détection d'encodage."""

    @staticmethod
    def read_file_content(
        full_path: Path,
        ext: str,
        *,
        detect_binary: bool = True,
        max_file_size_mb: int = 10,
        line_range: Optional[Tuple[int, int]] = None,
    ) -> Tuple[str, int, int, bool]:
        """
        Lit le contenu d'un fichier selon son extension.
        Retourne (content, num_lines, file_size, read_ok).
        """
        try:
            file_size = full_path.stat().st_size
            max_file_size = max_file_size_mb * 1024 * 1024

            if file_size > max_file_size:
                logger.warning(
                    "Fichier trop volumineux (%s octets, max %s Mo) : %s — ignoré",
                    file_size, max_file_size_mb, full_path,
                )
                content = f"// ERREUR: Fichier trop volumineux ({file_size} octets, max {max_file_size_mb} Mo)\n"
                return content, 0, file_size, False

            # Fichiers .mo : toujours en base64 (binaire)
            if ext == '.mo':
                with open(full_path, 'rb') as f:
                    raw = f.read()
                content = base64.b64encode(raw).decode('ascii')
                num_lines = len(content.splitlines())
                file_size = len(raw)
                return content, num_lines, file_size, True

            # Détection binaire AVANT lecture complète (si activée)
            if detect_binary and ContentReader._is_likely_binary(full_path):
                logger.warning(
                    "Fichier binaire détecté (extension %s) : %s — ignoré",
                    ext, full_path,
                )
                content = f"// ERREUR: Fichier binaire détecté (extension {ext})\n"
                return content, 0, file_size, False

            # Streaming pour gros fichiers
            if file_size > STREAMING_THRESHOLD:
                return ContentReader._read_streaming(full_path, ext, line_range, file_size)

            # Lecture standard pour petits fichiers
            content = ContentReader._read_text_with_fallback(full_path)
            if ext == '.json':
                from .content_formatter import format_json_content
                content = format_json_content(content, full_path)

            # Appliquer line_range si spécifié
            if line_range is not None:
                content = ContentReader._apply_line_range(content, line_range)

            num_lines = len(content.splitlines())
            return content, num_lines, file_size, True

        except UnicodeDecodeError as e:
            logger.error("Erreur d'encodage fichier %s : %s", full_path, e)
            content = f"// ERREUR: Encodage non supporté : {e}\n"
            return content, 0, file_size, False
        except OSError as e:
            logger.error("Erreur I/O fichier %s : %s", full_path, e)
            content = f"// ERREUR: Impossible de lire le fichier : {e}\n"
            return content, 0, 0, False
        except Exception as e:
            logger.exception("Erreur inattendue lecture fichier %s", full_path)
            content = f"// ERREUR: {e}\n"
            return content, 0, 0, False

    @staticmethod
    def _is_likely_binary(file_path: Path) -> bool:
        """
        Heuristique conservatrice pour détecter un fichier binaire.
        Lit les premiers 8 Ko et vérifie :
        - Présence de bytes NUL (\\x00)
        - Ratio de bytes non-ASCII (>30%)
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(BINARY_DETECTION_SIZE)
        except OSError:
            return False

        if not sample:
            return False

        # NUL byte = binaire certain
        if b'\x00' in sample:
            logger.debug("Fichier binaire détecté (NUL byte) : %s", file_path)
            return True

        # Compter bytes non-ASCII (>127)
        non_ascii = sum(1 for b in sample if b > 127)
        ratio = non_ascii / len(sample)

        # Seuil conservateur : 30% de non-ASCII
        if ratio > 0.30:
            logger.debug("Fichier binaire détecté (ratio non-ASCII %.2f%%) : %s", ratio * 100, file_path)
            return True

        return False

    @staticmethod
    def _read_streaming(
        file_path: Path,
        ext: str,
        line_range: Optional[Tuple[int, int]],
        file_size: int,
    ) -> Tuple[str, int, int, bool]:
        """
        Lit un gros fichier par chunks et écrit directement le contenu.
        Pour l'extraction, on doit retourner le contenu complet.
        On lit par chunks mais on accumule (le fichier de sortie est écrit par le writer).
        """
        logger.info("Lecture en streaming (%.1f Mo) : %s", file_size / 1024 / 1024, file_path)

        content_parts = []
        total_lines = 0
        start_line, end_line = line_range if line_range else (1, None)

        try:
            # Détecter l'encodage sur le premier chunk
            with open(file_path, 'rb') as f:
                first_chunk = f.read(CHUNK_SIZE)
            encoding = ContentReader._detect_encoding(first_chunk)
            logger.debug("Encodage détecté pour streaming : %s", encoding)

            # Relire depuis le début avec le bon encodage
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                current_line = 0
                for line in f:
                    current_line += 1
                    if current_line < start_line:
                        continue
                    if end_line is not None and current_line > end_line:
                        break
                    content_parts.append(line)
                    total_lines += 1

            content = ''.join(content_parts)

            if ext == '.json':
                from .content_formatter import format_json_content
                content = format_json_content(content, file_path)

            return content, total_lines, file_size, True

        except UnicodeDecodeError as e:
            logger.error("Erreur d'encodage en streaming %s : %s", file_path, e)
            return f"// ERREUR: Encodage non supporté en streaming : {e}\n", 0, file_size, False
        except Exception as e:
            logger.exception("Erreur streaming fichier %s", file_path)
            return f"// ERREUR: {e}\n", 0, file_size, False

    @staticmethod
    def _detect_encoding(sample: bytes) -> str:
        """Détecte l'encodage via BOM ou heuristique."""
        # BOM UTF-8
        if sample.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        # BOM UTF-16 LE
        if sample.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        # BOM UTF-16 BE
        if sample.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        # BOM UTF-32 LE
        if sample.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'
        # BOM UTF-32 BE
        if sample.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'

        # Heuristique : essayer utf-8 d'abord
        try:
            sample.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass

        # Fallback latin-1 (ne rate jamais)
        return 'latin-1'

    @staticmethod
    def _read_text_with_fallback(file_path: Path) -> str:
        """Tente plusieurs encodages pour lire un fichier texte (avec BOM)."""
        # D'abord détecter l'encodage via BOM
        with open(file_path, 'rb') as f:
            sample = f.read(4)
        encoding = ContentReader._detect_encoding(sample)

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            pass

        # Fallbacks classiques
        for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-15', 'utf-16']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    logger.debug("Fichier lu avec encodage fallback %s : %s", enc, file_path)
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Dernier recours : latin-1 (ne lève jamais d'exception)
        with open(file_path, 'r', encoding='latin-1') as f:
            logger.warning("Fallback latin-1 forcé : %s", file_path)
            return f.read()

    @staticmethod
    def _apply_line_range(content: str, line_range: Tuple[int, int]) -> str:
        """Applique une plage de lignes (1-indexed, inclusif)."""
        start, end = line_range
        lines = content.splitlines(keepends=True)
        # Convertir en index 0-based
        start_idx = max(0, start - 1)
        end_idx = end if end is not None else len(lines)
        return ''.join(lines[start_idx:end_idx])