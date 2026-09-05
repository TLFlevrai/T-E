# src/gui/network_center/services/file_transfer_service.py
from __future__ import annotations
import socket
import threading
from pathlib import Path
from dataclasses import dataclass
from hashlib import sha256
import hmac
from typing import Callable, Optional
from src.config import config
from src.logger import setup_logger

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
        self.auth_enabled = config.get('network.auth_enabled', True)
        self.auth_token = config.get('network.auth_token', 'change-me-secure-random-token').encode('utf-8')
        self.port = config.get('network.server_port', 50000)

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

            # 1. ENVOI AUTH TOKEN (si activé)
            if self.auth_enabled:
                auth_token = self._generate_auth_token()
                sock.sendall(len(auth_token).to_bytes(2, 'big'))
                sock.sendall(auth_token)

            # 2. Envoi header: nom (4 bytes len + bytes) + taille (8 bytes)
            name_bytes = filename.encode('utf-8')
            sock.sendall(len(name_bytes).to_bytes(4, 'big'))
            sock.sendall(name_bytes)
            sock.sendall(total_size.to_bytes(8, 'big'))

            # 3. Envoi données par chunks (hash incrémental, sans charger le fichier en RAM)
            hasher = sha256()
            sent = 0
            with open(file_path, 'rb') as f:
                while sent < total_size and not self._cancel_event.is_set():
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    hasher.update(chunk)
                    sent += len(chunk)
                    if progress_callback:
                        progress_callback(sent, total_size)

            if self._cancel_event.is_set():
                raise InterruptedError("Transfert annulé")

            # 4. Envoi hash
            sock.sendall(hasher.digest())

            if result_callback:
                result_callback(TransferResult(success=True, hostname=peer_ip))

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

    def _notify_error(self, callback: Optional[Callable[[TransferResult], None]], msg: str):
        if callback:
            callback(TransferResult(success=False, error_message=msg))