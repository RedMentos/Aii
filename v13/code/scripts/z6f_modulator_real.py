#!/usr/bin/env python3
"""WP-Z6f / G-MODULATOR-SPECIFICITY-001 with a real encoder: typed modulators vs scalar reward / human-only / outcome-only.

Same mechanism and controls as v13/ablation99.py part 2 (real Neuromod gate per event, control modulators accumulated
like the bus, safety veto kept in every arm), but the learner is a softmax route readout on the real native Needle
embeddings (v13.learning_worker.features) of generated German questions, and the self-generated labels come from the
real scaffold router (v13.cognition.scaffold_route), not from a synthetic bias vector.
Label sources per event: human correction (true label), real outcome (true label, task_success), self (scaffold route,
internal_crosscheck), dream (a fixed wrong route per class, source dream), unsafe success (wrong route, task_success,
safety veto). Halfway the true route of gist questions changes to 'both' (human/outcome follow, scaffold and dream don't).
Two label-source mixes (balanced, self_heavy). Criteria M1-M4: docs/proofs/continuation-20261026/z6f-modulator-real/PREREG.md.

  z6f_modulator_real.py embed <installed_home> <emb.npz> [--pool-seed 41]
  z6f_modulator_real.py run <emb.npz> <out.json> [--seeds 201,202,203,204,205]
"""
import argparse
import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from z6b_lifecycle_bench import make, ROUTE_NAMES  # noqa: E402

KINDS = ('simple', 'detail', 'gist', 'both')
PER_KIND = 160
T = 600; LR0 = .5
REGIMES = {'balanced': (('human', .20), ('outcome', .25), ('self', .25), ('dream', .20), ('unsafe', .10)),
           'self_heavy': (('human', .10), ('outcome', .15), ('self', .35), ('dream', .30), ('unsafe', .10))}  # replay/dream volume dominates
DREAM = {'simple': 'both', 'detail': 'gist', 'gist': 'simple', 'both': 'detail'}   # fixed wrong label per class
UNSAFE = {'simple': 'detail', 'detail': 'both', 'gist': 'detail', 'both': 'simple'}
ARMS = ('v13', 'v13_datamix', 'scalar_reward', 'human_only', 'outcome_only', 'gradient_only', 'gradient_only_matched')
CONTROLS = ('scalar_reward', 'human_only', 'outcome_only')


def embed(installed, out, pool_seed):
    from v13.config import initialize
    from v13.runtime import Runtime
    from v13.learning_worker import features
    from v13.cognition import scaffold_route
    rng = random.Random(pool_seed); used = set(); items = [(make(k, rng, used), k) for k in KINDS for _ in range(PER_KIND)]
    with tempfile.TemporaryDirectory(prefix='v13-z6f-') as d:
        h = Path(d); initialize(h)
        for n in ('models', 'bin'): shutil.rmtree(h/n); (h/n).symlink_to(Path(installed)/n, target_is_directory=True)
        shutil.copyfile(Path(installed)/'config/models.json', h/'config/models.json'); r = Runtime(h)
        try:
            vecs = []
            for t, _ in items:
                ref = r.store.source(t, 'USER'); vecs.append(r.learner.embedding(t, ref['source_id'], time.monotonic()+60))
            X = features(vecs)
        finally:
            r.close()
    np.savez(out, X=np.asarray(X, float), text=np.array([t for t, _ in items]), kind=np.array([k for _, k in items]),
             scaffold=np.array([scaffold_route(t) for t, _ in items]))


def stream(seed, kinds, scaffold, train_idx, share):
    rng = random.Random(seed); out = []
    for t in range(T):
        i = rng.choice(train_idx); k = kinds[i]; true = 'both' if (k == 'gist' and t >= T//2) else k
        r = rng.random(); src = None
        for name, s in share:
            r -= s
            if r <= 0: src = name; break
        src = src or share[-1][0]
        if src == 'human': lab, sig = true, {'source_class': 'human_correction', 'human_correction': 1.}
        elif src == 'outcome': lab, sig = true, {'source_class': 'real_deterministic_outcome', 'task_success': 1.}
        elif src == 'self': lab, sig = scaffold[i], {'source_class': 'internal_crosscheck', 'evidence_gain': .3}
        elif src == 'dream': lab, sig = DREAM[k], {'source_class': 'dream', 'surprise': .8, 'novelty': .5}
        else: lab, sig = UNSAFE[k], {'source_class': 'real_deterministic_outcome', 'task_success': 1., 'safety_veto': True}
        out.append({'t': t, 'path': 'route', 'i': i, 'label': lab, 'true': true, 'src': src, 'touch': True, 'signal': sig})
    return out


def softmax(z):
    z = z-z.max(1, keepdims=True); e = np.exp(z); return e/e.sum(1, keepdims=True)


def train(X, rows, f, test_idx, test_lab):
    W = np.zeros((X.shape[1], 4)); curve = []
    for n, (r, fi) in enumerate(zip(rows, f)):
        x = X[r['i']]; y = np.zeros(4); y[ROUTE_NAMES.index(r['label'])] = 1.
        p = softmax((x@W)[None])[0]; W -= LR0*fi*np.outer(x, p-y)/(1.+x@x)  # normalized step as the NLMS learners in ablation99
        if n % 50 == 49: curve.append(float(np.mean(np.argmax(X[test_idx]@W, 1) == test_lab)))
    pred = np.argmax(X[test_idx]@W, 1)
    return float(np.mean(pred == test_lab)), curve


def run_regime(X, kinds, scaffold, seeds, share):
    from v13 import ablation99 as AB
    res = {a: [] for a in ARMS}; curves = {a: [] for a in ARMS}; budgets = {a: [] for a in ARMS}
    for seed in seeds:
        rng = random.Random(seed*3); idx = list(range(len(kinds))); rng.shuffle(idx)
        test_idx = np.array(sorted(idx[:len(idx)//4])); train_idx = sorted(idx[len(idx)//4:])
        test_lab = np.array([ROUTE_NAMES.index('both' if kinds[i] == 'gist' else kinds[i]) for i in test_idx])  # after the shift
        rows = stream(seed, kinds, scaffold, train_idx, share)
        with tempfile.TemporaryDirectory(prefix='v13-z6f-st-') as d:
            store, _ = AB._store(Path(d)); gated = AB.record_gates(rows, store); store.close()
        for a in ARMS:
            f = AB.factors(gated, a, random.Random(seed*7+len(a)))
            acc, cur = train(X, gated, f, test_idx, test_lab); res[a].append(round(acc, 4)); curves[a].append(cur); budgets[a].append(round(float(np.mean(f)), 4))
    mean = {a: round(float(np.mean(v)), 4) for a, v in res.items()}
    return {'final_acc': res, 'mean_final_acc': mean, 'budget_mean': budgets,
            'curve_mean': {a: [round(float(np.mean([c[j] for c in v])), 4) for j in range(len(v[0]))] for a, v in curves.items()}}


def run(emb, out, seeds):
    z = np.load(emb); X = z['X']; kinds = list(z['kind']); scaffold = list(z['scaffold'])
    scaffold_acc = float(np.mean([s == k for s, k in zip(scaffold, kinds)]))
    reg = {name: run_regime(X, kinds, scaffold, seeds, share) for name, share in REGIMES.items()}
    sh, ba = reg['self_heavy'], reg['balanced']; m, res = sh['mean_final_acc'], sh['final_acc']
    crit = {
        'M1_typed_beats_each_control_self_heavy': all(m['v13']-m[c] >= .03 and sum(x > y for x, y in zip(res['v13'], res[c])) >= 4 for c in CONTROLS),
        'M2_typed_beats_same_budget_gradient_self_heavy': m['v13']-m['gradient_only_matched'] >= .03 and sum(x > y for x, y in zip(res['v13'], res['gradient_only_matched'])) >= 4,
        'M3_no_loss_balanced': all(ba['mean_final_acc']['v13'] >= ba['mean_final_acc'][c]-.02 for c in CONTROLS+('gradient_only_matched',)),
        'M4_learns_at_all': m['v13'] >= .70 and ba['mean_final_acc']['v13'] >= .70,
    }
    o = {'kind': 'V13_Z6F_MODULATOR_REAL', 'prereg': 'docs/proofs/continuation-20261026/z6f-modulator-real/PREREG.md', 'seeds': seeds,
         'regimes': {k: dict(v) for k, v in REGIMES.items()}, 'scaffold_label_accuracy_before_shift': round(scaffold_acc, 4), 'results': reg,
         'criteria': crit, 'verdict': 'Z6F_MODULATOR_REAL_PASS' if all(crit.values()) else 'Z6F_MODULATOR_REAL_FAIL',
         'claim_limit': 'real Needle encoder, real scaffold self-labels and real Neuromod gate; label sources and their mix are simulated; one learner kind (route readout); cloud'}
    Path(out).write_text(json.dumps(o, indent=1)); print(o['verdict'], json.dumps({k: v['mean_final_acc'] for k, v in reg.items()}), json.dumps(crit))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--pool-seed', type=int, default=41); ap.add_argument('--seeds', default='201,202,203,204,205')
    x = ap.parse_args()
    if x.cmd == 'embed': embed(x.a, x.b, x.pool_seed)
    else: run(x.a, x.b, [int(s) for s in x.seeds.split(',')])


if __name__ == '__main__':
    main()
