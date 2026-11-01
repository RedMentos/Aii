#!/usr/bin/env python3
"""WP-BP9d: own-source labels that are only PARTLY wrong (6 right, 2 wrong of 8) with a weight that does not exclude the source (SGD binds weights, BP9c).
16 facts per seed: human 4 (w .45) | outcome 4 (w 1.0) | own_right 6 | own_wrong 2 (own weight w_own in {0.15, 0.30}).
Arms: uniform_sgd (all 1) | own015_sgd | own030_sgd. SGD lr 0.01 momentum .9, 30 steps, resident LoRA session.
Metrics: recall of the trained target by group (own_wrong = adoption of the wrong label), general probes, neighbour leak.
Usage: python3 scripts/bp9d_partial_own.py --master DIR --out DIR --seed 1 [--arms uniform_sgd,own015_sgd,own030_sgd]
"""
import argparse, json, sys, time, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

GROUPS = ('human', 'outcome', 'own_right', 'own_wrong')
SIZES = {'human': 4, 'outcome': 4, 'own_right': 6, 'own_wrong': 2}
WEIGHTS = {'human': .45, 'outcome': 1.0}

def build(pool, seed):
    rng = np.random.default_rng(seed); idx = rng.permutation(len(pool))[:16].tolist(); pos = 0
    items, facts, groups = [], [], []
    for g in GROUPS:
        for i in idx[pos:pos + SIZES[g]]:
            q, a, keys, paras, nm = pool[i]; tgt, tkeys = a, keys
            if g == 'own_wrong':
                j = int(rng.choice([k for k in range(len(pool)) if k != i])); tgt, tkeys = pool[j][1], pool[j][2]
            it = {'memory_id': 'bp9d_%d' % i, 'prompt': q, 'target': tgt, 'answer_keys': tkeys}
            items.append(it); facts.append((q, tgt, tkeys, paras, nm)); groups.append(g)
        pos += SIZES[g]
    return items, facts, groups

def weights_for(arm, groups):
    if arm == 'uniform_sgd': return [1.0] * len(groups)
    w_own = {'own015_sgd': .15, 'own030_sgd': .30}[arm]
    return [WEIGHTS.get(g, w_own) for g in groups]

def by_group(rows, groups):
    return {g: sum(r['ok'] for r, gg in zip(rows, groups) if gg == g) / SIZES[g] for g in GROUPS}

def main():
    import bj1_body_jepa as J
    from bp9b_step_binding import EvalView
    from v13.lora_session import LoraSession
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arms', default='uniform_sgd,own015_sgd,own030_sgd'); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--steps', type=int, default=30); ap.add_argument('--sgd-lr', type=float, default=0.01)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    items, facts, groups = build(J.POOL, a.seed)
    rep = {'schema': 'v13-bp9d-partial-own-v1', 'seed': a.seed, 'groups': groups, 'sgd_lr': a.sgd_lr, 'platform': platform.platform(), 'arms': {}}
    path = out / ('bp9d-seed%d.json' % a.seed)
    for arm in a.arms.split(','):
        t = time.monotonic()
        sess = LoraSession(a.master, out / 'work' / ('s%d-%s' % (a.seed, arm)), anchors=J.ANCHORS,
                           cfg={'threads': a.threads, 'lr': a.sgd_lr, 'seed': a.seed, 'anchors_per_step': 6}, optimizer='sgd')
        ai = [dict(i, weight=w) for i, w in zip(items, weights_for(arm, groups))]
        for _ in range(a.steps): sess.step(ai, 1.0)
        sess.model.eval(); ev = J.evaluate(EvalView(sess), facts)
        res = {'recall_by_group': by_group(ev['rows']['learned'], groups), 'probe_correct': ev['probe_correct'], 'near_miss_leak': ev['near_miss_leak'],
               'wall_seconds': round(time.monotonic() - t, 1)}
        rep['arms'][arm] = res; print(json.dumps({'arm': arm, **res}), flush=True); path.write_text(json.dumps(rep, indent=1)); del sess
    print(str(path))

if __name__ == '__main__':
    main()
