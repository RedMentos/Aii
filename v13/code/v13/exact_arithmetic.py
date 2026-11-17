"""Bounded exact arithmetic for explicit simple requests; no eval or side effects."""
import re
from fractions import Fraction

_NUMBER = r'(?:\d{1,12}(?:\.\d{1,8})?)'
_EXPR = re.compile(rf'\s*({_NUMBER})\s*([+\-*/×÷])\s*({_NUMBER})\s*\??\s*')
_PREFIX = re.compile(r"(?i)\s*(?:what is|what's|calculate|compute|wie viel ist|was ist)\s*")

def verified_arithmetic(text):
    """Return a precise result or None, never infer arithmetic from prose."""
    if not isinstance(text, str) or len(text) > 128:
        return None
    expression = _PREFIX.sub('', text, count=1)
    match = _EXPR.fullmatch(expression)
    if not match:
        return None
    a, op, b = match.groups()
    left, right = Fraction(a), Fraction(b)
    if op == '+': result = left + right
    elif op == '-': result = left - right
    elif op in ('*', '×'): result = left * right
    else:
        if right == 0: return None
        result = left / right
    answer = str(result.numerator) if result.denominator == 1 else f'{result.numerator}/{result.denominator}'
    return {'answer': answer, 'method': 'EXACT_FRACTION',
            'confidence_scope': 'EXPLICIT_BINARY_ARITHMETIC_ONLY',
            'model_generated': False}
