# src/i18n.py
import gettext
import re
from pathlib import Path
from src.config import get_config
from src.logger import setup_logger

logger = setup_logger(__name__)


class Translator:
    """Wrapper mutable pour la fonction de traduction avec support msgctxt."""

    def __init__(self):
        self._func = gettext.gettext
        self._context_catalog = {}  # {(context, message): translation}

    def __call__(self, message):
        return self._func(message)

    def pgettext(self, context: str, message: str) -> str:
        """Traduction avec contexte (msgctxt) - utilise le catalogue de contexte."""
        return self._context_catalog.get((context, message), message)

    def set_translation(self, func):
        """Change la fonction de traduction sous-jacente."""
        self._func = func

    def set_context_catalog(self, catalog: dict):
        """Définit le catalogue de traductions contextuelles."""
        self._context_catalog = catalog


class LazyString:
    """
    Chaîne traduite paresseusement - évaluée à CHAQUE affichAGE (str() ou format()).
    Permet le changement de langue à chaud sans redémarrer l'application.
    """
    __slots__ = ('_msgid', '_args', '_kwargs')

    def __init__(self, msgid: str, *args, **kwargs):
        self._msgid = msgid
        self._args = args
        self._kwargs = kwargs

    def __str__(self) -> str:
        translated = _(self._msgid)
        if self._args or self._kwargs:
            return translated.format(*self._args, **self._kwargs)
        return translated

    def __repr__(self) -> str:
        return f"LazyString({self._msgid!r})"

    def format(self, *args, **kwargs) -> 'LazyString':
        """Retourne un nouveau LazyString avec les arguments de formatage."""
        return LazyString(self._msgid, *args, **kwargs)

    # Pour compatibilité avec tkinter StringVar etc.
    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


class LazyStringContext:
    """
    Chaîne traduite paresseusement avec contexte (msgctxt).
    """
    __slots__ = ('_context', '_msgid', '_args', '_kwargs')

    def __init__(self, context: str, msgid: str, *args, **kwargs):
        self._context = context
        self._msgid = msgid
        self._args = args
        self._kwargs = kwargs

    def __str__(self) -> str:
        translated = pgettext(self._context, self._msgid)
        if self._args or self._kwargs:
            return translated.format(*self._args, **self._kwargs)
        return translated

    def __repr__(self) -> str:
        return f"LazyStringContext({self._context!r}, {self._msgid!r})"

    def format(self, *args, **kwargs) -> 'LazyStringContext':
        return LazyStringContext(self._context, self._msgid, *args, **kwargs)

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


# Instance globale unique
_ = Translator()


# Fonction de commodité pour pgettext
def pgettext(context: str, message: str) -> str:
    """Traduction avec contexte (msgctxt)."""
    return _.pgettext(context, message)


# Callbacks pour notification de changement de langue
_reload_callbacks: list[callable] = []


def _get_config():
    """Retourne la config actuelle (gère le reset du singleton)."""
    return get_config()


def _build_context_catalog(locale_dir: Path, lang: str) -> dict:
    """
    Construit un catalogue de traductions contextuelles depuis le fichier .po.
    Retourne un dict {(context, message): translation}.
    """
    catalog = {}
    po_path = locale_dir / lang / "LC_MESSAGES" / "messages.po"
    if not po_path.exists():
        return catalog

    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex pour extraire les entrées avec msgctxt
        # Format: msgctxt "context"\nmsgid "message"\nmsgstr "translation"
        pattern = r'msgctxt\s+"([^"]+)"\s*\nmsgid\s+"([^"]*)"(?:\s*\n\s*"([^"]*)")*\s*\nmsgstr\s+"([^"]*)"(?:\s*\n\s*"([^"]*)")*'
        matches = re.findall(pattern, content)

        for match in matches:
            context = match[0]
            # msgid peut être sur plusieurs lignes
            msgid_parts = [match[1]]
            if match[2]:
                msgid_parts.append(match[2])
            msgid = ''.join(msgid_parts)

            # msgstr peut être sur plusieurs lignes
            msgstr_parts = [match[3]]
            if match[4]:
                msgstr_parts.append(match[4])
            msgstr = ''.join(msgstr_parts)

            if msgstr:  # Seulement si traduction non vide
                catalog[(context, msgid)] = msgstr

    except Exception as e:
        logger.warning("Erreur lors du chargement du catalogue de contexte pour %s : %s", lang, e)

    return catalog


def setup_i18n():
    """Configure la traduction en fonction de la langue définie dans config."""
    lang = _get_config().get('language', 'fr')
    locale_dir = Path(__file__).parent.parent / "locale"

    try:
        translation = gettext.translation(
            'messages',
            localedir=locale_dir,
            languages=[lang],
            fallback=True
        )
        # Installe pour les appels builtins (gettext.install) si nécessaire
        translation.install()
        # Met à jour notre wrapper
        _.set_translation(translation.gettext)
        # Charge le catalogue de contexte
        _.set_context_catalog(_build_context_catalog(locale_dir, lang))
        logger.info("Traduction chargee pour la langue '%s'", lang)
    except Exception as e:
        logger.warning(
            "Traduction non disponible pour '%s', utilisation du fallback : %s", lang, e
        )
        # Installe le fallback
        gettext.install('messages', names=('ngettext',))
        _.set_translation(gettext.gettext)
        _.set_context_catalog({})

    return _


def reload_translations():
    """
    Recharge les traductions et notifie tous les callbacks enregistrés.
    Permet le changement de langue à chaud sans redémarrer l'application.
    """
    setup_i18n()
    for callback in _reload_callbacks:
        try:
            callback()
        except Exception as e:
            logger.error("Erreur dans callback de rechargement i18n : %s", e)


def register_reload_callback(callback: callable):
    """Enregistre un callback à appeler lors du changement de langue."""
    if callback not in _reload_callbacks:
        _reload_callbacks.append(callback)


def unregister_reload_callback(callback: callable):
    """Désenregistre un callback."""
    if callback in _reload_callbacks:
        _reload_callbacks.remove(callback)


def get_current_language():
    return _get_config().get('language', 'fr')


def change_language(lang_code: str):
    """
    Change la langue et recharge les traductions à chaud.
    Écrit dans config.json puis déclenche reload_translations().
    """
    config_path = Path(__file__).parent.parent / "config.json"
    import json
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['language'] = lang_code
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Recharger la config (le singleton Config doit être reset pour prendre en compte)
        from src.config import _Config
        _Config._reset_for_testing()

        # Recharger les traductions
        reload_translations()
        logger.info("Langue changee vers '%s'", lang_code)
        return True
    except Exception as e:
        logger.error("Impossible de changer la langue : %s", e)
        return False