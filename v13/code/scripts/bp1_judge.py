#!/usr/bin/env python3
"""WP-BP1: apply the preregistered decision rule (PREREG.md) to eval_*.json. Usage: bp1_judge.py RUN_DIR"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import offer_consumer as oc

GAP = ('calc_use', 'calc_hedge', 'abstain')
DEP = ('calc_use', 'calc_hedge')


def load(p):
    return json.loads(Path(p).read_text())


def oks(res, key):
    items = oc.build(res['seed'], 1, res['n'] // len(oc.FAMILIES))
    return items, [oc.score(i, a)['ok'] for i, a in zip(items, res['answers'][key])]


def boot_diff(a, b, idx, n=2000, seed=7):
    rng = random.Random(seed)
    d = [int(a[i]) - int(b[i]) for i in idx]
    m = []
    for _ in range(n):
        s = [d[rng.randrange(len(d))] for _ in d]
        m.append(sum(s) / len(s))
    m.sort()
    return round(sum(d) / len(d), 4), round(m[int(.025 * n)], 4)


def fam_rate(items, ok, fams):
    ix = [k for k, i in enumerate(items) if i['family'] in fams]
    return sum(ok[k] for k in ix) / len(ix)


def judge(run):
    base = load(run / 'eval_A1.json')
    out = {}
    for tag in ('A1', 'A2'):
        p = run / ('eval_%s.json' % tag)
        if not p.exists():
            continue
        r = load(p)
        items, on = oks(r, 'adapter:offers')
        _, bs = oks(base, 'base_adapter_off:offers')
        _, rem = oks(r, 'adapter:removed')
        gap = [k for k, i in enumerate(items) if i['family'] in GAP]
        shuf = r['answers']['adapter:shuffled']
        sh_items = items
        # follow rate: calc_use under shuffled offers contains the value of the *shuffled* offer (not the item's own result)
        import random as _r
        rng = _r.Random(r['seed'] + 99)
        pool = items
        shuf_off = [rng.choice([x for x in pool if x['offers'] and x is not it] or pool)['offers'] for it in items]
        fol = []
        for it, o, a in zip(items, shuf_off, shuf):
            if it['family'] == 'calc_use' and o:
                nums = re.findall(r'(\d+)\s+usable|=\s*(\d+)', o[0]['summary'])
                v = [x for t in nums for x in t if x]
                if v:
                    fol.append(bool(oc._num(v[-1]).search(a)))
        c = {'train_seed': tag, 'on': round(sum(on) / len(on), 4), 'base': round(sum(bs) / len(bs), 4),
             'wrong_commit': r['arms']['adapter:offers']['wrong_commit'],
             'gap_gain': boot_diff(on, bs, gap), 'overall_gain': boot_diff(on, bs, range(len(items))),
             'dep_on': round(fam_rate(items, on, DEP), 4), 'dep_removed': round(fam_rate(items, rem, DEP), 4),
             'follow_rate_shuffled_calc_use': round(sum(fol) / max(1, len(fol)), 4), 'drift_mean_kl': r.get('drift', {}).get('mean_kl')}
        c['c1'] = c['on'] >= .80 and c['on'] >= c['base'] + .15 and c['gap_gain'][0] >= .50 and c['gap_gain'][1] > 0
        c['c2'] = c['wrong_commit'] <= .05
        c['c3'] = c['dep_on'] - c['dep_removed'] >= .40 and c['follow_rate_shuffled_calc_use'] >= .60
        c['c5'] = c['drift_mean_kl'] is not None and c['drift_mean_kl'] <= .05
        out[tag] = c
    ctl = run / 'eval_C1.json'
    if ctl.exists():
        r = load(ctl)
        items, on = oks(r, 'adapter:offers')
        out['control_C1'] = {'dep_on': round(fam_rate(items, on, DEP), 4), 'overall': round(sum(on) / len(on), 4), 'c4': fam_rate(items, on, DEP) <= .20}
    return out


if __name__ == '__main__':
    run = Path(sys.argv[1])
    res = judge(run)
    full = all(k in res for k in ('A1', 'A2', 'control_C1'))
    ok = full and all(res[t][c] for t in ('A1', 'A2') for c in ('c1', 'c2', 'c3', 'c5')) and res['control_C1']['c4']
    part = full and all(res[t][c] for t in ('A1', 'A2') for c in ('c1', 'c2'))
    res['verdict'] = ('CONSUMER_SUPPORTED' if ok else 'CONSUMER_PARTIAL' if part else 'NO_CONSUMER_GAIN') if full else 'INCOMPLETE'
    print(json.dumps(res, indent=1))
    (run / 'judge.json').write_text(json.dumps(res, indent=1))
