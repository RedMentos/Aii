"""R4 part 6: arithmetic over listed values as a READ_LOCAL tool (`list_arith`).

Measured in R4 part 5 (docs/proofs/continuation-20261012/r4-typed-recipe/BEFUND.md, preregistered, fresh seed 17):
C3 LFM2.5-350M reads listed numbers reliably but can neither compute nor pick the operation; a fixed rule picking the
operation from the question wording plus a deterministic recipe raised the pass rate from 40/60 to 50/60 (p .006).
Here the same pieces become a tool in the live turn: `operation(text)` is the BOOT rule (like the regex proposer in
toolstep.py, not learned), the model reads typed values through READ_SCHEMA, and `tool()` re-checks every value against
the user's own text (WP-W2 number guard) before computing. Claim limit: English R3 plus conservative German BOOT wording; native German reading unmeasured; R3 misses about 40 % of new
wordings, and those get no proposal.
"""
import json
import re
from collections import Counter

OPERATIONS = ((re.compile(r'(?i)\bhow (?:many|much)\b[^.?]*\b(?:more|less|fewer)\b[^.?]*\bthan\b'), 'difference_max_min'),
              (re.compile(r'(?i)\b(?:total|sum)\b'), 'total'))
# R4 parts 9/10 (docs/proofs/continuation-20261012/r4-rule-r3/BEFUND.md, rule R3): wordings from training family A only, the
# rule reads the question part only (data lines like "Total: 173 euros." caused false alarms), and a total/overall
# number or count of things is counting, not a sum. New family E: macro-F1 .73 vs .50, 0 false alarms, 0 sum/difference mix-ups.
EXTRA = ((re.compile(r'(?i)\bdifference between\b|\bexceeds?\b|\bgap between\b|\bfar apart\b'), 'difference_max_min'),
         (re.compile(r'(?i)\badd\b[^.?]*\bup\b|\baltogether\b|\bcombined\b'), 'total'))
COUNT = re.compile(r'(?i)\b(?:total|overall)\s+(?:number|count)\s+of\b')
# Run362: conservative German question-only BOOT rules. A generic "difference
# between A and B" is NOT necessarily max-minus-min when a list has >2 rows.
DE_COUNT = re.compile(r'(?i)\b(?:gesamtanzahl|anzahl(?:\s+(?:der|von))?|wie\s+viele\s+(?:einträge|posten|artikel|positionen|personen|zeilen|stücke|teile|produkte|werte|zahlen|elemente|gruppen))\b')
# "Wie viele" normally asks for a count, even when the noun embeds "Preis".
# Explicit "wie viele Euro sind ..." is an amount, not a number of entries.
DE_PLURAL_COUNT = re.compile(r'(?i)\bwie\s+viele\b(?!\s+euro(?:\s|$))')
DE_DIFF_CUE = re.compile(r'(?i)\b(?:differenz|unterschied|abstand|auseinander|mehr|weniger)\b')
DE_HIGH = re.compile(r'(?i)\b(?:größt\w*|höchst\w*|maxim\w*)\b')
DE_LOW = re.compile(r'(?i)\b(?:kleinst\w*|niedrigst\w*|minim\w*)\b')
DE_TOTAL_STRONG = re.compile(r'(?i)\b(?:summe|gesamtbetrag|addier\w*|aufsummier\w*|zusammenrechn\w*)\b')
DE_TOTAL_WEAK = re.compile(r'(?i)\b(?:zusammen|insgesamt)\b')
DE_AMOUNT = re.compile(r'(?i)\b(?:wie\s+viel\b|wie\s+viele\s+euro\b|wie\s+hoch\b|was\s+kostet\b|was\s+kosten\b|was\s+ergibt\b|betrag\w*|preis\w*|kosten\b|euro\b)\b')
DE_REQUEST = re.compile(r'(?i)\?|\b(?:wie|was|addier\w*|berechn\w*|ermitt\w*|rechne\w*)\b')
READ_SYSTEM = ('Read the numbers in the text. Return JSON only. values: every listed item with its name and its number '
               'copied exactly from the text. Never calculate anything yourself.')
READ_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['values'], 'properties': {
    'values': {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'number'],
                                                          'properties': {'name': {'type': 'string', 'maxLength': 40}, 'number': {'type': 'integer'}}}}}}
SCHEMA = {'operation': 'str', 'text': 'text', 'values': 'text'}
MAX_TEXT = 2000
_INT = re.compile(r'(?<![\d.+\-\u2212])[+\-\u2212]?\d+(?!\d|\.\d)')  # keep a sign; sentence-final period is not a decimal point
# R4 part 7: C3 read a stated summary line ("Total: 173 euros") as one more item in 1/30 sums on seeds 7 and 19;
# the guard passes it because 173 is in the text. A value with such a name is the claim under test, never an input.
AGGREGATE = re.compile(r'(?i)^\s*(?:the\s+)?(?:grand\s+|stated\s+)?(?:total|sum|summe|gesamt\w*|summary(?:\s+line)?)\s*$')


def question_part(text):
    """Trailing sentences without digits (the question asked about the data); else the last sentence."""
    parts = [p for p in re.split(r'(?<=[.!?"])\s+', str(text).strip()) if p]
    tail = []
    for p in reversed(parts):
        if re.search(r'\d', p):
            break
        tail.insert(0, p)
    return ' '.join(tail) if tail else (parts[-1] if parts else str(text))


def operation(text):
    """BOOT rule R3 on the question part: which recipe the question asks for, or None."""
    t = str(text)
    if len(t) > MAX_TEXT:
        return None
    q = question_part(t)
    if COUNT.search(q) or DE_COUNT.search(q) or DE_PLURAL_COUNT.search(q):
        return None
    english=next((op for rx, op in OPERATIONS+EXTRA if rx.search(q)), None)
    if english is not None:
        return english
    # German is conservative: no data-line-only trigger, no ambiguous
    # two-named-item difference when the actual list may have more items.
    if not DE_REQUEST.search(q):
        return None
    if DE_DIFF_CUE.search(q) and DE_HIGH.search(q) and DE_LOW.search(q):
        return 'difference_max_min'
    if DE_TOTAL_STRONG.search(q) or (DE_TOTAL_WEAK.search(q) and DE_AMOUNT.search(q)):
        return 'total'
    return None


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
    values = [v for v in values if not AGGREGATE.match(str(v.get('name', '')))]
    nums = [int(v['number']) for v in values]
    if len(nums) < 2:
        raise ValueError('fewer than two values')
    tokens = Counter(token.replace('\u2212', '-').lstrip('+') for token in _INT.findall(str(text)))
    # Review 2026-10-21 (Claude for GPT): count occurrences, so a value read twice must also appear twice in the text.
    if any(c > tokens[n] for n, c in Counter(str(n) for n in nums).items()):
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
