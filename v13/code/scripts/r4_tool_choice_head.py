"""R4 part 8: learned tool choice for list_arith on the frozen C2 Needle embedding (§57) vs the BOOT wording rule.

Parts 6/7: list_arith helps a lot (fresh 54-55/60 vs 40-42), but the BOOT rule (agi/listarith.operation) only knows two
English phrasings. Question here: does a small head on the frozen C2 Needle embedding (the encoder fastpolicy's heads use)
recognise none / total / difference_max_min over reworded questions better than the rule, without false alarms and
without confusing sum and difference (a wrong operation would put a wrong "exact" value into the answer)?
Corpus: generated list contexts (expenses, rainfall, points, stock; some expense contexts carry a stated "Total:" line)
with question templates in three disjoint families written before any embedding was computed:
  train  family A (English), used for fitting and model selection (grouped by template)
  test   family B (English, held-out wording), decides the verdict once
  de     family C (German contexts + questions), reported only (English first, user decision 2026-10-09)
  embed     r4_tool_choice_head.py embed <installed_home> <vectors.npz>
  prereg    r4_tool_choice_head.py prereg <vectors.npz> <prereg.json>
  evaluate  r4_tool_choice_head.py evaluate <prereg.json> <vectors.npz> <report.json>
Claim limit: generated texts, one encoder, cloud CPU; the head is not wired into the runtime here."""
import hashlib
import json
import random
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write  # noqa: E402
from v13.agi import listarith  # noqa: E402

CLASSES = ('none', 'total', 'difference_max_min')
TEMPLATES = {
    'train': {
        'total': ('What is the total?', 'Add them all up.', 'What do they come to altogether?', 'Give the sum of all values.',
                  'How much is that in total?', 'What is the combined amount?'),
        'difference_max_min': ('How many more does the largest have than the smallest?', 'What is the difference between the highest and the lowest value?',
                               'By how much does the biggest exceed the smallest?', 'What is the gap between the top and bottom value?',
                               'How far apart are the maximum and the minimum?', 'How much less is the smallest than the largest?'),
        'none': ('Which one is the largest?', 'List the items in alphabetical order.', 'Which item is the smallest?', 'Is any value above 50?',
                 'Name the second item.', 'Which is the most expensive?', 'How many items are there?', 'What is the first value?')},
    'test': {
        'total': ('Can you tell me the overall amount?', 'Sum these up for me.', "What's the grand total of everything listed?",
                  'If you combine all of them, what do you get?', 'Tally up the numbers.', 'What do all the values add up to?'),
        'difference_max_min': ("What's the spread between the highest and lowest?", 'How big is the difference between the top value and the bottom value?',
                               'Subtract the lowest from the highest, what is left?', 'How much higher is the maximum than the minimum?',
                               'What separates the largest value from the smallest one?', 'Compared with the lowest, how much more does the highest have?'),
        'none': ('Which entry has the lowest value?', 'Sort the entries from high to low.', 'Which one stands out as the biggest?',
                 'Are all values even numbers?', 'What is the name of the last entry?', 'How many entries are listed?',
                 'Which entry would you pick as the cheapest?')},
    'de': {
        'total': ('Wie viel ist das insgesamt?', 'Rechne alles zusammen.', 'Was ist die Summe aller Werte?', 'Wie hoch ist der Gesamtbetrag?'),
        'difference_max_min': ('Wie viel mehr hat der größte Wert als der kleinste?', 'Was ist der Unterschied zwischen dem höchsten und dem niedrigsten Wert?',
                               'Um wie viel übertrifft der größte den kleinsten?', 'Wie groß ist der Abstand zwischen Maximum und Minimum?'),
        'none': ('Welcher Eintrag ist der größte?', 'Liste die Einträge alphabetisch auf.', 'Wie viele Einträge gibt es?', 'Welcher Wert ist der kleinste?')}}
PER_TEMPLATE = {'train': 12, 'test': 12, 'de': 10}
SEEDS = {'train': 801, 'test': 802, 'de': 803}
EN_CONTEXTS = (('Expense report. Items: ', '%s %d euros', ('printer paper', 'train tickets', 'coffee beans', 'cables', 'postage', 'snacks'), (12, 95)),
               ('Monthly rainfall in millimetres: ', '%s %d', ('Lyon', 'Brno', 'Graz', 'Porto', 'Malmo', 'Bremen'), (100, 900)),
               ('Points scored this season: ', '%s %d', ('Mira', 'Jonas', 'Aylin', 'Tomas', 'Greta', 'Omar'), (3, 60)),
               ('Boxes in storage: ', '%s %d', ('shelf A', 'shelf B', 'shelf C', 'shelf D', 'the loft', 'the cellar'), (5, 120)))
DE_CONTEXTS = (('Ausgaben: ', '%s %d Euro', ('Druckerpapier', 'Bahntickets', 'Kaffeebohnen', 'Kabel', 'Porto', 'Snacks'), (12, 95)),
               ('Niederschlag im Monat in Millimetern: ', '%s %d', ('Lyon', 'Brno', 'Graz', 'Porto', 'Malmö', 'Bremen'), (100, 900)),
               ('Punkte in dieser Saison: ', '%s %d', ('Mira', 'Jonas', 'Aylin', 'Tomas', 'Greta', 'Omar'), (3, 60)))
GRID = tuple((view, l2) for view in ('full', 'question') for l2 in (1e-3, 1e-1))
DECISION = ("Test family B (English, held-out wording), once: LEARNED_CHOICE_SUPPORTED iff head macro-F1 >= rule macro-F1 + 0.15 AND "
            "head false-alarm rate on 'none' <= 0.05 AND total<->difference confusions <= 2% of arithmetic items. Head = multinomial "
            "logistic regression on standardised Needle vectors; view and L2 chosen on train only by leave-one-template-out CV "
            "(score = macro-F1 minus 2 x false-alarm rate). German family C and the hybrid 'rule, else head' are reported only.")


def corpus():
    rows = []
    for split, by_class in TEMPLATES.items():
        rng = random.Random(SEEDS[split]); contexts = DE_CONTEXTS if split == 'de' else EN_CONTEXTS
        for label, qs in by_class.items():
            for ti, q in enumerate(qs):
                for k in range(PER_TEMPLATE[split]):
                    head, fmt, names, (lo, hi) = contexts[rng.randrange(len(contexts))]
                    items = rng.sample(names, rng.choice((3, 4))); vals = rng.sample(range(lo, hi+1), len(items))
                    text = head+', '.join(fmt % (n, v) for n, v in zip(items, vals))+'.'
                    if fmt.endswith('euros') and rng.random() < .5:  # a stated summary line, as in utility_bench2 (rule weakness, part 6)
                        text += ' Summary line at the bottom: "Total: %d euros."' % (sum(vals)+rng.choice((-10, 10)))
                    elif fmt.endswith('Euro') and rng.random() < .5:
                        text += ' Letzte Zeile: "Summe: %d Euro."' % (sum(vals)+rng.choice((-10, 10)))
                    rows.append({'split': split, 'label': label, 'template': f'{split}:{label}:{ti}', 'question': q, 'text': text+' '+q})
    return rows


def question_view(text):
    """Deterministic question-only view: the last sentence (the question asked about the data)."""
    parts = [p for p in re.split(r'(?<=[.!?"])\s+', str(text).strip()) if p]
    return parts[-1] if parts else str(text)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def corpus_sha():
    return hashlib.sha256(json.dumps(corpus(), sort_keys=True).encode()).hexdigest()


def embed(installed, out):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    installed = Path(installed).resolve(); rows = corpus(); full = []; quest = []
    with tempfile.TemporaryDirectory(prefix='v13-r4head-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False})
        r = Runtime(home)
        try:
            revision = r.models.revision('C2_CONTROL')
            for i, row in enumerate(rows):
                full.append(r.needle.embed(row['text'], r.cancel_event, time.monotonic()+60))
                quest.append(r.needle.embed(question_view(row['text']), r.cancel_event, time.monotonic()+60))
                if i % 50 == 0:
                    print(i, len(rows), flush=True)
        finally:
            r.close()
    np.savez_compressed(out, full=np.asarray(full, np.float32), question=np.asarray(quest, np.float32),
                        meta=np.asarray(json.dumps({'corpus_sha256': corpus_sha(), 'encoder_revision': revision, 'script_sha256': sha(__file__)})))


def load(path):
    z = np.load(path); meta = json.loads(str(z['meta']))
    if meta['corpus_sha256'] != corpus_sha():
        raise SystemExit('vectors are from another corpus')
    return {'full': z['full'], 'question': z['question']}, meta


def fit(X, y, l2, epochs=400, lr=.5):
    mu = X.mean(0); sd = X.std(0)+1e-6; Z = (X-mu)/sd; W = np.zeros((Z.shape[1], len(CLASSES))); b = np.zeros(len(CLASSES))
    Y = np.eye(len(CLASSES))[y]
    for _ in range(epochs):
        P = Z@W+b; P = np.exp(P-P.max(1, keepdims=True)); P /= P.sum(1, keepdims=True)
        W -= lr*(Z.T@(P-Y)/len(Z)+l2*W); b -= lr*(P-Y).mean(0)
    return lambda Xn: np.argmax(((Xn-mu)/sd)@W+b, 1)


def metrics(y, p):
    y = np.asarray(y); p = np.asarray(p); f1 = []
    for c in range(len(CLASSES)):
        tp = int(((p == c) & (y == c)).sum()); fp = int(((p == c) & (y != c)).sum()); fn = int(((p != c) & (y == c)).sum())
        f1.append(0. if tp == 0 else 2*tp/(2*tp+fp+fn))
    none = y == 0; arith = y > 0
    return {'macro_f1': round(float(np.mean(f1)), 4), 'f1': dict(zip(CLASSES, [round(x, 4) for x in f1])),
            'false_alarm_rate': round(float((p[none] > 0).mean()), 4) if none.any() else None,
            'op_confusion_rate': round(float(((p > 0) & (p != y))[arith].mean()), 4) if arith.any() else None,
            'missed_rate': round(float((p[arith] == 0).mean()), 4) if arith.any() else None,
            'confusion': [[int(((y == a) & (p == b)).sum()) for b in range(len(CLASSES))] for a in range(len(CLASSES))]}


def rule(rows):
    return [CLASSES.index(listarith.operation(r['text']) or 'none') for r in rows]


def select(vecs, rows):
    idx = [i for i, r in enumerate(rows) if r['split'] == 'train']; y = np.array([CLASSES.index(rows[i]['label']) for i in idx])
    groups = np.array([rows[i]['template'] for i in idx]); scores = {}
    for view, l2 in GRID:
        X = vecs[view][idx]; pred = np.zeros(len(idx), int)
        for g in sorted(set(groups)):
            m = groups == g; pred[m] = fit(X[~m], y[~m], l2)(X[m])
        mt = metrics(y, pred); scores[f'{view}:{l2}'] = mt | {'score': round(mt['macro_f1']-2*mt['false_alarm_rate'], 4)}
    best = max(scores, key=lambda k: scores[k]['score']); view, l2 = best.split(':')
    return view, float(l2), scores


def prereg(vec_path, out):
    vecs, meta = load(vec_path); rows = corpus(); view, l2, scores = select(vecs, rows)
    train = [r for r in rows if r['split'] == 'train']
    body = {'schema': 'v13-r4-tool-choice-head-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'vectors_sha256': sha(vec_path), 'vectors_meta': meta, 'corpus_sha256': corpus_sha(),
            'n': {s: sum(r['split'] == s for r in rows) for s in TEMPLATES}, 'train_cv': scores, 'chosen': {'view': view, 'l2': l2},
            'train_rule': metrics([CLASSES.index(r['label']) for r in train], rule(train)), 'decision_rule': DECISION,
            'script_sha256': sha(__file__), 'listarith_sha256': sha(listarith.__file__)}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, vec_path, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['vectors_sha256'] != sha(vec_path) or reg['listarith_sha256'] != sha(listarith.__file__):
        raise SystemExit('script, vectors or rule changed since preregistration')
    vecs, _ = load(vec_path); rows = corpus(); view = reg['chosen']['view']; l2 = reg['chosen']['l2']
    tr = [i for i, r in enumerate(rows) if r['split'] == 'train']
    head = fit(vecs[view][tr], np.array([CLASSES.index(rows[i]['label']) for i in tr]), l2); res = {}
    for split in ('test', 'de'):
        idx = [i for i, r in enumerate(rows) if r['split'] == split]; y = [CLASSES.index(rows[i]['label']) for i in idx]
        h = head(vecs[view][idx]); ru = rule([rows[i] for i in idx]); hy = [a if a else b for a, b in zip(ru, h)]
        res[split] = {'head': metrics(y, h), 'rule': metrics(y, ru), 'hybrid_rule_else_head': metrics(y, hy),
                      'head_errors': [{'template': rows[i]['template'], 'question': rows[i]['question'], 'pred': CLASSES[int(p)]}
                                      for i, p, t in zip(idx, h, y) if p != t][:40]}
    t = res['test']; ok = (t['head']['macro_f1'] >= t['rule']['macro_f1']+.15 and t['head']['false_alarm_rate'] <= .05
                           and t['head']['op_confusion_rate'] <= .02)
    body = {'prereg_sha256': sha(reg_path), 'chosen': reg['chosen'], 'results': res,
            'verdict': 'LEARNED_CHOICE_SUPPORTED' if ok else 'NOT_SUPPORTED', 'runtime_changed': False, 'phone_measured': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps({k: body[k] for k in ('chosen', 'verdict')}
                                                                          | {s: {m: res[s][m]['macro_f1'] for m in ('head', 'rule', 'hybrid_rule_else_head')} for s in res}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'embed':
        embed(a[1], a[2])
    elif a[0] == 'prereg':
        prereg(a[1], a[2])
    else:
        evaluate(a[1], a[2], a[3])
