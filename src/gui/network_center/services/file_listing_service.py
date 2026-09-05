# src/gui/network_center/services/file_listing_service.py
from __future__ import annotations
from pathlib import Path
from typing import List
from ..models import FileItem
from src.logger import setup_logger

logger = setup_logger(__name__)


class FileListingService:
    """Service de listage des fichiers envoyables (.txt dans out/)."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def list_files(self) -> List[FileItem]:
        """Retourne la liste des fichiers .txt triés par nom."""
        items = []
        try:
            for file_path in self.output_dir.rglob('*.txt'):
                if file_path.is_file():
                    display = str(file_path.relative_to(self.output_dir))
                    items.append(FileItem(
                        display_name=display,
                        full_path=file_path,
                        size=file_path.stat().st_size
                    ))
            items.sort(key=lambda x: x.display_name)
        except Exception as e:
            logger.error(f"Erreur listage fichiers : {e}")
        return items