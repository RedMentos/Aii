#!/usr/bin/env python3
"""WP-Z6j / G-MODULATOR-SPECIFICITY-001: typed modulator credited per sample (follow-up of Z6f).

Z6f showed the real Neuromod gate scales one budget per path, so in a path that mixes clean and wrong label sources typing
changes nothing. Here every arm weights each training sample by its own signal (same learner, stream, encoder and label
sources as scripts/z6f_modulator_real.py):
  v13_sample      v13.neuromod.sample_factor (§35.3 kind weights, §63 source credibility, safety veto)
  scalar_sample   one scalar per sample: clamp(sum of channels)          (safety veto kept, as in Z6f)
  human_sample    clamp(human_correction)                                (safety veto kept)
  outcome_sample  clamp(max outcome channel)                             (safety veto kept)
  gradient_only / gradient_only_matched (mean budget of v13_sample)
Reported, not judged: v13 (path gate, Z6f), v13_datamix (path gate + data-mix guard).
Criteria: docs/proofs/continuation-20261027/z6j-modulator-sample/PREREG.md.

  z6j_modulator_sample.py embed <installed_home> <emb.npz> [--pool-seed 47]
  z6j_modulator_sample.py run <emb.npz> <out.json> [--seeds 211,212,213,214,215]
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

ARMS = ('v13_sample', 'scalar_sample', 'human_sample', 'outcome_sample', 'gradient_only', 'gradient_only_matched', 'v13', 'v13_datamix')
CONTROLS = ('scalar_sample', 'human_sample', 'outcome_sample')


def sample_factors(rows, arm):
    from v13 import ablation99 as AB
    from v13.neuromod import sample_factor, clamp
    out = []
    for r in rows:
        s = dict(r['signal']); src = s.pop('source_class'); veto = s.pop('safety_veto', False)
        if arm == 'v13_sample': out.append(sample_factor(r['path'], src, safety_veto=veto, **s)); continue
        if veto: out.append(0.); continue
        if arm == 'scalar_sample': out.append(clamp(sum(s.values())))
        elif arm == 'human_sample': out.append(clamp(s.get('human_correction', 0.)))
        else: out.append(clamp(max([s.get(c, 0.) for c in AB.OUTCOME_CH]+[0.])))
    return out


def run_regime(X, kinds, scaffold, seeds, share):
    from v13 import ablation99 as AB
    res = {a: [] for a in ARMS}; budgets = {a: [] for a in ARMS}; curves = {a: [] for a in ARMS}
    for seed in seeds:
        rng = random.Random(seed*3); idx = list(range(len(kinds))); rng.shuffle(idx)
        test_idx = np.array(sorted(idx[:len(idx)//4])); train_idx = sorted(idx[len(idx)//4:])
        test_lab = np.array([F.ROUTE_NAMES.index('both' if kinds[i] == 'gist' else kinds[i]) for i in test_idx])
        rows = F.stream(seed, kinds, scaffold, train_idx, share)
        with tempfile.TemporaryDirectory(prefix='v13-z6j-st-') as d:
            store, _ = AB._store(Path(d)); gated = AB.record_gates(rows, store); store.close()
        fac = {a: sample_factors(gated, a) for a in ('v13_sample',)+CONTROLS}
        fac['gradient_only'] = [1.]*len(gated); fac['gradient_only_matched'] = [float(np.mean(fac['v13_sample']))]*len(gated)
        for a in ('v13', 'v13_datamix'): fac[a] = AB.factors(gated, a, random.Random(seed*7+len(a)))
        for a in ARMS:
            acc, cur = F.train(X, gated, fac[a], test_idx, test_lab); res[a].append(round(acc, 4)); curves[a].append(cur); budgets[a].append(round(float(np.mean(fac[a])), 4))
    return {'final_acc': res, 'mean_final_acc': {a: round(float(np.mean(v)), 4) for a, v in res.items()}, 'budget_mean': budgets,
            'curve_mean': {a: [round(float(np.mean([c[j] for c in v])), 4) for j in range(len(v[0]))] for a, v in curves.items()}}


def run(emb, out, seeds):
    z = np.load(emb); X = z['X']; kinds = list(z['kind']); scaffold = list(z['scaffold'])
    reg = {name: run_regime(X, kinds, scaffold, seeds, share) for name, share in F.REGIMES.items()}
    sh, ba = reg['self_heavy'], reg['balanced']; m, res = sh['mean_final_acc'], sh['final_acc']
    wins = lambda a, b, R: sum(x > y for x, y in zip(R[a], R[b]))
    crit = {
        'M1_typed_beats_each_control_self_heavy': all(m['v13_sample']-m[c] >= .03 and wins('v13_sample', c, res) >= 4 for c in CONTROLS),
        'M2_typed_beats_same_budget_gradient_self_heavy': m['v13_sample']-m['gradient_only_matched'] >= .03 and wins('v13_sample', 'gradient_only_matched', res) >= 4,
        'M3_no_loss_balanced': all(ba['mean_final_acc']['v13_sample'] >= ba['mean_final_acc'][c]-.02 for c in CONTROLS+('gradient_only_matched',)),
        'M4_learns_at_all': m['v13_sample'] >= .70 and ba['mean_final_acc']['v13_sample'] >= .70,
        'M5_per_sample_beats_path_gate': all(R['mean_final_acc']['v13_sample']-R['mean_final_acc']['v13'] >= .03 and wins('v13_sample', 'v13', R['final_acc']) >= 4 for R in (sh, ba)),
    }
    spec = all(crit[k] for k in ('M1_typed_beats_each_control_self_heavy', 'M2_typed_beats_same_budget_gradient_self_heavy', 'M3_no_loss_balanced'))
    verdict = 'Z6J_SAMPLE_MODULATOR_PASS' if all(crit.values()) else ('Z6J_SPECIFIC_BUT_WEAK' if spec else 'Z6J_SAMPLE_MODULATOR_FAIL')
    o = {'kind': 'V13_Z6J_MODULATOR_SAMPLE', 'prereg': 'docs/proofs/continuation-20261027/z6j-modulator-sample/PREREG.md', 'seeds': seeds,
         'emb': str(emb), 'regimes': {k: dict(v) for k, v in F.REGIMES.items()}, 'results': reg, 'criteria': crit, 'verdict': verdict,
         'claim_limit': 'real Needle encoder, real scaffold self-labels, real sample_factor/Neuromod code; label sources and their mix are simulated; one learner kind (route readout); cloud'}
    Path(out).write_text(json.dumps(o, indent=1)); print(verdict, json.dumps({k: v['mean_final_acc'] for k, v in reg.items()}), json.dumps(crit))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--pool-seed', type=int, default=47); ap.add_argument('--seeds', default='211,212,213,214,215')
    x = ap.parse_args()
    if x.cmd == 'embed': F.embed(x.a, x.b, x.pool_seed)
    else: run(x.a, x.b, [int(s) for s in x.seeds.split(',')])


if __name__ == '__main__':
    main()
