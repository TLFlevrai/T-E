# src/config/__init__.py
from __future__ import annotations
import json
import threading
from pathlib import Path
from .schema import AppConfig, ExtractionOptions, NetworkConfig, GuiConfig

from src.logger import setup_logger
logger = setup_logger(__name__)

__all__ = ['AppConfig', 'ExtractionOptions', 'NetworkConfig', 'GuiConfig', 'get_config']

# Chemin vers config.json à la racine du projet
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"


class _Config:
    """Chargeur de configuration centralisé (Singleton thread-safe)."""
    
    _instance = None
    _config: AppConfig = None
    _lock = threading.Lock()  # Verrou de classe pour l'initialisation

    def __new__(cls):
        # Premier check SANS verrou (performance chemin normal)
        if cls._instance is not None:
            return cls._instance
        
        # Verrou pour la création réelle
        with cls._lock:
            # Double-check APRÈS avoir acquis le verrou
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._load()  # Initialisation protégée
        return cls._instance

    @classmethod
    def _load(cls):
        """Charge la configuration depuis config.json ou utilise les valeurs par défaut.
        
        Appelée UNE SEULE FOIS sous verrou lors de la première instanciation.
        """
        default = AppConfig()
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cls._config = AppConfig(**data)
                logger.info("Configuration chargee depuis %s", CONFIG_PATH)
            except Exception as e:
                logger.error("Erreur de chargement de config.json : %s", e)
                logger.info("Utilisation des valeurs par defaut")
                cls._config = default
        else:
            logger.info("Fichier %s non trouve, utilisation des valeurs par defaut", CONFIG_PATH)
            cls._config = default

    def get(self, key: str, default=None):
        """
        Récupère une valeur par chemin pointé (ex: 'network.server_port').
        
        Args:
            key: Chemin pointé (ex: 'extraction.include_json')
            default: Valeur par défaut si la clé n'existe pas
        
        Returns:
            La valeur configurée ou default
        """
        # Lecture sans verrou : _config est immuable après _load()
        keys = key.split('.')
        value = self._config
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        return value

    def get_all(self) -> AppConfig:
        """Retourne l'objet AppConfig complet (immuable)."""
        return self._config

    def save(self) -> bool:
        """Sauvegarde la configuration actuelle dans config.json."""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Erreur de sauvegarde de config.json : %s", e)
            return False

    def update_gui(self, **kwargs) -> bool:
        """Met à jour les options GUI et sauvegarde."""
        gui = self._config.gui
        for key, value in kwargs.items():
            if hasattr(gui, key):
                setattr(gui, key, value)
        return self.save()

    # --- Pour tests : reset contrôlé (optionnel) ---
    @classmethod
    def _reset_for_testing(cls):
        """Réinitialise le singleton (UNIQUEMENT pour tests unitaires)."""
        with cls._lock:
            cls._instance = None
            cls._config = None


def get_config() -> _Config:
    """Retourne l'instance singleton de configuration (toujours à jour après reset)."""
    return _Config()


# Pour compatibilité - déprécié, utiliser get_config()
class _ConfigProxy:
    def __getattr__(self, name):
        return getattr(get_config(), name)

config = _ConfigProxy()