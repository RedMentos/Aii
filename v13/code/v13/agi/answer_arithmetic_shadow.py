"""WP-AGE0d candidate: answer-visible, source-bound arithmetic cross-check.

Pure SHADOW diagnostic. No runtime consumer, no message delivery, no claim of
model accuracy. Only one explicitly phrased English arithmetic operation is
supported; ambiguous answers abstain. Inputs and evidence remain in memory.
"""
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction

AUTHORITY = 'SHADOW_ONLY'
MAX_QUESTION = 2000
MAX_ANSWER = 256
NUMBER = r'[+-]?\d{1,9}(?:\.\d{1,4})?'
RESULT_NUMBER = r'[+-]?\d{1,18}(?:\.\d{1,4})?'
OPERATOR = r'(?:\+|\-|−|plus|minus|times|\*|multiplied\s+by|divided\s+by|/)'  # one operation only
QUESTION = re.compile(
    rf'\s*(?:what\s+is|calculate|compute)\s+(?P<a>{NUMBER})\s+(?P<op>{OPERATOR})\s+(?P<b>{NUMBER})\s*[?.]?\s*',
    re.IGNORECASE,
)
BARE = re.compile(rf'\s*(?P<result>{RESULT_NUMBER})\.?\s*', re.IGNORECASE)
SENTENCE = re.compile(
    rf'\s*(?:the\s+answer\s+is|it\s+is|result\s*:)\s*(?P<result>{RESULT_NUMBER})\.?\s*', re.IGNORECASE
)
EQUATION = re.compile(
    rf'\s*(?P<a>{NUMBER})\s*(?P<op>{OPERATOR})\s*(?P<b>{NUMBER})\s*=\s*(?P<result>{RESULT_NUMBER})\.?\s*',
    re.IGNORECASE,
)


def _operation(text):
    t = ' '.join(text.lower().split())
    if t in ('+', 'plus'): return '+'
    if t in ('-', '−', 'minus'): return '-'
    if t in ('*', 'times', 'multiplied by'): return '*'
    if t in ('/', 'divided by'): return '/'
    return None


def _canonical(value):
    if value == 0: return '0'
    return format(value.normalize(), 'f')


def _expected(a, op, b):
    if op == '+': return a + b
    if op == '-': return a - b
    if op == '*': return a * b
    if op != '/' or b == 0: return None
    frac = Fraction(a) / Fraction(b)
    # Finite decimal with <=4 fractional places only. No rounding verdicts.
    d = frac.denominator
    for p in (2, 5):
        while d % p == 0: d //= p
    if d != 1: return None
    value = Decimal(frac.numerator) / Decimal(frac.denominator)
    if value.as_tuple().exponent < -4: return None
    return value


def evaluate(question, answer):
    """Return CORRECT/MISMATCH/ABSTAIN, never a command to revise/deliver.

    The two evidence spans are included for local human review only; callers
    must not persist or broadcast them without separate user permission.
    """
    base = {'status': 'ABSTAIN', 'reason': 'unsupported_or_ambiguous',
            'authority': AUTHORITY, 'may_deliver': False}
    if not isinstance(question, str) or not isinstance(answer, str): return base
    if len(question) > MAX_QUESTION or len(answer) > MAX_ANSWER: return base
    if '\n' in question or '\r' in question or '\n' in answer or '\r' in answer: return base
    m = QUESTION.fullmatch(question)
    if m is None: return base
    op = _operation(m.group('op'))
    if op is None: return base
    try:
        a, b = Decimal(m.group('a')), Decimal(m.group('b'))
        expected = _expected(a, op, b)
    except (InvalidOperation, OverflowError, ValueError, ZeroDivisionError):
        return base
    if expected is None or abs(expected) > Decimal('1e18'): return base
    n = BARE.fullmatch(answer) or SENTENCE.fullmatch(answer)
    if n is None:
        n = EQUATION.fullmatch(answer)
        if n is None: return base
        # Echo must be the same ordered operation and exact operand values.
        try:
            if (Decimal(n.group('a')), _operation(n.group('op')), Decimal(n.group('b'))) != (a, op, b):
                return base
        except InvalidOperation:
            return base
    try: claimed = Decimal(n.group('result'))
    except InvalidOperation: return base
    return {'status': 'CORRECT' if claimed == expected else 'MISMATCH',
            'reason': 'exact_single_operation_check', 'authority': AUTHORITY,
            'may_deliver': False, 'expected': _canonical(expected),
            'claimed': _canonical(claimed),
            'question_span': question[m.start('a'):m.end('b')],
            'answer_span': answer[n.start('result'):n.end('result')]}
