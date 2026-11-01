#!/usr/bin/env python3
"""WP-BP9a: do typed per-sample weights (sample_labels.modulate) keep an unreliable label source out of a real weight update?

Real body B1 (LFM2.5-1.2B) LoRA update in one batch of 16 facts from three sources:
  human (4, correct) | outcome (4, correct, deterministic) | own_right (4, model-written, correct) | own_wrong (4, model-written, WRONG target)
Arms (same loop, steps, anchors, facts): uniform (all weight 1) | typed (sample_labels.modulate) | no_own (own dropped) | shuffled (typed weight multiset
randomly reassigned across items: control, shows the SOURCE type matters and not only smaller weights).
Metrics (greedy, fp32 master): recall of the trained target by group; for own_wrong the recall of the WRONG target = adoption of the bad label;
general probe retention; near-miss leak.
Usage: python3 scripts/bp9_typed_weights.py --master DIR --out DIR --seed 1 [--arms uniform,typed,no_own,shuffled] [--smoke]
"""
import argparse, json, sys, time, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from v13.sample_labels import modulate
from v13.common import file_hash

GROUPS = ('human', 'outcome', 'own_right', 'own_wrong')

def build(pool, seed, per=4):
    """Pick per*4 facts; own_wrong facts get the answer of another pool fact as WRONG target. Returns items, eval facts, group per index."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(pool))[:per * 4].tolist()
    items, facts, groups = [], [], []
    for gi, g in enumerate(GROUPS):
        for i in idx[gi * per:(gi + 1) * per]:
            q, a, keys, paras, nm = pool[i]
            tgt, tkeys = a, keys
            if g == 'own_wrong':
                j = int(rng.choice([k for k in range(len(pool)) if k != i]))
                tgt, tkeys = pool[j][1], pool[j][2]
            it = {'memory_id': 'bp9_%d' % i, 'prompt': q, 'target': tgt, 'answer_keys': tkeys}
            if g == 'human': it['origin'] = 'human'
            elif g == 'outcome': it['kind'] = 'tool_outcome'
            else: it['origin'] = 'self'
            items.append(it); facts.append((q, tgt, tkeys, paras, nm)); groups.append(g)
    return items, facts, groups

def arm_items(arm, items, groups, seed):
    if arm == 'uniform':
        return [dict(i, weight=1.0) for i in items]
    typed, _ = modulate([dict(i) for i in items])
    w = {i['memory_id']: i['weight'] for i in typed}
    if arm == 'typed':
        return [dict(i, weight=w[i['memory_id']]) for i in items]
    if arm == 'no_own':
        return [dict(i, weight=w[i['memory_id']]) for i, g in zip(items, groups) if not g.startswith('own')]
    if arm == 'shuffled':
        vals = [w[i['memory_id']] for i in items]
        perm = np.random.default_rng(seed + 1000).permutation(len(vals))
        return [dict(i, weight=vals[p]) for i, p in zip(items, perm)]
    raise ValueError(arm)

def by_group(rows, groups, present):
    out = {}
    for g in GROUPS:
        ok = [r['ok'] for r, gg in zip(rows, groups) if gg == g]
        out[g] = (sum(ok) / len(ok)) if ok and g in present else None
    return out

def main():
    from bj1_body_jepa import POOL, ANCHORS, evaluate
    from v13.body_jepa import BodyJepaTrainer
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arms', default='uniform,typed,no_own,shuffled'); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--steps', type=int, default=30); ap.add_argument('--lr', type=float, default=5e-4); ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    items, facts, groups = build(POOL, a.seed)
    rep = {'schema': 'v13-bp9a-typed-weights-v1', 'seed': a.seed, 'groups': groups, 'platform': platform.platform(),
           'master_sha256': file_hash(Path(a.master) / 'model.safetensors'), 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'weights_typed': {g: round(float(np.mean([i['weight'] for i, gg in zip(arm_items('typed', items, groups, a.seed), groups) if gg == g])), 4) for g in GROUPS}, 'arms': {}}
    path = out / ('bp9a-seed%d.json' % a.seed)
    for arm in a.arms.split(','):
        ai = arm_items(arm, items, groups, a.seed)
        present = {g for g, i in zip(groups, items) if any(x['memory_id'] == i['memory_id'] for x in ai)}
        cfg = {'threads': a.threads, 'max_steps': a.steps, 'min_steps': a.steps, 'lr': a.lr, 'seed': a.seed, 'anchors_per_step': 6, 'jepa_weight': 0.}
        if a.smoke: cfg.update(max_steps=2, min_steps=2)
        tr = BodyJepaTrainer(a.master, out / 'work' / ('s%d-%s' % (a.seed, arm)), anchors=ANCHORS, cfg=cfg, arch='lfm2')
        t = time.monotonic(); r = tr.fit(ai, 'bp9a')
        ev = evaluate(tr, facts)
        rows = ev['rows']
        res = {'recall_by_group': by_group(rows['learned'], groups, present), 'para_by_group': by_group(rows['para'][0::2], groups, present),
               'near_miss_leak': ev['near_miss_leak'], 'probe_correct': ev['probe_correct'], 'final_ce': r['metrics']['final_ce'],
               'steps': r['metrics']['steps'], 'wall_seconds': round(time.monotonic() - t, 1), 'weights': {i['memory_id']: i['weight'] for i in ai}}
        rep['arms'][arm] = res
        print(json.dumps({'arm': arm, **{k: res[k] for k in ('recall_by_group', 'probe_correct', 'near_miss_leak', 'wall_seconds')}}), flush=True)
        path.write_text(json.dumps(rep, indent=1, ensure_ascii=False)); del tr
    print(str(path))

if __name__ == '__main__':
    main()
