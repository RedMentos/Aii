"""Exact, deliberately narrow arithmetic reflex for a sourced user turn.

No eval, tools, model claims or external side effects. Ambiguous language
returns None and uses the normal multi-organ route. Date-shaped subtraction
requires an explicit calculation verb rather than a generic question prefix.
"""
import re
from fractions import Fraction

_PATTERN = re.compile(
    r"\s*(?:(what\s+is|what's|was\s+ist|wie\s+viel\s+ist|how\s+much\s+is|"
    r"berechne|calculate|compute)\s+)?"
    r"([+-]?\d{1,8}\s*[+\-*/]\s*[+-]?\d{1,8})\s*[?=]?\s*",
    re.IGNORECASE,
)
_EXPRESSION = re.compile(r"([+-]?\d{1,8})\s*([+\-*/])\s*([+-]?\d{1,8})")


def _date_shaped_subtraction(left, right):
    """Conservatively reject common month/day, day/month and year/month forms."""
    month_day = 1 <= left <= 12 and 1 <= right <= 31
    day_month = 1 <= left <= 31 and 1 <= right <= 12
    year_month = 1000 <= left <= 9999 and 1 <= right <= 12
    return month_day or day_month or year_month


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
    prefix, expression = match.groups()
    expr = _EXPRESSION.fullmatch(expression)
    if not expr:
        return None
    a, op, b = int(expr.group(1)), expr.group(2), int(expr.group(3))
    explicit_math = prefix is not None and prefix.lower() in {
        "berechne", "calculate", "compute",
    }
    if op == "-" and not explicit_math and _date_shaped_subtraction(a, b):
        return None
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
