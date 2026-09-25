# src/gui/network_center/services/file_transfer_service.py
from __future__ import annotations
import socket
import threading
from pathlib import Path
from dataclasses import dataclass
from hashlib import sha256
import hmac
from typing import Callable, Optional
from src.config import get_config
from src.logger import setup_logger
from src.network.protocol import CURRENT_VERSION, build_v1_header, write_v1_message

logger = setup_logger(__name__)


@dataclass
class TransferResult:
    success: bool
    error_message: str = ""
    hostname: str = ""


class FileTransferService:
    """Service d'envoi de fichier via socket TCP (protocole binaire avec auth)."""

    CHUNK_SIZE = 64 * 1024
    TIMEOUT = 10
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 Mo

    def __init__(self):
        self._cancel_event = threading.Event()
        # Config auth
        self.auth_enabled = get_config().get('network.auth_enabled', True)
        self.auth_token = get_config().get('network.auth_token', 'change-me-secure-random-token').encode('utf-8')
        self.port = get_config().get('network.server_port', 50000)

    def send_file(
        self,
        file_path: Path,
        peer_ip: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        result_callback: Optional[Callable[[TransferResult], None]] = None
    ) -> None:
        """Envoie un fichier en thread séparé."""
        self._cancel_event.clear()
        thread = threading.Thread(
            target=self._send_worker,
            args=(file_path, peer_ip, progress_callback, result_callback),
            daemon=True
        )
        thread.start()

    def cancel(self):
        self._cancel_event.set()

    def _generate_auth_token(self) -> bytes:
        """Génère le token HMAC attendu par le serveur."""
        return hmac.new(self.auth_token, b'PYEXTRACTOR_AUTH', 'sha256').digest()

    def _send_worker(
        self,
        file_path: Path,
        peer_ip: str,
        progress_callback: Optional[Callable[[int, int], None]],
        result_callback: Optional[Callable[[TransferResult], None]]
    ):
        sock = None
        try:
            total_size = file_path.stat().st_size
            if total_size > self.MAX_FILE_SIZE:
                raise ValueError("Fichier trop volumineux (>100Mo)")

            filename = file_path.name

            # Connexion
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.TIMEOUT)
            sock.connect((peer_ip, self.port))

            # Construire le payload v0 (format legacy)
            v0_payload = self._build_v0_payload(filename, total_size, file_path, progress_callback)

            # Essayer d'abord le protocole v1
            if self._try_send_v1(sock, v0_payload):
                if result_callback:
                    result_callback(TransferResult(success=True, hostname=peer_ip))
                return

            # Fallback v0 : le serveur n'a pas compris v1
            # IMPORTANT : ne pas réutiliser la socket polluée par le magic v1 partiel
            # → ouvrir une nouvelle connexion pour v0
            logger.info("Fallback vers protocole v0 pour %s (nouvelle connexion)", peer_ip)
            try:
                sock.close()
            except OSError:
                pass
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.TIMEOUT)
            sock.connect((peer_ip, self.port))
            if self._send_v0(sock, v0_payload, progress_callback):
                if result_callback:
                    result_callback(TransferResult(success=True, hostname=peer_ip))
            else:
                self._notify_error(result_callback, "Échec de l'envoi (protocole non supporté)")

        except socket.timeout:
            self._notify_error(result_callback, "Le serveur distant ne répond pas (timeout)")
        except ConnectionRefusedError:
            self._notify_error(result_callback, "Le serveur distant a refusé la connexion")
        except Exception as e:
            logger.error(f"Erreur envoi : {e}")
            self._notify_error(result_callback, f"Échec de l'envoi : {e}")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    def _build_v0_payload(self, filename: str, total_size: int, file_path: Path,
                          progress_callback: Optional[Callable[[int, int], None]]) -> bytes:
        """Construit le payload complet au format v0 (sans l'enveloppe v1)."""
        auth_token = self._generate_auth_token() if self.auth_enabled else b''
        name_bytes = filename.encode('utf-8')

        # Collecter les chunks du fichier pour le hash
        hasher = sha256()
        file_chunks = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                file_chunks.append(chunk)
                hasher.update(chunk)
                if progress_callback:
                    progress_callback(hasher.digest().__sizeof__(), total_size)  # approximation

        # Construire le payload v0
        parts = []
        if self.auth_enabled:
            parts.append(len(auth_token).to_bytes(2, 'big'))
            parts.append(auth_token)
        parts.append(len(name_bytes).to_bytes(4, 'big'))
        parts.append(name_bytes)
        parts.append(total_size.to_bytes(8, 'big'))
        parts.extend(file_chunks)
        parts.append(hasher.digest())

        return b''.join(parts)

    def _try_send_v1(self, sock: socket.socket, v0_payload: bytes) -> bool:
        """Tente d'envoyer via protocole v1. Retourne True si succès."""
        try:
            # write_v1_message envoie déjà le magic complet dans l'en-tête
            return write_v1_message(sock, v0_payload, self.auth_enabled)
        except Exception:
            logger.debug("Échec envoi protocole v1, fallback v0", exc_info=True)
            return False

    def _send_v0(self, sock: socket.socket, v0_payload: bytes,
                 progress_callback: Optional[Callable[[int, int], None]]) -> bool:
        """Envoie le payload v0 brut (fallback)."""
        try:
            sock.sendall(v0_payload)
            return True
        except Exception:
            logger.debug("Échec envoi protocole v0", exc_info=True)
            return False

    def _notify_error(self, callback: Optional[Callable[[TransferResult], None]], msg: str):
        if callback:
            callback(TransferResult(success=False, error_message=msg))