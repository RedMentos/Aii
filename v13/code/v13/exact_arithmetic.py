"""Exact, bounded arithmetic admission for a future C5 source-grounded answer route.

This module does not authorize tools or bypass the body/C3 path. A caller must
explicitly select its output and record the original source reference.
"""
import ast
import re
from decimal import Decimal, InvalidOperation, localcontext

_EXPRESSION = re.compile(r"^\s*(?:(?:what is|what's|calculate|compute|solve)\s+)?([0-9][0-9 .+*/()\-]*[0-9)]|[0-9])\s*[?!.]?\s*$", re.I)
_ALLOWED = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_MAX_CHARS = 80
_MAX_DIGITS = 16
_MAX_NODES = 31
_MAX_MAGNITUDE = Decimal("1e18")


def exact_arithmetic(text):
    """Return an exact decimal answer or None when input is ambiguous/unsafe.

    No eval, exponentiation, variables, function calls, units or locale guessing.
    No mutation or side effects. A negative number is accepted only as a
    unary sign in an otherwise explicit expression.
    """
    if not isinstance(text, str) or len(text) > _MAX_CHARS:
        return None
    match = _EXPRESSION.fullmatch(text)
    if not match:
        return None
    expr = match.group(1)
    if not any(op in expr for op in "+-*/"):
        return None
    if re.search(r"\d\s+\d|\d\.\d*\.", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
            return None
        with localcontext() as ctx:
            ctx.prec = 48
            def compute(node):
                if isinstance(node, ast.Expression):
                    return compute(node.body)
                if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                    raw = ast.get_source_segment(expr, node)
                    if not raw or len(raw.replace(".", "")) > _MAX_DIGITS:
                        raise ValueError("literal bound")
                    value = Decimal(raw)
                elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
                    value = compute(node.operand)
                    if isinstance(node.op, ast.USub):
                        value = -value
                elif isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED):
                    left, right = compute(node.left), compute(node.right)
                    if isinstance(node.op, ast.Add):
                        value = left + right
                    elif isinstance(node.op, ast.Sub):
                        value = left - right
                    elif isinstance(node.op, ast.Mult):
                        value = left * right
                    else:
                        if not right:
                            raise ValueError("division by zero")
                        value = left / right
                else:
                    raise ValueError("unsupported syntax")
                if not value.is_finite() or abs(value) > _MAX_MAGNITUDE:
                    raise ValueError("magnitude bound")
                return value
            result = compute(tree)
            answer = format(result.normalize(), "f")
            return answer if len(answer) <= 48 else None
    except (SyntaxError, ValueError, ArithmeticError, InvalidOperation, TypeError):
        return None
