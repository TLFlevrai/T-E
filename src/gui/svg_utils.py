# src/gui/svg_utils.py
"""Rendu d'images SVG vers PIL avec resvg (aucune dépendance native requise)."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path

from PIL import Image


class SVGError(RuntimeError):
    """Erreur lors du rendu d'un fichier SVG."""


def svg_to_pil(svg_path, size: int | None = None) -> Image.Image:
    """Rend un fichier SVG en image PIL (RGBA).

    Utilise resvg (binaire autonome) pour rasteriser le SVG.
    ``size`` force la plus grande dimension de sortie en pixels.
    """
    try:
        from resvg_py import svg_to_bytes
    except ImportError as exc:  # pragma: no cover - dépendance manquante
        raise SVGError(
            "Le rendu SVG nécessite le paquet 'resvg-py' (pip install resvg-py)"
        ) from exc

    path = str(svg_path)
    kwargs = {"svg_path": path, "background": None}
    if size:
        kwargs["width"] = size
        kwargs["height"] = size
    try:
        png = svg_to_bytes(**kwargs)
    except Exception as exc:
        raise SVGError(f"Impossible de rendre le SVG : {exc}") from exc

    try:
        return Image.open(BytesIO(png)).convert("RGBA")
    except Exception as exc:
        raise SVGError(f"Impossible de décoder le rendu SVG : {exc}") from exc


def svg_to_ico(svg_path, ico_path, sizes) -> None:
    """Convertit un SVG en fichier ICO multi-tailles.

    La première image passée à Pillow doit être la plus grande taille,
    sinon les tailles supérieures sont ignorées par l'encodeur ICO.
    """
    sizes = sorted({int(s) for s in sizes if int(s) > 0}, reverse=True)
    if not sizes:
        raise SVGError("Aucune taille valide fournie")

    base = svg_to_pil(svg_path, size=sizes[0])
    images = [base.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:],
    )