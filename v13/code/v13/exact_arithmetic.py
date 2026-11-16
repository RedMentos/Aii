"""Bounded source-exact arithmetic reflex for unambiguous simple questions.

No LLM output is treated as arithmetic evidence. Complex queries still use the
normal A/B/C focal pipeline. This does not grant any tool or model authority.
"""
import re
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction

_NUMBER = r"(?:\\d{1,9}(?:\\.\\d{1,6})?)"
_EXPR = re.compile(rf"^\\s*({_NUMBER})\\s*([+\\-*/×÷])\\s*({_NUMBER})\\s*$")
_WRAPPER = re.compile(r"^\\s*(?:(?:what\\s+is|what's|calculate|compute|solve|wie\\s+viel\\s+ist|was\\s+ist|rechne)\\s+)?(.+?)\\s*[?=.!]?\\s*$", re.I)

def exact_arithmetic(text):
    """Return canonical numeric text, or None if not provably an exact two-operand query."""
    if not isinstance(text, str) or len(text) > 100:
        return None
    match = _WRAPPER.fullmatch(text)
    if not match:
        return None
    expr = _EXPR.fullmatch(match.group(1).strip())
    if not expr:
        return None
    a, op, b = expr.groups()
    try:
        with localcontext() as ctx:
            ctx.prec = 40
            left, right = Decimal(a), Decimal(b)
            if op == '+':
                value = left + right
            elif op == '-':
                value = left - right
            elif op in ('*', '×'):
                value = left * right
            else:
                if right == 0:
                    return None
                fraction = Fraction(left) / Fraction(right)
                denominator = fraction.denominator
                for prime in (2, 5):
                    while denominator % prime == 0:
                        denominator //= prime
                if denominator != 1:
                    return None  # repeating decimal: not an exact finite answer
                value = left / right
            if not value.is_finite():
                return None
            result = format(value.normalize(), 'f')
            return '0' if Decimal(result) == 0 else result
    except (InvalidOperation, ArithmeticError, ValueError):
        return None
