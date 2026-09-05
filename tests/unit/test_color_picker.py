# tests/unit/test_color_picker.py
"""Tests unitaires pour l'outil Color Picker."""
from __future__ import annotations

import pytest

from src.tools.color_picker import (
    _hex_to_rgb,
    _hsl_to_rgb,
    _is_valid_hex,
    _rgb_to_hex,
    _rgb_to_hsl,
)


class TestRgbToHex:
    """Tests pour _rgb_to_hex()."""

    def test_red(self):
        assert _rgb_to_hex(255, 0, 0) == "#ff0000"

    def test_green(self):
        assert _rgb_to_hex(0, 255, 0) == "#00ff00"

    def test_blue(self):
        assert _rgb_to_hex(0, 0, 255) == "#0000ff"

    def test_white(self):
        assert _rgb_to_hex(255, 255, 255) == "#ffffff"

    def test_black(self):
        assert _rgb_to_hex(0, 0, 0) == "#000000"

    def test_mixed(self):
        assert _rgb_to_hex(52, 152, 219) == "#3498db"


class TestHexToRgb:
    """Tests pour _hex_to_rgb()."""

    def test_red(self):
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_green(self):
        assert _hex_to_rgb("#00ff00") == (0, 255, 0)

    def test_blue(self):
        assert _hex_to_rgb("#0000ff") == (0, 0, 255)

    def test_short_hex(self):
        assert _hex_to_rgb("#fff") == (255, 255, 255)

    def test_short_hex_mixed(self):
        assert _hex_to_rgb("#abc") == (170, 187, 204)

    def test_without_hash(self):
        assert _hex_to_rgb("ff0000") == (255, 0, 0)


class TestRgbToHsl:
    """Tests pour _rgb_to_hsl()."""

    def test_red(self):
        h, s, l = _rgb_to_hsl(255, 0, 0)
        assert h == 0
        assert s == 100
        assert l == 50

    def test_white(self):
        h, s, l = _rgb_to_hsl(255, 255, 255)
        assert h == 0
        assert s == 0
        assert l == 100

    def test_black(self):
        h, s, l = _rgb_to_hsl(0, 0, 0)
        assert h == 0
        assert s == 0
        assert l == 0

    def test_blue(self):
        h, s, l = _rgb_to_hsl(0, 0, 255)
        assert h == 240
        assert s == 100
        assert l == 50


class TestHslToRgb:
    """Tests pour _hsl_to_rgb()."""

    def test_red(self):
        r, g, b = _hsl_to_rgb(0, 100, 50)
        assert r == 255
        assert g == 0
        assert b == 0

    def test_white(self):
        r, g, b = _hsl_to_rgb(0, 0, 100)
        assert r == 255
        assert g == 255
        assert b == 255

    def test_black(self):
        r, g, b = _hsl_to_rgb(0, 0, 0)
        assert r == 0
        assert g == 0
        assert b == 0

    def test_blue(self):
        r, g, b = _hsl_to_rgb(240, 100, 50)
        assert r == 0
        assert g == 0
        assert b == 255


class TestIsValidHex:
    """Tests pour _is_valid_hex()."""

    def test_valid_6_chars(self):
        assert _is_valid_hex("#3498db") is True

    def test_valid_3_chars(self):
        assert _is_valid_hex("#fff") is True

    def test_valid_uppercase(self):
        assert _is_valid_hex("#FF0000") is True

    def test_invalid_no_hash(self):
        assert _is_valid_hex("3498db") is False

    def test_invalid_too_short(self):
        assert _is_valid_hex("#fff0") is False

    def test_invalid_chars(self):
        assert _is_valid_hex("#gggggg") is False

    def test_empty(self):
        assert _is_valid_hex("") is False


class TestRoundtrip:
    """Tests de conversion aller-retour."""

    def test_rgb_hex_roundtrip(self):
        r, g, b = 128, 64, 192
        hex_color = _rgb_to_hex(r, g, b)
        r2, g2, b2 = _hex_to_rgb(hex_color)
        assert (r, g, b) == (r2, g2, b2)

    def test_rgb_hsl_roundtrip(self):
        r, g, b = 100, 150, 200
        h, s, l = _rgb_to_hsl(r, g, b)
        r2, g2, b2 = _hsl_to_rgb(h, s, l)
        # Tolérance de ±5 pour les arrondis
        assert abs(r - r2) <= 5
        assert abs(g - g2) <= 5
        assert abs(b - b2) <= 5
