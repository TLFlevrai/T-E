# src/extractor/content_formatter.py
from __future__ import annotations
import json

def format_json_content(content, file_path=None):
    """Essaie de formater joliment le contenu JSON.
       En cas d'échec, retourne le contenu brut précédé d'un commentaire d'erreur.
    """
    try:
        json_data = json.loads(content)
        return json.dumps(json_data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"// ERREUR: JSON invalide - {str(e)}\n{content}"