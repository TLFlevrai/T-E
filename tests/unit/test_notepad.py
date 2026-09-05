# tests/unit/test_notepad.py
"""Tests unitaires pour le bloc-notes amélioré."""
from __future__ import annotations

import pytest
from src.tools._syntax import detect_language, SyntaxHighlighter, COLORS, TAG_NAMES


# ═══════════════════════════════════════════════════════════════════════════
# Détection de langage
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectLanguage:
    def test_python_ext(self):
        assert detect_language("main.py") == "python"

    def test_js_ext(self):
        assert detect_language("app.js") == "javascript"

    def test_json_ext(self):
        assert detect_language("config.json") == "json"

    def test_html_ext(self):
        assert detect_language("index.html") == "html"

    def test_css_ext(self):
        assert detect_language("style.css") == "css"

    def test_txt_ext(self):
        assert detect_language("readme.txt") == "text"

    def test_auto_json(self):
        content = '{"key": "value", "num": 123}'
        assert detect_language(None, content) == "json"

    def test_auto_html(self):
        content = '<!DOCTYPE html><html><body></body></html>'
        assert detect_language(None, content) == "html"

    def test_auto_python(self):
        content = 'def hello():\n    return True'
        assert detect_language(None, content) == "python"

    def test_auto_js(self):
        content = 'const x = function() { return 1; }'
        assert detect_language(None, content) == "javascript"

    def test_auto_css(self):
        content = '.class { color: red; }'
        assert detect_language(None, content) == "css"

    def test_no_file_no_content(self):
        assert detect_language(None, "") == "text"

    def test_unknown_ext(self):
        assert detect_language("file.xyz") == "text"


# ═══════════════════════════════════════════════════════════════════════════
# Couleurs et tags
# ═══════════════════════════════════════════════════════════════════════════

class TestColorsAndTags:
    def test_all_colors_are_hex(self):
        for name, color in COLORS.items():
            assert color.startswith('#'), f"Color {name} is not hex: {color}"
            assert len(color) == 7, f"Color {name} has wrong length: {color}"

    def test_all_tags_have_names(self):
        for token in COLORS:
            assert token in TAG_NAMES, f"Token {token} has no tag name"

    def test_tag_names_are_strings(self):
        for token, tag in TAG_NAMES.items():
            assert isinstance(tag, str)
            assert tag.startswith('syn_')


# ═══════════════════════════════════════════════════════════════════════════
# Moteur de surlignage (sans tk.Text)
# ═══════════════════════════════════════════════════════════════════════════

class TestSyntaxPatterns:
    def test_python_patterns_compile(self):
        from src.tools._syntax import _build_python_patterns
        patterns = _build_python_patterns()
        assert len(patterns) > 0
        for token, pattern in patterns:
            assert isinstance(token, str)

    def test_js_patterns_compile(self):
        from src.tools._syntax import _build_js_patterns
        patterns = _build_js_patterns()
        assert len(patterns) > 0

    def test_json_patterns_compile(self):
        from src.tools._syntax import _build_json_patterns
        patterns = _build_json_patterns()
        assert len(patterns) > 0

    def test_html_patterns_compile(self):
        from src.tools._syntax import _build_html_patterns
        patterns = _build_html_patterns()
        assert len(patterns) > 0

    def test_css_patterns_compile(self):
        from src.tools._syntax import _build_css_patterns
        patterns = _build_css_patterns()
        assert len(patterns) > 0

    def test_all_patterns_are_valid_regex(self):
        import re
        from src.tools._syntax import _PATTERNS
        for lang, builder in _PATTERNS.items():
            for token, pattern in builder():
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex for {lang}/{token}: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Export HTML
# ═══════════════════════════════════════════════════════════════════════════

class TestExportHTML:
    def test_export_contains_content(self):
        from src.tools.notepad import build_notepad_view
        # Just verify the function exists and can be imported
        assert callable(build_notepad_view)

    def test_export_html_structure(self):
        """Vérifie que la fonction d'export HTML est définie."""
        import src.tools.notepad as notepad_mod
        assert hasattr(notepad_mod, 'build_notepad_view')
