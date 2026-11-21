"""Conservative exact arithmetic for the C2 answer verifier.

Only a whole-message binary integer calculation is admitted. This is not a
replacement for body deliberation or a general expression evaluator.
"""
import re
from fractions import Fraction

_PATTERN = re.compile(r'^\\s*(?:what\\s+is\\s+|calculate\\s+|compute\\s+)?([+-]?\\d{1,12})\\s*([+\\-*/×÷])\\s*([+-]?\\d{1,12})\\s*\\??\\s*$', re.I)

def exact_arithmetic(text):
    if not isinstance(text, str) or len(text) > 100:
        return None
    match = _PATTERN.fullmatch(text)
    if match is None:
        return None
    a, op, b = match.groups()
    x, y = int(a), int(b)
    if op == '+': value = Fraction(x+y)
    elif op == '-': value = Fraction(x-y)
    elif op in ('*', '×'): value = Fraction(x*y)
    elif y == 0: return None
    else: value = Fraction(x, y)
    result = str(value.numerator) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'
    return {'answer': result, 'source': 'EXACT_USER_EXPRESSION', 'method': 'integer_fraction_v1', 'expression': match.group(0).strip()}
