# src/tools/_syntax.py
"""Moteur de surlignage syntaxique pour le bloc-notes amélioré.

Supporte : Python, JavaScript, JSON, HTML, CSS, YAML.
Utilise le système de tags de tk.Text pour coloriser le code.
"""
from __future__ import annotations

import re
from pathlib import Path

import tkinter as tk

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
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.txt': 'text',
    '.csv': 'text',
    '.xml': 'html',
}

def detect_language(filename: str | None, content: str = '') -> str:
    """Détecte le langage depuis le nom de fichier et le contenu.

    Priorité : extension de fichier → reconnaissance par motif → ``'text'``.
    """
    lang: str | None = None

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
    'variable':   '#9CDCFE',
    'class':      '#4EC9B0',
    'title':      '#D7BA7D',
    'section':    '#4EC9B0',
    'meta':       '#C586C0',
    'string2':    '#CE9178',
    'line':       '#808080',
    'error':      '#F44747',
    'builtin2':   '#4EC9B0',
    'decorator':  '#DCDCAA',
    'prompt':     '#6A9955',
    'string3':    '#CE9178',
    'string4':    '#CE9178',
    'number2':    '#B5CEA8',
    'number3':    '#B5CEA8',
    'number4':    '#B5CEA8',
    'number5':    '#B5CEA8',
}

TAG_NAMES = {
    'keyword':    'Keyword',
    'string':     'String',
    'string2':    'String2',
    'string3':    'String3',
    'string4':    'String4',
    'number':     'Number',
    'number2':    'Number2',
    'number3':    'Number3',
    'number4':    'Number4',
    'number5':    'Number5',
    'comment':    'Comment',
    'operator':   'Operator',
    'bracket':    'Bracket',
    'function':   'Function',
    'builtin':    'Builtin',
    'builtin2':   'Builtin2',
    'decorator':  'Decorator',
    'variable':   'Variable',
    'class':      'Class',
    'title':      'Title',
    'section':    'Section',
    'meta':       'Meta',
    'tag':        'Tag',
    'attribute':  'Attribute',
    'key':        'Key',
    'prompt':     'Prompt',
    'line':       'Line',
    'error':      'Error',
}

# ═══════════════════════════════════════════════════════════════════════════
# Helpers Tkinter
# ═══════════════════════════════════════════════════════════════════════════

def _to_index(offset: int, content: str, base_line: int = 1, base_col: int = 0) -> str:
    """Convertit un offset dans ``content`` en index Tkinter 'ligne.col'."""
    line = content.count('\n', 0, offset)
    col = offset - (content.rfind('\n', 0, offset) + 1)
    return f"{base_line + line}.{base_col + col}"


# ═══════════════════════════════════════════════════════════════════════════
# Définitions de motifs par langage
# ═══════════════════════════════════════════════════════════════════════════

def _build_python_patterns() -> list[tuple[str, str]]:
    return [
        ('keyword', r'(?<![.#\w])\b(?:False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b'),
        ('builtin', r'(?<![.#\w])\b(?:abs|all|any|ascii|bin|bool|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip)\b'),
        ('decorator', r'(?<!\w)@\w+'),
        ('string', r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'),
        ('string2', r'("[\s\S]*?"|\'[\s\S]*?\')'),
        ('string3', r'f(["\']{3}[\s\S]*?\3|f)(?<!\\)(?:"[\s\S]*?"|\'[\s\S]*?\')'),
        ('string4', r'f(?<!\\)(?:"(?:\\.|[^"\\])*?"|\'(?:\\.|[^\'\\])*?\')'),
        ('number', r'\b(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+\.?\d*[eE][+-]?\d+|\d+\.?\d*|\d*\.?\d+[eE][+-]?\d+|\d*\.?\d+)\b'),
        ('comment', r'#.*(?:\n|$)'),
        ('operator', r'[=+\-*/%<>!&|^~?:;,.\[\]{}().]'),
    ]


def _build_js_patterns() -> list[tuple[str, str]]:
    return [
        ('keyword', r'(?<![.#\w])\b(?:async|await|break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|function|if|import|in|instanceof|let|new|of|return|static|super|switch|this|throw|try|typeof|var|void|while|with|yield)\b'),
        ('builtin', r'(?<![.#\w])\b(?:Array|Boolean|Date|Error|Function|JSON|Math|Number|Object|RegExp|String|Promise|Symbol|Map|Set|WeakMap|WeakSet|console|parseInt|parseFloat|isNaN|isFinite|decodeURI|encodeURI|decodeURIComponent|encodeURIComponent|escape|unescape|eval)\b'),
        ('string', r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'),
        ('string2', r'("(?:\\.|[^"\\])*?"|\'(?:\\.|[^\'\\])*?\')'),
        ('string3', r'`(?:\\.|[^`\\])*?`'),
        ('number', r'\b(?:0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+\.?\d*[eE][+-]?\d+|\d+\.?\d*|\d*\.?\d+[eE][+-]?\d+|\d*\.?\d+)\b'),
        ('comment', r'//.*$|\/\*[\s\S]*?\*\/'),
        ('operator', r'[=+\-*/%<>!&|^~?:;,.\[\]{}().]'),
        ('function', r'(?<=\s|\()([\w$]+)\s*(?=\()'),
    ]


def _build_json_patterns() -> list[tuple[str, str]]:
    return [
        ('key', r'"(?:\\.|[^"\\])*?"\s*(?=\s*:)'),
        ('string', r'"(?:\\.|[^"\\])*?"'),
        ('number', r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\b'),
        ('boolean', r'\b(?:true|false)\b'),
        ('null', r'\bnull\b'),
        ('operator', r'[:,]'),
    ]


def _build_html_patterns() -> list[tuple[str, str]]:
    return [
        ('tag', r'<\/?[\w-]+'),
        ('attribute', r'(?<=\s)(?:[\w-]+\s*=\s*)?"(?:\\.|[^"\\])*?"'),
        ('string', r'"(?:\\.|[^"\\])*?"'),
        ('comment', r'<!--[\s\S]*?-->'),
        ('operator', r'[=+\-*/%<>!&|^~?:;,.\[\]{}().]'),
    ]


def _build_css_patterns() -> list[tuple[str, str]]:
    return [
        ('keyword', r'(?<![.#\w])\b(?:inherit|initial|revert|unset|none|auto|block|inline|inline-block|flex|grid|table|hidden|visible|scroll|fixed|absolute|relative|static|sticky|center|flex-start|flex-end|space-between|space-around|space-evenly|wrap|nowrap|wrap-reverse|column|row|normal|bold|italic|underline|line-through|capitalize|uppercase|lowercase|left|right|center|top|bottom|middle|baseline|sub|super|sub|super|dotted|dashed|solid|double|groove|ridge|outset|inset|closer|both|none)\b'),
        ('number', r'\b\d+\.?\d*(?:px|em|rem|vh|vw|vmin|vmax|%|cm|mm|in|pt|pc|ex|ch|fr|gap|s|ms|Hz|kHz|dpi|dpcm|dppx)?\b'),
        ('string', r'"(?:\\.|[^"\\])*?"|\'(?:\\.|[^\'\\])*?\''),
        ('comment', r'/\*[\s\S]*?\*\/'),
        ('tag', r'(?<![.#\w])[\w-]+(?=\s*\{)'),
        ('attribute', r'[\w-]+(?=\s*:)'),
        ('key', r'[\w-]+(?=\s*:)'),
        ('color', r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b'),
        ('operator', r'[:;{}()]'),
    ]


def _build_yaml_patterns() -> list[tuple[str, str]]:
    return [
        ('key', r'^\s*[\w.-]+(?=\s*:)'),
        ('string', r'"(?:\\.|[^"\\])*?"|\'(?:\\.|[^\'\\])*?\''),
        ('number', r'\b\d+\.?\d*(?:[eE][+-]?\d+)?\b'),
        ('boolean', r'\b(?:true|false|yes|no|on|off)\b'),
        ('null', r'\b(?:null|~)\b'),
        ('comment', r'#.*$'),
        ('operator', r'[:,{}[\]\-]'),
    ]

_PATTERNS = {
    'python': _build_python_patterns,
    'javascript': _build_js_patterns,
    'json': _build_json_patterns,
    'html': _build_html_patterns,
    'css': _build_css_patterns,
    'yaml': _build_yaml_patterns,
}


# ═══════════════════════════════════════════════════════════════════════════
# Surligneur
# ═══════════════════════════════════════════════════════════════════════════

class SyntaxHighlighter:
    """Surligne le code source dans un widget tk.Text."""

    def __init__(self, text_widget: tk.Text) -> None:
        self.text = text_widget
        self._compiled: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        self._configure_tags()

    def _configure_tags(self) -> None:
        for token, color in COLORS.items():
            tag = TAG_NAMES.get(token)
            if tag:
                self.text.tag_configure(tag, foreground=color)

    def _get_patterns(self, lang: str) -> list[tuple[str, re.Pattern[str]]] | None:
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
        result = self._compiled.get(lang)
        if result is None:
            return []
        return result

    def highlight_range(self, start: str, end: str, lang: str) -> None:
        """Applique le surlignage sur la plage [start, end] (format tkinter '1.0')."""
        patterns = self._get_patterns(lang)
        if not patterns:
            return

        # Supprimer les tags existants dans la plage
        for tag in TAG_NAMES.values():
            self.text.tag_remove(tag, start, end)

        content = self.text.get(start, end)
        parts = start.split('.', 1)
        base_line = int(parts[0])
        base_col = int(parts[1]) if len(parts) > 1 else 0

        def _to_index(offset: int) -> str:
            line = content.count('\n', 0, offset)
            col = offset - (content.rfind('\n', 0, offset) + 1)
            return f"{base_line + line}.{base_col + col}"

        for token_name, pattern in patterns:
            tag = TAG_NAMES.get(token_name)
            if not tag:
                continue
            for match in pattern.finditer(content):
                self.text.tag_add(tag, _to_index(match.start()), _to_index(match.end()))

    def highlight_all(self, lang: str) -> None:
        """Surligne tout le contenu du widget."""
        self.highlight_range('1.0', tk.END, lang)


def highlight_all(text_widget: tk.Text, lang: str) -> None:
    """Fonction de commodité : surligne tout le contenu."""
    SyntaxHighlighter(text_widget).highlight_range('1.0', tk.END, lang)
