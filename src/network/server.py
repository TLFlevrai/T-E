# src/network/server.py
from __future__ import annotations
import socket
import threading
import re
import os
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import hmac
from src.logger import setup_logger
from src.config import get_config
from src.network.protocol import is_v1_protocol, read_v1_message

logger = setup_logger(__name__)

# Timeout appliqué aux connexions clientes une fois acceptées.
# Le socket d'écoute garde son propre timeout court (pour vérifier _stop_event),
# mais il ne doit PAS être hérité par les transferts (sinon tout stall > 1s
# interromprait un transfert légitime).
CLIENT_TIMEOUT = 30.0

# Nouveaux timeouts pour résistance connexions lentes
HEADER_TIMEOUT = 5.0          # Timeout lecture auth + filename + size
DATA_TIMEOUT = 300.0          # Timeout global transfert (5 min pour 100Mo)

# Noms de périphériques réservés Windows (con, prn, aux, nul, com1-9, lpt1-9)
_WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    *(f'COM{i}' for i in range(1, 10)),
    *(f'LPT{i}' for i in range(1, 10)),
}


def recv_exact(conn: socket.socket, n: int) -> bytes:
    """Lit exactement n octets depuis le socket.

    TCP est un flux : un seul recv(n) peut retourner moins de n octets.
    Cette boucle garantit la lecture complète ou l'échec (connexion fermée).
    """
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


class ReceiveServer(threading.Thread):
    MAX_FILENAME_LEN = 255
    MAX_FILE_SIZE = 100 * 1024 * 1024
    # Extensions par défaut, surchargées par config
    DEFAULT_ALLOWED_EXTENSIONS = {'.txt'}

    def __init__(self, host=None, port=None, received_dir=None, max_workers=10, on_event=None):
        super().__init__(daemon=True)
        cfg = get_config()
        self.host = host or cfg.get('network.server_host', '127.0.0.1')
        self.port = port or cfg.get('network.server_port', 50000)

        output_dir = Path(cfg.get('output_dir', 'out'))
        received_subdir = cfg.get('received_subdir', 'received')
        self.received_dir = (received_dir or output_dir / received_subdir)

        # Auth config
        self.auth_enabled = cfg.get('network.auth_enabled', True)
        self.auth_token = str(cfg.get('network.auth_token', 'change-me-secure-random-token')).strip().encode('utf-8')
        # Normalisation : les comparaisons se font en minuscules côté serveur,
        # la config doit donc être normalisée ici ('.TXT' et '.txt' doivent marcher)
        raw_extensions = cfg.get('network.allowed_extensions', ['.txt']) or ['.txt']
        self.allowed_extensions = {str(e).strip().lower() for e in raw_extensions}

        if self.auth_enabled and self.auth_token == b'change-me-secure-random-token':
            logger.warning("[WARN] TOKEN D'AUTHENTIFICATION PAR DEFAUT DETECTE ! Changez 'auth_token' dans config.json")

        # Timeouts pour résistance connexions lentes
        self.header_timeout = HEADER_TIMEOUT
        self.data_timeout = DATA_TIMEOUT

        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ServerWorker")
        self._observers = []
        if on_event:
            self._observers.append(on_event)

    def add_observer(self, callback):
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback):
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify(self, event_type, data=None):
        for cb in list(self._observers):
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error("Erreur dans un observateur : %s", e)

    @staticmethod
    def _sanitize_filename(raw_filename: str) -> str:
        """Nettoie un nom de fichier reçu du réseau.

        - ne conserve que le nom (protection traversée de chemin) ;
        - remplace les caractères non sûrs ;
        - borne la longueur ;
        - neutralise les noms de périphériques réservés Windows.
        """
        filename = Path(raw_filename).name
        if not filename or filename in {'.', '..'}:
            return ''
        filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        if filename.startswith('.'):
            filename = '_' + filename
        stem = Path(filename).stem.upper()
        if stem in _WINDOWS_RESERVED:
            filename = '_' + filename
        if len(filename) > ReceiveServer.MAX_FILENAME_LEN:
            filename = filename[:ReceiveServer.MAX_FILENAME_LEN]
        return filename

    def run(self):
        # Sécurité : refuser d'exposer le serveur hors de la machine locale avec
        # le token public connu (le canal n'est pas chiffré, l'auth serait décorative).
        is_localhost = self.host in {'127.0.0.1', 'localhost', '::1'}
        is_default_token = self.auth_token == b'change-me-secure-random-token'

        if not is_localhost and self.auth_enabled and is_default_token:
            msg = (
                "Refus de démarrer le serveur sur %s : le jeton d'authentification "
                "par défaut est public. Définissez un 'network.auth_token' unique dans "
                "config.json avant d'écouter sur une interface non locale." % self.host
            )
            logger.error(msg)
            self._notify('start_failed', {'error': msg})
            return

        # Avertissement explicite pour écoute LAN (non-localhost) avec token custom
        if not is_localhost and self.auth_enabled and not is_default_token:
            warning_msg = (
                "⚠ Écoute sur interface non-locale (%s:%s) : le trafic n'est PAS chiffré. "
                "Utilisez un VPN ou tunnel SSH pour réseaux non de confiance." % (self.host, self.port)
            )
            logger.warning(warning_msg)
            # Notifier l'UI pour afficher l'avertissement (évite de créer un 2e Tk)
            self._notify('lan_warning', {'message': warning_msg})

        try:
            self.received_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Impossible de créer le dossier de réception : %s", e)
            self._notify('start_failed', {'error': str(e)})
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind((self.host, self.port))
                server_socket.listen(5)
                server_socket.settimeout(1.0)
                logger.info("Serveur démarré sur %s:%s (auth=%s)", self.host, self.port, 'ON' if self.auth_enabled else 'OFF')
                self._notify('started', {'host': self.host, 'port': self.port})
            except Exception as e:
                logger.error("Impossible de démarrer le serveur : %s", e)
                self._notify('start_failed', {'error': str(e)})
                return

            accept_errors = 0
            while not self._stop_event.is_set():
                try:
                    conn, addr = server_socket.accept()
                except socket.timeout:
                    continue
                except OSError as e:
                    # Erreur transitoire (ex: EMFILE) : on logue et on continue,
                    # sauf si le socket est fermé (arrêt volontaire).
                    accept_errors += 1
                    logger.error("Erreur accept (%d) : %s", accept_errors, e)
                    if accept_errors >= 50 or server_socket.fileno() < 0:
                        break
                    continue
                accept_errors = 0
                conn.settimeout(CLIENT_TIMEOUT)
                self._executor.submit(self._handle_client, conn, addr)

            logger.info("Serveur arrêté")

    def _handle_client(self, conn, addr):
        try:
            # D'abord, lire les premiers 4 octets pour détecter le protocole
            conn.settimeout(self.header_timeout)
            first_bytes = b''
            while len(first_bytes) < 4:
                chunk = conn.recv(4 - len(first_bytes))
                if not chunk:
                    logger.warning("Connexion fermée par %s avant détection protocole", addr)
                    self._notify('rejected', {'reason': 'no_protocol', 'addr': addr})
                    return
                first_bytes += chunk
            
            # Vérifier si c'est le protocole v1 (magic TE01)
            if is_v1_protocol(first_bytes):
                # Protocole v1 : lire le message complet (header + payload)
                from src.network.protocol import read_v1_message
                payload = read_v1_message(conn, timeout=self.header_timeout)
                if payload is None:
                    logger.warning("Échec lecture message v1 de %s", addr)
                    self._notify('rejected', {'reason': 'invalid_v1_message', 'addr': addr})
                    return
                
                # Traiter le payload comme du v0 (via un socket-like wrapper)
                from io import BytesIO
                payload_stream = BytesIO(payload)
                
                def recv_from_payload(n):
                    return payload_stream.read(n)
                
                self._process_v0_payload(recv_from_payload, addr)
            else:
                # Protocole v0 legacy : first_bytes contient [auth_len:2][premiers octets auth_token]
                # On doit reconstruire le flux v0 complet
                from io import BytesIO
                legacy_stream = BytesIO(first_bytes)
                
                def recv_from_legacy(n):
                    data = legacy_stream.read(n)
                    if len(data) < n:
                        more = conn.recv(n - len(data))
                        if not more and len(data) < n:
                            # Connexion fermée
                            return data
                        data += more
                    return data
                
                self._process_v0_payload(recv_from_legacy, addr)

        except socket.timeout:
            logger.warning("Timeout connexion avec %s", addr)
            self._notify('rejected', {'reason': 'timeout', 'addr': addr})
        except Exception as e:
            logger.error("Erreur inattendue avec %s : %s", addr, e)
            self._notify('rejected', {'reason': 'exception', 'error': str(e), 'addr': addr})
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _process_v0_payload(self, recv_fn, addr):
        """Traite un payload au format v0 (legacy).
        
        Args:
            recv_fn: fonction(n) -> bytes, comme recv_exact mais source flexible
            addr: adresse du client pour logs
        """
        # Appliquer timeout pour les headers (auth + filename + size)
        # Note: on ne peut pas faire conn.settimeout ici car recv_fn peut être un BytesIO
        # Le timeout est géré au niveau appelant

        # 1. AUTHENTIFICATION (avant tout traitement)
        if self.auth_enabled:
            try:
                # Lire la taille du token (2 bytes)
                token_len_bytes = recv_fn(2)
                if len(token_len_bytes) != 2:
                    logger.warning("Auth incomplète (token_len) de %s", addr)
                    self._notify('rejected', {'reason': 'auth_failed', 'addr': addr})
                    return
                token_len = int.from_bytes(token_len_bytes, 'big')

                if token_len > 1024:  # Protection DoS
                    logger.warning("Token trop long (%d) de %s", token_len, addr)
                    self._notify('rejected', {'reason': 'auth_failed', 'addr': addr})
                    return

                # Lire le token client
                client_token = recv_fn(token_len)
                if len(client_token) != token_len:
                    logger.warning("Token incomplet de %s", addr)
                    self._notify('rejected', {'reason': 'auth_failed', 'addr': addr})
                    return

                # Vérification HMAC en temps constant
                expected = hmac.new(self.auth_token, b'PYEXTRACTOR_AUTH', 'sha256').digest()
                if not hmac.compare_digest(client_token, expected):
                    logger.warning("Authentification échouée pour %s", addr)
                    self._notify('rejected', {'reason': 'auth_failed', 'addr': addr})
                    return

            except Exception as e:
                logger.warning("Erreur auth de %s : %s", addr, e)
                self._notify('rejected', {'reason': 'auth_failed', 'addr': addr})
                return

        # 2. Lecture nom fichier
        name_size_bytes = recv_fn(4)
        if len(name_size_bytes) != 4:
            logger.warning("Connexion fermée par %s avant le nom", addr)
            self._notify('rejected', {'reason': 'no_name', 'addr': addr})
            return
        name_size = int.from_bytes(name_size_bytes, 'big')
        if name_size > 1024:
            logger.warning("Nom trop long (%d) de %s", name_size, addr)
            self._notify('rejected', {'reason': 'name_too_long', 'addr': addr})
            return

        try:
            raw_filename = recv_fn(name_size).decode('utf-8')
        except UnicodeDecodeError:
            logger.warning("Nom illisible (UTF-8 invalide) de %s", addr)
            self._notify('rejected', {'reason': 'invalid_name', 'addr': addr})
            return

        filename = self._sanitize_filename(raw_filename)
        if not filename:
            logger.warning("Nom vide de %s", addr)
            self._notify('rejected', {'reason': 'empty_name', 'addr': addr})
            return

        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            logger.warning("Extension non autorisée '%s' de %s", ext, addr)
            self._notify('rejected', {'reason': 'extension_not_allowed', 'filename': filename, 'addr': addr})
            return

        # 3. Taille des données
        data_size_bytes = recv_fn(8)
        if len(data_size_bytes) != 8:
            logger.warning("Connexion fermée par %s avant la taille", addr)
            self._notify('rejected', {'reason': 'no_size', 'addr': addr})
            return
        data_size = int.from_bytes(data_size_bytes, 'big')
        if data_size > self.MAX_FILE_SIZE:
            logger.warning("Fichier trop gros (%d) de %s", data_size, addr)
            self._notify('rejected', {'reason': 'file_too_large', 'size': data_size, 'addr': addr})
            return

        # 4. Réception en streaming vers un fichier temporaire (hash incrémental).
        # Évite de bufferiser jusqu'à 100 Mo par connexion en mémoire.
        hasher = sha256()
        received_hash = b''
        bytes_received = 0
        tmp_path = None
        try:
            fd, tmp_name = tempfile.mkstemp(prefix='recv_', suffix='.part', dir=str(self.received_dir))
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, 'wb') as tmp_file:
                while bytes_received < data_size + 32:
                    remaining = (data_size + 32) - bytes_received
                    chunk = recv_fn(min(65536, remaining))
                    if not chunk:
                        break

                    overflow = bytes_received + len(chunk) - data_size
                    if overflow <= 0:
                        hasher.update(chunk)
                        tmp_file.write(chunk)
                    else:
                        file_part = chunk[:len(chunk) - overflow]
                        hash_part = chunk[len(chunk) - overflow:]
                        hasher.update(file_part)
                        tmp_file.write(file_part)
                        received_hash += hash_part
                    bytes_received += len(chunk)
        except Exception:
            if tmp_path is not None:
                _silent_unlink(tmp_path)
            raise

        if bytes_received != data_size + 32 or len(received_hash) != 32:
            logger.error("Taille reçue incorrecte pour %s de %s", filename, addr)
            _silent_unlink(tmp_path)
            self._notify('rejected', {'reason': 'incomplete', 'filename': filename, 'addr': addr})
            return

        # 5. Vérification hash
        computed_hash = hasher.digest()
        if not hmac.compare_digest(computed_hash, received_hash):
            logger.error("Hash incorrect pour %s de %s", filename, addr)
            _silent_unlink(tmp_path)
            self._notify('rejected', {'reason': 'hash_mismatch', 'filename': filename, 'addr': addr})
            return

        # 6. Sauvegarde atomique (renommage du fichier temporaire validé)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.received_dir / f"{timestamp}_{filename}"
        counter = 1
        while filepath.exists():
            filepath = self.received_dir / f"{timestamp}_{counter}_{filename}"
            counter += 1
        try:
            os.replace(str(tmp_path), str(filepath))
        except OSError:
            _silent_unlink(tmp_path)
            raise

        logger.info("Fichier reçu de %s: %s (%d octets)", addr, filepath, data_size)
        self._notify('file_received', {
            'filename': filename,
            'path': str(filepath),
            'size': data_size,
            'addr': addr
        })

    def stop(self):
        """Arrête le serveur sans bloquer le thread appelant (UI).

        L'arrêt signale l'événement et ferme le socket d'écoute ; les
        transferts déjà en cours sont annulés au plus vite. On ne joint pas
        l'exécuteur ici : cette méthode peut être appelée depuis le thread UI
        pendant la fermeture de la fenêtre.
        """
        logger.info("Arrêt du serveur demandé")
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._notify('stopped', {})
        self._executor.shutdown(wait=False, cancel_futures=True)


def _silent_unlink(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass