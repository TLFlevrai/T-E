# tests/unit/test_content_reader.py
"""Tests unitaires pour ContentReader."""
from __future__ import annotations

from pathlib import Path

from src.extractor.content_reader import ContentReader, MAX_FILE_SIZE


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
        # Créer un fichier plus grand que MAX_FILE_SIZE
        file.write_bytes(b'x' * (MAX_FILE_SIZE + 1))
        content, lines, size, ok = ContentReader.read_file_content(file, '.txt')
        assert ok is False
        assert "volumineux" in content

    def test_read_mo_file(self, tmp_path):
        file = tmp_path / "test.mo"
        file.write_bytes(b'\x00\x01\x02\x03')
        content, lines, size, ok = ContentReader.read_file_content(file, '.mo')
        assert ok is True
        assert lines >= 1
