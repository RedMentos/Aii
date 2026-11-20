"""Source-exact bounded integer arithmetic evidence for C/JEF, never model authority.

Only a complete, unambiguous expression is accepted. No eval, Python parsing,
fuzzy intent detection, implicit tool execution or floating point.
"""
import re

_PATTERN = re.compile(r"[ \t]*(?:what is|what's|calculate|compute|was ist|wie viel ist|wieviel ist)?[ \t]*([+-]?\d{1,9})[ \t]*([+*×-])[ \t]*([+-]?\d{1,9})[ \t]*\??[ \t]*", re.IGNORECASE)

def evidence(source):
    if not isinstance(source, str) or len(source) > 96:
        return None
    # A bare ISO year-month is more likely a date than an arithmetic request.
    if re.fullmatch(r"[ \\t]*\\d{4}-\\d{1,2}[ \\t]*", source):
        return None
    m = _PATTERN.fullmatch(source)
    if m is None:
        return None
    a, op, b = m.groups()
    left, right = int(a), int(b)
    if op == '+':
        result = left + right
    elif op == '-':
        result = left - right
    else:
        result = left * right
    return {
        'kind': 'SOURCE_EXACT_INTEGER_ARITHMETIC',
        'source': source,
        'operands': [left, right],
        'operator': '*' if op == '×' else op,
        'result': str(result),
        'model_generated': False,
        'authority': 'DETERMINISTIC_EVIDENCE_ONLY',
    }


def direct_output(*, fixed_answer=None, exact_copy=None, arithmetic=None):
    """Choose a verified local direct output without dereferencing an absent copy match."""
    if fixed_answer is not None:
        return fixed_answer
    if exact_copy is not None:
        return exact_copy
    if (type(arithmetic) is dict
            and arithmetic.get('authority') == 'DETERMINISTIC_EVIDENCE_ONLY'
            and type(arithmetic.get('result')) is str):
        return arithmetic['result']
    raise ValueError('No verified direct output')
