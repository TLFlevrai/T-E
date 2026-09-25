# tests/unit/test_network_server.py
"""Tests du serveur de réception TCP (authentification, validation, stockage)."""
import hashlib
import hmac as hmac_mod
import json
import socket
import threading
import time
from pathlib import Path

import pytest

from src.network.server import ReceiveServer, recv_exact

AUTH_MSG = b'PYEXTRACTOR_AUTH'


class FakePartialSocket:
    """Socket simulé qui livre les octets en petits morceaux (TCP réaliste)."""

    def __init__(self, data: bytes, chunk_sizes):
        self._data = data
        self._chunk_sizes = list(chunk_sizes)
        self._pos = 0

    def recv(self, n: int) -> bytes:
        if self._pos >= len(self._data):
            return b''
        take = min(n, self._chunk_sizes.pop(0) if self._chunk_sizes else n)
        chunk = self._data[self._pos:self._pos + take]
        self._pos += len(chunk)
        return chunk


class TestRecvExact:
    def test_reads_exact_across_partial_deliveries(self):
        data = bytes(range(256)) * 4  # 1024 octets
        sock = FakePartialSocket(data, chunk_sizes=[1, 2, 3, 500] * 100)
        assert recv_exact(sock, 1024) == data

    def test_returns_short_on_eof(self):
        sock = FakePartialSocket(b'abc', chunk_sizes=[1])
        assert recv_exact(sock, 10) == b'abc'


class TestSanitizeFilename:
    def test_path_traversal_neutralized(self):
        assert ReceiveServer._sanitize_filename('../../etc/evil.txt') == 'evil.txt'
        assert ReceiveServer._sanitize_filename('..\\..\\evil.txt') == 'evil.txt'

    def test_windows_reserved_name_prefixed(self):
        assert ReceiveServer._sanitize_filename('con.txt') == '_con.txt'
        assert ReceiveServer._sanitize_filename('NUL') == '_NUL'

    def test_unsafe_chars_replaced(self):
        assert ReceiveServer._sanitize_filename('a\x00b.txt') == 'a_b.txt'
        assert ReceiveServer._sanitize_filename('mon fichier!.txt') == 'mon_fichier_.txt'

    def test_dotfile_and_empty(self):
        assert ReceiveServer._sanitize_filename('.hidden') == '_.hidden'
        assert ReceiveServer._sanitize_filename('') == ''
        assert ReceiveServer._sanitize_filename('.') == ''
        assert ReceiveServer._sanitize_filename('..') == ''

    def test_length_bounded(self):
        long_name = 'a' * 400 + '.txt'
        result = ReceiveServer._sanitize_filename(long_name)
        assert len(result) <= ReceiveServer.MAX_FILENAME_LEN


def _hmac_for(token: str) -> bytes:
    return hmac_mod.new(token.encode('utf-8'), AUTH_MSG, 'sha256').digest()


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server_env(tmp_path, monkeypatch):
    """Démarre un vrai ReceiveServer sur 127.0.0.1 avec config de test."""
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps({
        'output_dir': str(tmp_path / 'out'),
        'network': {
            'server_host': '127.0.0.1',
            'server_port': _free_port(),
            'discovery_port': _free_port(),
            'auth_enabled': True,
            'auth_token': 'unit-test-token-123',
            'allowed_extensions': ['.TXT', '.md'],
        },
    }), encoding='utf-8')

    import src.config
    original_path = src.config.CONFIG_PATH
    src.config.CONFIG_PATH = config_path
    from src.config import _Config
    _Config._reset_for_testing()

    received_dir = tmp_path / 'received'
    started = threading.Event()
    events = []

    server = ReceiveServer(
        host='127.0.0.1',
        port=_free_port(),
        received_dir=received_dir,
        max_workers=2,
        on_event=lambda t, d: (events.append((t, d)), started.set()) if t == 'started' else events.append((t, d)),
    )
    server.start()
    assert started.wait(timeout=5), "Le serveur n'a pas démarré"

    yield {
        'server': server,
        'events': events,
        'received_dir': received_dir,
        'token': 'unit-test-token-123',
    }

    server.stop()
    server.join(timeout=3)
    src.config.CONFIG_PATH = original_path
    _Config._reset_for_testing()


def _send(env, filename: str, payload: bytes, token: str = None,
          declared_size: int = None, corrupt_hash: bool = False) -> None:
    """Client brut : reproduit le protocole FileTransferService."""
    token = token if token is not None else env['token']
    auth = hmac_mod.new(token.encode('utf-8'), AUTH_MSG, 'sha256').digest()
    name_bytes = filename.encode('utf-8')
    size = declared_size if declared_size is not None else len(payload)
    digest = hashlib.sha256(payload).digest()
    if corrupt_hash:
        digest = bytes(32)

    try:
        with socket.create_connection((env['server'].host, env['server'].port), timeout=5) as s:
            s.sendall(len(auth).to_bytes(2, 'big'))
            s.sendall(auth)
            s.sendall(len(name_bytes).to_bytes(4, 'big'))
            s.sendall(name_bytes)
            s.sendall(size.to_bytes(8, 'big'))
            s.sendall(payload)
            s.sendall(digest)
    except ConnectionResetError:
        # Le serveur a fermé la connexion (ex: auth échouée) - c'est attendu
        pass


def _wait_for(predicate, timeout=3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class TestTransferIntegration:
    def test_valid_transfer_writes_file(self, server_env):
        payload = b'contenu de test' * 100
        _send(server_env, 'note.txt', payload)
        assert _wait_for(lambda: list(server_env['received_dir'].glob('*note.txt')))
        files = list(server_env['received_dir'].glob('*note.txt'))
        assert len(files) == 1
        assert files[0].read_bytes() == payload
        types = [t for t, _ in server_env['events']]
        assert 'file_received' in types

    def test_case_insensitive_extension(self, server_env):
        # Config déclare '.TXT' : la comparaison doit être insensible à la casse
        payload = b'uppercase ext'
        _send(server_env, 'UPPER.TXT', payload)
        assert _wait_for(lambda: list(server_env['received_dir'].glob('*UPPER.TXT')))

    def test_wrong_auth_rejected(self, server_env):
        _send(server_env, 'evil.txt', b'data', token='wrong-token')
        assert _wait_for(lambda: any(t == 'rejected' and d.get('reason') == 'auth_failed'
                                     for t, d in server_env['events']), timeout=5)
        # received_dir est créé au démarrage du serveur ; vérifier qu'il reste vide
        assert not list(server_env['received_dir'].iterdir())

    def test_bad_extension_rejected(self, server_env):
        _send(server_env, 'program.exe', b'MZ...')
        time.sleep(0.3)
        reasons = [d.get('reason') for t, d in server_env['events'] if t == 'rejected']
        assert 'extension_not_allowed' in reasons

    def test_hash_mismatch_leaves_no_file_nor_temp(self, server_env):
        _send(server_env, 'corrupt.md', b'data data', corrupt_hash=True)
        assert _wait_for(lambda: any(t == 'rejected' and d.get('reason') == 'hash_mismatch'
                                     for t, d in server_env['events']))
        leftovers = list(server_env['received_dir'].iterdir()) if server_env['received_dir'].exists() else []
        assert leftovers == []

    def test_traversal_filename_stays_in_received_dir(self, server_env):
        _send(server_env, '../escaped.md', b'attempt')
        assert _wait_for(lambda: any(t == 'file_received' for t, _ in server_env['events']))
        for _, data in [e for e in server_env['events'] if e[0] == 'file_received']:
            saved = Path(data['path'])
            assert server_env['received_dir'].resolve() in saved.resolve().parents or \
                saved.parent == server_env['received_dir'].resolve()
            assert saved.exists()

    def test_oversized_declared_size_rejected(self, server_env):
        _send(server_env, 'big.txt', b'', declared_size=ReceiveServer.MAX_FILE_SIZE + 1)
        assert _wait_for(lambda: any(t == 'rejected' and d.get('reason') == 'file_too_large'
                                     for t, d in server_env['events']))


class TestFailClosedOnDefaultToken:
    def test_refuses_non_loopback_with_default_token(self, tmp_path, monkeypatch):
        config_path = tmp_path / 'config.json'
        config_path.write_text(json.dumps({
            'output_dir': str(tmp_path / 'out'),
            'network': {
                'server_host': '0.0.0.0',
                'server_port': _free_port(),
                'discovery_port': 50001,
                'auth_enabled': True,
                'auth_token': 'change-me-secure-random-token',
            },
        }), encoding='utf-8')
        monkeypatch.setattr('src.config.CONFIG_PATH', config_path)
        from src.config import _Config
        _Config._reset_for_testing()
        try:
            failures = []
            started = threading.Event()
            server = ReceiveServer(
                host='192.168.1.99',
                port=_free_port(),
                received_dir=tmp_path / 'r',
                on_event=lambda t, d: failures.append(d) if t == 'start_failed'
                else (started.set() if t == 'started' else None),
            )
            server.start()
            server.join(timeout=3)
            assert not started.is_set(), "Le serveur ne doit pas démarrer avec le token par défaut hors localhost"
            assert failures, "Un événement start_failed doit être émis"
        finally:
            _Config._reset_for_testing()
