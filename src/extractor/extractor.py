# src/extractor/extractor.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Callable
from src.config import ExtractionOptions
from src.extractor.engine import ExtractionEngine, SUCCESS, FAILED, CANCELLED
from src.extractor.context import ExtractionContext
from src.extractor.file_discovery import FileDiscoveryService
from src.extractor.structure_generator import generate_project_structure
from src.logger import setup_logger

logger = setup_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


class CodeExtractor:
    def __init__(self, options: Optional[ExtractionOptions] = None, **overrides):
        if options is None:
            base = ExtractionOptions()
        else:
            base = options
        if overrides:
            base_dict = base.dict()
            base_dict.update(overrides)
            self.options = ExtractionOptions(**base_dict)
        else:
            self.options = base

        self.discovery = FileDiscoveryService(self.options)

    def find_files(self, folder: str):
        """Retourne la liste des fichiers découvrables (pour GUI, aperçu)."""
        return self.discovery.find_files(folder)

    def generate_project_structure(self, folder: str) -> str:
        """
        Génère la structure du projet.
        Utilise la nouvelle API unifiée (options complet passé).
        """
        return generate_project_structure(folder, self.options)

    def extract_all(
        self,
        folder: str,
        output_filename: str,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
        selected_files: Optional[List[str]] = None,
        cancel_event=None,
    ) -> tuple:
        """
        Point d'entrée principal.
        Retourne (success, py_count, json_count, txt_count, po_count, mo_count,
                  html_count, css_count, js_count)
        success est True (SUCCESS), False (FAILED) ou None (CANCELLED).
        """
        folder_path = Path(folder)
        output_path = Path(output_filename)

        selected_set = None
        if selected_files is not None:
            selected_set = set(Path(f).as_posix() for f in selected_files)

        context = ExtractionContext(
            folder_path=folder_path,
            options=self.options,
            output_path=output_path,
            selected_files=selected_set
        )

        engine = ExtractionEngine(context)
        if cancel_event is not None:
            engine.set_cancel_event(cancel_event)
        result = engine.run(progress_callback, log_callback)

        if result == SUCCESS:
            stats = context.stats
            return (
                True,
                stats.get('py', 0),
                stats.get('json', 0),
                stats.get('txt', 0),
                stats.get('po', 0),
                stats.get('mo', 0),
                stats.get('html', 0),
                stats.get('css', 0),
                stats.get('js', 0)
            )
        elif result == CANCELLED:
            return None, 0, 0, 0, 0, 0, 0, 0, 0
        else:
            return False, 0, 0, 0, 0, 0, 0, 0, 0