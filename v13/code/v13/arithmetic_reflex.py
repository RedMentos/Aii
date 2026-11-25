"""Exact, deliberately narrow arithmetic reflex for a sourced user turn.

No eval, tools, model claims or external side effects. Ambiguous language
returns None and uses the normal multi-organ route.
"""
import re
from fractions import Fraction

_PATTERN = re.compile(
    r"\s*(?:(?:what\s+is|what's|was\s+ist|berechne|calculate|compute|wie\s+viel\s+ist|wieviel\s+ist)\s+)?"
    r"([+-]?\d{1,8}\s*[+\-*/]\s*[+-]?\d{1,8})\s*[?=]?\s*",
    re.IGNORECASE,
)
_EXPRESSION = re.compile(r"([+-]?\d{1,8})\s*([+\-*/])\s*([+-]?\d{1,8})")
_DATE_SHAPE = re.compile(r"\s*(?:\d{4}\s*-\s*\d{1,2}|\d{1,2}\s*-\s*\d{1,2})\s*\??\s*")
_EXPLICIT_MATH_CUE = re.compile(r"\s*(?:calculate|compute|berechne)\s+", re.IGNORECASE)


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
    expression = match.group(1)
    # A month/day or year/month subtraction is ambiguous without an explicit
    # calculation verb. Generic question prefixes ("What is", "Was ist")
    # must not silently turn a date into arithmetic.
    if _DATE_SHAPE.fullmatch(expression) and not _EXPLICIT_MATH_CUE.match(text):
        return None
    expr = _EXPRESSION.fullmatch(expression)
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
