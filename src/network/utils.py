# src/network/utils.py
from __future__ import annotations
import socket

def get_local_ip() -> str:
    """Retourne l'adresse IP locale utilisée pour les connexions sortantes."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'