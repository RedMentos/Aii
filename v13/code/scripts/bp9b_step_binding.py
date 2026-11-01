#!/usr/bin/env python3
"""WP-BP9b: does a per-source weight bind the update when the optimizer is plain SGD (BP9a: AdamW undid it)?
Same facts/groups/arms idea as bp9_typed_weights.py, but trained in a resident LoRA session (v13/lora_session.py) with a chosen optimizer.
Modes: --pilot (learning-rate calibration on human+outcome facts only, no own labels, teacher-forced accuracy every 10 steps)
       run:    arms uniform_adamw | typed_adamw | uniform_sgd | typed_sgd   (--sgd-lr from the pilot, fixed before the run)
Usage: python3 scripts/bp9b_step_binding.py --master DIR --out DIR --seed 1 [--pilot --lrs 0.05,0.2,0.5,1.0] [--sgd-lr X] [--arms ...]
"""
import argparse, json, sys, time, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

class EvalView:
    """The few attributes bj1_body_jepa.evaluate needs, backed by a LoraSession."""
    def __init__(self, sess):
        self.torch, self.model, self.tok = sess.torch, sess.model, sess.tok
        self._encode, self._greedy = sess.tr._encode, sess.tr._greedy

def run(arm, S, items, facts, groups, a, J, B):
    opt, kind = arm.split('_')[1], arm.split('_')[0]
    sess = S(a.master, Path(a.out) / 'work' / ('s%d-%s' % (a.seed, arm)), anchors=J.ANCHORS,
             cfg={'threads': a.threads, 'lr': a.sgd_lr if opt == 'sgd' else a.lr, 'seed': a.seed, 'anchors_per_step': 6}, optimizer=opt)
    ai = B.arm_items('typed' if kind == 'typed' else 'uniform', items, groups, a.seed)
    t = time.monotonic()
    for k in range(a.steps): sess.step(ai, 1.0)
    sess.model.eval(); ev = J.evaluate(EvalView(sess), facts); rows = ev['rows']
    res = {'recall_by_group': B.by_group(rows['learned'], groups, set(B.GROUPS)), 'probe_correct': ev['probe_correct'], 'near_miss_leak': ev['near_miss_leak'],
           'steps': a.steps, 'wall_seconds': round(time.monotonic() - t, 1)}
    del sess; return res

def pilot(S, items, facts, groups, a, J, B):
    keep = [(i, f) for i, f, g in zip(items, facts, groups) if g in ('human', 'outcome')]
    out = {}
    for lr in [float(x) for x in a.lrs.split(',')]:
        sess = S(a.master, Path(a.out) / 'work' / ('pilot-%g' % lr), anchors=J.ANCHORS, cfg={'threads': a.threads, 'lr': lr, 'seed': a.seed, 'anchors_per_step': 6}, optimizer='sgd')
        its = [dict(i, weight=1.0) for i, _ in keep]; probes = [(i['prompt'], i['target']) for i in its]; curve = {}
        for k in range(1, a.steps + 1):
            sess.step(its, 1.0)
            if k % 10 == 0:
                acc = sess.probe_accuracies(probes); curve[k] = round(sum(acc) / len(acc), 3); print(json.dumps({'lr': lr, 'step': k, 'acc': curve[k]}), flush=True)
        out[lr] = curve; del sess
    return out

def main():
    import bj1_body_jepa as J, bp9_typed_weights as B
    from v13.lora_session import LoraSession
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arms', default='uniform_adamw,typed_adamw,uniform_sgd,typed_sgd'); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--steps', type=int, default=30); ap.add_argument('--lr', type=float, default=5e-4); ap.add_argument('--sgd-lr', type=float, default=0.2)
    ap.add_argument('--pilot', action='store_true'); ap.add_argument('--lrs', default='0.05,0.2,0.5,1.0')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    items, facts, groups = B.build(J.POOL, a.seed)
    if a.pilot:
        r = pilot(LoraSession, items, facts, groups, a, J, B); (out / 'pilot.json').write_text(json.dumps(r, indent=1)); print(json.dumps(r)); return
    rep = {'schema': 'v13-bp9b-step-binding-v1', 'seed': a.seed, 'sgd_lr': a.sgd_lr, 'groups': groups, 'platform': platform.platform(), 'arms': {}}
    path = out / ('bp9b-seed%d.json' % a.seed)
    for arm in a.arms.split(','):
        rep['arms'][arm] = run(arm, LoraSession, items, facts, groups, a, J, B)
        print(json.dumps({'arm': arm, **rep['arms'][arm]}), flush=True); path.write_text(json.dumps(rep, indent=1))
    print(str(path))

if __name__ == '__main__':
    main()
