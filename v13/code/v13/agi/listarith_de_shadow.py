"""German question-scoped typed arithmetic proposal, SHADOW ONLY (seed67).

This module is deliberately NOT wired to ToolStep, C5, runtime, or tool execution.
It never changes existing English listarith.operation/compute or any age gate.
"""
from __future__ import annotations
import re
from .listarith import question_part, MAX_TEXT

AUTHORITY = 'SHADOW_ONLY'
REVISION = 'listarith-de-shadow-seed67-v1'

# Reject counts, lookup/selection, means, ratios and specific pairwise differences.
_UNSUPPORTED = re.compile(
    r'(?i)\b(?:gesamtzahl|gesamtanzahl|anzahl|durchschnitt|median|prozent\w*|'
    r'unterschiedlich\w*|fasse\b|nenne\b|welche\b|welcher\b|welches\b|'
    r'wie\s+viele\s+(?:eintr[aä]ge|positionen|st[aä]dte|werte\s+stehen|dinge)|'
    r'wie\s+viel\s+kostet\s+[A-Z]\b|ist\s+[A-Z]\s+teurer\s+als\s+[A-Z])\b')
_SPECIFIC_PAIR = re.compile(r'(?i)\b(?:zwischen|hat)\s+[A-Z]\s+(?:und|als)\s+[A-Z]\b')
_HI = re.compile(r'(?i)\b(?:h[oö]chst\w*|gr[oö][sß]t\w*|maximum|max|spitzenwert)\b')
_LO = re.compile(r'(?i)\b(?:niedrigst\w*|kleinst\w*|minimum|min|tiefstwert)\b')
_DIFF = re.compile(r'(?i)\b(?:differenz|mehr|abstand|[uü]bersteig\w*|auseinander|spannweite|'
                   r'gr[oö][sß]er|trenn\w*|minus|unterschied|[uü]ber|h[oö]her)\b')
_TOTAL = re.compile(r'(?i)\b(?:summe|gesamtsumme|gesamtbetrag|gesamtwert|insgesamt|'
                    r'addier\w*|addition|zusammen|alles\s+addieren)\b')


def propose(text):
    """Return a non-authoritative recipe proposal; no numeric result or action."""
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        return {'proposal': None, 'authority': AUTHORITY, 'reason': 'INVALID_INPUT'}
    q = question_part(text).strip()
    if not q or _UNSUPPORTED.search(q) or _SPECIFIC_PAIR.search(q):
        return {'proposal': None, 'authority': AUTHORITY, 'reason': 'UNSUPPORTED_QUESTION'}
    diff = bool((_HI.search(q) and _LO.search(q) and _DIFF.search(q)) or
                re.search(r'(?i)\bspannweite\b', q))
    total = bool(_TOTAL.search(q))
    if diff and total:
        return {'proposal': None, 'authority': AUTHORITY, 'reason': 'CONFLICTING_OPERATIONS'}
    if diff:
        return {'proposal': 'difference_max_min', 'authority': AUTHORITY, 'reason': 'DE_EXPLICIT_MAX_MIN'}
    if total:
        return {'proposal': 'total', 'authority': AUTHORITY, 'reason': 'DE_EXPLICIT_TOTAL'}
    return {'proposal': None, 'authority': AUTHORITY, 'reason': 'NO_SUPPORTED_RECIPE'}