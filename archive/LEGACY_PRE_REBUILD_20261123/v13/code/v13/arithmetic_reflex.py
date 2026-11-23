"""Exact, deliberately narrow arithmetic reflex for a sourced user turn.

No eval, tools, model claims or external side effects. Ambiguous language
returns None and uses the normal multi-organ route.
"""
import re
from fractions import Fraction

_PATTERN = re.compile(
    r"\s*(?:(?:what\s+is|what's|was\s+ist|berechne|calculate)\s+)?"
    r"([+-]?\d{1,8}\s*[+\-*/]\s*[+-]?\d{1,8})\s*[?=]?\s*",
    re.IGNORECASE,
)
_EXPRESSION = re.compile(r"([+-]?\d{1,8})\s*([+\-*/])\s*([+-]?\d{1,8})")


def exact_arithmetic(text):
    """Return an exact decimal/integer or rational answer, or None.

    Restrict to two signed bounded integers, one binary operator. This is
    intentionally NOT a general math parser or a claim about model reasoning.
    """
    if type(text) is not str or len(text) > 96:
        return None
    match = _PATTERN.fullmatch(text)
    if not match:
        return None
    expr = _EXPRESSION.fullmatch(match.group(1))
    if not expr:
        return None
    a, op, b = int(expr.group(1)), expr.group(2), int(expr.group(3))
    if op == '+':
        result = Fraction(a + b)
    elif op == '-':
        result = Fraction(a - b)
    elif op == '*':
        result = Fraction(a * b)
    else:
        if b == 0:
            return None
        result = Fraction(a, b)
    return str(result.numerator) if result.denominator == 1 else (
        str(result.numerator) + '/' + str(result.denominator))
