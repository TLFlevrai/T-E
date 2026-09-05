# src/tools/_text_stats.py
"""Logique pure pour l'analyseur de texte : statistiques, fréquence, minification, encodage."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Statistiques
# ═══════════════════════════════════════════════════════════════════════════

_STOPWORDS_FR = {
    'le', 'la', 'les', 'de', 'des', 'du', 'un', 'une', 'et', 'est', 'en',
    'que', 'qui', 'dans', 'ce', 'il', 'ne', 'sur', 'se', 'pas', 'plus',
    'par', 'avec', 'tout', 'faire', 'comme', 'mais', 'ou', 'où', 'son',
    'sa', 'ses', 'aux', 'aussi', 'bien', 'être', 'avoir', 'cette', 'nous',
    'vous', 'ils', 'elle', 'elles', 'mon', 'ton', 'leur', 'leurs',
    'nos', 'vos', 'mes', 'tes', 'ses', 'lui', 'eux', 'y', 'ça', 'très',
    'peu', 'si', 'donc', 'car', 'quand', 'alors', 'après', 'avant',
    'entre', 'chez', 'sans', 'sous', 'même', 'encore', 'déjà',
}

_STOPWORDS_EN = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'and', 'but', 'or', 'nor', 'not', 'so', 'very', 'just',
    'than', 'too', 'also', 'here', 'there', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
    'such', 'no', 'only', 'own', 'same', 'that', 'this', 'which', 'what',
    'who', 'whom', 'it', 'its', 'i', 'me', 'my', 'we', 'our', 'you',
    'your', 'he', 'him', 'his', 'she', 'her', 'they', 'them', 'their',
    'about', 'up', 'down', 'if', 'while', 'because', 'although', 'though',
    'since', 'until', 'unless', 'whereas', 'whether', 'while',
}

_ALL_STOPWORDS = _STOPWORDS_FR | _STOPWORDS_EN


def compute_stats(text: str) -> dict:
    """Calcule les statistiques complètes d'un texte."""
    if not text:
        return _empty_stats()

    lines = text.split('\n')
    words = text.split()
    chars_with = len(text)
    chars_without = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

    sentences = 0
    for ch in text:
        if ch in '.!?':
            sentences += 1
    if sentences == 0 and text.strip():
        sentences = 1

    paragraphs = 0
    for block in re.split(r'\n\s*\n', text):
        if block.strip():
            paragraphs += 1
    if paragraphs == 0 and text.strip():
        paragraphs = 1

    empty_lines = sum(1 for l in lines if l.strip() == '')
    max_line_len = max((len(l) for l in lines), default=0)
    avg_words_per = round(len(words) / sentences, 1) if sentences > 0 else 0

    return {
        'lines': len(lines),
        'words': len(words),
        'chars_with_spaces': chars_with,
        'chars_without_spaces': chars_without,
        'sentences': sentences,
        'paragraphs': paragraphs,
        'avg_words_per_sentence': avg_words_per,
        'empty_lines': empty_lines,
        'max_line_length': max_line_len,
    }


def _empty_stats() -> dict:
    return {
        'lines': 0, 'words': 0, 'chars_with_spaces': 0,
        'chars_without_spaces': 0, 'sentences': 0, 'paragraphs': 0,
        'avg_words_per_sentence': 0, 'empty_lines': 0, 'max_line_length': 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Fréquence des mots
# ═══════════════════════════════════════════════════════════════════════════

def word_frequency(text: str, top_n: int = 10, exclude_stopwords: bool = True) -> list[tuple[str, int, float]]:
    """Retourne les top N mots les plus fréquents avec pourcentage."""
    if not text.strip():
        return []

    tokens = re.findall(r'\b\w+\b', text.lower())
    total = len(tokens)
    if total == 0:
        return []

    filtered = [
        t for t in tokens
        if len(t) > 2 and (not exclude_stopwords or t not in _ALL_STOPWORDS)
    ]

    counts = Counter(filtered)
    result = []
    for word, count in counts.most_common(top_n):
        pct = round(count / total * 100, 1)
        result.append((word, count, pct))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Détection d'encodage
# ═══════════════════════════════════════════════════════════════════════════

def detect_encoding(file_path: Path) -> dict:
    """Détecte l'encodage d'un fichier."""
    raw = file_path.read_bytes()
    return detect_encoding_bytes(raw)


def detect_encoding_bytes(raw: bytes) -> dict:
    """Détecte l'encodage depuis des octets bruts."""
    if not raw:
        return {'encoding': 'unknown', 'confidence': 0, 'bom': 'Aucune', 'line_ending': 'Inconnu'}

    # BOM detection
    bom = 'Aucune'
    encoding = 'UTF-8'
    if raw[:3] == b'\xef\xbb\xbf':
        bom = 'UTF-8'
        encoding = 'UTF-8 (BOM)'
        raw = raw[3:]
    elif raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        bom = 'UTF-16'
        encoding = 'UTF-16'
        raw = raw[2:]
    elif raw[:4] in (b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff'):
        bom = 'UTF-32'
        encoding = 'UTF-32'

    # Line ending detection
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n') - crlf
    cr = raw.count(b'\r') - crlf
    if crlf > lf and crlf > cr:
        line_ending = 'CRLF (Windows)'
    elif cr > 0 and cr > lf:
        line_ending = 'CR (ancien Mac)'
    else:
        line_ending = 'LF (Unix)'

    # Try chardet if available
    confidence = 95
    try:
        import chardet
        result = chardet.detect(raw)
        if result and result['encoding']:
            encoding = result['encoding']
            confidence = round((result['confidence'] or 0.8) * 100)
    except ImportError:
        # Heuristic: try UTF-8
        try:
            raw.decode('utf-8')
            encoding = 'UTF-8' if bom == 'Aucune' else encoding
            confidence = 98
        except UnicodeDecodeError:
            encoding = 'Latin-1'
            confidence = 70

    return {
        'encoding': encoding,
        'confidence': confidence,
        'bom': bom,
        'line_ending': line_ending,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Minification
# ═══════════════════════════════════════════════════════════════════════════

def minify_js(code: str) -> str:
    """Minifie du JavaScript (suppression commentaires et espaces)."""
    # Supprimer commentaires multi-lignes
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Supprimer commentaires single-line
    code = re.sub(r'//[^\n]*', '', code)
    # Supprimer espaces multiples
    code = re.sub(r'\s+', ' ', code)
    # Supprimer espaces autour des opérateurs
    code = re.sub(r'\s*([{};,:=+\-*/<>!&|?])\s*', r'\1', code)
    return code.strip()


def minify_css(code: str) -> str:
    """Minifie du CSS."""
    # Supprimer commentaires
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Supprimer espaces multiples et sauts de ligne
    code = re.sub(r'\s+', ' ', code)
    # Supprimer espaces autour de { } ; : ,
    code = re.sub(r'\s*([{};:,])\s*', r'\1', code)
    return code.strip()


def minify_html(code: str) -> str:
    """Minifie du HTML."""
    # Supprimer commentaires
    code = re.sub(r'<!--.*?-->', '', code, flags=re.DOTALL)
    # Supprimer espaces entre balises
    code = re.sub(r'>\s+<', '><', code)
    # Supprimer espaces multiples
    code = re.sub(r'\s+', ' ', code)
    return code.strip()


def minify(text: str, fmt: str = 'auto') -> dict:
    """Minifie un texte et retourne le résultat avec stats."""
    if fmt == 'auto':
        fmt = _detect_format(text)

    minifiers = {'js': minify_js, 'css': minify_css, 'html': minify_html}
    minifier = minifiers.get(fmt)

    if not minifier:
        return {'original': text, 'minified': text, 'format': fmt,
                'original_size': len(text), 'minified_size': len(text), 'gain_pct': 0}

    minified = minifier(text)
    original_size = len(text.encode('utf-8'))
    minified_size = len(minified.encode('utf-8'))
    gain = round((1 - minified_size / original_size) * 100, 1) if original_size > 0 else 0

    return {
        'original': text,
        'minified': minified,
        'format': fmt,
        'original_size': original_size,
        'minified_size': minified_size,
        'gain_pct': gain,
    }


def _detect_format(text: str) -> str:
    """Détecte le format du code."""
    stripped = text.strip()
    if stripped.startswith('<') and ('</' in stripped or '/>' in stripped):
        return 'html'
    if '{' in stripped and (';' in stripped or ':' in stripped):
        if re.search(r'[\w-]+\s*:', text):
            return 'css'
        return 'js'
    return 'js'


# ═══════════════════════════════════════════════════════════════════════════
# Comparaison rapide
# ═══════════════════════════════════════════════════════════════════════════

def quick_compare(text_a: str, text_b: str) -> dict:
    """Compare deux textes et retourne des métriques rapides."""
    if not text_a and not text_b:
        return {'identical_pct': 100, 'added': 0, 'removed': 0, 'modified': 0}

    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    set_a = set(lines_a)
    set_b = set(lines_b)

    added = set_b - set_a
    removed = set_a - set_b
    common = set_a & set_b

    total_lines = max(len(set_a), len(set_b), 1)
    identical_pct = round(len(common) / total_lines * 100, 1)

    return {
        'identical_pct': identical_pct,
        'added': len(added),
        'removed': len(removed),
        'modified': len(removed & added),
        'total_a': len(lines_a),
        'total_b': len(lines_b),
        'common': len(common),
    }
