"""Source-exact bounded integer arithmetic evidence for C/JEF, never model authority.

Only a complete, unambiguous expression is accepted. No eval, Python parsing,
fuzzy intent detection, implicit tool execution or floating point.
"""
import re

_PATTERN = re.compile(r"[ \t]*(?:what is|what's|calculate|compute|was ist|wieviel ist)?[ \t]*([+-]?\d{1,9})[ \t]*([+*×-])[ \t]*([+-]?\d{1,9})[ \t]*\??[ \t]*", re.IGNORECASE)

def evidence(source):
    if not isinstance(source, str) or len(source) > 96:
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
