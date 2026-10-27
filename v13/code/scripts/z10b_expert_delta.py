#!/usr/bin/env python3
"""WP-Z10b (WP-BP3): active expert deltas with frozen router (§91 STEP6C phase A/B) on a real sparse MoE body.

Isolated cloud candidate (HF transformers fp32, no runtime file touched). Learns a fact set only through a
reversible low-rank delta (LoRA, B=0 start) on the w1/w2/w3 projections of selected experts in a layer window.
Router, attention, norms and embeddings are never trainable. Arms (same facts per seed as Z10a):
  active16  the 16 experts per window layer that the new fact tokens hit most often (router top-k counts)
  random16  16 random experts per window layer (control: does choosing the active ones matter?)
  all64     delta on every expert (control: does restricting to few experts cost anything?)
Measured per arm and seed: steps to reach the target, old-task loss delta, router metrics against the receiver-native
calibration (B3-H6 gate), expert-delta rollback exactness (delta off -> old-task loss identical), delta size.
Reuses Body/facts/old texts/calibration of ``moe_router_bench`` and the monitor of ``moe_router_monitor``.
"""
import argparse
import json
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moe_router_monitor as M  # noqa: E402
import moe_router_bench as B  # noqa: E402

PROJ = ('w1', 'w2', 'w3')


class LoraLinear:
    """Built lazily with torch (module-level import of torch is avoided so tests can import the file)."""


def make_lora(torch, base, rank, alpha):
    nn = torch.nn

    class _Lora(nn.Module):
        def __init__(self):
            super().__init__()
            self.base = base
            self.A = nn.Parameter(torch.empty(rank, base.in_features))
            self.B = nn.Parameter(torch.zeros(base.out_features, rank))
            nn.init.kaiming_uniform_(self.A, a=5 ** .5)
            self.scale = alpha / rank
            self.on = True

        def forward(self, x):
            y = self.base(x)
            if self.on:
                y = y + (x @ self.A.t()) @ self.B.t() * self.scale
            return y
    return _Lora()


def active_experts(body, facts, window, k):
    """Router top-k hit counts of the new fact tokens in each window layer -> the k most-hit experts."""
    counts = {i: np.zeros(int(body.model.config.num_local_experts)) for i in window}
    for n, c in facts:
        ids, ln = body.ids(B.fact_text(n, c))
        cap, _ = body.run(ids)
        for i in window:
            lg = cap.layers[i].logits
            top = np.argsort(-lg, axis=-1)[:, :body.top_k]
            for e in top.reshape(-1):
                counts[i][e] += 1
    return {i: [int(e) for e in np.argsort(-counts[i], kind='stable')[:k]] for i in window}, \
           {i: [int(x) for x in counts[i]] for i in window}


def attach(body, selection, rank, alpha):
    """Wrap w1/w2/w3 of the selected experts. Returns (params, restore_fn, set_on_fn, stats)."""
    torch = body.torch
    wrapped, params = [], []
    for i, ex in selection.items():
        moe = body.layers[i].block_sparse_moe
        for e in ex:
            mlp = moe.experts[e]
            for name in PROJ:
                orig = getattr(mlp, name)
                w = make_lora(torch, orig, rank, alpha)
                setattr(mlp, name, w)
                wrapped.append((mlp, name, orig, w))
                params += [w.A, w.B]

    def restore():
        for mlp, name, orig, _ in wrapped:
            setattr(mlp, name, orig)

    def set_on(flag):
        for *_, w in wrapped:
            w.on = flag
    n_params = int(sum(p.numel() for p in params))
    full = int(sum(o.weight.numel() for _, _, o, _ in wrapped))
    return params, restore, set_on, {'delta_params': n_params, 'replaced_full_params': full,
                                     'delta_bytes_fp16': n_params * 2}


def run_arm(body, cal, base_cap, base_old, texts, facts, window, arm, k, rank, alpha, lr, steps, target, seed, hit):
    torch = body.torch
    for p in body.model.parameters():
        p.requires_grad_(False)
    n_exp = int(body.model.config.num_local_experts)
    if arm == 'active16':
        sel = {i: hit[i] for i in window}
    elif arm == 'random16':
        rng = random.Random(7000 + seed)
        sel = {i: sorted(rng.sample(range(n_exp), k)) for i in window}
    else:
        sel = {i: list(range(n_exp)) for i in window}
    torch.manual_seed(seed)
    params, restore, set_on, stats = attach(body, sel, rank, alpha)
    train = [body.ids(B.fact_text(n, c))[0] for n, c in facts]

    def new_loss():
        tot = 0.0
        for ids in train:
            x = torch.tensor([ids])
            tot = tot + body.model(x, labels=x).loss
        return tot / len(train)

    def old_eval():
        caps, nlls = [], []
        for lang, t in texts:
            ids, n = body.ids(t)
            cap, nll = body.run(ids, labels_from=len(ids) - n)
            caps.append(cap.tail(n))
            nlls.append(nll)
        merged = M.Capture({i: M.LayerCapture(np.concatenate([c.layers[i].logits for c in caps]),
                                               np.concatenate([c.layers[i].router_input for c in caps]),
                                               np.concatenate([c.layers[i].residual for c in caps]))
                            for i in caps[0].layers}, body.top_k)
        return merged, float(np.mean(nlls))

    for p in params:
        p.requires_grad_(True)
    opt = torch.optim.Adam(params, lr=lr)
    with torch.no_grad():
        start = float(new_loss())
    used, t0 = 0, time.time()
    for step in range(steps):
        opt.zero_grad(set_to_none=True)
        loss = new_loss()
        loss.backward()
        opt.step()
        used = step + 1
        if float(loss.detach()) <= target * start:
            break
    for p in params:
        p.requires_grad_(False)
    with torch.no_grad():
        end = float(new_loss())
    after_cap, after_old = old_eval()
    rep = M.interference_report(base_cap, after_cap, base_old, after_old, calibration=cal, min_forgetting=0.0)
    cmp = M.compare(base_cap, after_cap)
    gate = M.router_stability_gate(cmp['aggregate'], cal, old_task_loss_delta=rep['old_task_loss_delta'])
    # rollback: delta off (adapter bypassed) must give the base old-task loss again; then physically removed
    def old_loss():
        with torch.no_grad():
            r = []
            for _, t in texts:
                ids, n = body.ids(t)
                r.append(body.run(ids, capture=False, labels_from=len(ids) - n)[1])
        return float(np.mean(r))
    set_on(False)
    off_loss = old_loss()
    restore()
    removed_loss = old_loss()
    del opt
    res = {'seed': seed, 'arm': arm, 'window': list(window), 'k': k, 'rank': rank, 'lr': lr, 'steps': used,
           'new_task_loss_start': start, 'new_task_loss_end': end, 'ratio_end_start': end / start,
           'old_task_loss_before': base_old, 'old_task_loss_after': after_old,
           'old_task_loss_delta': after_old - base_old, 'router_gate': gate,
           'route_kl': rep['old_task_route_shift'], 'topk_flip': rep['old_task_topk_flip'],
           'router_input_drift': rep['router_input_drift'], 'pre_router_drift': rep['pre_router_drift'],
           'rollback_off_delta': off_loss - base_old, 'rollback_removed_delta': removed_loss - base_old,
           'selection': {str(i): v for i, v in sel.items()}, 'seconds': round(time.time() - t0, 1), **stats}
    print(f"z10b seed={seed} arm={arm} steps={used} new {start:.3f}->{end:.3f} old {base_old:.4f}->{after_old:.4f} "
          f"kl={rep['old_task_route_shift']:.4f} flip={rep['old_task_topk_flip']:.3f} gate={gate['verdict']} "
          f"rollback={res['rollback_removed_delta']:+.2e}", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True)
    ap.add_argument('--model-id', default='')
    ap.add_argument('--revision', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', default='13,21,34')
    ap.add_argument('--window', default='8,9')
    ap.add_argument('--arms', default='active16,random16,all64')
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--rank', type=int, default=8)
    ap.add_argument('--alpha', type=float, default=16)
    ap.add_argument('--lr', type=float, default=3e-3)
    ap.add_argument('--steps', type=int, default=40)
    ap.add_argument('--target', type=float, default=0.1)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--max-texts', type=int, default=0)
    a = ap.parse_args()
    texts = [('en', t) for t in B.OLD_EN] + [('de', t) for t in B.OLD_DE]
    if a.max_texts:
        texts = texts[:a.max_texts // 2] + texts[len(B.OLD_EN):len(B.OLD_EN) + a.max_texts // 2]
    import torch
    import transformers
    out = {'schema': 'v13-z10b-expert-delta-v1', 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'model_id': a.model_id, 'revision': a.revision, 'args': vars(a),
           'host': {'python': platform.python_version(), 'torch': torch.__version__,
                    'transformers': transformers.__version__},
           'evidence_level': 'Linux cloud CPU, HF transformers fp32; not llama.cpp, not Redmi'}
    body = B.Body(a.model, a.threads)
    window = [int(x) for x in a.window.split(',')]
    t0 = time.time()
    cal = B.part_calib(body, texts, out)
    print('calibration', json.dumps(cal['thresholds']), flush=True)
    caps, nlls = [], []
    for lang, t in texts:
        ids, n = body.ids(t)
        cap, nll = body.run(ids, labels_from=len(ids) - n)
        caps.append(cap.tail(n))
        nlls.append(nll)
    base_cap = M.Capture({i: M.LayerCapture(np.concatenate([c.layers[i].logits for c in caps]),
                                            np.concatenate([c.layers[i].router_input for c in caps]),
                                            np.concatenate([c.layers[i].residual for c in caps]))
                          for i in caps[0].layers}, body.top_k)
    base_old = float(np.mean(nlls))
    out['base_old_task_loss'] = base_old
    out['results'] = []
    for seed in [int(s) for s in a.seeds.split(',')]:
        facts = B.fresh_facts(seed)
        hit, counts = active_experts(body, facts, window, a.k)
        for arm in a.arms.split(','):
            out['results'].append(run_arm(body, cal, base_cap, base_old, texts, facts, window, arm, a.k, a.rank,
                                          a.alpha, a.lr, a.steps, a.target, seed, hit))
            out['results'][-1]['hit_counts'] = {str(i): v for i, v in counts.items()}
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=float))
    out['seconds'] = round(time.time() - t0, 1)
    import resource
    out['maxrss_mb'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=float))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
