# src/network/utils.py
from __future__ import annotations
import socket

from src.logger import setup_logger

logger = setup_logger(__name__)

def get_local_ip() -> str:
    """Retourne l'adresse IP locale utilisée pour les connexions sortantes."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        logger.debug("Impossible de déterminer l'IP locale, fallback 127.0.0.1", exc_info=True)
        return '127.0.0.1'