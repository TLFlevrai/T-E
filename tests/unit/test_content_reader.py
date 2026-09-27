# tests/unit/test_content_reader.py
"""Tests unitaires pour ContentReader."""
from __future__ import annotations

from pathlib import Path

from src.extractor.content_reader import ContentReader


class TestContentReader:
    """Tests pour ContentReader."""

    def test_read_text_file(self, tmp_path):
        file = tmp_path / "test.py"
        file.write_text("print('hello')\n", encoding='utf-8')
        content, lines, size, ok = ContentReader.read_file_content(file, '.py')
        assert ok is True
        assert "print('hello')" in content
        assert lines == 1
        assert size > 0

    def test_read_empty_file(self, tmp_path):
        file = tmp_path / "empty.txt"
        file.write_text("", encoding='utf-8')
        content, lines, size, ok = ContentReader.read_file_content(file, '.txt')
        assert ok is True
        assert lines == 0

    def test_read_nonexistent_file(self, tmp_path):
        file = tmp_path / "nonexistent.txt"
        content, lines, size, ok = ContentReader.read_file_content(file, '.txt')
        assert ok is False
        assert "ERREUR" in content

    def test_read_large_file_rejected(self, tmp_path):
        file = tmp_path / "large.txt"
        # Créer un fichier plus grand que 10 Mo (défaut)
        file.write_bytes(b'x' * (11 * 1024 * 1024))
        content, lines, size, ok = ContentReader.read_file_content(file, '.txt', max_file_size_mb=10)
        assert ok is False
        assert "volumineux" in content

    def test_read_mo_file(self, tmp_path):
        file = tmp_path / "test.mo"
        file.write_bytes(b'\x00\x01\x02\x03')
        content, lines, size, ok = ContentReader.read_file_content(file, '.mo')
        assert ok is True
        assert lines >= 1

    def test_streaming_line_range_returns_total_lines(self, tmp_path):
        """BUG #5: line_range ne doit pas affecter num_lines retourné."""
        # Créer un fichier > 1 Mo pour forcer le streaming (seuil = 1 Mo)
        file = tmp_path / "big.txt"
        # ~1.5 Mo = ~150000 lignes de 10 chars
        lines_content = [f"ligne {i:06d}\n" for i in range(1, 150001)]
        file.write_text("".join(lines_content), encoding='utf-8')
        
        # Lire seulement lignes 10000-10020
        content, num_lines, size, ok = ContentReader.read_file_content(
            file, '.txt', line_range=(10000, 10020), max_file_size_mb=10
        )
        
        assert ok is True
        # num_lines doit être le total du fichier (150000), pas les 21 extraites
        assert num_lines == 150000, f"Expected 150000 total lines, got {num_lines}"
        # Mais le contenu ne doit contenir que les lignes demandées
        content_lines = content.splitlines()
        assert len(content_lines) == 21
        assert content_lines[0] == "ligne 010000"
        assert content_lines[-1] == "ligne 010020"
