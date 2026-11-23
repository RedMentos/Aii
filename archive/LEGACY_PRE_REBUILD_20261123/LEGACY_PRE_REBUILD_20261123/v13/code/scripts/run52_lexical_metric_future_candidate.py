"""Isolated future Run52 lexical metric candidate; never rescore frozen seed479.

Conservative string-only diagnostic. It is not a semantic oracle or a native
utility gate. The original registered Run52 scorer remains authoritative for
its own cohort, even where this audit demonstrates false positives.
"""
from __future__ import annotations
import re


def strict_future_choice_signal(summary, oracle):
    """Require explicit selection and unambiguous *positive integer* remainder.

    Intentionally conservative; new cohort calibration is needed before use.
    """
    if type(summary) is not str or type(oracle) is not dict or len(summary) > 4096:
        return 0
    choice = oracle.get("choice")
    if choice == "NONE":
        if re.search(r"\b(?:option|choice)\s*[AB]\b", summary, re.I):
            return 0
        return int(bool(re.search(
            r"\b(?:no eligible option|neither option qualifies|"
            r"none of the options (?:qualifies|is eligible))\b", summary, re.I)))
    if choice not in ("A", "B") or type(oracle.get("remaining")) is not int:
        return 0
    amount = oracle["remaining"]
    if amount < 0:
        return 0
    # Require the explicit Option/Choice marker, never the article 'a'.
    labels = re.findall(r"\b(?:option|choice)\s*([AB])\b", summary, re.I)
    if not labels or any(label.upper() != choice for label in labels):
        return 0
    # Require an unambiguous positive whole amount and a nearby remainder verb.
    number = r"(?<![\w.,+\-])" + re.escape(str(amount)) + r"(?![\d.,])"
    for match in re.finditer(number, summary):
        lo, hi = max(0, match.start()-40), min(len(summary), match.end()+40)
        if re.search(r"\b(?:remain(?:s|ing)?|leaves?|left)\b",
                     summary[lo:hi], re.I):
            return 1
    return 0
