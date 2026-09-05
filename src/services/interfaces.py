# src/services/interfaces.py
"""
Interfaces (Protocoles) pour l'inversion de dépendances.
Permet de découpler les services de leurs implémentations concrètes.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Callable, Protocol, Tuple

# Signature de callback de progression : (fichier courant, total, nom relatif)
ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


class ICodeExtractor(Protocol):
    """Protocole pour l'extracteur de code."""
    
    def find_files(self, folder: str) -> List[Tuple[Path, Path, str]]:
        """Retourne la liste des fichiers découvrables."""
        ...
    
    def generate_project_structure(self, folder: str) -> str:
        """Génère la structure arborescente du projet."""
        ...
    
    def extract_all(
        self,
        folder: str,
        output_filename: str,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
        selected_files: Optional[List[str]] = None,
        cancel_event=None,
    ) -> Tuple[Optional[bool], int, int, int, int, int, int, int, int]:
        """
        Extrait tous les fichiers.
        Retourne (success, py_count, json_count, txt_count, po_count, mo_count,
                  html_count, css_count, js_count)
        success : True (ok), False (échec) ou None (annulé).
        """
        ...


class IVersionManager(Protocol):
    """Protocole pour la gestion des versions."""
    
    def get_next_version(self, folder_name: str, output_dir: Path) -> int:
        """Retourne le prochain numéro de version disponible."""
        ...
    
    def use_version(self, folder_name: str, version: int) -> None:
        """Marque une version comme utilisée."""
        ...
    
    def reset(self) -> None:
        """Réinitialise tout l'historique."""
        ...
    
    def reset_project(self, folder_name: str) -> None:
        """Réinitialise le compteur pour un projet spécifique."""
        ...


class IExtractionService(Protocol):
    """Protocole pour le service d'extraction (couche use-case)."""
    
    def extract_folder(
        self,
        folder_path: str | Path,
        options: dict,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
        selected_files: Optional[List[str]] = None,
        cancel_event=None,
    ) -> Tuple[Optional[bool], Optional[str], Optional[dict]]:
        """
        Exécute l'extraction complète.
        Retourne (success, output_filename, stats_dict)
        success : True (ok), False (échec) ou None (annulé).
        """
        ...
    
    def clean_versions(self, archive: bool = False) -> str:
        """Nettoie l'historique des versions."""
        ...