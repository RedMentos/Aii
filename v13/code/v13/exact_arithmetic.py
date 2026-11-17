"""Exact, bounded arithmetic reflex for an entire bare expression.

This is a deterministic C5 answer path, not learned reasoning or an
authorization to skip B1/B2 on complex requests. No eval or tool execution.
"""
import re
from fractions import Fraction

EXPRESSION = re.compile(r"\s*([+-]?\d{1,9})\s*([+*/×÷-])\s*([+-]?\d{1,9})\s*(?:=|\?)?\s*\Z")

def exact_arithmetic(text):
    if type(text) is not str or len(text) > 48:
        return None
    match = EXPRESSION.fullmatch(text)
    if match is None:
        return None
    left, operator, right = match.groups()
    a, b = int(left), int(right)
    if operator == '+':
        result = Fraction(a+b)
    elif operator == '-':
        result = Fraction(a-b)
    elif operator in ('*', '×'):
        result = Fraction(a*b)
    else:
        if b == 0:
            return None
        result = Fraction(a,b)
    return str(result.numerator) if result.denominator == 1 else f"{result.numerator}/{result.denominator}"
