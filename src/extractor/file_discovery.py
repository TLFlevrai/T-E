# src/extractor/file_discovery.py
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Tuple, Set, Iterator, Optional
from src.config import ExtractionOptions
from src.logger import setup_logger
from src.extractor._filters import (
    DEFAULT_IGNORED_PATTERNS,
    EXCLUDED_FILE_SUFFIXES,
    EXCLUDED_FILE_NAMES,
    should_ignore_dir,
    should_ignore_file,
    prune_dirs,
)

logger = setup_logger(__name__)


class FileDiscoveryService:
    """
    Service unique de découverte de fichiers avec élagage (pruning) au niveau FS.
    Ne descend JAMAIS dans les dossiers techniques/cachés configurés.
    """

    def __init__(self, options: ExtractionOptions):
        self.options = options
        # Construire la liste des patterns d'exclusion en fusionnant :
        # - les patterns venant de options.ignore_patterns (nouveau)
        # - les exclusions legacy (ignore_git, ignore_pycache) pour rétro-compatibilité
        self._ignored_patterns: list[str] = list(options.ignore_patterns)
        if options.ignore_git:
            if ".git" not in self._ignored_patterns:
                self._ignored_patterns.append(".git")
        if options.ignore_pycache:
            if "__pycache__" not in self._ignored_patterns:
                self._ignored_patterns.append("__pycache__")
        # Extensions autorisées (calculées une fois)
        self._allowed_extensions: List[str] = self._build_extension_list()

    # --------------------------------------------------------------------- #
    # API PUBLIQUE
    # --------------------------------------------------------------------- #

    def find_files(self, folder: str) -> List[Tuple[Path, Path, str]]:
        """
        Retourne la liste des fichiers à extraire.
        Format: [(full_path, relative_path, extension), ...]
        """
        items = list(self._walk(Path(folder).resolve(), collect_dirs=False))
        return [(item.full_path, item.rel_path, item.extension) for item in items]

    def find_all_paths(self, folder: str, all_files: bool = False) -> Tuple[List[Tuple[Path, Path, str]], Set[Path]]:
        """
        Retourne (fichiers, dossiers_parents) pour génération de structure.
        Utilise le MÊME parcours optimisé que find_files.

        Args:
            all_files: si True, inclut TOUS les fichiers sans filtre d'extension
                       (vidéos, images, archives, ...) tout en respectant le pruning.
        """
        folder_path = Path(folder).resolve()
        files = []
        dirs_set = set()

        for item in self._walk(folder_path, collect_dirs=True, all_files=all_files):
            if item.kind == 'file':
                files.append((item.full_path, item.rel_path, item.extension))
            elif item.kind == 'dir':
                dirs_set.add(item.rel_path)

        return files, dirs_set

    # --------------------------------------------------------------------- #
    # INTERNE
    # --------------------------------------------------------------------- #

    class _WalkItem:
        """Résultat d'un pas de parcours."""
        __slots__ = ('kind', 'full_path', 'rel_path', 'extension', 'size')

        def __init__(self, kind: str, full_path: Optional[Path] = None,
                     rel_path: Optional[Path] = None, extension: Optional[str] = None, size: int = -1):
            self.kind = kind
            self.full_path = full_path
            self.rel_path = rel_path
            self.extension = extension
            self.size = size  # FIX BUG #3 : taille du fichier calculée au parcours (-1 si inconnu)

    def _walk(self, folder_path: Path, collect_dirs: bool = False,
              all_files: bool = False) -> Iterator[_WalkItem]:
        """
        Générateur unique de parcours avec pruning, protection cycles et limite de profondeur.

        Args:
            folder_path: Racine du parcours (déjà résolue)
            collect_dirs: Si True, émet aussi les dossiers découverts
            all_files: Si True, ne filtre pas par extension (structure complète)
                       mais filtre TOUJOURS les fichiers techniques/système
                       sauf si force_include_all=True

        Yields:
            _WalkItem pour chaque fichier (et dossier si collect_dirs)
        """
        max_depth = self.options.max_depth if self.options.max_depth and self.options.max_depth > 0 else None
        force_include_all = getattr(self.options, 'force_include_all', False)
        visited: set[Path] = set()
        yielded_dirs: set[Path] = set()  # Pour dédupliquer les dossiers yieldés

        for root, dirs, filenames in os.walk(folder_path, topdown=True, followlinks=False):
            root_path = Path(root)
            resolved_root = root_path.resolve()

            # Protection anti-cycles : si on a déjà visité ce chemin résolu
            if resolved_root in visited:
                dirs[:] = []
                continue
            visited.add(resolved_root)

            # Calculer la profondeur relative
            if max_depth is not None:
                try:
                    rel = root_path.relative_to(folder_path)
                    depth = len(rel.parts)
                except ValueError:
                    depth = 0
                if depth >= max_depth:
                    dirs[:] = []
                    continue

            # --- PRUNING : supprime les dossiers ignorés AVANT la descente ---
            prune_dirs(dirs, self._ignored_patterns)

            # Si include_subdirs=False, on vide dirs pour ne pas descendre
            if not self.options.include_subdirs and root != str(folder_path):
                dirs[:] = []

            root_path = Path(root)
            rel_root = root_path.relative_to(folder_path)
            rel_root_str = str(rel_root) if rel_root != Path('.') else ''

            # Collecter les dossiers (pour l'affichage structure)
            if collect_dirs:
                for d in dirs:
                    dir_rel = Path(rel_root_str) / d if rel_root_str else Path(d)
                    if dir_rel not in yielded_dirs:
                        yielded_dirs.add(dir_rel)
                        yield self._WalkItem('dir', rel_path=dir_rel)

            # Collecter les fichiers
            for fname in filenames:
                # Filtrage des fichiers techniques/système : s'applique TOUJOURS
                # sauf si force_include_all=True (debug uniquement)
                if should_ignore_file(fname, self._ignored_patterns, force_include_all):
                    continue

                # Filtre d'extension : uniquement si on ne veut PAS tout inclure
                if not all_files and not self._is_extractable_file(fname):
                    continue
                # ignore_init : option d'extraction, sans effet sur la structure complète
                if self.options.ignore_init and fname == '__init__.py' and not all_files:
                    continue

                full_path = root_path / fname
                try:
                    rel_path = full_path.relative_to(folder_path)
                except ValueError:
                    # Hors racine (symlink étrange) -> ignorer
                    continue

                # Parents du fichier pour l'arbre (si collect_dirs)
                if collect_dirs:
                    for parent in rel_path.parents:
                        if parent != Path('.') and parent not in yielded_dirs:
                            yielded_dirs.add(parent)
                            yield self._WalkItem('dir', rel_path=parent)

                # FIX BUG #3 : calculer la taille une seule fois au parcours
                file_size = -1
                try:
                    file_size = full_path.stat().st_size
                except OSError:
                    pass
                yield self._WalkItem('file', full_path=full_path, rel_path=rel_path, extension=full_path.suffix, size=file_size)

    def _is_extractable_file(self, filename: str) -> bool:
        """Vérification rapide d'extension (pas d'allocation Path)."""
        # On suppose que la liste est petite -> tuple plus rapide que set pour < 10 items
        return any(filename.endswith(ext) for ext in self._allowed_extensions)

    def _build_extension_list(self) -> List[str]:
        extensions = ['.py']
        if self.options.include_json:
            extensions.append('.json')
        if self.options.include_txt:
            extensions.append('.txt')
        if self.options.include_po:
            extensions.append('.po')
        if self.options.include_mo:
            extensions.append('.mo')
        if self.options.include_html:
            extensions.extend(['.html', '.htm'])
        if self.options.include_css:
            extensions.append('.css')
        if self.options.include_js:
            extensions.append('.js')
        return extensions