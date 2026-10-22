"""R4 part 6: arithmetic over listed values as a READ_LOCAL tool (`list_arith`).

Measured in R4 part 5 (docs/proofs/continuation-20261012/r4-typed-recipe/BEFUND.md, preregistered, fresh seed 17):
C3 LFM2.5-350M reads listed numbers reliably but can neither compute nor pick the operation; a fixed rule picking the
operation from the question wording plus a deterministic recipe raised the pass rate from 40/60 to 50/60 (p .006).
Here the same pieces become a tool in the live turn: `operation(text)` is the BOOT rule (like the regex proposer in
toolstep.py, not learned), the model reads typed values through READ_SCHEMA, and `tool()` re-checks every value against
the user's own text (WP-W2 number guard) before computing. Claim limit: English only; rule R3 (parts 9/10) misses about 40 % of new
wordings, and those get no proposal.
"""
import json
import re

OPERATIONS = ((re.compile(r'(?i)\bhow (?:many|much)\b[^.?]*\b(?:more|less|fewer)\b[^.?]*\bthan\b'), 'difference_max_min'),
              (re.compile(r'(?i)\b(?:total|sum)\b'), 'total'))
# R4 parts 9/10 (docs/proofs/continuation-20261012/r4-rule-r3/BEFUND.md, rule R3): wordings from training family A only, the
# rule reads the question part only (data lines like "Total: 173 euros." caused false alarms), and a total/overall
# number or count of things is counting, not a sum. New family E: macro-F1 .73 vs .50, 0 false alarms, 0 sum/difference mix-ups.
EXTRA = ((re.compile(r'(?i)\bdifference between\b|\bexceeds?\b|\bgap between\b|\bfar apart\b'), 'difference_max_min'),
         (re.compile(r'(?i)\badd\b[^.?]*\bup\b|\baltogether\b|\bcombined\b'), 'total'))
COUNT = re.compile(r'(?i)\b(?:total|overall)\s+(?:number|count)\s+of\b')
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
    if COUNT.search(q):
        return None
    return next((op for rx, op in OPERATIONS+EXTRA if rx.search(q)), None)


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
    tokens = {token.replace('\u2212', '-').lstrip('+') for token in _INT.findall(str(text))}
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


# WP-DS3b (bench-results/ds3b-name-check-20261022/BEFUND.md, preregistered, fresh seeds 47/53/59): after the recipe most
# wrong answers are confident (right number, wrong city), so token uncertainty misses them. A fixed cross-check of the
# finished answer against the executed recipe caught 18 of 21 wrong tool answers (precision .78). Only runs under cfg
# tool_answer_check (default off).
MAX_WORDS = re.compile(r'(?i)\b(?:most|largest|highest|greatest|wettest|maximum|max)\b')
NEGATION = re.compile(r"(?i)\b(?:no|not|incorrect|wrong|error|mistake|discrepancy|does not match|doesn't match)\b")
_ANS_NUM = re.compile(r'(?<![\d.,])\d+(?![\d])')
CHECK_NOTE = ('Check: this answer does not match the exact local calculation ({recipe} = {value}). '
              'Treat the answer above as unsure.')


def _clauses(answer):
    return [c for c in re.split(r'(?<=[.;!?])\s+|,\s+(?:and\s+|while\s+|but\s+)?|\s+(?:and|while|but|whereas)\s+', str(answer)) if c.strip()]


def _named(clause, names):
    hits = []
    for n in names:
        m = re.search(r'(?i)(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])', clause)
        if m:
            hits.append((m.start(), n))
    return [n for _, n in sorted(hits)]


def answer_check(args, value, answer):
    """(ok, reason): does the finished answer agree with the executed recipe? Uses only the user text, the read values
    and the result: the answer names the result; for difference_max_min the clause saying "most/largest/..." names the
    recipe's largest item; when the user text asks whether a stated number is correct and that number differs from the
    result, the answer says it is wrong."""
    values = [v for v in decode(args['values']) if not AGGREGATE.match(str(v.get('name', '')))]
    names = [str(v['name']).strip() for v in values if str(v['name']).strip()]
    text = str(args['text']); answer = str(answer)
    if str(value) not in _ANS_NUM.findall(answer):
        return False, 'value_missing'
    if args['operation'] == 'difference_max_min' and names:
        nums = [int(v['number']) for v in values]; hi = names[nums.index(max(nums))]
        if not _named(answer, names):
            return False, 'no_item_named'
        for c in _clauses(answer):
            got = _named(c, names)
            if MAX_WORDS.search(c) and got and got[0] != hi:
                return False, 'wrong_largest'
        if hi.lower() not in answer.lower():
            return False, 'largest_not_named'
    if re.search(r'(?i)\bcorrect\?', text):
        read = {int(v['number']) for v in values}
        stated = [int(n) for n in _ANS_NUM.findall(text[:text.rfind('?')+1]) if int(n) not in read]
        if any(n != value for n in stated) and not NEGATION.search(answer):
            return False, 'stated_number_not_flagged'
    return True, 'ok'


def check_note(args, value):
    return CHECK_NOTE.format(recipe=label(args) or args['operation'], value=value)
