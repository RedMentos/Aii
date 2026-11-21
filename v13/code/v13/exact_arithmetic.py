"""Source-bound exact integer arithmetic evidence for the existing C5 policy path.

Only one complete binary integer expression is admitted. No eval, model call,
floating point, division, tool permission, or external action authority.
"""
from __future__ import annotations

import re

_PATTERN = re.compile(
    r"[ \t]*(?:(?:what is|what's|calculate|compute|berechne|was ist|wie viel ist|wieviel ist)[ \t]*)?"
    r"([+-]?\d{1,9})[ \t]*([+*×-])[ \t]*([+-]?\d{1,9})[ \t]*\??[ \t]*",
    re.IGNORECASE,
)
_YEAR_MONTH = re.compile(
    r"[ \t]*(?:(?:what is|what's|was ist|wie viel ist|wieviel ist)[ \t]*)?"
    r"\d{4}[ \t]*-[ \t]*\d{1,2}[ \t]*\??[ \t]*",
    re.IGNORECASE,
)
_BARE_MONTH_DAY = re.compile(r"[ \t]*\d{1,2}-\d{1,2}[ \t]*\??[ \t]*")


def evidence(source: str) -> dict | None:
    """Return exact source evidence for a narrow, unambiguous binary expression."""
    if not isinstance(source, str) or len(source) > 96:
        return None
    if _YEAR_MONTH.fullmatch(source) or _BARE_MONTH_DAY.fullmatch(source):
        return None
    match = _PATTERN.fullmatch(source)
    if match is None:
        return None

    left_text, operator, right_text = match.groups()
    left, right = int(left_text), int(right_text)
    if operator == "+":
        result = left + right
    elif operator == "-":
        result = left - right
    else:
        result = left * right

    return {
        "kind": "SOURCE_EXACT_INTEGER_ARITHMETIC",
        "source": source,
        "operands": [left, right],
        "operator": "*" if operator == "×" else operator,
        "result": str(result),
        "model_generated": False,
        "authority": "DETERMINISTIC_EVIDENCE_ONLY",
    }
