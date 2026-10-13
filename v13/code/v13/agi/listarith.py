"""R4 part 6: arithmetic over listed values as a READ_LOCAL tool (`list_arith`).

Measured in R4 part 5 (docs/proofs/continuation-20261012/r4-typed-recipe/BEFUND.md, preregistered, fresh seed 17):
C3 LFM2.5-350M reads listed numbers reliably but can neither compute nor pick the operation; a fixed rule picking the
operation from the question wording plus a deterministic recipe raised the pass rate from 40/60 to 50/60 (p .006).
Here the same pieces become a tool in the live turn: `operation(text)` is the BOOT rule (like the regex proposer in
toolstep.py, not learned), the model reads typed values through READ_SCHEMA, and `tool()` re-checks every value against
the user's own text (WP-W2 number guard) before computing. Claim limit: English wording of the R4 tasks only; other
phrasings return no operation and nothing is proposed.
"""
import json
import re

OPERATIONS = ((re.compile(r'(?i)\bhow (?:many|much)\b[^.?]*\b(?:more|less|fewer)\b[^.?]*\bthan\b'), 'difference_max_min'),
              (re.compile(r'(?i)\b(?:total|sum)\b'), 'total'))
READ_SYSTEM = ('Read the numbers in the text. Return JSON only. values: every listed item with its name and its number '
               'copied exactly from the text. Never calculate anything yourself.')
READ_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['values'], 'properties': {
    'values': {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'number'],
                                                          'properties': {'name': {'type': 'string', 'maxLength': 40}, 'number': {'type': 'integer'}}}}}}
SCHEMA = {'operation': 'str', 'text': 'text', 'values': 'text'}
MAX_TEXT = 2000
_INT = re.compile(r'(?<![\d.])\d+(?!\d|\.\d)')  # a sentence-final period is not a decimal point


def operation(text):
    """BOOT rule: which recipe the question asks for, or None."""
    t = str(text)
    if len(t) > MAX_TEXT:
        return None
    return next((op for rx, op in OPERATIONS if rx.search(t)), None)


def encode(values):
    """Typed values -> 'name=number' lines (the tool's text argument)."""
    return '\n'.join(f"{str(v['name']).strip().replace('=', ' ')[:40]}={int(v['number'])}" for v in values)


def decode(lines):
    out = []
    for line in str(lines).split('\n'):
        if line.strip():
            name, _, number = line.rpartition('=')
            out.append({'name': name.strip(), 'number': int(number)})
    return out


def compute(op, values, text):
    """Recipe with number guard; returns (value, label) or raises ValueError."""
    if op not in ('total', 'difference_max_min'):
        raise ValueError('unknown operation')
    nums = [int(v['number']) for v in values]
    if len(nums) < 2:
        raise ValueError('fewer than two values')
    tokens = set(_INT.findall(str(text)))
    if any(str(n) not in tokens for n in nums):
        raise ValueError('number not in the user text')
    names = [str(v.get('name', '')).strip()[:40] for v in values]
    if op == 'total':
        return sum(nums), ' + '.join(f'{n} {x}' if n else str(x) for n, x in zip(names, nums))
    hi = max(range(len(nums)), key=lambda i: nums[i]); lo = min(range(len(nums)), key=lambda i: nums[i])
    return nums[hi]-nums[lo], f'largest {names[hi]} {nums[hi]} - smallest {names[lo]} {nums[lo]}'


def tool(operation, text, values):
    """ToolRegistry entry point: deterministic, re-checks every value against the text."""
    return compute(operation, decode(values), text)[0]


def label(args):
    """Human-readable recipe line for the answering body (largest/smallest named), or None."""
    try:
        return compute(args['operation'], decode(args['values']), args['text'])[1]
    except (KeyError, ValueError, TypeError):
        return None


def read_values(runner, text, cancel, deadline, max_tokens=160):
    """The model only reads typed values; returns the list or raises ValueError/JSON errors."""
    raw = ''.join(runner.generate([{'role': 'system', 'content': READ_SYSTEM}, {'role': 'user', 'content': str(text)}],
                                  cancel, deadline, max_tokens, READ_SCHEMA))
    values = json.loads(raw)['values']
    if not isinstance(values, list):
        raise ValueError('values')
    return values
