"""R4 part 9: BOOT wording rule for list_arith applied to the question only (no model).

Part 8 (r4_tool_choice_head.py): the current rule R0 (agi/listarith.operation on the whole text) misses 70 % of new English
wordings and its false alarms come from the data ("Total: 173 euros." in an expense list). Variants, frozen here:
  R0  current rule on the whole text
  R1  same patterns on the question part only (trailing sentences without digits; else the last sentence)
  R2  R1 + wordings taken only from training family A of part 8 (add up, altogether, combined, difference between, exceed,
      gap between, apart)
Test family B of part 8 is exposed (its rule results were read), so a new family D (written before any rule ran on it) and
the old utility_bench2 R4 tasks (must keep their operation) decide.
  prereg    r4_rule_question_only.py prereg <prereg.json>
  evaluate  r4_rule_question_only.py evaluate <prereg.json> <report.json>
Claim limit: generated English texts, one author for all families; no model involved."""
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from v13.agi import listarith  # noqa: E402
import r4_tool_choice_head as H  # noqa: E402
import utility_bench2 as U2  # noqa: E402

FAMILY_D = {
    'total': ("What's the sum total here?", 'Work out the total amount for me.', 'Add up every value.', 'What is everything combined?',
              'Please total these values.', 'How much do they make together?'),
    'difference_max_min': ('What is the difference between the biggest and the smallest value?', 'How much does the top entry exceed the bottom one by?',
                           'How many fewer does the lowest have than the highest?', 'What is the range from lowest to highest?',
                           'How much bigger is the largest than the smallest?', 'Find the gap between the maximum and minimum.'),
    'none': ('Which value is highest?', 'Put the entries in order.', 'What is the total number of entries?', 'Which entry is in the middle?',
             'Which two entries are closest?', 'Name every entry.', 'How many values are above 40?')}
SEED_D = 804
R2_EXTRA = ((re.compile(r'(?i)\bdifference between\b|\bexceeds?\b|\bgap between\b|\bfar apart\b'), 'difference_max_min'),
            (re.compile(r'(?i)\badd\b[^.?]*\bup\b|\baltogether\b|\bcombined\b'), 'total'))
DECISION = ("Family D (new) plus part-8 family A as sanity: R2 adopted iff on D false-alarm rate <= 0.05 AND sum<->difference confusion "
            "<= 0.02 AND macro-F1 >= R0 + 0.15 AND all 60 utility_bench2 tasks of seeds 7, 11, 13, 17, 19, 23 keep R0's operation. "
            "Else R1 adopted iff on D false-alarm rate <= 0.05, confusion <= 0.02, macro-F1 >= R0 and the same task check. Else nothing.")


def question_part(text):
    """Trailing sentences without digits (the question asked about the data); else the last sentence."""
    parts = [p for p in re.split(r'(?<=[.!?"])\s+', str(text).strip()) if p]
    tail = []
    for p in reversed(parts):
        if re.search(r'\d', p):
            break
        tail.insert(0, p)
    return ' '.join(tail) if tail else (parts[-1] if parts else str(text))


def r0(text):
    """The rule before part 10 (whole text, OPERATIONS only); frozen here since agi/listarith.operation became R3."""
    t = str(text)
    return None if len(t) > listarith.MAX_TEXT else next((op for rx, op in listarith.OPERATIONS if rx.search(t)), None)


def _r1_patterns(q):
    return next((op for rx, op in listarith.OPERATIONS if rx.search(q)), None)


def r1(text):
    return _r1_patterns(question_part(text))


def r2(text):
    q = question_part(text)
    return _r1_patterns(q) or next((op for rx, op in R2_EXTRA if rx.search(q)), None)


RULES = {'R0': r0, 'R1': r1, 'R2': r2}


def family_d():
    rows = []; rng = random.Random(SEED_D)
    for label, qs in FAMILY_D.items():
        for ti, q in enumerate(qs):
            for _ in range(12):
                head, fmt, names, (lo, hi) = H.EN_CONTEXTS[rng.randrange(len(H.EN_CONTEXTS))]
                items = rng.sample(names, rng.choice((3, 4))); vals = rng.sample(range(lo, hi+1), len(items))
                text = head+', '.join(fmt % (n, v) for n, v in zip(items, vals))+'.'
                if fmt.endswith('euros') and rng.random() < .5:
                    text += ' Summary line at the bottom: "Total: %d euros."' % (sum(vals)+rng.choice((-10, 10)))
                rows.append({'split': 'D', 'label': label, 'template': f'D:{label}:{ti}', 'question': q, 'text': text+' '+q})
    return rows


def score(rows, fn):
    y = [H.CLASSES.index(r['label']) for r in rows]; p = [H.CLASSES.index(fn(r['text']) or 'none') for r in rows]
    return H.metrics(y, p)


def task_check(fn):
    bad = [(s, f) for s in (7, 11, 13, 17, 19, 23) for f, t, _, _ in U2.tasks(s) if fn(t) != r0(t)]
    return {'changed': len(bad), 'examples': bad[:5]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prereg(out):
    a = [r for r in H.corpus() if r['split'] == 'train']
    body = {'schema': 'v13-r4-rule-question-only-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'family_d_sha256': hashlib.sha256(json.dumps(family_d(), sort_keys=True).encode()).hexdigest(), 'n_d': len(family_d()),
            'train_family_a': {k: score(a, fn) for k, fn in RULES.items()}, 'decision_rule': DECISION,
            'script_sha256': sha(__file__), 'listarith_sha256': sha(listarith.__file__), 'head_script_sha256': sha(H.__file__)}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps({k: {m: v[m] for m in ('macro_f1', 'false_alarm_rate', 'op_confusion_rate', 'missed_rate')}
                                                                           for k, v in body['train_family_a'].items()}, indent=1))


def evaluate(reg_path, out):
    reg = json.loads(Path(reg_path).read_text())
    if (reg['script_sha256'], reg['listarith_sha256'], reg['head_script_sha256']) != (sha(__file__), sha(listarith.__file__), sha(H.__file__)):
        raise SystemExit('script or rule changed since preregistration')
    d = family_d(); res = {k: score(d, fn) for k, fn in RULES.items()}; checks = {k: task_check(fn) for k, fn in RULES.items()}
    b = [r for r in H.corpus() if r['split'] == 'test']; res_b = {k: score(b, fn) for k, fn in RULES.items()}

    def ok(k, gain):
        m = res[k]
        return m['false_alarm_rate'] <= .05 and m['op_confusion_rate'] <= .02 and m['macro_f1'] >= res['R0']['macro_f1']+gain and checks[k]['changed'] == 0
    adopted = 'R2' if ok('R2', .15) else 'R1' if ok('R1', 0.) else None
    body = {'prereg_sha256': sha(reg_path), 'family_d': res, 'family_b_exposed_reported_only': res_b, 'r4_task_check': checks,
            'adopted': adopted, 'verdict': f'{adopted}_ADOPTED' if adopted else 'NOT_SUPPORTED', 'model_involved': False}
    atomic_write(Path(out), json.dumps(body, indent=1))
    print(json.dumps({'adopted': adopted} | {k: {m: v[m] for m in ('macro_f1', 'false_alarm_rate', 'op_confusion_rate', 'missed_rate')} for k, v in res.items()}
                     | {'checks': {k: v['changed'] for k, v in checks.items()}}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'prereg':
        prereg(a[1])
    else:
        evaluate(a[1], a[2])
