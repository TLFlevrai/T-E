# tests/unit/test_file_transfer.py
"""Tests pour FileTransferService."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.gui.network_center.services.file_transfer_service import FileTransferService


class TestFileTransferService:
    """Tests pour FileTransferService."""

    def test_build_v0_payload_progress_reaches_total(self):
        """Vérifie que le callback de progression atteint total_size."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Créer un fichier de 256 Ko (4 chunks de 64 Ko)
            test_data = b'x' * (256 * 1024)
            f.write(test_data)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = FileTransferService()
            calls = []
            
            def progress_cb(sent, total):
                calls.append((sent, total))
            
            payload = service._build_v0_payload(
                "test.bin",
                len(test_data),
                temp_path,
                progress_callback=progress_cb
            )
            
            # Vérifier que la progression a été appelée
            assert len(calls) > 0, "Le callback de progression doit être appelé"
            
            # Le dernier appel doit atteindre total_size
            last_sent, last_total = calls[-1]
            assert last_total == len(test_data), f"total={last_total} != expected={len(test_data)}"
            assert last_sent == len(test_data), f"sent={last_sent} != expected={len(test_data)}"
            
            # Vérifier que la progression est monotone
            for i in range(1, len(calls)):
                assert calls[i][0] >= calls[i-1][0], "La progression doit être croissante"
                
        finally:
            temp_path.unlink(missing_ok=True)

    def test_build_v0_payload_small_file(self):
        """Vérifie le payload pour un petit fichier (< CHUNK_SIZE)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'small file content'
            f.write(test_data)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = FileTransferService()
            calls = []
            
            payload = service._build_v0_payload(
                "small.txt",
                len(test_data),
                temp_path,
                progress_callback=lambda s, t: calls.append((s, t))
            )
            
            # Pour un petit fichier, un seul appel de progression
            assert len(calls) >= 1
            assert calls[-1] == (len(test_data), len(test_data))
            
        finally:
            temp_path.unlink(missing_ok=True)

    def test_build_v0_payload_exact_chunk_boundary(self):
        """Vérifie le fichier exactement à la limite du chunk (64 Ko)."""
        chunk_size = 64 * 1024
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'y' * chunk_size
            f.write(test_data)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = FileTransferService()
            calls = []
            
            payload = service._build_v0_payload(
                "exact_chunk.bin",
                len(test_data),
                temp_path,
                progress_callback=lambda s, t: calls.append((s, t))
            )
            
            assert len(calls) >= 1
            assert calls[-1] == (len(test_data), len(test_data))
            
        finally:
            temp_path.unlink(missing_ok=True)

    def test_build_v0_payload_multiple_chunks(self):
        """Vérifie un fichier de 3 chunks (192 Ko)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'z' * (192 * 1024)
            f.write(test_data)
            f.flush()
            temp_path = Path(f.name)

        try:
            service = FileTransferService()
            calls = []
            
            payload = service._build_v0_payload(
                "multi.bin",
                len(test_data),
                temp_path,
                progress_callback=lambda s, t: calls.append((s, t))
            )
            
            # Doit avoir au moins 3 appels (1 par chunk)
            assert len(calls) >= 3
            assert calls[-1] == (len(test_data), len(test_data))
            
        finally:
            temp_path.unlink(missing_ok=True)