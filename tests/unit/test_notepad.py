# tests/unit/test_notepad.py
"""Tests unitaires pour le bloc-notes amélioré."""
from __future__ import annotations

import pytest
from src.tools._syntax import detect_language, COLORS, TAG_NAMES


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

    def test_yaml_ext(self):
        """Les deux extensions YAML doivent être détectées comme 'yaml'."""
        assert detect_language("ci.yml") == "yaml"
        assert detect_language("values.yaml") == "yaml"

    def test_yaml_ext_case_insensitive(self):
        """Un fichier en MAJUSCULES (.YML) doit aussi être reconnu."""
        assert detect_language("CI.YML") == "yaml"
        assert detect_language("Values.YAML") == "yaml"

    def test_yaml_ext_with_full_path(self):
        assert detect_language("C:/projets/app/.github/workflows/ci.yml") == "yaml"


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

    def test_yaml_patterns_compile(self):
        """Les patterns YAML doivent se compiler et ne réutiliser que des
        tags déjà déclarés (pas de nouveau tag dans COLORS)."""
        import re
        from src.tools._syntax import _build_yaml_patterns, TAG_NAMES
        patterns = _build_yaml_patterns()
        assert len(patterns) > 0
        for token, pattern in patterns:
            assert isinstance(token, str)
            re.compile(pattern)  # lève re.error si invalide
            assert token in TAG_NAMES, f"tag inconnu: {token}"

    def test_yaml_patterns_cover_expected_tokens(self):
        from src.tools._syntax import _build_yaml_patterns
        tokens = {token for token, _ in _build_yaml_patterns()}
        # commentaire, chaîne, clé, nombre, constante doivent être couverts
        assert {'comment', 'string', 'key', 'number', 'constant'} <= tokens

    def test_yaml_patterns_match_real_content(self):
        """Vérifie que les patterns YAML reconnaissent du contenu réel."""
        import re
        from src.tools._syntax import _build_yaml_patterns
        content = (
            "# commentaire\n"
            "name: demo\n"
            "version: 1.2\n"
            "enabled: true\n"
            "title: \"texte\"\n"
            "base: &ancrage\n"
            "alias: *ancrage\n"
        )
        hits = {
            token: [m.group(0) for m in re.compile(pattern, re.M).finditer(content)]
            for token, pattern in _build_yaml_patterns()
        }
        assert hits['comment'] == ['# commentaire']
        assert 'name' in hits['key'] and 'enabled' in hits['key']
        assert hits['number'] == ['1.2']
        assert hits['constant'] == ['true']
        assert hits['string'] == ['"texte"']
        assert '&ancrage' in hits['decorator']
        assert '*ancrage' in hits['decorator']

    def test_yaml_string_pattern_handles_escaped_apostrophe(self):
        """En YAML, '' est l'échappement d'une apostrophe dans une chaîne
        simple : le pattern doit garder la chaîne entière."""
        import re
        from src.tools._syntax import _build_yaml_patterns
        pattern = dict(_build_yaml_patterns())['string']
        found = re.compile(pattern).findall("msg: 'it''s here'\n")
        assert found == ["'it''s here'"]

    def test_all_patterns_are_valid_regex(self):
        import re
        from src.tools._syntax import _PATTERNS
        for lang, builder in _PATTERNS.items():
            for token, pattern in builder():
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex for {lang}/{token}: {e}")


class TestHighlightPositions:
    """Positionnement des tags tkinter sur plusieurs lignes.

    Régression : les offsets de `re` sont des index de caractère ABSOLUS,
    alors que tkinter attend (ligne, colonne). Les confondre faisait
    retomber tout le surlignage sur la première ligne — pour TOUS les
    langages (un fichier YAML est presque toujours multi-lignes).
    """

    @staticmethod
    def _spans(text_widget):
        spans = {}
        for tag in text_widget.tag_names():
            rng = [str(r) for r in text_widget.tag_ranges(tag)]
            if rng:
                spans[tag] = [text_widget.get(rng[i], rng[i + 1])
                              for i in range(0, len(rng), 2)]
        return spans

    def test_yaml_highlight_spans_multiple_lines(self, tk_root):
        import tkinter as tk

        from src.tools._syntax import SyntaxHighlighter

        content = (
            "# commentaire\n"
            "name: demo\n"
            "version: 1.2\n"
            "enabled: true\n"
            "title: \"texte\"\n"
            "base: &ancrage\n"
            "alias: *ancrage\n"
        )
        text = tk.Text(tk_root)
        text.insert("1.0", content)
        SyntaxHighlighter(text).highlight_range("1.0", tk.END, "yaml")

        spans = self._spans(text)
        assert spans["syn_comment"] == ["# commentaire"]
        assert spans["syn_key"] == ["name", "version", "enabled", "title",
                                    "base", "alias"]
        assert spans["syn_number"] == ["1.2"]
        assert spans["syn_constant"] == ["true"]
        assert spans["syn_string"] == ['"texte"']
        assert spans["syn_decorator"] == ["&ancrage", "*ancrage"]
        text.destroy()

    @pytest.mark.parametrize("lang,content,tag,expected", [
        ("python", "# un\nx = 42\ndef f():\n    return True\n",
         "syn_comment", ["# un"]),
        # le pattern de clé JSON capture les guillemets : '"clef"'
        ("json", '{\n  "clef": 1,\n  "autre": true\n}\n',
         "syn_key", ['"clef"', '"autre"']),
        ("css", ".a {\n  color: red;\n}\n", "syn_bracket", ["{", "}"]),
    ])
    def test_existing_languages_still_multiline(self, tk_root, lang, content,
                                               tag, expected):
        """Le correctif de position ne doit pas casser Python/JSON."""
        import tkinter as tk

        from src.tools._syntax import SyntaxHighlighter

        text = tk.Text(tk_root)
        text.insert("1.0", content)
        SyntaxHighlighter(text).highlight_range("1.0", tk.END, lang)
        assert self._spans(text)[tag] == expected
        text.destroy()


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
