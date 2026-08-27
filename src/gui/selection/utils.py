# src/gui/selection/utils.py
from src.utils import human_size

def get_allowed_extensions(options):
    """Retourne la liste des extensions autorisées selon les options.
    
    Args:
        options: Dictionnaire ou objet contenant les flags d'inclusion.
                 Accepte soit un dict (depuis BaseController.get_include_options)
                 soit un objet ExtractionOptions (depuis le moteur principal).
    """
    # Gérer les deux types d'entrée (dict ou objet Pydantic)
    def get_opt(key, default):
        if isinstance(options, dict):
            return options.get(key, default)
        return getattr(options, key, default)

    extensions = ['.py']
    if get_opt('include_json', True):
        extensions.append('.json')
    if get_opt('include_txt', False):
        extensions.append('.txt')
    if get_opt('include_po', False):
        extensions.append('.po')
    if get_opt('include_mo', False):
        extensions.append('.mo')
    if get_opt('include_html', True):
        extensions.extend(['.html', '.htm'])
    if get_opt('include_css', True):
        extensions.append('.css')
    if get_opt('include_js', True):
        extensions.append('.js')
    return extensions

def format_size(size_bytes):
    """Retourne la taille formatée via human_size."""
    return human_size(size_bytes) if size_bytes >= 0 else "?"