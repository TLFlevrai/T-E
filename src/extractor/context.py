# src/extractor/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict
from src.config import ExtractionOptions

# Extensions ayant une ligne dédiée dans la section STATISTIQUES du rapport.
# Tout ce qui n'est pas dans cette liste est regroupé sous « Autres
# extensions » (extractions via `extra_extensions`).
CLASSIC_STAT_KEYS = (
    'py', 'json', 'txt', 'md', 'po', 'mo',
    'html', 'css', 'js',
)

# Extensions synonymes fusionnées dans un compteur unique.
# Sans cela, un projet contenant `ci.yml` ET `values.yaml` afficherait deux
# lignes « Fichiers YAML : 1 » dans le rapport : le libellé est identique
# (FILE_TYPES), donc la duplication n'apporte aucune information et donne
# l'impression d'un bug. Une extension absente de cette table reste comptée
# sous son propre nom.
STAT_KEY_ALIASES = {
    'yml': 'yaml',      # .yaml et .yml → « YAML »
    'cfg': 'ini',       # .ini, .cfg, .conf → « INI »
    'conf': 'ini',
    'htm': 'html',      # .html, .htm → « HTML »
}


def stat_key_for_ext(ext: str) -> str:
    """Clé de compteur correspondant à une extension.

    Applique les synonymes (cf. STAT_KEY_ALIASES) pour que le rapport
    regroupe ce qui est affiché sous un même libellé.
    """
    key = ext.lstrip('.')
    return STAT_KEY_ALIASES.get(key, key)


@dataclass
class ExtractionContext:
    """Contexte partagé lors d'une extraction."""
    folder_path: Path
    options: ExtractionOptions
    output_path: Path
    selected_files: Optional[set] = None

    # Compteurs (seront remplis par le file_processor)
    stats: Dict[str, int] = field(default_factory=lambda: {
        'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    })
    line_counts: Dict[str, int] = field(default_factory=lambda: {
        'py': 0, 'json': 0, 'txt': 0, 'md': 0, 'po': 0, 'mo': 0,
        'html': 0, 'css': 0, 'js': 0
    })
    total_size: int = 0
    processed_files: int = 0
    # FIX BUG #12 : compteurs de dossiers/packages calculés lors du parcours de structure
    num_dirs: int = 0
    num_packages: int = 0

    def ensure_stat_key(self, key: str) -> None:
        """Déclare dynamiquement une clé de compteur (extensions
        supplémentaires). Sans cela, `_update_stats` ignorerait les fichiers
        dont l'extension n'a pas de compteur prédéfini."""
        if key not in self.stats:
            self.stats[key] = 0
        if key not in self.line_counts:
            self.line_counts[key] = 0

    def extra_stat_keys(self) -> list[str]:
        """Clés de compteur hors extensions classiques, triées pour un
        rapport stable d'une extraction à l'autre."""
        return sorted(k for k in self.stats if k not in CLASSIC_STAT_KEYS)
