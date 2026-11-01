#!/usr/bin/env python3
"""WP-Z6k / G-MODULATOR-SPECIFICITY-001: Z6j comparison with a stable measuring instrument.

Z6j showed the single-pass learner's last iterate swings by up to .35 even with clean labels, so one final snapshot cannot
separate arms. Same arms, stream, learner and encoder as scripts/z6j_modulator_sample.py; changed only:
  - metric: mean held-out accuracy over the last four checkpoints (events 450, 500, 550, 600; all after the shift)
  - 20 seeds (231-250) on a fresh pool (seed 53); seed-win thresholds 15/20
  - reported ceiling arm `clean_oracle` (every label true, weight 1) to show what the learner can reach.
Criteria: docs/proofs/continuation-20261027/z6k-modulator-stable/PREREG.md.
  z6k_modulator_stable.py embed <installed_home> <emb.npz> [--pool-seed 53]
  z6k_modulator_stable.py run <emb.npz> <out.json> [--seeds 231-250]
"""
import argparse
import json
import random
import sys
import tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import z6f_modulator_real as F  # noqa: E402
import z6j_modulator_sample as J  # noqa: E402

ARMS = J.ARMS+('clean_oracle',)
WINS = 15


def run_regime(X, kinds, scaffold, seeds, share):
    from v13 import ablation99 as AB
    res = {a: [] for a in ARMS}; last = {a: [] for a in ARMS}
    for seed in seeds:
        rng = random.Random(seed*3); idx = list(range(len(kinds))); rng.shuffle(idx)
        test_idx = np.array(sorted(idx[:len(idx)//4])); train_idx = sorted(idx[len(idx)//4:])
        test_lab = np.array([F.ROUTE_NAMES.index('both' if kinds[i] == 'gist' else kinds[i]) for i in test_idx])
        rows = F.stream(seed, kinds, scaffold, train_idx, share)
        with tempfile.TemporaryDirectory(prefix='v13-z6k-st-') as d:
            store, _ = AB._store(Path(d)); gated = AB.record_gates(rows, store); store.close()
        fac = {a: J.sample_factors(gated, a) for a in ('v13_sample',)+J.CONTROLS}
        fac['gradient_only'] = [1.]*len(gated); fac['gradient_only_matched'] = [float(np.mean(fac['v13_sample']))]*len(gated)
        for a in ('v13', 'v13_datamix'): fac[a] = AB.factors(gated, a, random.Random(seed*7+len(a)))
        for a in ARMS:
            data = [r | {'label': r['true']} for r in gated] if a == 'clean_oracle' else gated
            acc, cur = F.train(X, data, [1.]*len(gated) if a == 'clean_oracle' else fac[a], test_idx, test_lab)
            res[a].append(round(float(np.mean(cur[-4:])), 4)); last[a].append(round(acc, 4))
    return {'tail_acc': res, 'mean_tail_acc': {a: round(float(np.mean(v)), 4) for a, v in res.items()},
            'last_iterate_acc': last, 'mean_last_iterate_acc': {a: round(float(np.mean(v)), 4) for a, v in last.items()}}


def run(emb, out, seeds):
    z = np.load(emb); X = z['X']; kinds = list(z['kind']); scaffold = list(z['scaffold'])
    reg = {name: run_regime(X, kinds, scaffold, seeds, share) for name, share in F.REGIMES.items()}
    sh, ba = reg['self_heavy'], reg['balanced']; m, res = sh['mean_tail_acc'], sh['tail_acc']
    wins = lambda a, b, R: sum(x > y for x, y in zip(R[a], R[b]))
    crit = {
        'M1_typed_beats_each_control_self_heavy': all(m['v13_sample']-m[c] >= .03 and wins('v13_sample', c, res) >= WINS for c in J.CONTROLS),
        'M2_typed_beats_same_budget_gradient_self_heavy': m['v13_sample']-m['gradient_only_matched'] >= .03 and wins('v13_sample', 'gradient_only_matched', res) >= WINS,
        'M3_no_loss_balanced': all(ba['mean_tail_acc']['v13_sample'] >= ba['mean_tail_acc'][c]-.02 for c in J.CONTROLS+('gradient_only_matched',)),
        'M4_learns_at_all': m['v13_sample'] >= .70 and ba['mean_tail_acc']['v13_sample'] >= .70,
        'M5_per_sample_beats_path_gate': all(R['mean_tail_acc']['v13_sample']-R['mean_tail_acc']['v13'] >= .03 and wins('v13_sample', 'v13', R['tail_acc']) >= WINS for R in (sh, ba)),
    }
    spec = all(crit[k] for k in ('M1_typed_beats_each_control_self_heavy', 'M2_typed_beats_same_budget_gradient_self_heavy', 'M3_no_loss_balanced'))
    verdict = 'Z6K_SAMPLE_MODULATOR_PASS' if all(crit.values()) else ('Z6K_SPECIFIC_BUT_WEAK' if spec else 'Z6K_SAMPLE_MODULATOR_FAIL')
    o = {'kind': 'V13_Z6K_MODULATOR_STABLE', 'prereg': 'docs/proofs/continuation-20261027/z6k-modulator-stable/PREREG.md', 'seeds': seeds,
         'regimes': {k: dict(v) for k, v in F.REGIMES.items()}, 'results': reg, 'criteria': crit, 'verdict': verdict,
         'claim_limit': 'real Needle encoder, real scaffold self-labels, real sample_factor/Neuromod code; label sources and mix simulated; one learner kind; cloud'}
    Path(out).write_text(json.dumps(o, indent=1)); print(verdict, json.dumps({k: v['mean_tail_acc'] for k, v in reg.items()}), json.dumps(crit))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--pool-seed', type=int, default=53); ap.add_argument('--seeds', default='231-250')
    x = ap.parse_args()
    if x.cmd == 'embed': F.embed(x.a, x.b, x.pool_seed)
    else:
        lo, hi = map(int, x.seeds.split('-')); run(x.a, x.b, list(range(lo, hi+1)))


if __name__ == '__main__':
    main()
