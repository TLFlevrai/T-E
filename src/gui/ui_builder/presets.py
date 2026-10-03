# src/gui/ui_builder/presets.py
from __future__ import annotations

from typing import Any

from .ui_widgets import EXTRA_EXT_CHOICES

# Ensemble des extensions proposées par l'onglet « Extensions avancées ».
# Dérivé d'EXTRA_EXT_CHOICES : un preset « Complet » reste donc cohérent dès
# qu'une extension y est ajoutée, sans réécrire des listes à la main.
ALL_EXTRA_EXTENSIONS: tuple[str, ...] = tuple(
    ext for _attr, exts, _label in EXTRA_EXT_CHOICES for ext in exts
)

# Presets d'export partagés par le menu Options et l'onglet Avancé.
# `extra_extensions` est réinjecté à l'application : il cible un ensemble de
# cases à cocher, pas une simple variable booléenne.
_PRESETS: dict[str, dict[str, Any]] = {
    'python_only': {
        'include_json': False, 'include_html': False, 'include_css': False,
        'include_js': False, 'include_txt': False, 'include_md': False,
        'include_po': False, 'include_mo': False,
        'include_structure': True,
        'extra_extensions': [],
    },
    'web_assets': {
        'include_json': True, 'include_html': True, 'include_css': True,
        'include_js': True, 'include_txt': False, 'include_md': True,
        'include_po': False, 'include_mo': False,
        'include_structure': True,
        'extra_extensions': [],
    },
    'full': {
        'include_json': True, 'include_html': True, 'include_css': True,
        'include_js': True, 'include_txt': True, 'include_md': True,
        'include_po': True, 'include_mo': True,
        'include_structure': True,
        'include_statistics': True, 'include_file_metadata': True,
        'extra_extensions': list(ALL_EXTRA_EXTENSIONS),
    },
    'minimal': {
        'include_json': False, 'include_html': False, 'include_css': False,
        'include_js': False, 'include_txt': False, 'include_md': False,
        'include_po': False, 'include_mo': False,
        'include_structure': True, 'include_statistics': True,
        'extra_extensions': [],
    },
}


def preset_options(preset: str) -> dict[str, Any]:
    """Retourne une copie des valeurs d'options associées à un preset.

    `extra_extensions` est recopié : le caller (UI) peut le modifier sans
    corrompre le preset d'origine.
    """
    values = _PRESETS.get(preset)
    if values is None:
        return {}
    result = dict(values)
    result['extra_extensions'] = list(values.get('extra_extensions', []))
    return result
