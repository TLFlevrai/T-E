# src/extractor/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict
from src.config import ExtractionOptions


@dataclass
class ExtractionContext:
    """Contexte partagé lors d'une extraction."""
    folder_path: Path
    options: ExtractionOptions
    output_path: Path
    selected_files: Optional[set] = None

    # Compteurs (seront remplis par le file_processor)
    stats: Dict[str, int] = field(default_factory=lambda: {
        'py': 0, 'json': 0, 'txt': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    })
    line_counts: Dict[str, int] = field(default_factory=lambda: {
        'py': 0, 'json': 0, 'txt': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    })
    total_size: int = 0
    processed_files: int = 0