"""R4 part 10: question-only rule R3 = R2 of part 9 + counting exclusion, tested on a new family E (no model).

Part 9 (r4_rule_question_only.py): R2 reached macro-F1 .79 on family D, but every false alarm came from "What is the total
number of entries?" (counting, not a sum). R3 adds one narrow, frozen exclusion: a question asking for the total/overall
number or count of something is not list arithmetic. Family E was written before any rule ran on it and includes counting
questions phrased differently from family D.
  prereg    r4_rule_r3.py prereg <prereg.json>
  evaluate  r4_rule_r3.py evaluate <prereg.json> <report.json>"""
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
import r4_rule_question_only as Q  # noqa: E402

COUNT = re.compile(r'(?i)\b(?:total|overall)\s+(?:number|count)\s+of\b')
FAMILY_E = {
    'total': ('What is the overall sum?', 'How many points did they score in total?', 'Add these numbers together.',
              'Combine all the values into one figure.', 'What does the list add up to?', 'Give me the total of the list.'),
    'difference_max_min': ('What is the difference between the largest and smallest numbers?', 'How much more is the highest value than the lowest one?',
                           'By how much is the maximum above the minimum?', 'How many units separate the top and bottom entries?',
                           "What's the gap from the smallest to the largest?", 'How much does the leader exceed the last one by?'),
    'none': ('What is the overall count of entries?', 'How many entries does the list contain?', 'Which entry is the second largest?',
             'Which entries are under 50?', 'Rank the entries.', 'What is the average?', 'Who is first in the list?')}
SEED_E = 805
DECISION = ("Family E (new): R3 adopted into agi/listarith.operation iff on E false-alarm rate <= 0.05 AND sum<->difference confusion "
            "<= 0.02 AND macro-F1 >= R0 + 0.15 AND all 360 utility_bench2 tasks of seeds 7, 11, 13, 17, 19, 23 keep R0's operation. "
            "Family D (exposed) reported only.")


def r3(text):
    return None if COUNT.search(Q.question_part(text)) else Q.r2(text)


RULES = {'R0': Q.r0, 'R2': Q.r2, 'R3': r3}


def family_e():
    rows = []; rng = random.Random(SEED_E)
    for label, qs in FAMILY_E.items():
        for ti, q in enumerate(qs):
            for _ in range(12):
                head, fmt, names, (lo, hi) = H.EN_CONTEXTS[rng.randrange(len(H.EN_CONTEXTS))]
                items = rng.sample(names, rng.choice((3, 4))); vals = rng.sample(range(lo, hi+1), len(items))
                text = head+', '.join(fmt % (n, v) for n, v in zip(items, vals))+'.'
                if fmt.endswith('euros') and rng.random() < .5:
                    text += ' Summary line at the bottom: "Total: %d euros."' % (sum(vals)+rng.choice((-10, 10)))
                rows.append({'split': 'E', 'label': label, 'template': f'E:{label}:{ti}', 'question': q, 'text': text+' '+q})
    return rows


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def shas():
    return {'script': sha(__file__), 'part9': sha(Q.__file__), 'part8': sha(H.__file__), 'listarith': sha(listarith.__file__)}


def prereg(out):
    d = Q.family_d()
    body = {'schema': 'v13-r4-rule-r3-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'family_e_sha256': hashlib.sha256(json.dumps(family_e(), sort_keys=True).encode()).hexdigest(), 'n_e': len(family_e()),
            'family_d_exposed': {k: Q.score(d, fn) for k, fn in RULES.items()}, 'decision_rule': DECISION, 'sha256': shas()}
    atomic_write(Path(out), json.dumps(body, indent=1))
    print(json.dumps({k: {m: v[m] for m in ('macro_f1', 'false_alarm_rate', 'op_confusion_rate')} for k, v in body['family_d_exposed'].items()}, indent=1))


def evaluate(reg_path, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['sha256'] != shas():
        raise SystemExit('scripts or rule changed since preregistration')
    e = family_e(); res = {k: Q.score(e, fn) for k, fn in RULES.items()}; checks = {k: Q.task_check(fn) for k, fn in RULES.items()}
    m = res['R3']; ok = (m['false_alarm_rate'] <= .05 and m['op_confusion_rate'] <= .02 and m['macro_f1'] >= res['R0']['macro_f1']+.15
                         and checks['R3']['changed'] == 0)
    errors = [{'question': r['question'], 'label': r['label'], 'r3': r3(r['text'])} for r in e if (r3(r['text']) or 'none') != r['label']]
    body = {'prereg_sha256': sha(reg_path), 'family_e': res, 'r4_task_check': checks, 'r3_errors_by_question': sorted({(x['question'], x['label'], str(x['r3'])) for x in errors}),
            'verdict': 'R3_ADOPTED' if ok else 'NOT_SUPPORTED', 'model_involved': False}
    atomic_write(Path(out), json.dumps(body, indent=1))
    print(json.dumps({'verdict': body['verdict']} | {k: {x: v[x] for x in ('macro_f1', 'false_alarm_rate', 'op_confusion_rate', 'missed_rate')} for k, v in res.items()}
                     | {'checks': {k: v['changed'] for k, v in checks.items()}, 'r3_errors': body['r3_errors_by_question']}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'prereg':
        prereg(a[1])
    else:
        evaluate(a[1], a[2])
