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

    def test_debug_counters_disabled_by_default(self, tmp_path):
        """BUG #3: _DEBUG_ENABLED doit être False par défaut."""
        import os
        # Vérifier que la variable d'env n'est pas définie
        assert os.environ.get('TE_DEBUG_COUNTERS') != '1'
        
        from src.extractor.file_discovery import _DEBUG_ENABLED, _DEBUG_COUNTERS
        
        assert _DEBUG_ENABLED is False
        assert _DEBUG_COUNTERS == {
            "walk_items_yielded": 0,
            "walk_roots_visited": 0,
            "files_emitted": 0,
            "bytes_written": 0,
        }

    def test_resolve_output_dir_consistency(self, tmp_path, monkeypatch):
        """BUG #7: PDFService et Application utilisent la même résolution output_dir."""
        # Configurer un output_dir relatif
        config_path = tmp_path / 'config.json'
        config_path.write_text('{"output_dir": "custom_out"}', encoding='utf-8')
        monkeypatch.setattr('src.config.CONFIG_PATH', config_path)
        from src.config import _Config
        _Config._reset_for_testing()
        
        try:
            from src.paths import resolve_output_dir
            import src.paths as paths_module
            from src.core.app import Application
            
            # Test resolve_output_dir
            resolved = resolve_output_dir()
            # Utiliser la MÊME logique que resolve_output_dir (basée sur paths.py)
            project_root = Path(paths_module.__file__).parent.parent.parent
            expected = project_root / 'custom_out'
            assert resolved == expected
            
            # Test Application._resolve_output_dir utilise la même fonction
            app_resolved = Application._resolve_output_dir(Application)
            assert app_resolved == resolved
        finally:
            _Config._reset_for_testing()

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
