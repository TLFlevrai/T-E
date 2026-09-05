# src/gui/calculator.py
"""Calculatrice complète et sûre (évaluation via AST, pas de eval brut).

Modes :
- Standard : +, -, ×, ÷, %, parenthèses, x², 1/x, |x|
- Scientifique : sin, cos, tan, log, ln, π, e, √, xⁿ
- Pourcentage : %, remise, pourboire, augmentation
- Conversion de bases : Décimal ↔ Hex ↔ Bin ↔ Oct
- Unités : °C/°F/K, longueur, poids
"""
from __future__ import annotations
import ast
import math
import operator
import tkinter as tk
from tkinter import ttk

from src.i18n import _
from src.logger import setup_logger
from .base_dialog import BaseDialog

logger = setup_logger(__name__)

_BIN_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MATH_FUNCTIONS = {
    'sqrt': math.sqrt,
    'abs': abs,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log10,
    'ln': math.log,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'ceil': math.ceil,
    'floor': math.floor,
    'radians': math.radians,
    'degrees': math.degrees,
}

_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
    'phi': (1 + math.sqrt(5)) / 2,
    'sqrt2': math.sqrt(2),
    'math.pi': math.pi,
    'math.e': math.e,
}

_HISTORY_MAX = 50


def safe_eval(expression: str):
    """Évalue une expression arithmétique de façon sûre (pas de builtins)."""
    tree = ast.parse(expression, mode='eval')
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _BIN_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        operand = _eval_node(node.operand)
        return _UNARY_OPERATORS[type(node.op)](operand)
    if isinstance(node, ast.Call):
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name and func_name in _MATH_FUNCTIONS and len(node.args) == 1:
            arg = _eval_node(node.args[0])
            return _MATH_FUNCTIONS[func_name](arg)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        attr_name = f"{node.value.id}.{node.attr}"
        if attr_name in _CONSTANTS:
            return _CONSTANTS[attr_name]
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    raise ValueError("Expression non supportée")


def _format_result(value) -> str:
    """Formate un résultat : entier si entier, sinon arrondi."""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "Erreur"
        if value == int(value) and abs(value) <= 1e15:
            return str(int(value))
        return f"{round(value, 12):g}"
    return str(value)


# ═══════════════════════════════════════════════════════════════════════════
# Conversions de bases
# ═══════════════════════════════════════════════════════════════════════════

_BASES = {
    'Décimal': 10,
    'Hexadécimal': 16,
    'Binaire': 2,
    'Octal': 8,
}


def _convert_base(value: int, from_base: int, to_base: int) -> str:
    if from_base == to_base:
        return str(value)
    # D'abord convertir en base 10
    if from_base != 10:
        decimal = int(str(value), from_base)
    else:
        decimal = value
    # Puis convertir vers la base cible
    if to_base == 10:
        return str(decimal)
    digits = "0123456789ABCDEF"
    if decimal == 0:
        return "0"
    neg = decimal < 0
    v = abs(decimal)
    result = ""
    while v > 0:
        result = digits[v % to_base] + result
        v //= to_base
    return ("-" + result) if neg else result


# ═══════════════════════════════════════════════════════════════════════════
# Conversions d'unités
# ═══════════════════════════════════════════════════════════════════════════

_UNIT_CATEGORIES = {
    'Température': {
        'unités': ['°C', '°F', 'K'],
        'vers_base': {'°C': lambda x: x, '°F': lambda x: (x - 32) * 5 / 9, 'K': lambda x: x - 273.15},
        'depuis_base': {'°C': lambda x: x, '°F': lambda x: x * 9 / 5 + 32, 'K': lambda x: x + 273.15},
    },
    'Longueur': {
        'unités': ['mm', 'cm', 'm', 'km', 'in', 'ft', 'yd', 'mi'],
        'vers_base': {
            'mm': lambda x: x / 1000, 'cm': lambda x: x / 100, 'm': lambda x: x,
            'km': lambda x: x * 1000, 'in': lambda x: x * 0.0254, 'ft': lambda x: x * 0.3048,
            'yd': lambda x: x * 0.9144, 'mi': lambda x: x * 1609.344,
        },
        'depuis_base': {
            'mm': lambda x: x * 1000, 'cm': lambda x: x * 100, 'm': lambda x: x,
            'km': lambda x: x / 1000, 'in': lambda x: x / 0.0254, 'ft': lambda x: x / 0.3048,
            'yd': lambda x: x / 0.9144, 'mi': lambda x: x / 1609.344,
        },
    },
    'Poids': {
        'unités': ['mg', 'g', 'kg', 't', 'oz', 'lb'],
        'vers_base': {
            'mg': lambda x: x / 1e6, 'g': lambda x: x / 1000, 'kg': lambda x: x,
            't': lambda x: x * 1000, 'oz': lambda x: x * 0.0283495, 'lb': lambda x: x * 0.453592,
        },
        'depuis_base': {
            'mg': lambda x: x * 1e6, 'g': lambda x: x * 1000, 'kg': lambda x: x,
            't': lambda x: x / 1000, 'oz': lambda x: x / 0.0283495, 'lb': lambda x: x / 0.453592,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Widget principal
# ═══════════════════════════════════════════════════════════════════════════

class CalculatorContent(ttk.Frame):
    """Cadre de calculatrice réutilisable avec modes multiples."""

    def __init__(self, parent, global_keys: bool = False, **kwargs):
        super().__init__(parent, padding=10, **kwargs)
        self.expression = "0"
        self._memory = 0.0
        self._has_memory = False
        self._history: list[tuple[str, str]] = []
        self._global_keys = False
        self._paren_depth = 0
        self._mode = "Standard"
        self._create_widgets()
        if global_keys:
            self.enable_global_keys()
        else:
            self._bind_local_keys()
        self._refresh_display()

    # ── Construction ──

    def _create_widgets(self):
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Affichage ──
        self.display_var = tk.StringVar(value="0")
        display = ttk.Entry(
            main, textvariable=self.display_var,
            font=('Segoe UI', 20), justify=tk.RIGHT, state='readonly',
        )
        display.pack(fill=tk.X, pady=(0, 4))

        # Indicateur mémoire + mode
        info_frame = ttk.Frame(main)
        info_frame.pack(fill=tk.X, pady=(0, 2))
        self.memory_indicator = ttk.Label(info_frame, text="", font=('Segoe UI', 8), foreground='#888888')
        self.memory_indicator.pack(side=tk.LEFT)
        self.mode_label = ttk.Label(info_frame, text="Standard", font=('Segoe UI', 8, 'bold'), foreground='#5599ff')
        self.mode_label.pack(side=tk.RIGHT)

        # ── Sélecteur de mode ──
        mode_frame = ttk.Frame(main)
        mode_frame.pack(fill=tk.X, pady=(0, 4))
        modes = ['Standard', 'Scientifique', 'Pourcentage', 'Bases', 'Unités']
        self._mode_var = tk.StringVar(value=self._mode)
        for m in modes:
            ttk.Radiobutton(
                mode_frame, text=str(_(m)), variable=self._mode_var,
                value=m, command=self._switch_mode,
            ).pack(side=tk.LEFT, padx=2)

        # ── Zone contenu (clavier + historique) ──
        body = ttk.Frame(main)
        body.pack(fill=tk.BOTH, expand=True)

        self._keypad_frame = ttk.Frame(body)
        self._keypad_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Historique à droite
        hist_frame = ttk.Frame(body, width=160)
        hist_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        hist_frame.pack_propagate(False)

        ttk.Label(hist_frame, text=str(_("Historique")), font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, pady=(0, 4))
        self._history_listbox = tk.Listbox(
            hist_frame, font=('Consolas', 9),
            bg='#1B2027', fg='#E7EBF0', selectbackground='#3E4452',
            selectforeground='#E7EBF0', bd=0, highlightthickness=0, activestyle='none',
        )
        hist_scroll = ttk.Scrollbar(hist_frame, orient=tk.VERTICAL, command=self._history_listbox.yview)
        self._history_listbox.configure(yscrollcommand=hist_scroll.set)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._history_listbox.bind('<Double-Button-1>', self._on_history_select)
        ttk.Button(hist_frame, text=str(_("Effacer")), style='AppGhost.TButton', command=self._clear_history).pack(fill=tk.X, pady=(4, 0))

        self._build_standard_keypad()

    def _switch_mode(self):
        self._mode = self._mode_var.get()
        self.mode_label.config(text=str(_(self._mode)))
        for w in self._keypad_frame.winfo_children():
            w.destroy()
        builder = {
            'Standard': self._build_standard_keypad,
            'Scientifique': self._build_scientific_keypad,
            'Pourcentage': self._build_percentage_keypad,
            'Bases': self._build_bases_keypad,
            'Unités': self._build_unit_keypad,
        }
        builder.get(self._mode, self._build_standard_keypad)()

    def _clear_keypad(self):
        for w in self._keypad_frame.winfo_children():
            w.destroy()

    # ── Clavier Standard ──

    def _build_standard_keypad(self):
        frame = self._keypad_frame
        buttons = [
            ('MC', self._mem_clear, 'mem'), ('MR', self._mem_recall, 'mem'),
            ('M+', self._mem_add, 'mem'), ('M−', self._mem_sub, 'mem'),
            ('√', lambda: self._insert_func('sqrt'), 'func'), ('x²', self._square, 'func'),
            ('1/x', self._inverse, 'func'), ('|x|', lambda: self._insert_func('abs'), 'func'),
            ('(', lambda: self._insert_char('('), 'util'), (')', lambda: self._insert_char(')'), 'util'),
            ('C', self._clear, 'action'), ('⌫', self._backspace, 'action'),
            ('7', lambda: self._digit('7'), 'd'), ('8', lambda: self._digit('8'), 'd'),
            ('9', lambda: self._digit('9'), 'd'), ('÷', lambda: self._insert_op('/'), 'o'),
            ('4', lambda: self._digit('4'), 'd'), ('5', lambda: self._digit('5'), 'd'),
            ('6', lambda: self._digit('6'), 'd'), ('×', lambda: self._insert_op('*'), 'o'),
            ('1', lambda: self._digit('1'), 'd'), ('2', lambda: self._digit('2'), 'd'),
            ('3', lambda: self._digit('3'), 'd'), ('−', lambda: self._insert_op('-'), 'o'),
            ('±', self._toggle_sign, 'util'), ('0', lambda: self._digit('0'), 'd'),
            ('.', lambda: self._insert_char('.'), 'd'), ('=', self._evaluate, 'eq'),
            ('%', lambda: self._insert_char('%'), 'o'),
        ]
        self._layout_buttons(frame, buttons)

    # ── Clavier Scientifique ──

    def _build_scientific_keypad(self):
        frame = self._keypad_frame
        buttons = [
            ('sin', lambda: self._insert_func('sin'), 'func'), ('cos', lambda: self._insert_func('cos'), 'func'),
            ('tan', lambda: self._insert_func('tan'), 'func'), ('π', lambda: self._insert_const('pi'), 'const'),
            ('log', lambda: self._insert_func('log'), 'func'), ('ln', lambda: self._insert_func('ln'), 'func'),
            ('asin', lambda: self._insert_func('asin'), 'func'), ('e', lambda: self._insert_const('e'), 'const'),
            ('xⁿ', lambda: self._insert_op('**'), 'func'), ('√', lambda: self._insert_func('sqrt'), 'func'),
            ('φ', lambda: self._insert_const('phi'), 'const'), ('√2', lambda: self._insert_const('sqrt2'), 'const'),
            ('MC', self._mem_clear, 'mem'), ('MR', self._mem_recall, 'mem'),
            ('M+', self._mem_add, 'mem'), ('M−', self._mem_sub, 'mem'),
            ('(', lambda: self._insert_char('('), 'util'), (')', lambda: self._insert_char(')'), 'util'),
            ('C', self._clear, 'action'), ('⌫', self._backspace, 'action'),
            ('7', lambda: self._digit('7'), 'd'), ('8', lambda: self._digit('8'), 'd'),
            ('9', lambda: self._digit('9'), 'd'), ('÷', lambda: self._insert_op('/'), 'o'),
            ('4', lambda: self._digit('4'), 'd'), ('5', lambda: self._digit('5'), 'd'),
            ('6', lambda: self._digit('6'), 'd'), ('×', lambda: self._insert_op('*'), 'o'),
            ('1', lambda: self._digit('1'), 'd'), ('2', lambda: self._digit('2'), 'd'),
            ('3', lambda: self._digit('3'), 'd'), ('−', lambda: self._insert_op('-'), 'o'),
            ('±', self._toggle_sign, 'util'), ('0', lambda: self._digit('0'), 'd'),
            ('.', lambda: self._insert_char('.'), 'd'), ('=', self._evaluate, 'eq'),
            ('abs', lambda: self._insert_func('abs'), 'func'), ('x²', self._square, 'func'),
        ]
        self._layout_buttons(frame, buttons, cols=4)

    # ── Clavier Pourcentage ──

    def _build_percentage_keypad(self):
        frame = self._keypad_frame
        ttk.Label(frame, text=str(_("Saisissez un montant, puis choisissez l'opération")),
                  font=('Segoe UI', 9), wraplength=300).grid(row=0, column=0, columnspan=4, pady=(0, 8))

        buttons = [
            ('7', lambda: self._digit('7'), 'd'), ('8', lambda: self._digit('8'), 'd'),
            ('9', lambda: self._digit('9'), 'd'), ('⌫', self._backspace, 'action'),
            ('4', lambda: self._digit('4'), 'd'), ('5', lambda: self._digit('5'), 'd'),
            ('6', lambda: self._digit('6'), 'd'), ('C', self._clear, 'action'),
            ('1', lambda: self._digit('1'), 'd'), ('2', lambda: self._digit('2'), 'd'),
            ('3', lambda: self._digit('3'), 'd'), ('.', lambda: self._insert_char('.'), 'd'),
            ('±', self._toggle_sign, 'util'), ('0', lambda: self._digit('0'), 'd'),
            ('=', self._evaluate, 'eq'), ('%', lambda: self._insert_char('%'), 'o'),
        ]
        self._layout_buttons(frame, buttons, start_row=1)

        sep = ttk.Separator(frame, orient=tk.HORIZONTAL)
        sep.grid(row=5, column=0, columnspan=4, sticky='ew', pady=8)

        ttk.Label(frame, text=str(_("Calculs rapides")), font=('Segoe UI', 9, 'bold')).grid(row=6, column=0, columnspan=4, sticky='w')
        pct_buttons = [
            ('% du montant', self._pct_of, 7), ('Remise %', self._discount, 8),
            ('Pourboire 15%', lambda: self._tip(15), 9), ('Pourboire 20%', lambda: self._tip(20), 10),
            ('+ X%', self._increase, 11), ('- X%', self._decrease, 12),
        ]
        for text, cmd, row in pct_buttons:
            ttk.Button(frame, text=str(_(text)), command=cmd, width=18).grid(row=row, column=0, columnspan=4, pady=1, sticky='ew')

    def _pct_of(self):
        try:
            val = safe_eval(self.expression)
            result = val / 100
            self._add_history(f"{_format_result(val)}%", _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = str(_("Erreur"))
        self._refresh_display()

    def _discount(self):
        try:
            val = safe_eval(self.expression)
            result = val * 0.9
            self._add_history(str(_("Remise 10% sur {val}")).format(val=_format_result(val)), _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = str(_("Erreur"))
        self._refresh_display()

    def _tip(self, pct: int):
        try:
            val = safe_eval(self.expression)
            result = val * (1 + pct / 100)
            self._add_history(str(_("+{pct}% sur {val}")).format(pct=pct, val=_format_result(val)), _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = str(_("Erreur"))
        self._refresh_display()

    def _increase(self):
        try:
            val = safe_eval(self.expression)
            result = val * 1.10
            self._add_history(str(_("+10% sur {val}")).format(val=_format_result(val)), _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = str(_("Erreur"))
        self._refresh_display()

    def _decrease(self):
        try:
            val = safe_eval(self.expression)
            result = val * 0.90
            self._add_history(str(_("-10% sur {val}")).format(val=_format_result(val)), _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = str(_("Erreur"))
        self._refresh_display()

    # ── Clavier Bases ──

    def _build_bases_keypad(self):
        frame = self._keypad_frame
        ttk.Label(frame, text=str(_("Entrez un nombre, choisissez la base source puis la base cible")),
                  font=('Segoe UI', 9), wraplength=300).grid(row=0, column=0, columnspan=4, pady=(0, 6))

        self._base_from_var = tk.StringVar(value='Décimal')
        self._base_to_var = tk.StringVar(value='Hexadécimal')

        base_frame = ttk.Frame(frame)
        base_frame.grid(row=1, column=0, columnspan=4, pady=(0, 6), sticky='ew')
        ttk.Label(base_frame, text=str(_("De :")), font=('Segoe UI', 9)).pack(side=tk.LEFT)
        ttk.Combobox(base_frame, textvariable=self._base_from_var, values=list(_BASES.keys()),
                     state='readonly', width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(base_frame, text=str(_("Vers :")), font=('Segoe UI', 9)).pack(side=tk.LEFT)
        ttk.Combobox(base_frame, textvariable=self._base_to_var, values=list(_BASES.keys()),
                     state='readonly', width=12).pack(side=tk.LEFT, padx=4)

        ttk.Button(base_frame, text=str(_("Convertir")), command=self._convert_bases).pack(side=tk.LEFT, padx=6)

        digits = [
            ('A', lambda: self._digit('A')), ('B', lambda: self._digit('B')),
            ('C', lambda: self._digit('C')), ('D', lambda: self._digit('D')),
            ('E', lambda: self._digit('E')), ('F', lambda: self._digit('F')),
        ]
        for i, (txt, cmd) in enumerate(digits):
            ttk.Button(frame, text=txt, command=cmd, width=4).grid(row=2, column=i, padx=1, pady=1)

        num_buttons = [
            ('7', lambda: self._digit('7')), ('8', lambda: self._digit('8')),
            ('9', lambda: self._digit('9')), ('÷', lambda: self._insert_op('/')),
            ('4', lambda: self._digit('4')), ('5', lambda: self._digit('5')),
            ('6', lambda: self._digit('6')), ('×', lambda: self._insert_op('*')),
            ('1', lambda: self._digit('1')), ('2', lambda: self._digit('2')),
            ('3', lambda: self._digit('3')), ('−', lambda: self._insert_op('-')),
            ('±', self._toggle_sign), ('0', lambda: self._digit('0')),
            ('.', lambda: self._insert_char('.')), ('=', self._evaluate),
        ]
        for i, (txt, cmd) in enumerate(num_buttons):
            r, c = divmod(i, 4)
            ttk.Button(frame, text=txt, command=cmd, width=4).grid(row=3 + r, column=c, padx=1, pady=1)

        self._base_result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._base_result_var, font=('Consolas', 10, 'bold'),
                  foreground='#5599ff', wraplength=300).grid(row=7, column=0, columnspan=4, pady=(8, 0), sticky='w')
        ttk.Button(frame, text=str(_("C")), command=self._clear, width=4).grid(row=8, column=0, padx=1, pady=1)
        ttk.Button(frame, text=str(_("⌫")), command=self._backspace, width=4).grid(row=8, column=1, padx=1, pady=1)

    def _convert_bases(self):
        try:
            from_base = _BASES[self._base_from_var.get()]
            to_base = _BASES[self._base_to_var.get()]
            val = int(self.expression, from_base) if from_base != 10 else int(safe_eval(self.expression))
            if to_base == 10:
                result = str(val)
            else:
                digits = "0123456789ABCDEF"
                if val == 0:
                    result = "0"
                else:
                    neg = val < 0
                    v = abs(val)
                    result = ""
                    while v > 0:
                        result = digits[v % to_base] + result
                        v //= to_base
                    if neg:
                        result = "-" + result
            self._base_result_var.set(f"{self._base_from_var.get()} → {self._base_to_var.get()} : {result}")
            self._add_history(f"base({self.expression})", result)
        except Exception as exc:
            self._base_result_var.set(str(_("Erreur")))

    # ── Clavier Unités ──

    def _build_unit_keypad(self):
        frame = self._keypad_frame
        ttk.Label(frame, text=str(_("Convertissez entre unités")),
                  font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, columnspan=4, pady=(0, 6))

        self._unit_cat_var = tk.StringVar(value='Température')
        self._unit_from_var = tk.StringVar(value='°C')
        self._unit_to_var = tk.StringVar(value='°F')

        cat_frame = ttk.Frame(frame)
        cat_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 4))
        ttk.Label(cat_frame, text=str(_("Catégorie :")), font=('Segoe UI', 9)).pack(side=tk.LEFT)
        ttk.Combobox(cat_frame, textvariable=self._unit_cat_var, values=list(_UNIT_CATEGORIES.keys()),
                     state='readonly', width=12).pack(side=tk.LEFT, padx=4)
        self._unit_cat_var.trace_add('write', lambda *_: self._on_unit_cat_change())

        unit_frame = ttk.Frame(frame)
        unit_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(0, 4))
        ttk.Label(unit_frame, text=str(_("De :")), font=('Segoe UI', 9)).pack(side=tk.LEFT)
        self._unit_from_cb = ttk.Combobox(unit_frame, textvariable=self._unit_from_var, state='readonly', width=6)
        self._unit_from_cb.pack(side=tk.LEFT, padx=4)
        ttk.Label(unit_frame, text=str(_("Vers :")), font=('Segoe UI', 9)).pack(side=tk.LEFT)
        self._unit_to_cb = ttk.Combobox(unit_frame, textvariable=self._unit_to_var, state='readonly', width=6)
        self._unit_to_cb.pack(side=tk.LEFT, padx=4)
        ttk.Button(unit_frame, text=str(_("Convertir")), command=self._convert_units).pack(side=tk.LEFT, padx=6)

        num_buttons = [
            ('7', lambda: self._digit('7')), ('8', lambda: self._digit('8')),
            ('9', lambda: self._digit('9')), ('⌫', self._backspace),
            ('4', lambda: self._digit('4')), ('5', lambda: self._digit('5')),
            ('6', lambda: self._digit('6')), ('C', self._clear),
            ('1', lambda: self._digit('1')), ('2', lambda: self._digit('2')),
            ('3', lambda: self._digit('3')), ('.', lambda: self._insert_char('.')),
            ('±', self._toggle_sign), ('0', lambda: self._digit('0')),
            ('=', self._evaluate), ('.', lambda: self._insert_char('.')),
        ]
        for i, (txt, cmd) in enumerate(num_buttons):
            r, c = divmod(i, 4)
            ttk.Button(frame, text=txt, command=cmd, width=4).grid(row=3 + r, column=c, padx=1, pady=1)

        self._unit_result_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._unit_result_var, font=('Consolas', 10, 'bold'),
                  foreground='#5599ff', wraplength=300).grid(row=7, column=0, columnspan=4, pady=(8, 0), sticky='w')

        self._on_unit_cat_change(self._unit_cat_var.get())

    def _on_unit_cat_change(self, _cat=None):
        cat = self._unit_cat_var.get()
        unités = _UNIT_CATEGORIES[cat]['unités']
        self._unit_from_cb['values'] = unités
        self._unit_to_cb['values'] = unités
        if unités:
            self._unit_from_var.set(unités[0])
            self._unit_to_var.set(unités[1] if len(unités) > 1 else unités[0])

    def _convert_units(self):
        try:
            val = safe_eval(self.expression)
            cat = _UNIT_CATEGORIES[self._unit_cat_var.get()]
            from_u = self._unit_from_var.get()
            to_u = self._unit_to_var.get()
            base_val = cat['vers_base'][from_u](val)
            result = cat['depuis_base'][to_u](base_val)
            result_str = _format_result(result)
            self._unit_result_var.set(f"{_format_result(val)} {from_u} = {result_str} {to_u}")
            self._add_history(f"{_format_result(val)} {from_u} → {to_u}", result_str)
            self.expression = result_str
        except Exception as exc:
            self._unit_result_var.set(str(_("Erreur")))
        self._refresh_display()

    # ── Layout générique ──

    def _layout_buttons(self, frame, buttons, cols=4, start_row=0):
        styles = {
            'd': {'width': 4, 'padding': (6, 6)},
            'o': {'width': 4, 'padding': (6, 6)},
            'util': {'width': 4, 'padding': (6, 6)},
            'func': {'width': 4, 'padding': (6, 6)},
            'mem': {'width': 4, 'padding': (6, 6)},
            'const': {'width': 4, 'padding': (6, 6)},
            'action': {'width': 4, 'padding': (6, 6)},
            'eq': {'width': 4, 'padding': (6, 6)},
        }
        for i, item in enumerate(buttons):
            text, command = item[0], item[1]
            kind = item[2] if len(item) > 2 else 'd'
            row, col = divmod(i, cols)
            btn = ttk.Button(frame, text=text, command=command, **styles.get(kind, styles['d']))
            btn.grid(row=start_row + row, column=col, padx=1, pady=1, sticky='nsew')
            if kind == 'eq':
                self.equal_btn = btn
        for c in range(cols):
            frame.columnconfigure(c, weight=1)

    # ── Logique commune ──

    def _refresh_display(self):
        self.display_var.set(self.expression)

    def _update_memory_indicator(self):
        if self._has_memory:
            self.memory_indicator.config(text=f"M = {_format_result(self._memory)}")
        else:
            self.memory_indicator.config(text="")

    def _digit(self, digit: str):
        if self.expression in ("0", str(_("Erreur"))):
            self.expression = digit
        else:
            self.expression += digit
        self._refresh_display()

    def _insert_char(self, token: str):
        if self.expression == str(_("Erreur")):
            return
        if token == '.':
            last_op = max(self.expression.rfind(op) for op in '+-*/%(')
            current_number = self.expression[last_op + 1:]
            if '.' in current_number:
                return
            if not current_number or not current_number[-1].isdigit():
                if self.expression and self.expression[-1] in '+-*/%(':
                    self.expression += '0'
            self.expression += '.'
        elif token == '(':
            if self.expression in ("0", "Erreur"):
                self.expression = "("
            else:
                self.expression += '('
            self._paren_depth += 1
        elif token == ')':
            if self._paren_depth > 0:
                self.expression += ')'
                self._paren_depth -= 1
        elif token == '%':
            self.expression += '%'
        else:
            self.expression += token
        self._refresh_display()

    def _insert_op(self, op: str):
        if self.expression == "Erreur":
            return
        if self.expression and self.expression[-1] in '+-*/%(':
            self.expression = self.expression[:-1] + op
        else:
            self.expression += op
        self._refresh_display()

    def _insert_func(self, func_name: str):
        if self.expression in ("0", "Erreur"):
            self.expression = f"{func_name}("
        else:
            self.expression += f"{func_name}("
        self._paren_depth += 1
        self._refresh_display()

    def _insert_const(self, const_name: str):
        val = _format_result(_CONSTANTS[const_name])
        if self.expression in ("0", "Erreur"):
            self.expression = val
        else:
            self.expression += val
        self._refresh_display()

    def _square(self):
        if self.expression == "Erreur":
            return
        try:
            value = safe_eval(self.expression)
            result = value ** 2
            self._add_history(f"{self.expression}²", _format_result(result))
            self.expression = _format_result(result)
        except Exception:
            self.expression = "Erreur"
        self._refresh_display()

    def _inverse(self):
        if self.expression == "Erreur":
            return
        try:
            value = safe_eval(self.expression)
            if value == 0:
                self.expression = "Erreur"
            else:
                result = 1 / value
                self._add_history(f"1/({self.expression})", _format_result(result))
                self.expression = _format_result(result)
        except Exception:
            self.expression = "Erreur"
        self._refresh_display()

    def _clear(self):
        self.expression = "0"
        self._paren_depth = 0
        self._refresh_display()

    def _backspace(self):
        if self.expression == "Erreur":
            self._clear()
            return
        if self.expression.endswith('('):
            self._paren_depth = max(0, self._paren_depth - 1)
        elif self.expression.endswith(')'):
            self._paren_depth += 1
        self.expression = self.expression[:-1] if len(self.expression) > 1 else "0"
        self._refresh_display()

    def _toggle_sign(self):
        if self.expression == "Erreur":
            return
        i = len(self.expression)
        while i > 0 and (self.expression[i - 1].isdigit() or self.expression[i - 1] == '.'):
            i -= 1
        if i > 0 and self.expression[i - 1] in '+-':
            i -= 1
        number = self.expression[i:]
        if not number:
            return
        new_number = number[1:] if number.startswith('-') else '-' + number
        self.expression = self.expression[:i] + new_number
        self._refresh_display()

    def _evaluate(self):
        if self.expression == "Erreur":
            return
        while self._paren_depth > 0:
            self.expression += ')'
            self._paren_depth -= 1
        try:
            value = safe_eval(self.expression)
            result_str = _format_result(value)
            self._add_history(self.expression, result_str)
            self.expression = result_str
        except (ZeroDivisionError, ValueError, SyntaxError, ArithmeticError):
            self.expression = "Erreur"
        self._refresh_display()

    # ── Mémoire ──

    def _mem_clear(self):
        self._memory = 0.0
        self._has_memory = False
        self._update_memory_indicator()

    def _mem_recall(self):
        if not self._has_memory:
            return
        mem_str = _format_result(self._memory)
        if self.expression in ("0", "Erreur"):
            self.expression = mem_str
        else:
            self.expression += mem_str
        self._refresh_display()

    def _mem_add(self):
        try:
            value = safe_eval(self.expression)
            self._memory += value
            self._has_memory = True
            self._update_memory_indicator()
        except Exception:
            logger.debug("Exception in memory add operation", exc_info=True)

    def _mem_sub(self):
        try:
            value = safe_eval(self.expression)
            self._memory -= value
            self._has_memory = True
            self._update_memory_indicator()
        except Exception:
            logger.debug("Exception in memory subtract operation", exc_info=True)

    # ── Historique ──

    def _add_history(self, expression: str, result: str):
        self._history.append((expression, result))
        if len(self._history) > _HISTORY_MAX:
            self._history.pop(0)
        self._history_listbox.delete(0, tk.END)
        for expr, res in self._history:
            self._history_listbox.insert(tk.END, f"{expr} = {res}")
        self._history_listbox.see(tk.END)

    def _clear_history(self):
        self._history.clear()
        self._history_listbox.delete(0, tk.END)

    def _on_history_select(self, _event):
        sel = self._history_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._history):
            _, result = self._history[idx]
            self.expression = result
            self._refresh_display()

    # ── Copier / Coller ──

    def _copy_result(self):
        if self.expression and self.expression != "Erreur":
            self.clipboard_clear()
            self.clipboard_append(self.expression)

    def _paste_expression(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                safe_eval(text.replace(' ', ''))
                self.expression = text
                self._refresh_display()
        except Exception:
            logger.debug("Exception in paste expression from clipboard", exc_info=True)

    # ── Clavier physique ──

    def _bind_local_keys(self):
        self.bind('<Key>', self._on_key, add='+')
        for widget in self._iter_descendants():
            widget.bind('<Key>', self._on_key, add='+')

    def _iter_descendants(self):
        stack = list(self.winfo_children())
        while stack:
            widget = stack.pop()
            yield widget
            stack.extend(widget.winfo_children())

    def enable_global_keys(self):
        if not self._global_keys:
            self._global_keys = True
            self._global_keys_funcid = str(
                self.bind_all('<Key>', self._on_key, add='+')
            )

    def disable_global_keys(self):
        if self._global_keys:
            self._global_keys = False
            funcid = getattr(self, '_global_keys_funcid', None)
            if funcid:
                self.unbind_all('<Key>', funcid)

    def _on_key(self, event):
        key = event.char
        state = event.state
        if state & 0x4 and event.keysym == 'c':
            self._copy_result()
            return "break"
        if state & 0x4 and event.keysym == 'v':
            self._paste_expression()
            return "break"
        if event.keysym == 'Return':
            self._evaluate()
            return "break"
        if event.keysym == 'BackSpace':
            self._backspace()
            return "break"
        if event.keysym == 'Escape':
            self._clear()
            return "break"
        if key.isdigit():
            self._digit(key)
            return "break"
        if key in '*/%':
            self._insert_op(key)
            return "break"
        if key in '+-':
            self._insert_op(key)
            return "break"
        if key == '.':
            self._insert_char('.')
            return "break"
        if key in '()':
            self._insert_char(key)
            return "break"
        return None


class CalculatorDialog(BaseDialog):
    """Fenêtre de calculatrice avec modes multiples."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Calculatrice"),
            geometry="620x580",
            minsize=(560, 520),
        )
        self.resizable(True, True)
        self.content = CalculatorContent(self, global_keys=True)
        self.content.pack(fill=tk.BOTH, expand=True)

    def destroy(self):
        try:
            self.content.disable_global_keys()
        except Exception:
            logger.debug("Exception disabling global keys on destroy", exc_info=True)
        super().destroy()


def open_calculator(parent):
    """Ouvre la calculatrice."""
    CalculatorDialog(parent)