# tests/unit/test_text_analyzer.py
"""Tests unitaires pour l'analyseur de texte."""
from __future__ import annotations

import pytest
from src.tools._text_stats import (
    compute_stats, word_frequency, detect_encoding_bytes, minify,
    minify_js, minify_css, minify_html, quick_compare,
)


# ═══════════════════════════════════════════════════════════════════════════
# compute_stats
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeStats:
    def test_empty_text(self):
        stats = compute_stats("")
        assert stats['lines'] == 0
        assert stats['words'] == 0

    def test_simple_text(self):
        text = "Bonjour le monde.\nCeci est un test."
        stats = compute_stats(text)
        assert stats['lines'] == 2
        assert stats['words'] == 7
        assert stats['sentences'] == 2

    def test_multiline(self):
        text = "Ligne 1\nLigne 2\nLigne 3"
        stats = compute_stats(text)
        assert stats['lines'] == 3
        assert stats['words'] == 6

    def test_empty_lines(self):
        text = "A\n\n\nB"
        stats = compute_stats(text)
        assert stats['empty_lines'] == 2

    def test_paragraphs(self):
        text = "Paragraphe 1.\n\nParagraphe 2.\n\nParagraphe 3."
        stats = compute_stats(text)
        assert stats['paragraphs'] == 3

    def test_chars_count(self):
        text = "abc de"
        stats = compute_stats(text)
        assert stats['chars_with_spaces'] == 6
        assert stats['chars_without_spaces'] == 5

    def test_max_line_length(self):
        text = "court\nun peu plus long"
        stats = compute_stats(text)
        assert stats['max_line_length'] == 16


# ═══════════════════════════════════════════════════════════════════════════
# word_frequency
# ═══════════════════════════════════════════════════════════════════════════

class TestWordFrequency:
    def test_empty_text(self):
        assert word_frequency("") == []

    def test_simple(self):
        text = "chat chat chien chien chien"
        freq = word_frequency(text, top_n=3, exclude_stopwords=False)
        assert freq[0][0] == "chien"
        assert freq[0][1] == 3
        assert freq[1][0] == "chat"
        assert freq[1][1] == 2

    def test_stopwords_excluded(self):
        text = "the the the the the cat cat"
        freq = word_frequency(text, top_n=3, exclude_stopwords=True)
        assert freq[0][0] == "cat"

    def test_short_words_filtered(self):
        text = "ab abc ab ab abcd"
        freq = word_frequency(text, top_n=5, exclude_stopwords=False)
        words = [w for w, _, _ in freq]
        assert "ab" not in words

    def test_percentage(self):
        text = "bonjour bonjour bonjour monde monde"
        freq = word_frequency(text, top_n=2, exclude_stopwords=False)
        assert freq[0][0] == "bonjour"
        assert freq[0][2] == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# detect_encoding_bytes
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectEncoding:
    def test_empty(self):
        result = detect_encoding_bytes(b"")
        assert result['encoding'] == 'unknown'

    def test_utf8(self):
        raw = "Bonjour éàü".encode('utf-8')
        result = detect_encoding_bytes(raw)
        assert 'UTF' in result['encoding']

    def test_utf8_bom(self):
        raw = b'\xef\xbb\xbf' + "Hello".encode('utf-8')
        result = detect_encoding_bytes(raw)
        assert result['bom'] == 'UTF-8'

    def test_crlf(self):
        raw = b"line1\r\nline2\r\n"
        result = detect_encoding_bytes(raw)
        assert 'CRLF' in result['line_ending']

    def test_lf(self):
        raw = b"line1\nline2\n"
        result = detect_encoding_bytes(raw)
        assert 'LF' in result['line_ending']


# ═══════════════════════════════════════════════════════════════════════════
# minify
# ═══════════════════════════════════════════════════════════════════════════

class TestMinify:
    def test_minify_js(self):
        code = """
        // comment
        var x = 1;
        var y = 2;
        """
        result = minify(code, 'js')
        assert result['format'] == 'js'
        assert '//' not in result['minified']
        assert result['gain_pct'] > 0

    def test_minify_css(self):
        code = """
        /* comment */
        .class {
            color: red;
            background: blue;
        }
        """
        result = minify(code, 'css')
        assert '/*' not in result['minified']
        assert result['gain_pct'] > 0

    def test_minify_html(self):
        code = """
        <!-- comment -->
        <div>
            <p>Hello</p>
        </div>
        """
        result = minify(code, 'html')
        assert '<!--' not in result['minified']
        assert result['gain_pct'] > 0

    def test_minify_auto_detect(self):
        code = "body { color: red; }"
        result = minify(code, 'auto')
        assert result['format'] == 'css'

    def test_minify_js_functions(self):
        assert minify_js("// comment\nvar x = 1;") == "var x=1;"

    def test_minify_css_functions(self):
        assert minify_css("/* c */ .a { color: red; }") == ".a{color:red;}"

    def test_minify_html_functions(self):
        assert minify_html("<!-- c --><p> hi </p>") == "<p> hi </p>"


# ═══════════════════════════════════════════════════════════════════════════
# quick_compare
# ═══════════════════════════════════════════════════════════════════════════

class TestQuickCompare:
    def test_identical(self):
        result = quick_compare("abc\n123", "abc\n123")
        assert result['identical_pct'] == 100
        assert result['added'] == 0
        assert result['removed'] == 0

    def test_different(self):
        result = quick_compare("abc", "xyz")
        assert result['identical_pct'] == 0
        assert result['added'] == 1
        assert result['removed'] == 1

    def test_partial(self):
        a = "a\nb\nc"
        b = "a\nb\nd"
        result = quick_compare(a, b)
        assert result['identical_pct'] > 0
        assert result['added'] >= 1
        assert result['removed'] >= 1

    def test_empty(self):
        result = quick_compare("", "")
        assert result['identical_pct'] == 100

    def test_one_empty(self):
        result = quick_compare("abc", "")
        assert result['identical_pct'] == 0
        assert result['removed'] == 1
