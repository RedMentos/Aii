#!/usr/bin/env python3
"""WP-BP7b: does a policy-only dream change behaviour (abstain on never-told facts) without costing taught facts or general knowledge?

Real body B1 (LFM2.5-1.2B) LoRA, fp32 master, greedy. Arms (same loop, steps, anchors, taught facts per seed):
  facts_only     sleep A only: replay of 8 taught facts
  facts_policy   + 16 policy-only dream items (abstain on generic personal questions; no stored value, none of the probe questions)
  facts_other    + 16 dream items of equal count with irrelevant content (route choice): control that "more dream text" is not the cause
Measures (v13/behavior_probe.py): abstain rate on 12 never-told questions, taught-fact answer rate, over-abstain on taught facts, general probes, near-miss leak.
Usage: python3 scripts/bp7_dream_behavior.py --master DIR --out DIR --seed 1 [--arms ...] [--smoke]
"""
import argparse, json, sys, time, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from v13 import behavior_probe as BP
from v13.common import file_hash

def run_probe(tr, facts, gen, probes, answer_hit):
    ua = [gen(tr, q) for q in BP.UNKNOWN]
    ka = [gen(tr, f[0]) for f in facts]
    s = BP.score(ua, ka, [f[2] for f in facts])
    pr = [answer_hit(gen(tr, p['prompt']), p['expect']) for p in probes]
    leak = [answer_hit(gen(tr, f[4]), f[2]) for f in facts]
    s.update({'probe_correct': sum(pr) / len(pr), 'near_miss_leak': sum(leak) / len(leak)})
    return s, {'unknown_texts': [t[:140] for t in ua], 'known_texts': [t[:140] for t in ka]}

def main():
    import bj1_body_jepa as J
    from v13.body_jepa import BodyJepaTrainer
    from v13.lora_trainer import answer_hit
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arms', default='facts_only,facts_policy,facts_other'); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--steps', type=int, default=30); ap.add_argument('--lr', type=float, default=5e-4); ap.add_argument('--dream', type=int, default=16)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed); idx = sorted(rng.choice(len(J.POOL), size=8, replace=False).tolist())
    facts = [J.POOL[i] for i in idx]
    fact_items = [{'memory_id': 'bp7_%d' % i, 'prompt': q, 'target': t, 'answer_keys': k, 'origin': 'human'} for i, (q, t, k, _, _) in zip(idx, facts)]
    gen = lambda tr, q: J.gen(tr, tr.torch, tr.model, tr.tok, q)
    rep = {'schema': 'v13-bp7b-dream-behavior-v1', 'seed': a.seed, 'fact_index': idx, 'platform': platform.platform(),
           'master_sha256': file_hash(Path(a.master) / 'model.safetensors'), 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'arms': {}}
    path = out / ('bp7b-seed%d.json' % a.seed)
    for arm in a.arms.split(','):
        items = list(fact_items)
        if arm == 'facts_policy': items += BP.policy_items_en(a.dream, a.seed)
        elif arm == 'facts_other': items += BP.policy_items_en(a.dream, a.seed, other=True)
        cfg = {'threads': a.threads, 'max_steps': a.steps, 'min_steps': a.steps, 'lr': a.lr, 'seed': a.seed, 'anchors_per_step': 6, 'jepa_weight': 0.}
        if a.smoke: cfg.update(max_steps=2, min_steps=2)
        tr = BodyJepaTrainer(a.master, out / 'work' / ('s%d-%s' % (a.seed, arm)), anchors=J.ANCHORS, cfg=cfg, arch='lfm2')
        t = time.monotonic(); r = tr.fit(items, 'bp7b')
        if 'base' not in rep:
            g0 = lambda tr_, q: J.gen(tr_, tr_.torch, tr_.model, tr_.tok, q, adapter=False)
            rep['base'], rep['base_texts'] = run_probe(tr, facts, g0, J.PROBES, answer_hit)
        res, texts = run_probe(tr, facts, gen, J.PROBES, answer_hit)
        res.update({'items': len(items), 'final_ce': r['metrics']['final_ce'], 'steps': r['metrics']['steps'], 'wall_seconds': round(time.monotonic() - t, 1)})
        rep['arms'][arm] = res; rep.setdefault('texts', {})[arm] = texts
        print(json.dumps({'arm': arm, **res}), flush=True)
        path.write_text(json.dumps(rep, indent=1, ensure_ascii=False)); del tr
    print(str(path))

if __name__ == '__main__':
    main()
