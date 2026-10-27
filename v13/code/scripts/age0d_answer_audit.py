"""WP-AGE0d: narrow, answer-aware arithmetic diagnostic. NOT a live self-correction hook.

Only anchored EN/DE arithmetic questions and unambiguous numeric answers are
accepted. Everything else abstains. No model, store, tools, or message delivery.
"""
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import hashlib
import json
import re

REVISION = 'age0d-answer-audit-v1'
NUMBER = r'[+-]?(?:\d{1,12}(?:[.,]\d{1,12})?)'
BINARY = re.compile(
    rf'(?:what is|calculate|compute|wie viel ist|berechne)\s+'
    rf'(?P<left>{NUMBER})\s*(?P<op>[+*/x×÷-])\s*(?P<right>{NUMBER})\s*\??',
    re.IGNORECASE,
)
HALF = re.compile(
    rf'(?:what is half of|calculate half of|wie viel ist die hälfte von|'
    rf'berechne die hälfte von)\s+(?P<value>{NUMBER})\s*(?:euro|€)?\s*[?.]?',
    re.IGNORECASE,
)
BUDGET_HALF = re.compile(
    rf'budget\s+(?P<value>{NUMBER})\s+euro\.\s*berechne die hälfte\.',
    re.IGNORECASE,
)
ANSWER = re.compile(
    rf'(?:(?:answer|ergebnis)\s*:\s*|(?:the answer is|das ergebnis ist)\s+)?'
    rf'(?P<value>{NUMBER})\s*(?:euro|€)?\s*\.?',
    re.IGNORECASE,
)
STATUSES = ('CORRECT', 'MISMATCH', 'ABSTAIN')


def _number(text):
    try:
        return Decimal(text.replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _exact_divide(left, right):
    """Return None for zero division or recurring decimals (no rounding alarms)."""
    if not right:
        return None
    quotient = Fraction(left) / Fraction(right)
    denominator = quotient.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1:
        return None
    with localcontext() as ctx:
        ctx.prec = 64
        return Decimal(quotient.numerator) / Decimal(quotient.denominator)


def _question(text):
    if type(text) is not str or not 1 <= len(text) <= 160 or any(c in text for c in '\r\n\t'):
        return None
    q = text.strip()
    half = HALF.fullmatch(q) or BUDGET_HALF.fullmatch(q)
    if half:
        value = _number(half.group('value'))
        return None if value is None else _exact_divide(value, Decimal(2))
    m = BINARY.fullmatch(q)
    if m is None:
        return None
    left, right = _number(m.group('left')), _number(m.group('right'))
    if left is None or right is None:
        return None
    op = m.group('op').lower()
    if op == '+':
        return left + right
    if op == '-':
        return left - right
    if op in ('*', 'x', '×'):
        return left * right
    if op in ('/', '÷'):
        return _exact_divide(left, right)
    return None


def audit(question, answer):
    """Return structured evidence only; a mismatch NEVER grants delivery rights."""
    result = {'revision': REVISION, 'status': 'ABSTAIN',
              'reason': 'UNSUPPORTED_OR_AMBIGUOUS', 'delivery_allowed': False,
              'authority': 'NONE', 'evidence_level': 'SOFTWARE_DETERMINISTIC_ONLY'}
    expected = _question(question)
    if expected is None or type(answer) is not str or not 1 <= len(answer) <= 120:
        return result
    if any(c in answer for c in '\r\n\t'):
        return result
    m = ANSWER.fullmatch(answer.strip())
    if m is None:
        return result
    observed = _number(m.group('value'))
    if observed is None:
        return result
    match = observed == expected
    return {**result, 'status': 'CORRECT' if match else 'MISMATCH',
            'reason': 'EXACT_ARITHMETIC_MATCH' if match else 'EXACT_ARITHMETIC_MISMATCH',
            'expected': str(expected), 'observed': str(observed)}


def score_cases(cases):
    """No prompts or answers in the report; synthetic fixture hash is provenance."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError('Expected nonempty frozen cases')
    counts = {status: 0 for status in STATUSES}
    unexpected = 0
    for case in cases:
        if not isinstance(case, (tuple, list)) or len(case) != 3 or case[2] not in STATUSES:
            raise ValueError('Invalid frozen case')
        actual = audit(case[0], case[1])['status']
        counts[case[2]] += 1
        unexpected += actual != case[2]
    fixture = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return {'revision': REVISION, 'fixture_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
            'expected_counts': counts, 'unexpected': unexpected,
            'false_mismatch_on_correct': sum(
                audit(q, a)['status'] == 'MISMATCH' for q, a, status in cases if status == 'CORRECT'),
            'detected_wrong': sum(
                audit(q, a)['status'] == 'MISMATCH' for q, a, status in cases if status == 'MISMATCH'),
            'abstained_unsupported': sum(
                audit(q, a)['status'] == 'ABSTAIN' for q, a, status in cases if status == 'ABSTAIN'),
            'runtime_wired': False, 'utility_proven': False, 'age_authority': 0}
