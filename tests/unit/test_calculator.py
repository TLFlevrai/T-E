# tests/unit/test_calculator.py
"""Tests unitaires pour la calculatrice."""
from __future__ import annotations

import math
import pytest
from src.gui.calculator import (
    safe_eval, _format_result, _CONSTANTS, _convert_base,
    _UNIT_CATEGORIES,
)


class TestSafeEval:
    def test_addition(self):
        assert safe_eval("2+3") == 5

    def test_subtraction(self):
        assert safe_eval("10-4") == 6

    def test_multiplication(self):
        assert safe_eval("6*7") == 42

    def test_division(self):
        assert safe_eval("10/4") == 2.5

    def test_modulo(self):
        assert safe_eval("10%3") == 1

    def test_power(self):
        assert safe_eval("2**3") == 8

    def test_parentheses(self):
        assert safe_eval("(2+3)*4") == 20

    def test_unary_minus(self):
        assert safe_eval("-5") == -5

    def test_unary_plus(self):
        assert safe_eval("+5") == 5

    def test_sqrt(self):
        assert safe_eval("sqrt(9)") == 3

    def test_abs(self):
        assert safe_eval("abs(-7)") == 7

    def test_sin(self):
        assert safe_eval("sin(0)") == 0

    def test_cos(self):
        assert safe_eval("cos(0)") == 1

    def test_tan(self):
        assert safe_eval("tan(0)") == 0

    def test_log(self):
        assert safe_eval("log(100)") == 2

    def test_ln(self):
        assert safe_eval("ln(1)") == 0

    def test_asin(self):
        assert safe_eval("asin(1)") == math.pi / 2

    def test_acos(self):
        assert safe_eval("acos(1)") == 0

    def test_atan(self):
        assert safe_eval("atan(0)") == 0

    def test_ceil(self):
        assert safe_eval("ceil(2.1)") == 3

    def test_floor(self):
        assert safe_eval("floor(2.9)") == 2

    def test_radians(self):
        assert safe_eval("radians(180)") == math.pi

    def test_degrees(self):
        assert safe_eval("degrees(math.pi)") == 180

    def test_constant_pi(self):
        assert safe_eval("pi") == math.pi

    def test_constant_e(self):
        assert safe_eval("e") == math.e

    def test_constant_phi(self):
        assert safe_eval("phi") == (1 + math.sqrt(5)) / 2

    def test_constant_sqrt2(self):
        assert safe_eval("sqrt2") == math.sqrt(2)

    def test_complex_expression(self):
        assert safe_eval("2+3*4") == 14

    def test_nested_parentheses(self):
        assert safe_eval("((2+3)*4)") == 20

    def test_invalid_expression(self):
        with pytest.raises((ValueError, SyntaxError)):
            safe_eval("import os")

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            safe_eval("1/0")

    def test_negative_sqrt(self):
        with pytest.raises(ValueError):
            safe_eval("sqrt(-1)")


class TestFormatResult:
    def test_integer(self):
        assert _format_result(42) == "42"

    def test_float_integer_value(self):
        assert _format_result(5.0) == "5"

    def test_float_decimal(self):
        assert _format_result(3.14) == "3.14"

    def test_nan(self):
        assert _format_result(float('nan')) == "Erreur"

    def test_inf(self):
        assert _format_result(float('inf')) == "Erreur"

    def test_bool_true(self):
        assert _format_result(True) == "1"

    def test_bool_false(self):
        assert _format_result(False) == "0"

    def test_large_number(self):
        result = _format_result(1e15)
        assert result == "1000000000000000"

    def test_small_float(self):
        result = _format_result(0.1 + 0.2)
        assert result == "0.3"


class TestConvertBase:
    def test_dec_to_hex(self):
        assert _convert_base(255, 10, 16) == "FF"

    def test_dec_to_bin(self):
        assert _convert_base(10, 10, 2) == "1010"

    def test_dec_to_oct(self):
        assert _convert_base(255, 10, 8) == "377"

    def test_hex_to_dec(self):
        assert _convert_base("FF", 16, 10) == "255"

    def test_bin_to_dec(self):
        assert _convert_base("1010", 2, 10) == "10"

    def test_zero(self):
        assert _convert_base(0, 10, 2) == "0"


class TestUnitConversions:
    def test_celsius_to_fahrenheit(self):
        cat = _UNIT_CATEGORIES['Température']
        base = cat['vers_base']['°C'](100)
        result = cat['depuis_base']['°F'](base)
        assert abs(result - 212) < 0.01

    def test_fahrenheit_to_celsius(self):
        cat = _UNIT_CATEGORIES['Température']
        base = cat['vers_base']['°F'](32)
        result = cat['depuis_base']['°C'](base)
        assert abs(result) < 0.01

    def test_celsius_to_kelvin(self):
        cat = _UNIT_CATEGORIES['Température']
        base = cat['vers_base']['°C'](0)
        result = cat['depuis_base']['K'](base)
        assert abs(result - 273.15) < 0.01

    def test_meters_to_feet(self):
        cat = _UNIT_CATEGORIES['Longueur']
        base = cat['vers_base']['m'](1)
        result = cat['depuis_base']['ft'](base)
        assert abs(result - 3.28084) < 0.01

    def test_km_to_miles(self):
        cat = _UNIT_CATEGORIES['Longueur']
        base = cat['vers_base']['km'](1)
        result = cat['depuis_base']['mi'](base)
        assert abs(result - 0.621371) < 0.01

    def test_kg_to_pounds(self):
        cat = _UNIT_CATEGORIES['Poids']
        base = cat['vers_base']['kg'](1)
        result = cat['depuis_base']['lb'](base)
        assert abs(result - 2.20462) < 0.01

    def test_grams_to_ounces(self):
        cat = _UNIT_CATEGORIES['Poids']
        base = cat['vers_base']['g'](1000)
        result = cat['depuis_base']['oz'](base)
        assert abs(result - 35.274) < 0.01


class TestConstants:
    def test_pi(self):
        assert abs(_CONSTANTS['pi'] - 3.14159265) < 0.0001

    def test_e(self):
        assert abs(_CONSTANTS['e'] - 2.71828182) < 0.0001

    def test_phi(self):
        assert abs(_CONSTANTS['phi'] - 1.61803398) < 0.0001

    def test_sqrt2(self):
        assert abs(_CONSTANTS['sqrt2'] - 1.41421356) < 0.0001

    def test_tau(self):
        assert abs(_CONSTANTS['tau'] - 6.28318530) < 0.0001
