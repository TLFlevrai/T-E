# src/network/protocol.py
"""Protocole réseau T-E avec versioning.

Format v0 (legacy) :
  [auth_len:2][auth_token:N][name_len:4][name:N][data_size:8][data:N][hash:32]

Format v1 (avec magic + version) :
  [magic:4=b'TE01'][version:1][flags:1][payload_len:8][payload]
  payload = format v0 ci-dessus
"""
from __future__ import annotations
import struct
from typing import Optional, Tuple

from src.logger import setup_logger

logger = setup_logger(__name__)

PROTOCOL_MAGIC = b'TE01'
CURRENT_VERSION = 1

# Flags
FLAG_AUTH_ENABLED = 0x01
FLAG_COMPRESSION = 0x02  # Futur


def build_v1_header(payload_len: int, auth_enabled: bool = True, compression: bool = False) -> bytes:
    """Construit l'en-tête v1 (magic + version + flags + payload_len)."""
    flags = 0
    if auth_enabled:
        flags |= FLAG_AUTH_ENABLED
    if compression:
        flags |= FLAG_COMPRESSION
    return struct.pack('>4sBBQ', PROTOCOL_MAGIC, CURRENT_VERSION, flags, payload_len)


def parse_v1_header(header: bytes) -> Optional[Tuple[int, int, int]]:
    """Parse l'en-tête v1.
    
    Returns:
        (version, flags, payload_len) ou None si invalide
    """
    if len(header) != 14:
        return None
    magic, version, flags, payload_len = struct.unpack('>4sBBQ', header)
    if magic != PROTOCOL_MAGIC:
        return None
    return version, flags, payload_len


def is_v1_protocol(first_bytes: bytes) -> bool:
    """Vérifie si les premiers octets correspondent au magic v1."""
    return first_bytes.startswith(PROTOCOL_MAGIC)


def read_v1_message(conn, timeout: float = 5.0) -> Optional[bytes]:
    """Lit un message complet v1 depuis la connexion.
    
    Returns:
        payload complet (format v0) ou None si erreur/timeout
    """
    import socket
    original_timeout = conn.gettimeout()
    try:
        conn.settimeout(timeout)
        # Lire l'en-tête v1 (14 bytes)
        header = b''
        while len(header) < 14:
            chunk = conn.recv(14 - len(header))
            if not chunk:
                return None
            header += chunk
        
        parsed = parse_v1_header(header)
        if parsed is None:
            return None
        version, flags, payload_len = parsed
        
        if version != CURRENT_VERSION:
            # Version future non supportée
            return None
        
        if payload_len > 200 * 1024 * 1024:  # 200 Mo max
            return None
        
        # Lire le payload
        payload = b''
        while len(payload) < payload_len:
            chunk = conn.recv(min(65536, payload_len - len(payload)))
            if not chunk:
                return None
            payload += chunk
        
        return payload
    except socket.timeout:
        return None
    except Exception:
        logger.debug("Erreur lecture payload v1", exc_info=True)
        return None
    finally:
        try:
            conn.settimeout(original_timeout)
        except Exception:
            logger.debug("Erreur restauration timeout socket", exc_info=True)


def write_v1_message(conn, payload: bytes, auth_enabled: bool = True) -> bool:
    """Écrit un message complet v1 sur la connexion."""
    import socket
    original_timeout = conn.gettimeout()
    try:
        conn.settimeout(10.0)
        header = build_v1_header(len(payload), auth_enabled)
        conn.sendall(header)
        conn.sendall(payload)
        return True
    except Exception:
        logger.debug("Erreur écriture message v1", exc_info=True)
        return False
    finally:
        try:
            conn.settimeout(original_timeout)
        except Exception:
            logger.debug("Erreur restauration timeout socket", exc_info=True)