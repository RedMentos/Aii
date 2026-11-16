"""Strict exact-integer arithmetic reflex for explicitly bounded questions.

Not a general semantic calculator: ambiguous text always goes to the multi-organ
route. No eval, no floating point, no learned authority and no tool permission.
"""
import re

_EXPR = re.compile(r"^\s*(?:(?:what is|what's|calculate|compute|was ist|wieviel ist)\s+)?([+-]?\d{1,9})\s*([+*×-])\s*([+-]?\d{1,9})\s*\??\s*$", re.I)

def answer(text):
    if not isinstance(text, str) or len(text) > 80:
        return None
    m = _EXPR.fullmatch(text)
    if m is None:
        return None
    a, op, b = int(m[1]), m[2], int(m[3])
    if op == '+':
        result = a + b
    elif op == '-':
        result = a - b
    else:
        result = a * b
    return str(result)
