#!/usr/bin/env python3
"""WP-T17 / §13 world model, §99 "JEPA predictor helps" for action consequences: does the latent predictor, conditioned on
the action, predict what a text action does to the B2 state better than controls without a predictor?

Real B2 taps: Qwen3.5-0.8B GGUF through llama-server --embedding --pooling mean (1024 dims). Data: the 376 C3 sentences of
jepa_ablation_bench (16 topics) and, per sentence, the C3 (LFM2.5-350M) outcome of four text actions: translate_de,
question, negate, summarize (cached in --actions JSON). Train = sentences of 10 topics, test = the 6 other topics.
Scores are surprise values ||pred(x, a) - T y||^2; lower = more expected.
Tasks on held-out topics:
  verify_action    AUROC: true outcome of a vs outcome of another action on the SAME sentence (did the action happen?)
  verify_content   AUROC: true outcome of a vs outcome of a on ANOTHER test sentence (is this the result of this input?)
  inverse_acc      which action turned x into y? argmin over a of surprise (chance .25)
  forward_top1     given x and a, the true outcome ranks first among all test outcomes of a
Arms:
  jepa_shared_*    shared encoder p and EMA/SIGReg target T, one 16x16 (or 128x128) predictor q_a per action; the runtime
                   loss (predictor_worker.loss_gradient), BOOT / long budget; the action-conditioned form of the runtime JEPA
  jepa_per_action  the unchanged runtime optimizer trained once per action (own p, q, T); surprises z-scored per action
  no_predictor     random projection p0, copy distance ||p0 x - p0 y||^2 (action-blind)
  mean_delta_16    p0 x + mean train delta of action a in the 16-dim projection (no learning beyond 4 means)
  mean_delta_full  same in the full 1024 space
  ridge_full       one ridge W_a: x -> y per action in the full space
  supervised_inv   softmax readout on y - x trained with action labels (inverse upper bound)
  python3 scripts/jepa_action_bench.py --server BIN --model GGUF --sentences JSON --actions JSON --out DIR [--seed N]
"""
import argparse, json, platform, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13 import predictor_worker as pw  # noqa: E402
from jepa_ablation_bench import BOOT, LONG, auroc, taps  # noqa: E402

ACTIONS = ('translate_de', 'question', 'negate', 'summarize')
SIG = {'predictor_regularizer': 'sigreg', 'sigreg_projections': 32, 'sigreg_weight': 1.}

def optimize_actions(x, y, a, p, cfg, k):
    """Runtime JEPA loss, shared encoder p / target T, one predictor q_a per action; gradients averaged over actions."""
    p = p.copy(); target = p.copy(); anchor = p.copy(); q = [np.eye(p.shape[1]) for _ in range(k)]; mode = pw.regularizer(cfg)
    for step in range(cfg['predictor_steps']):
        kw = pw.regularizer_kwargs(cfg, p.shape[1], step); gp = np.zeros_like(p); dq = []
        for j in range(k):
            m = a == j; _, g, gq, _ = pw.loss_gradient(x[m], y[m], p, q[j], target, anchor, **kw); gp += g/k; dq.append(-cfg['predictor_lr']*gq)
        dp = -cfg['predictor_lr']*gp; norm = float(np.sqrt(np.sum(dp*dp)+sum(np.sum(d*d) for d in dq)))
        s = min(1., cfg['max_update_norm']/max(norm, 1e-12)); p += dp*s
        for j in range(k): q[j] = q[j]+dq[j]*s
        target = p.copy() if mode == 'sigreg' else cfg['ema_decay']*target+(1-cfg['ema_decay'])*p
    return p, q, target

def softmax_readout(F, y, k, steps=500, lr=.5, l2=1e-3):
    mu, sd = F.mean(0), F.std(0)+1e-6; Z = (F-mu)/sd; W = np.zeros((Z.shape[1], k)); b = np.zeros(k); Y = np.eye(k)[y]
    for _ in range(steps):
        L = Z@W+b; L -= L.max(1, keepdims=True); P = np.exp(L); P /= P.sum(1, keepdims=True); G = (P-Y)/len(Z)
        W -= lr*(Z.T@G+l2*W); b -= lr*G.sum(0)
    return lambda H: (((H-mu)/sd)@W+b).argmax(1)

def tasks(surprise, X, Y, k, rng):
    """surprise(x_rows, action_index, y_rows) -> per-row surprise. X: (n, d) test inputs, Y: (k, n, d) true outcomes."""
    n = len(X); true = np.stack([surprise(X, j, Y[j]) for j in range(k)])
    other = np.stack([surprise(X, j, Y[(j+1+rng.integers(0, k-1, n)) % k, np.arange(n)]) for j in range(k)])
    perm = np.array([rng.choice([i for i in range(n) if i != r]) for r in range(n)])
    wrong = np.stack([surprise(X, j, Y[j][perm]) for j in range(k)])
    full = np.stack([[surprise(X, a, Y[j]) for a in range(k)] for j in range(k)])  # [true action j, assumed a, row]
    inv = float(np.mean(full.argmin(1) == np.arange(k)[:, None]))
    top1 = []
    for j in range(k):
        for i in range(n):
            top1.append(int(np.argmin(surprise(np.repeat(X[i:i+1], n, 0), j, Y[j])) == i))
    lab = lambda pos, neg: np.r_[np.zeros(pos.size), np.ones(neg.size)]
    return {'verify_action_auroc': auroc(np.r_[true.ravel(), other.ravel()], lab(true, other)),
            'verify_content_auroc': auroc(np.r_[true.ravel(), wrong.ravel()], lab(true, wrong)),
            'inverse_acc': round(inv, 4), 'forward_top1': round(float(np.mean(top1)), 4)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--server', required=True); ap.add_argument('--model', required=True)
    ap.add_argument('--sentences', required=True); ap.add_argument('--actions', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, default=13); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); by_topic = json.loads(Path(a.sentences).read_text()); acts = json.loads(Path(a.actions).read_text())
    topics = sorted(by_topic); sents = [s for t in topics for s in by_topic[t] if s in acts]; topic_of = {s: t for t in topics for s in by_topic[t]}
    texts = sents+[acts[s][x] for x in ACTIONS for s in sents]; k = len(ACTIONS); n = len(sents)
    T = pw.normalize(taps(a.server, a.model, texts, out/'taps.npz')); X = T[:n]; Y = T[n:].reshape(k, n, -1); d = X.shape[1]
    rng = np.random.default_rng(a.seed); order = list(rng.permutation(topics)); train_t = set(order[:10])
    tr = np.array([topic_of[s] in train_t for s in sents]); te = ~tr
    xtr = np.tile(X[tr], (k, 1)); ytr = Y[:, tr].reshape(-1, d); atr = np.repeat(np.arange(k), tr.sum()); Xte = X[te]; Yte = Y[:, te]
    sq = lambda A, B: np.mean((A-B)**2, axis=1); res = {}; t0 = time.monotonic()
    for dim in (16, 128):
        p0 = np.linalg.qr(np.random.default_rng(a.seed).normal(size=(d, dim)))[0]
        runs = (('boot', BOOT | {'predictor_regularizer': 'ema'}), ('long', LONG | {'predictor_regularizer': 'ema'}), ('sigreg', LONG | SIG)) if dim == 16 else (('sigreg', LONG | SIG),)
        for name, cfg in runs:
            p, q, tgt = optimize_actions(xtr, ytr, atr, p0, cfg, k)
            res['jepa_shared_%s_%d' % (name, dim)] = tasks(lambda x, j, y: sq((x@p)@q[j], y@tgt), Xte, Yte, k, np.random.default_rng(7)) | {'steps': cfg['predictor_steps']}
        res['no_predictor_%d' % dim] = tasks(lambda x, j, y: sq(x@p0, y@p0), Xte, Yte, k, np.random.default_rng(7))
        md = [np.mean((ytr[atr == j]-xtr[atr == j])@p0, 0) for j in range(k)]
        res['mean_delta_%d' % dim] = tasks(lambda x, j, y: sq(x@p0+md[j], y@p0), Xte, Yte, k, np.random.default_rng(7))
    # Unchanged runtime optimizer, one predictor per action; own spaces, so surprises are z-scored by the train residuals.
    p0 = np.linalg.qr(np.random.default_rng(a.seed).normal(size=(d, 16)))[0]; per = []
    for j in range(k):
        m = atr == j; p, q, tgt, _ = pw.optimize(xtr[m], ytr[m], p0, np.eye(16), p0.copy(), p0.copy(), LONG | {'predictor_regularizer': 'ema'})
        r = sq((xtr[m]@p)@q, ytr[m]@tgt); per.append((p, q, tgt, r.mean(), r.std()+1e-12))
    res['jepa_per_action_long_16'] = tasks(lambda x, j, y: (sq((x@per[j][0])@per[j][1], y@per[j][2])-per[j][3])/per[j][4], Xte, Yte, k, np.random.default_rng(7))
    mdf = [np.mean(ytr[atr == j]-xtr[atr == j], 0) for j in range(k)]
    res['mean_delta_full'] = tasks(lambda x, j, y: sq(x+mdf[j], y), Xte, Yte, k, np.random.default_rng(7))
    W = [np.linalg.solve(xtr[atr == j].T@xtr[atr == j]+10.*np.eye(d), xtr[atr == j].T@ytr[atr == j]) for j in range(k)]
    res['ridge_full'] = tasks(lambda x, j, y: sq(x@W[j], y), Xte, Yte, k, np.random.default_rng(7))
    f = softmax_readout(ytr-xtr, atr, k); res['supervised_inv'] = {'inverse_acc': round(float(np.mean(f((Yte-Xte[None]).reshape(-1, d)) == np.repeat(np.arange(k), te.sum()))), 4), 'uses_labels': True}
    doc = {'schema': 'v13-jepa-action-v1', 'experiment': 'blueprint §13 world model / §99 JEPA predictor for action consequences', 'date': time.strftime('%Y-%m-%d'),
           'platform': platform.platform(), 'body': Path(a.model).name, 'tap_dim': d, 'actions': ACTIONS, 'topics': {'train': sorted(train_t), 'test': sorted(set(topics)-train_t)},
           'sentences': {'train': int(tr.sum()), 'test': int(te.sum())}, 'chance': {'auroc': .5, 'inverse_acc': 1/k, 'forward_top1': round(1/int(te.sum()), 4)},
           'seed': a.seed, 'boot_cfg': BOOT, 'long_cfg': LONG, 'arms': res, 'seconds': round(time.monotonic()-t0, 1),
           'claim_limit': 'per file one seed (split + projection), 4 text actions whose outcomes C3 wrote, mean-pooled last-layer taps; actions are text edits, not tool or world effects'}
    (out/('jepa_action.json' if a.seed == 13 else 'jepa_action_seed%d.json' % a.seed)).write_text(json.dumps(doc, indent=1)); print(json.dumps(res, indent=1)); return 0

if __name__ == '__main__':
    sys.exit(main())
