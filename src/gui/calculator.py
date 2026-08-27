# src/gui/calculator.py
"""Calculatrice simple et sûre (évaluation via AST, pas de eval brut).

Expose `CalculatorContent`, un cadre réutilisable (intégrable au workspace
du Shell TE), et `CalculatorDialog`, la fenêtre de dialogue classique.
"""
import ast
import operator
import tkinter as tk
from tkinter import ttk

from src.i18n import _
from src.logger import setup_logger
from .base_dialog import BaseDialog

logger = setup_logger(__name__)

# Opérateurs autorisés pour l'évaluation
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
    raise ValueError("Expression non supportée")


def _format_result(value) -> str:
    """Formate un résultat : entier si entier, sinon arrondi pour éviter 0.1+0.2."""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{round(value, 12):g}"
    return str(value)


class CalculatorContent(ttk.Frame):
    """Cadre de calculatrice réutilisable.

    - intégré au workspace : `CalculatorContent(parent)`
    - dans un dialogue    : wrapper par `CalculatorDialog`
    """

    def __init__(self, parent, global_keys: bool = False, **kwargs):
        super().__init__(parent, padding=10, **kwargs)
        self.expression = "0"
        self._global_keys = False
        self._create_widgets()
        if global_keys:
            self.enable_global_keys()
        else:
            self._bind_local_keys()
        self._refresh_display()

    # --- Construction ---

    def _create_widgets(self):
        # Affichage
        self.display_var = tk.StringVar(value="0")
        display = ttk.Entry(
            self,
            textvariable=self.display_var,
            font=('Segoe UI', 20),
            justify=tk.RIGHT,
            state='readonly',
        )
        display.pack(fill=tk.X, pady=(0, 10))

        # Clavier
        grid = ttk.Frame(self)
        grid.pack(fill=tk.BOTH, expand=True)

        buttons = [
            # (texte, commande, sticky)
            ('C', self._clear, 'n'),
            ('⌫', self._backspace, 'n'),
            ('%', lambda: self._insert('%'), 'n'),
            ('÷', lambda: self._insert('/'), 'o'),
            ('7', lambda: self._digit('7'), 'd'),
            ('8', lambda: self._digit('8'), 'd'),
            ('9', lambda: self._digit('9'), 'd'),
            ('×', lambda: self._insert('*'), 'o'),
            ('4', lambda: self._digit('4'), 'd'),
            ('5', lambda: self._digit('5'), 'd'),
            ('6', lambda: self._digit('6'), 'd'),
            ('−', lambda: self._insert('-'), 'o'),
            ('1', lambda: self._digit('1'), 'd'),
            ('2', lambda: self._digit('2'), 'd'),
            ('3', lambda: self._digit('3'), 'd'),
            ('+', lambda: self._insert('+'), 'o'),
            ('±', self._toggle_sign, 'n'),
            ('0', lambda: self._digit('0'), 'd'),
            ('.', lambda: self._insert('.'), 'd'),
            ('=', self._evaluate, 'eq'),
        ]

        styles = {
            'd': {'width': 5, 'padding': (8, 8)},
            'o': {'width': 5, 'padding': (8, 8)},
            'n': {'width': 5, 'padding': (8, 8)},
            'eq': {'width': 5, 'padding': (8, 8)},
        }

        for i, (text, command, kind) in enumerate(buttons):
            row, col = divmod(i, 4)
            btn = ttk.Button(grid, text=text, command=command, **styles[kind])
            btn.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            if kind == 'eq':
                self.equal_btn = btn

        for c in range(4):
            grid.columnconfigure(c, weight=1)
        for r in range(5):
            grid.rowconfigure(r, weight=1)

    # --- Logique ---

    def _refresh_display(self):
        """Affiche l'expression courante."""
        self.display_var.set(self.expression)

    def _digit(self, digit: str):
        """Ajoute un chiffre (évite les zéros en tête inutiles)."""
        if self.expression == "0":
            self.expression = digit
        elif self.expression == "Erreur":
            self.expression = digit
        else:
            self.expression += digit
        self._refresh_display()

    def _insert(self, token: str):
        """Insère un opérateur ou un point décimal."""
        if self.expression == "Erreur":
            return
        if token == '.':
            # Nombre courant = portion après le dernier opérateur
            last_op = max(self.expression.rfind(op) for op in '+-*/%')
            current_number = self.expression[last_op + 1:]
            # Un seul point par nombre
            if '.' in current_number:
                return
            # Zéro initial si le nombre est vide
            if not current_number or not current_number[-1].isdigit():
                if self.expression and self.expression[-1] in '+-*/%':
                    self.expression += '0'
            self.expression += '.'
        elif token in ('+', '-', '*', '/', '%'):
            # Remplacer un opérateur consécutif
            if self.expression and self.expression[-1] in '+-*/%':
                self.expression = self.expression[:-1] + token
            else:
                self.expression += token
        else:
            self.expression += token
        self._refresh_display()

    def _clear(self):
        """Réinitialise l'expression."""
        self.expression = "0"
        self._refresh_display()

    def _backspace(self):
        """Efface le dernier caractère."""
        if self.expression == "Erreur":
            self._clear()
            return
        self.expression = self.expression[:-1] if len(self.expression) > 1 else "0"
        self._refresh_display()

    def _toggle_sign(self):
        """Inverse le signe du dernier nombre saisi."""
        if self.expression == "Erreur":
            return
        # Rechercher le début du dernier nombre
        i = len(self.expression)
        while i > 0 and (self.expression[i - 1].isdigit() or self.expression[i - 1] == '.'):
            i -= 1
        # Inclure un '-' ou '+' précédent
        if i > 0 and self.expression[i - 1] in '+-':
            i -= 1
        number = self.expression[i:]
        if not number:
            return
        if number.startswith('-'):
            new_number = number[1:]
        else:
            new_number = '-' + number
        self.expression = self.expression[:i] + new_number
        self._refresh_display()

    def _evaluate(self):
        """Calcule le résultat de l'expression."""
        if self.expression == "Erreur":
            return
        try:
            # Remplacer ×÷ par * et / pour l'évaluation (fait à la saisie, sécurité ici)
            value = safe_eval(self.expression)
            self.expression = _format_result(value)
        except (ZeroDivisionError, ValueError, SyntaxError, ArithmeticError):
            self.expression = "Erreur"
        self._refresh_display()

    # --- Clavier physique ---

    def _bind_local_keys(self):
        """Permet de taper avec le clavier physique quand le cadre a le focus."""
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
        """Branche le clavier physique au niveau global (usage en dialogue)."""
        if not self._global_keys:
            self._global_keys = True
            # Conserver le funcid pour ne débrancher QUE ce binding :
            # unbind_all('<Key>') sans funcid retirerait aussi les bindings
            # <Key> globaux d'autres composants.
            self._global_keys_funcid = str(self.bind_all('<Key>', self._on_key, add='+'))

    def disable_global_keys(self):
        """Débranche le clavier physique global (ce binding uniquement)."""
        if self._global_keys:
            self._global_keys = False
            funcid = getattr(self, '_global_keys_funcid', None)
            if funcid:
                self.unbind_all('<Key>', funcid)

    def _on_key(self, event):
        key = event.char
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
        if key in '+-*/%':
            self._insert(key)
            return "break"
        if key == '.':
            self._insert('.')
            return "break"
        return None


class CalculatorDialog(BaseDialog):
    """Fenêtre de calculatrice avec clavier virtuel et clavier physique."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title=_("Calculatrice"),
            geometry="320x430",
            minsize=(280, 380),
        )

        self.resizable(False, False)
        self.content = CalculatorContent(self, global_keys=True)
        self.content.pack(fill=tk.BOTH, expand=True)

    def destroy(self):
        """Nettoie les liaisons clavier globales avant fermeture."""
        try:
            self.content.disable_global_keys()
        except Exception:
            pass
        super().destroy()


def open_calculator(parent):
    """Ouvre la calculatrice."""
    CalculatorDialog(parent)