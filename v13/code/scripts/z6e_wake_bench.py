#!/usr/bin/env python3
"""WP-Z6e / §24.22 C-native vs. selective body wake: C_native only, A only (B1 detail), B only (B2 gist), A+B, adaptive.

Real C3/B1/B2 through the runtime, same bench mode and per-turn handling as Z6a (scripts/z6a_effort_bench.run_arm: fresh
home per arm, temperature 0, post-commit observers cut). Arms are effort modes: disabled (C_native only), detail
(A only, new user mode), gist (B only, new user mode), max (A+B), adaptive. Five task classes x 12 (seeded): the four
WP-T3b kinds (summary = factual/exact, long = long-context/global, compare = mixed reasoning, notes = conflict) plus
'easy' (small talk and rewrites). Criteria E1-E5: docs/proofs/continuation-20261026/z6e-selective-wake/PREREG.md.
Usage: z6e_wake_bench.py <installed_home> <out.json> [arm,arm,...] [--seed 37] [--limit N]
"""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
import utility_bench2 as U2  # noqa: E402
from z6a_effort_bench import run_arm  # noqa: E402

ARMS = ('disabled', 'detail', 'gist', 'max', 'adaptive')
FIXED = ('disabled', 'detail', 'gist', 'max')
CLASS = {'easy': 'smalltalk/rewrite', 'summary': 'factual/exact', 'long': 'long-context/global', 'compare': 'mixed reasoning', 'notes': 'novelty/conflict'}
ROLE = {'detail': {'B1_DETAIL'}, 'gist': {'B2_GIST'}, 'max': {'B1_DETAIL', 'B2_GIST'}}
SENT = (('Send me the report by tomorrow.', 'report'), ('Your code is broken again.', 'code'), ('Fix the printer now.', 'printer'),
        ('The meeting was a waste of time.', 'meeting'), ('Call the supplier, the invoice is wrong.', 'invoice'),
        ('Stop changing the schedule every week.', 'schedule'), ('Where is the budget sheet?', 'budget'),
        ('The garden needs water today.', 'garden'))
GREET = (('Hi! How are you today?', r'(?i)\b(good|fine|great|well|doing|thanks|thank you|hello|hi)\b'),
         ('Good morning! Just say hello back, please.', r'(?i)\b(hello|hi|good morning|morning)\b'),
         ('Thanks for your help yesterday!', r"(?i)\b(welcome|glad|happy|pleasure|anytime|no problem)\b"),
         ('Say something friendly to start my day.', r'(?i)\b(good|great|wonderful|nice|happy|day|morning|hope)\b'))


def easy(seed, n):
    rng = random.Random(seed*101); out = []
    for i in range(n):
        if i % 2 == 0:
            s, key = rng.choice(SENT)
            out.append(('easy%02d' % i, 'Rewrite this sentence so it sounds polite and friendly: "%s"' % s, [], {'keeps': r'(?i)\b'+key, 'polite': r'(?i)\b(please|could|would|thank|kindly)\b'}))
        else:
            g, pat = rng.choice(GREET)
            out.append(('easy%02d' % i, g, [], {'reply': pat}))
    return out


def fixtures(seed, per_kind=12):
    return easy(seed, per_kind)+U2.tasks(seed=seed, per_kind=per_kind)


def analyse(rows):
    by = {}
    for r in rows: by.setdefault(r['arm'], {})[r['fixture']] = r
    kind = lambda f: f.rstrip('0123456789')
    woke = lambda r: r['wake'] not in (None, 'none')
    out = {'arms': {}}
    for arm, m in by.items():
        n = len(m)
        out['arms'][arm] = {'n': n, 'passed': sum(r['pass'] for r in m.values()), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
                            'planned_wake_rate': round(sum(woke(r) for r in m.values())/n, 3), 'offer_rate': round(sum(bool(r['offers']) for r in m.values())/n, 3),
                            'by_class': {CLASS[k]: sum(r['pass'] for f, r in m.items() if kind(f) == k) for k in CLASS if any(kind(f) == k for f in m)},
                            'wake_rate_by_class': {CLASS[k]: round(sum(woke(r) for f, r in m.items() if kind(f) == k)/max(1, sum(kind(f) == k for f in m)), 3) for k in CLASS if any(kind(f) == k for f in m)},
                            'turn_s_by_class': {CLASS[k]: round(sum(r['turn_s'] for f, r in m.items() if kind(f) == k)/max(1, sum(kind(f) == k for f in m)), 2) for k in CLASS if any(kind(f) == k for f in m)},
                            'wakes': {w: sum(r['wake'] == w for r in m.values()) for w in ('none', 'detail', 'gist', 'both', None)}}
    if not all(a in by for a in ARMS): return out
    ad, dis = by['adaptive'], by['disabled']; fx = sorted(ad)
    easy_f = [f for f in fx if kind(f) == 'easy']
    e1_wake = sum(woke(ad[f]) for f in easy_f)/len(easy_f); e1_loss = sum(dis[f]['pass'] for f in easy_f)-sum(ad[f]['pass'] for f in easy_f)
    solved = [f for f in fx if dis[f]['pass']]; unnecessary = [f for f in solved if woke(ad[f])]
    rescuable = [f for f in fx if not dis[f]['pass'] and any(by[a][f]['pass'] for a in ('detail', 'gist', 'max'))]
    def recruited(f):
        w = ad[f]['wake'] or 'none'; got = {'detail': {'B1_DETAIL'}, 'gist': {'B2_GIST'}, 'both': {'B1_DETAIL', 'B2_GIST'}}.get(w, set())
        return bool(got) and any(by[a][f]['pass'] and ROLE[a] <= got for a in ('detail', 'gist', 'max'))
    rec = [f for f in rescuable if recruited(f)]
    best = max(out['arms'][a]['passed'] for a in FIXED)
    crit = {
        'E1_easy_stays_cheap': {'wake_rate': round(e1_wake, 3), 'loss_vs_c_native': e1_loss, 'pass': e1_wake <= .20 and e1_loss <= 1},
        'E2_few_unnecessary_wakes': {'value': '%d/%d' % (len(unnecessary), len(solved)), 'pass': len(unnecessary) <= .30*len(solved)},
        'E3_escalation_recall': {'rescuable': len(rescuable), 'recruited_passing_body': len(rec), 'fixtures': rescuable,
                                 'pass': len(rescuable) >= 5 and len(rec) >= .70*len(rescuable), 'status': 'NO_RESCUE_HEADROOM' if len(rescuable) < 5 else 'MEASURED'},
        'E4_quality_near_best_fixed': {'adaptive': out['arms']['adaptive']['passed'], 'best_fixed': best, 'pass': out['arms']['adaptive']['passed'] >= best-3},
        'E5_cheaper_than_a_plus_b': {'adaptive_s': out['arms']['adaptive']['mean_turn_s'], 'max_s': out['arms']['max']['mean_turn_s'],
                                     'pass': out['arms']['adaptive']['mean_turn_s'] <= .6*out['arms']['max']['mean_turn_s']},
    }
    out['criteria'] = crit; out['verdict'] = 'Z6E_SELECTIVE_WAKE_PASS' if all(c['pass'] for c in crit.values()) else 'Z6E_SELECTIVE_WAKE_FAIL'
    out['descriptive'] = {'false_cheap_route': '%d/%d' % (sum(not woke(ad[f]) for f in rescuable), len(rescuable)),
                          'body_only_passes': {a: [f for f in fx if by[a][f]['pass'] and not dis[f]['pass']] for a in ('detail', 'gist', 'max')},
                          'body_breaks': {a: [f for f in fx if dis[f]['pass'] and not by[a][f]['pass']] for a in ('detail', 'gist', 'max')}}
    return out


def main(installed, out, arms=None, seed=37, limit=None):
    installed = Path(installed).resolve(); out = Path(out); arms = arms.split(',') if arms else ARMS; fx = fixtures(seed)
    if limit: fx = [f for i, f in enumerate(fx) if i % (len(fx)//limit) == 0][:limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows += run_arm(installed, arm, fx)
        atomic_write(out, json.dumps({'kind': 'V13_Z6E_SELECTIVE_WAKE', 'seed': seed, 'bench_cfg': U2.BENCH_CFG, 'fixtures': [f[0] for f in fx],
                                      **analyse(rows), 'rows': rows, 'phone_measured': False, 'canonical_gate_pass': False,
                                      'prereg': 'docs/proofs/continuation-20261026/z6e-selective-wake/PREREG.md',
                                      'claim_limit': 'deterministic bench decoding, generated English tasks, regex checks, one seed, cloud CPU, no energy'}, indent=1))
    print(json.dumps({k: v for k, v in analyse(rows).items() if k != 'arms'}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]; lim = None; seed = 37
    for flag in ('--limit', '--seed'):
        if flag in a:
            i = a.index(flag); v = int(a[i+1]); del a[i:i+2]
            if flag == '--limit': lim = v
            else: seed = v
    main(a[0], a[1], a[2] if len(a) > 2 else None, seed, lim)
