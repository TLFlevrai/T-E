# src/extractor/file_processor.py
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from src.i18n import _
from src.extractor.content_reader import ContentReader
from src.extractor.context import stat_key_for_ext
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


# Libellés traduits affichés dans l'en-tête « FICHIER <type> : <chemin> ».
# Les noms de langages/format (JSON, HTML, TOML, Rust...) restent en anglais,
# comme les types déjà présents ; seuls les libellés génériques ou dépendants
# de la langue le sont.
FILE_TYPES_I18N = {
    '.py': "Python",
    '.po': "Traduction (PO)",
    '.mo': "Traduction compilée (MO)",
    '.md': "Markdown",
    '.sh': "Script shell",
    '.bash': "Script shell",
    '.zsh': "Script shell",
    '.ps1': "Script PowerShell",
    '.bat': "Script batch",
    '.cmd': "Script batch",
    '.h': "En-tête C",
    '.hpp': "En-tête C++",
}

# Types non traduits (nom propre de la technologie), avec leur extension.
FILE_TYPES = {
    '.json': "JSON",
    '.html': "HTML",
    '.htm': "HTML",
    '.css': "CSS",
    '.js': "JavaScript",
    # Documentation
    '.rst': "reStructuredText",
    '.adoc': "AsciiDoc",
    # Config & build
    '.toml': "TOML",
    '.yaml': "YAML",
    '.yml': "YAML",
    '.ini': "INI",
    '.cfg': "INI",
    '.conf': "INI",
    '.xml': "XML",
    '.plist': "Apple plist",
    '.editorconfig': "EditorConfig",
    '.gitignore': ".gitignore",
    '.gitattributes': ".gitattributes",
    # Data
    '.csv': "CSV",
    '.tsv': "TSV",
    '.sql': "SQL",
    # Front
    '.ts': "TypeScript",
    '.tsx': "TypeScript JSX",
    '.jsx': "JavaScript JSX",
    '.vue': "Vue",
    '.svelte': "Svelte",
    '.scss': "SCSS",
    '.sass': "Sass",
    '.less': "Less",
    # Autres langages
    '.go': "Go",
    '.rs': "Rust",
    '.java': "Java",
    '.kt': "Kotlin",
    '.cs': "C#",
    '.php': "PHP",
    '.rb': "Ruby",
    '.c': "C",
    '.cpp': "C++",
    '.lua': "Lua",
    '.r': "R",
    '.jl': "Julia",
    '.proto': "Protocol Buffers",
    '.graphql': "GraphQL",
    '.gql': "GraphQL",
    '.tf': "Terraform",
    '.dockerfile': "Dockerfile",
}


def file_type_for_ext(ext: str) -> str:
    """Nom lisible d'une extension (ex. '.toml' -> 'TOML').

    Utilisé par l'en-tête des sections de fichier ET par les libellés des
    statistiques : une seule table, donc jamais de divergence entre les deux.
    """
    if ext in FILE_TYPES_I18N:
        return _(FILE_TYPES_I18N[ext])
    return FILE_TYPES.get(ext, _("Texte"))


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
        opts = self.context.options
        content, num_lines, file_size, read_ok = self.reader.read_file_content(
            full_path,
            ext,
            detect_binary=getattr(opts, 'detect_binary', True),
            max_file_size_mb=getattr(opts, 'max_file_size_mb', 10),
            line_range=getattr(opts, 'line_range', None),
        )

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
        return file_type_for_ext(ext)

    def _update_stats(self, ext: str, num_lines: int, file_size: int):
        key = stat_key_for_ext(ext)
        if not key:
            # Fichier sans extension exploitable : ne compte dans aucun
            # compteur (le volume reste tout de même mesuré).
            self.context.total_size += file_size
            return
        # Les extensions supplémentaires (extra_extensions) n'ont pas de
        # compteur prédéfini : on le déclare à la volée, sinon leur volume
        # serait invisible dans les statistiques et absent du total.
        # `stat_key_for_ext` fusionne les synonymes (.yml/.yaml → 'yaml').
        self.context.ensure_stat_key(key)
        self.context.stats[key] += 1
        self.context.line_counts[key] += num_lines
        self.context.total_size += file_size
