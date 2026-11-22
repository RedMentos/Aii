"""German list_arith v2 candidate: explicit SHADOW ONLY, no live consumer.

Based on exposed seed71 failure families. Seed73 is frozen before this file.
No C5, ToolStep, age-right, model or numeric execution authority.
"""
from __future__ import annotations
import re
from .listarith import question_part, MAX_TEXT

AUTHORITY = "SHADOW_ONLY"
REVISION = "listarith-de-v2-candidate-seed73-v1"

# A negated or metalinguistic mention of an operation is not an instruction.
_NEGATE = re.compile(r"(?i)\b(?:nicht|kein(?:e|en|em|er|es)?|ohne|niemals|vermeide)\b")
_META = re.compile(
    r"(?i)\b(?:richtig|falsch|plausibel|fehlerfrei|bereits|angegeben|"
    r"steht|stimmt|warum|korrekt|überprüf\w*|pr[üu]f\w*)\b"
)
_UNSUPPORTED = re.compile(
    r"(?i)\b(?:durchschnitt|mittelwert|median|prozent\w*|quotient|"
    r"verh[aä]ltnis|anzahl|gesamtanzahl|gesamtzahl|"
    r"wie\s+viele\s+(?:werte|eintr[aä]ge|positionen|posten|dinge|zahlen)|"
    r"wie\s+viel\s+kostet\s+[A-Z]\b|"
    r"welch(?:er|e|es)\s+(?:betrag|wert|zahl|posten|position)\b)\b"
)
_PAIR = re.compile(
    r"(?i)\b(?:zwischen|von|hat)\s+[A-Z]\s+(?:und|als|zu)\s+[A-Z]\b|"
    r"\b[A-Z]\s+(?:und|mit|gegen(?:über)?)\s+[A-Z]\b"
)
_HI = re.compile(
    r"(?i)\b(?:h[oö]chst\w*|gr[oö][sß]t\w*|maximum|max|"
    r"spitzenwert|teuerst\w*|h[oö]h\w*)\b"
)
_LO = re.compile(
    r"(?i)\b(?:niedrigst\w*|kleinst\w*|minimum|min|"
    r"tiefstwert|g[uü]nstigst\w*|billigst\w*)\b"
)
_DIFF = re.compile(
    r"(?i)\b(?:differenz|unterschied|abstand|mehr|h[oö]her|"
    r"auseinander|minus|subtrahier\w*|abzieh\w*|zieh\w*|"
    r"entfernt|weit|zwischen|liegen|spannweite|trenn\w*)\b"
)
_TOTAL = re.compile(
    r"(?i)\b(?:summe|gesamtsumme|gesamtbetrag|gesamtwert|"
    r"gesamtkosten|gesamtpreis|endbetrag|endpreis|insgesamt|"
    r"addier\w*|addiert\w*|addition|summier\w*|"
    r"zusammen(?:rechn\w*|z[aä]hl\w*)?|plus)\b"
)
_SPAN = re.compile(r"(?i)\bspannweite\b")
_PLUS = re.compile(r"(?<!\d)\d+\s*\+\s*\d+(?!\d)")


def propose(text):
    """Return only a non-authoritative operation proposal, never an answer."""
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        return {"proposal": None, "authority": AUTHORITY, "reason": "INVALID_INPUT"}
    q = question_part(text).strip()
    if not q:
        return {"proposal": None, "authority": AUTHORITY, "reason": "NO_QUESTION"}
    if _NEGATE.search(q) or _META.search(q):
        return {"proposal": None, "authority": AUTHORITY, "reason": "NEGATED_OR_META"}
    if _UNSUPPORTED.search(q) or _PAIR.search(q):
        return {"proposal": None, "authority": AUTHORITY, "reason": "UNSUPPORTED_OR_PAIR"}
    difference = bool(_SPAN.search(q) or
                      (_HI.search(q) and _LO.search(q) and _DIFF.search(q)))
    total = bool(_TOTAL.search(q) or _PLUS.search(q))
    if total and difference:
        return {"proposal": None, "authority": AUTHORITY, "reason": "CONFLICTING_OPERATIONS"}
    if difference:
        return {"proposal": "difference_max_min", "authority": AUTHORITY,
                "reason": "DE_EXPLICIT_MAX_MIN_V2"}
    if total:
        return {"proposal": "total", "authority": AUTHORITY,
                "reason": "DE_EXPLICIT_TOTAL_V2"}
    return {"proposal": None, "authority": AUTHORITY, "reason": "NO_SUPPORTED_RECIPE"}
