# src/tools/_syntax.py
"""Moteur de surlignage syntaxique pour le bloc-notes amélioré.

Supporte : Python, JavaScript, JSON, HTML, CSS.
Utilise le système de tags de tk.Text pour coloriser le code.
"""
from __future__ import annotations

import re
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Détection de langage
# ═══════════════════════════════════════════════════════════════════════════

_EXT_MAP = {
    '.py': 'python',
    '.pyw': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.json': 'json',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'css',
    '.less': 'css',
    '.md': 'markdown',
    '.txt': 'text',
    '.csv': 'text',
    '.xml': 'html',
}


def detect_language(filename: str | None, content: str = '') -> str:
    """Détecte le langage depuis le nom de fichier et le contenu."""
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXT_MAP:
            lang = _EXT_MAP[ext]
            if lang != 'text':
                return lang

    if content.strip():
        stripped = content.strip()
        if stripped.startswith('{') and ('"' in stripped):
            return 'json'
        if re.search(r'<(!DOCTYPE|html|div|span|p|body|head)', content, re.I):
            return 'html'
        if re.search(r'^\s*[\w-]+\s*:\s*[\w#]', content, re.M) or re.search(r'\{[^}]*[\w-]+\s*:', content):
            return 'css'
        if re.search(r'^\s*(def|class|import|from|return|if|elif|else)\s', content, re.M):
            return 'python'
        if re.search(r'^\s*(var|let|const|function|return|if|else|for|while)\s', content, re.M):
            return 'javascript'

    return 'text'


# ═══════════════════════════════════════════════════════════════════════════
# Palette de couleurs (VS Code Dark)
# ═══════════════════════════════════════════════════════════════════════════

COLORS = {
    'keyword':    '#569CD6',
    'string':     '#CE9178',
    'number':     '#B5CEA8',
    'comment':    '#6A9955',
    'operator':   '#D4D4D4',
    'tag':        '#569CD6',
    'attribute':  '#9CDCFE',
    'key':        '#9CDCFE',
    'bracket':    '#FFD700',
    'function':   '#DCDCAA',
    'builtin':    '#4EC9B0',
    'decorator':  '#C586C0',
    'regex':      '#D16969',
    'constant':   '#4FC1FF',
}

TAG_NAMES = {
    'keyword':   'syn_keyword',
    'string':    'syn_string',
    'number':    'syn_number',
    'comment':   'syn_comment',
    'operator':  'syn_operator',
    'tag':       'syn_tag',
    'attribute': 'syn_attribute',
    'key':       'syn_key',
    'bracket':   'syn_bracket',
    'function':  'syn_function',
    'builtin':   'syn_builtin',
    'decorator': 'syn_decorator',
    'regex':     'syn_regex',
    'constant':  'syn_constant',
}


# ═══════════════════════════════════════════════════════════════════════════
# Patterns par langage
# ═══════════════════════════════════════════════════════════════════════════

_PYTHON_KEYWORDS = frozenset({
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
    'try', 'while', 'with', 'yield',
})

_PYTHON_BUILTINS = frozenset({
    'print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict',
    'set', 'tuple', 'bool', 'type', 'input', 'open', 'super', 'self',
    'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed', 'abs',
    'all', 'any', 'bin', 'hex', 'oct', 'chr', 'ord', 'min', 'max',
    'sum', 'round', 'isinstance', 'hasattr', 'getattr', 'setattr',
})

_JS_KEYWORDS = frozenset({
    'async', 'await', 'break', 'case', 'catch', 'class', 'const',
    'continue', 'debugger', 'default', 'delete', 'do', 'else',
    'export', 'extends', 'finally', 'for', 'from', 'function',
    'if', 'import', 'in', 'instanceof', 'let', 'new', 'of',
    'return', 'static', 'super', 'switch', 'this', 'throw',
    'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
})

_JS_CONSTANTS = frozenset({
    'true', 'false', 'null', 'undefined', 'NaN', 'Infinity',
})

_JSON_CONSTANTS = frozenset({'true', 'false', 'null'})

_CSS_PROPERTIES = frozenset({
    'color', 'background', 'margin', 'padding', 'border', 'display',
    'font', 'width', 'height', 'position', 'top', 'left', 'right',
    'bottom', 'z-index', 'opacity', 'overflow', 'text-align',
    'line-height', 'letter-spacing', 'word-spacing', 'float', 'clear',
    'flex', 'grid', 'align', 'justify', 'content', 'items',
})


# ═══════════════════════════════════════════════════════════════════════════
# Regex patterns
# ═══════════════════════════════════════════════════════════════════════════

def _build_python_patterns() -> list[tuple[str, str]]:
    return [
        ('comment',   r'#[^\n]*'),
        ('string',    r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),
        ('decorator', r'@\w+'),
        ('number',    r'\b\d+\.?\d*(?:e[+-]?\d+)?\b'),
        ('builtin',   r'\b(?:' + '|'.join(_PYTHON_BUILTINS) + r')\b'),
        ('keyword',   r'\b(?:' + '|'.join(_PYTHON_KEYWORDS) + r')\b'),
        ('function',  r'\b\w+(?=\()'),
        ('operator',  r'=|!=|<=|>=|<>|<<|>>|\*\*|[+\-*/%&|^~<>]'),
        ('bracket',   r'[()[\]{}]]'),
    ]


def _build_js_patterns() -> list[tuple[str, str]]:
    return [
        ('comment',   r'//[^\n]*|/\*[\s\S]*?\*/'),
        ('string',    r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`'),
        ('regex',     r'/(?:[^/\\]|\\.)+/[gimsuy]*'),
        ('constant',  r'\b(?:' + '|'.join(_JS_CONSTANTS) + r')\b'),
        ('number',    r'\b\d+\.?\d*(?:e[+-]?\d+)?\b'),
        ('keyword',   r'\b(?:' + '|'.join(_JS_KEYWORDS) + r')\b'),
        ('function',  r'\b\w+(?=\()'),
        ('operator',  r'=|!=|===|!==|<=|>=|=>|&&|\|\||[+\-*/%&|^~<>!?]'),
        ('bracket',   r'[()[\]{}]]'),
    ]


def _build_json_patterns() -> list[tuple[str, str]]:
    return [
        ('key',       r'"[^"]*"(?=\s*:)'),
        ('string',    r'"(?:[^"\\]|\\.)*"'),
        ('constant',  r'\b(?:' + '|'.join(_JSON_CONSTANTS) + r')\b'),
        ('number',    r'-?\b\d+\.?\d*(?:e[+-]?\d+)?\b'),
        ('bracket',   r'[()[\]{}]]'),
        ('operator',  r'[,:;]'),
    ]


def _build_html_patterns() -> list[tuple[str, str]]:
    return [
        ('comment',   r'<!--[\s\S]*?-->'),
        ('tag',       r'</?[a-zA-Z][a-zA-Z0-9]*\b[^>]*?/?>'),
        ('attribute', r'\b[a-zA-Z-]+(?==)'),
        ('string',    r'"[^"]*"|\'[^\']*\''),
    ]


def _build_css_patterns() -> list[tuple[str, str]]:
    return [
        ('comment',   r'/\*[\s\S]*?\*/'),
        ('string',    r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),
        ('number',    r'[+-]?\b\d+\.?\d*(?:px|em|rem|%|vh|vw|pt|cm|mm|in|s|ms)?\b'),
        ('keyword',   r'@[a-zA-Z-]+'),
        ('bracket',   r'[(){}[\]]'),
        ('operator',  r'[:;{},]'),
    ]


_PATTERNS = {
    'python':     _build_python_patterns,
    'javascript': _build_js_patterns,
    'json':       _build_json_patterns,
    'html':       _build_html_patterns,
    'css':        _build_css_patterns,
}


# ═══════════════════════════════════════════════════════════════════════════
# Moteur principal
# ═══════════════════════════════════════════════════════════════════════════

class SyntaxHighlighter:
    """Surligne le code source dans un widget tk.Text."""

    def __init__(self, text_widget):
        self.text = text_widget
        self._compiled: dict[str, list[tuple[str, re.Pattern]]] = {}
        self._configure_tags()

    def _configure_tags(self):
        for token, color in COLORS.items():
            tag = TAG_NAMES.get(token)
            if tag:
                self.text.tag_configure(tag, foreground=color)

    def _get_patterns(self, lang: str) -> list[tuple[str, re.Pattern]]:
        if lang not in self._compiled:
            builders = _PATTERNS
            builder = builders.get(lang)
            if builder:
                self._compiled[lang] = [
                    (token, re.compile(pattern, re.MULTILINE))
                    for token, pattern in builder()
                ]
            else:
                self._compiled[lang] = []
        return self._compiled[lang]

    def highlight_range(self, start: str, end: str, lang: str):
        """Applique le surlignage sur la plage [start, end] (format tkinter '1.0')."""
        patterns = self._get_patterns(lang)
        if not patterns:
            return

        # Supprimer les tags existants dans la plage
        for tag in TAG_NAMES.values():
            self.text.tag_remove(tag, start, end)

        content = self.text.get(start, end)
        if not content:
            return

        line_start = start.split('.')[0]
        offset = self.text.index(start)

        for token_name, pattern in patterns:
            tag = TAG_NAMES.get(token_name)
            if not tag:
                continue
            for match in pattern.finditer(content):
                # Calculer les positions tkinter
                match_start = f"{line_start}.{match.start()}"
                match_end = f"{line_start}.{match.end()}"
                self.text.tag_add(tag, match_start, match_end)

    def highlight_all(self, lang: str):
        """Surligne tout le contenu du widget."""
        self.highlight_range('1.0', tk.END, lang)


import tkinter as tk


def highlight_all(text_widget, lang: str):
    """Fonction de commodité : surligne tout le contenu."""
    highlighter = SyntaxHighlighter(text_widget)
    highlighter.highlight_range('1.0', tk.END, lang)
