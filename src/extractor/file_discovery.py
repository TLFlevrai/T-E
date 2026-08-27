# src/extractor/file_discovery.py
import os
from pathlib import Path
from typing import List, Tuple, Set, Iterator, Optional
from src.config import ExtractionOptions
from src.logger import setup_logger

logger = setup_logger(__name__)


class FileDiscoveryService:
    """
    Service unique de découverte de fichiers avec élagage (pruning) au niveau FS.
    Ne descend JAMAIS dans .git, __pycache__ ni autres dossiers ignorés.
    """

    def __init__(self, options: ExtractionOptions):
        self.options = options
        # Noms de dossiers à ignorer complètement (pruning)
        self._ignored_dir_names: Set[str] = set()
        if options.ignore_git:
            self._ignored_dir_names.add('.git')
        if options.ignore_pycache:
            self._ignored_dir_names.add('__pycache__')
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
        __slots__ = ('kind', 'full_path', 'rel_path', 'extension')

        def __init__(self, kind: str, full_path: Optional[Path] = None,
                     rel_path: Optional[Path] = None, extension: Optional[str] = None):
            self.kind = kind
            self.full_path = full_path
            self.rel_path = rel_path
            self.extension = extension

    def _walk(self, folder_path: Path, collect_dirs: bool = False,
              all_files: bool = False) -> Iterator[_WalkItem]:
        """
        Générateur unique de parcours avec pruning.
        
        Args:
            folder_path: Racine du parcours (déjà résolue)
            collect_dirs: Si True, émet aussi les dossiers découverts
            all_files: Si True, ne filtre pas par extension (structure complète)
            
        Yields:
            _WalkItem pour chaque fichier (et dossier si collect_dirs)
        """
        for root, dirs, filenames in os.walk(folder_path, topdown=True):
            # --- PRUNING : supprime les dossiers ignorés AVANT la descente ---
            dirs[:] = [d for d in dirs if d not in self._ignored_dir_names]

            # Si include_subdirs=False, on vide dirs pour ne pas descendre
            if not self.options.include_subdirs and root != str(folder_path):
                dirs[:] = []

            root_path = Path(root)
            rel_root = root_path.relative_to(folder_path)
            rel_root_str = str(rel_root) if rel_root != Path('.') else ''

            # Collecter les dossiers (pour l'affichage structure)
            if collect_dirs:
                for d in dirs:
                    if rel_root_str:
                        yield self._WalkItem('dir', rel_path=Path(rel_root_str) / d)
                    else:
                        yield self._WalkItem('dir', rel_path=Path(d))

            # Collecter les fichiers
            for fname in filenames:
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
                        if parent != Path('.'):
                            yield self._WalkItem('dir', rel_path=parent)

                yield self._WalkItem('file', full_path=full_path, rel_path=rel_path, extension=full_path.suffix)

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