"""WP-AGE0d candidate: answer-aware exact integer arithmetic SHADOW checker.

Unlike the failed Age0c missing-number heuristic, this candidate inspects the
actual final answer. It verifies only explicit bounded integer equations or
strict question-expression + numeric-answer pairs. It does not decide whether
an answer addresses the question, deliver a correction, learn, or gain any Age
right. Real correct/incorrect-answer calibration is still required.
"""
from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import re

REVISION = "v13-age0d-answer-arithmetic-shadow-run12f-v1"
AUTHORITY = "SHADOW_ONLY_NO_DELIVERY"
MAX_CHARS = 4096
MAX_RESULT = 10**12
INT = r"[+-]?\d{1,6}"
EXPR = rf"{INT}(?:\s*[+\-*/×÷]\s*{INT}){{1,3}}"
EQ = re.compile(rf"(?<![\w.+*/×÷-])(?P<expr>{EXPR})\s*=\s*(?P<rhs>[+-]?\d{{1,9}})(?![\w.+*/×÷-])")
QUESTION = re.compile(r"\s*(?:what is|calculate|was ist|berechne)\s+(.+?)\s*\??\s*", re.I)
ANSWER = re.compile(r"\s*([+-]?\d{1,9})[.!]?\s*")


class UnsafeExpression(ValueError):
    pass


def _bounded(value):
    if abs(value) > MAX_RESULT:
        raise UnsafeExpression("RESULT_BOUND")
    return value


def evaluate(expression):
    """Exact Fraction result; no eval, names, calls, exponent or float literals."""
    if type(expression) is not str or len(expression) > 100:
        raise UnsafeExpression("EXPRESSION_BOUND")
    normalized = expression.replace("×", "*").replace("÷", "/")
    if not re.fullmatch(EXPR, expression):
        raise UnsafeExpression("EXPRESSION_GRAMMAR")
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise UnsafeExpression("EXPRESSION_SYNTAX") from exc

    def visit(node, depth=0):
        if depth > 8:
            raise UnsafeExpression("AST_DEPTH")
        if isinstance(node, ast.Expression):
            return visit(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return _bounded(Fraction(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth + 1)
            return _bounded(value if isinstance(node.op, ast.UAdd) else -value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = visit(node.left, depth + 1)
            right = visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return _bounded(left + right)
            if isinstance(node.op, ast.Sub):
                return _bounded(left - right)
            if isinstance(node.op, ast.Mult):
                return _bounded(left * right)
            if right == 0:
                raise UnsafeExpression("DIVIDE_BY_ZERO")
            return _bounded(left / right)
        raise UnsafeExpression("AST_NOT_ALLOWED")

    return visit(tree)


def _base(status, reason, evidence=()):
    return {
        "revision": REVISION, "authority": AUTHORITY,
        "status": status, "reason": reason, "evidence": list(evidence),
        "delivery_allowed": False, "learning_allowed": False,
        "age_promotion": False, "whole_answer_verified": False,
    }


def inspect(question, final_answer):
    """Bounded exact-arithmetic diagnostic, not a general truth detector."""
    if type(question) is not str or type(final_answer) is not str:
        return _base("ABSTAIN", "NON_TEXT")
    if len(question) > MAX_CHARS or len(final_answer) > MAX_CHARS:
        return _base("ABSTAIN", "TEXT_BOUND")
    # Quoted examples or code can be intentionally false; do not call them errors.
    if any(marker in final_answer for marker in ('`', '"', '“', '”', '„', '«', '»', '‘', '’', "'")):
        return _base("ABSTAIN", "QUOTED_OR_CODE_EXAMPLE")
    matches = list(EQ.finditer(final_answer))
    if matches:
        evidence = []
        for match in matches:
            expr, rhs = match.group("expr"), int(match.group("rhs"))
            try:
                expected = evaluate(expr)
            except UnsafeExpression:
                return _base("ABSTAIN", "UNSAFE_EXPLICIT_EXPRESSION")
            correct = expected == rhs
            evidence.append({
                "kind": "EXPLICIT_EQUATION", "equation": match.group(),
                "expected": str(expected), "actual": str(rhs),
                "correct": correct,
            })
        if any(not item["correct"] for item in evidence):
            return _base("POSSIBLE_ARITHMETIC_ERROR_SHADOW", "EXPLICIT_EQUATION_MISMATCH", evidence)
        return _base("LOCAL_ARITHMETIC_CONSISTENT", "EXPLICIT_EQUATIONS_MATCH", evidence)
    # No general free-text numeric extraction: only a strict simple math question
    # and a bare integer answer. Extra context => ABSTAIN, not a false alarm.
    query = QUESTION.fullmatch(question)
    answer = ANSWER.fullmatch(final_answer)
    if not query or not answer:
        return _base("ABSTAIN", "NO_UNAMBIGUOUS_ARITHMETIC_PAIR")
    try:
        expected = evaluate(query.group(1))
    except UnsafeExpression:
        return _base("ABSTAIN", "UNSAFE_QUESTION_EXPRESSION")
    actual = int(answer.group(1))
    evidence = [{
        "kind": "QUESTION_ANSWER_INTEGER", "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "expected": str(expected), "actual": str(actual), "correct": expected == actual,
    }]
    if expected != actual:
        return _base("POSSIBLE_ARITHMETIC_ERROR_SHADOW", "QUESTION_ANSWER_MISMATCH", evidence)
    return _base("LOCAL_ARITHMETIC_CONSISTENT", "QUESTION_ANSWER_MATCH", evidence)
