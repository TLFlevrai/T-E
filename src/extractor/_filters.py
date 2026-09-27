# src/extractor/_filters.py
"""Filtres communs pour la découverte de fichiers et parcours d'arborescence.

Ce module centralise la logique d'exclusion des dossiers et fichiers
techniques, utilisée à la fois par FileDiscoveryService et VersionService.
"""
from __future__ import annotations
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

# Suffices de fichiers à exclure systématiquement (même avec all_files=True)
EXCLUDED_FILE_SUFFIXES = (
    ".pyc", ".pyo", ".pyd",
    ".so", ".dll", ".dylib",
    ".log",
)

# Noms de fichiers à exclure systématiquement
EXCLUDED_FILE_NAMES = frozenset({
    "CACHEDIR.TAG",
    "lastfailed",
    "nodeids",
    ".DS_Store",
    "Thumbs.db",
})

# Patterns par défaut pour l'exclusion des dossiers
DEFAULT_IGNORED_PATTERNS = [
    ".git", ".hg", ".svn",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
    "__pycache__",
    ".venv", "venv", "env",
    "node_modules",
    ".idea", ".vscode",
    "dist", "build", ".eggs",
    ".coverage", ".tox",
    "*.egg-info",
]


def _matches_any_pattern(name: str, patterns: Iterable[str]) -> bool:
    """Matche un nom contre une liste de patterns (glob-like)."""
    return any(fnmatch(name, p) for p in patterns)


def should_ignore_dir(dirname: str, ignored_patterns: Iterable[str]) -> bool:
    """Vérifie si un nom de dossier doit être ignoré selon les patterns."""
    return _matches_any_pattern(dirname, ignored_patterns)


def should_ignore_file(filename: str, ignored_patterns: Iterable[str], force_include_all: bool = False) -> bool:
    """Vérifie si un fichier doit être ignoré.

    Args:
        filename: Nom du fichier (sans chemin)
        ignored_patterns: Patterns d'exclusion à tester
        force_include_all: Si True, ignore les filtres de suffixes/noms (debug)

    Returns:
        True si le fichier doit être ignoré
    """
    if force_include_all:
        return False

    # Exclusion par suffixe
    if any(filename.endswith(suf) for suf in EXCLUDED_FILE_SUFFIXES):
        return True

    # Exclusion par nom exact
    if filename in EXCLUDED_FILE_NAMES:
        return True

    # Exclusion par pattern (pour les noms de fichiers aussi)
    if _matches_any_pattern(filename, ignored_patterns):
        return True

    return False


def prune_dirs(dirs: list[str], ignored_patterns: Iterable[str]) -> None:
    """Modifie la liste `dirs` en place pour retirer les dossiers ignorés.

    Utilisé avec os.walk(topdown=True) pour pruner avant la descente.
    """
    dirs[:] = [d for d in dirs if not _matches_any_pattern(d, ignored_patterns)]


def iter_safe_txt_files(root: Path) -> list[Path]:
    """Itère sur les fichiers .txt en excluant les dossiers techniques.

    Utilisé par VersionService pour scanner les fichiers d'export.
    """
    ignored = DEFAULT_IGNORED_PATTERNS
    results = []
    for root_dir, dirs, filenames in os.walk(root, topdown=True, followlinks=False):
        prune_dirs(dirs, ignored)
        for fname in filenames:
            if fname.endswith(".txt") and not should_ignore_file(fname, ignored):
                results.append(Path(root_dir) / fname)
    return results