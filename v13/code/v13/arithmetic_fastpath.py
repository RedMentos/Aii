"""Strict exact arithmetic fastpath for a single standalone text expression.

It is deliberately not a general natural-language calculator. Any additional
intent, comparison, audio source, unsupported syntax or unsafe magnitude falls
through to the normal multi-organ Runtime path.
"""
from __future__ import annotations

import ast
import math
import re
import unicodedata
from fractions import Fraction


RULE_ID = "BUILTIN_ARITHMETIC_EXACT_V1"
MAX_TEXT_CHARS = 96
MAX_AST_NODES = 32
MAX_DEPTH = 16
MAX_ABS_RESULT = 10**18
MAX_EXPONENT = 12

_PREFIXES = (
    "what is ",
    "was ist ",
    "calculate ",
    "compute ",
    "berechne ",
)
_ALLOWED = re.compile(r"[0-9\\s()+\\-*/%.]+\\Z")


def is_text_only_event(event: object) -> bool:
    """Reject audio and non-text modalities so RAW EAR is never bypassed."""
    if not isinstance(event, dict):
        return False
    source_ref = event.get("source_ref")
    return (
        isinstance(source_ref, dict)
        and source_ref.get("modality") == "text"
        and event.get("_audio_window") is None
    )


def _extract_expression(text: object) -> str | None:
    if type(text) is not str or not 1 <= len(text) <= MAX_TEXT_CHARS:
        return None
    value = unicodedata.normalize("NFKC", text).strip().casefold()
    value = re.sub(r"[?.!…]+\\Z", "", value).strip()
    for prefix in _PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
            break
    if not _ALLOWED.fullmatch(value):
        return None
    if not any(ch.isdigit() for ch in value):
        return None
    if not any(ch in "+-*/%" for ch in value):
        return None
    return value


def _bounded(value: Fraction) -> Fraction:
    if (value.numerator.bit_length() > 128
            or value.denominator.bit_length() > 128
            or abs(value) > MAX_ABS_RESULT):
        raise ValueError("arithmetic result outside exact fastpath bounds")
    return value


def _evaluate(node: ast.AST, *, depth: int, counter: list[int]) -> Fraction:
    if depth > MAX_DEPTH:
        raise ValueError("arithmetic expression too deep")
    counter[0] += 1
    if counter[0] > MAX_AST_NODES:
        raise ValueError("arithmetic expression too complex")

    if isinstance(node, ast.Constant):
        if type(node.value) is int:
            return _bounded(Fraction(node.value, 1))
        if type(node.value) is float and math.isfinite(node.value):
            return _bounded(Fraction(str(node.value)))
        raise ValueError("only finite real numeric literals are supported")

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand, depth=depth + 1, counter=counter)
        return _bounded(value if isinstance(node.op, ast.UAdd) else -value)

    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left, depth=depth + 1, counter=counter)
        right = _evaluate(node.right, depth=depth + 1, counter=counter)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise ZeroDivisionError("division by zero")
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ZeroDivisionError("division by zero")
            result = Fraction(left // right, 1)
        elif isinstance(node.op, ast.Mod):
            if right == 0:
                raise ZeroDivisionError("modulo by zero")
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if right.denominator != 1 or abs(right.numerator) > MAX_EXPONENT:
                raise ValueError("exponent outside exact fastpath bounds")
            exponent = right.numerator
            if exponent < 0 and left == 0:
                raise ZeroDivisionError("zero cannot have a negative exponent")
            result = left ** exponent
        else:
            raise ValueError("unsupported arithmetic operator")
        return _bounded(Fraction(result))

    raise ValueError("unsupported arithmetic syntax")


def _format(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)

    remaining = value.denominator
    twos = fives = 0
    while remaining % 2 == 0:
        remaining //= 2
        twos += 1
    while remaining % 5 == 0:
        remaining //= 5
        fives += 1

    if remaining == 1:
        scale = max(twos, fives)
        scaled = value.numerator * (2 ** (scale - twos)) * (5 ** (scale - fives))
        sign = "-" if scaled < 0 else ""
        digits = str(abs(scaled)).rjust(scale + 1, "0")
        whole = digits[:-scale]
        fractional = digits[-scale:].rstrip("0")
        return sign + whole + ("." + fractional if fractional else "")

    return f"{value.numerator}/{value.denominator}"


def match(text: object, *, event: object = None) -> dict | None:
    """Return an exact answer only for one bounded standalone arithmetic expression."""
    if event is not None and not is_text_only_event(event):
        return None
    expression = _extract_expression(text)
    if expression is None:
        return None
    try:
        parsed = ast.parse(expression, mode="eval")
        value = _evaluate(parsed.body, depth=0, counter=[0])
        result = _format(value)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError,
            OverflowError, RecursionError):
        return None
    return {
        "rule_id": RULE_ID,
        "scope": "EXACT_SINGLE_EXPRESSION_ONLY",
        "expression": " ".join(expression.split()),
        "result": result,
        "reply": result,
        "exact": True,
    }
