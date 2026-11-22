#!/usr/bin/env python3
"""WP-T14 / §99 row "JEPA predictor helps": latent predictor vs supervised readout vs next-token-like probe vs none.

Real B2 taps: Qwen3.5-0.8B GGUF through llama-server --embedding --pooling mean (1024 dims, the body V13 runs as B2).
Task where a future-state predictor should matter: detect the topic shift / episode boundary between consecutive
sentences of a stream (WP-N8 uses prediction error as a cut signal). Sentences come from 16 topics (generated once by C3,
cached in DIR/sentences.json). Streams: 4 topic segments of 3-6 sentences. Train streams use 10 topics, test streams the
6 other topics only, so nothing can memorise a topic.
Arms (score per pair t -> t+1, higher = boundary; AUROC on held-out pairs):
  jepa_boot       v13.predictor_worker.optimize with the runtime BOOT budget (EMA target), surprise = ||q(p x) - T y||^2
  jepa_long       same objective, long budget (does the mechanism help at all?)
  jepa_sigreg     long budget, SIGReg instead of the variance floor
  no_predictor    same random 16-dim projection, no learning: ||p0 x - p0 y||^2
  *_128           JEPA (SIGReg, long) and no-predictor control with a 128-dim projection (bottleneck check)
  raw_cosine      1 - cos(x, y) on the full tap, no learning
  next_token      ridge x -> y in the full 1024 space (next-step regression), surprise = ||W x - y||^2
  supervised      logistic readout on |x - y| trained WITH boundary labels (upper bound, needs labels)
  python3 scripts/jepa_ablation_bench.py --server BIN --model GGUF --sentences JSON --out DIR
"""
import argparse, json, platform, subprocess, sys, time, urllib.request
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import predictor_worker as pw  # noqa: E402
from v13.config import KNOBS  # noqa: E402

BOOT = {'predictor_steps': KNOBS['predictor_steps'][0], 'predictor_lr': KNOBS['predictor_lr'][0], 'ema_decay': KNOBS['ema_decay'][0],
        'max_update_norm': KNOBS['max_update_norm'][0], 'seed': 13}
LONG = BOOT | {'predictor_steps': 3000, 'predictor_lr': .05, 'max_update_norm': .5}

def auroc(score, label):
    score = np.asarray(score, float); label = np.asarray(label, bool); pos = score[label]; neg = score[~label]
    if not len(pos) or not len(neg): return None
    ranks = np.argsort(np.argsort(np.r_[pos, neg])) + 1.
    return float((ranks[:len(pos)].sum() - len(pos)*(len(pos)+1)/2) / (len(pos)*len(neg)))

def taps(server, model, texts, cache):
    if cache.exists():
        z = np.load(cache)
        if list(z['texts']) == texts: return z['x']
    p = subprocess.Popen([server, '-m', model, '--embedding', '--pooling', 'mean', '--port', '18102', '-c', '2048', '-t', '4', '--no-webui', '--log-disable'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(240):
            try: urllib.request.urlopen('http://127.0.0.1:18102/health', timeout=1); break
            except OSError: time.sleep(.5)
        out = []
        for i in range(0, len(texts), 16):
            req = urllib.request.Request('http://127.0.0.1:18102/v1/embeddings', json.dumps({'input': texts[i:i+16]}).encode(), {'Content-Type': 'application/json'})
            out += [r['embedding'] for r in sorted(json.load(urllib.request.urlopen(req, timeout=600))['data'], key=lambda r: r['index'])]
    finally: p.kill(); p.wait()
    x = np.asarray(out, dtype=np.float64); np.savez(cache, x=x, texts=np.asarray(texts)); return x

def streams(by_topic, topics, n, rng):
    out = []
    for _ in range(n):
        seq = []; prev = None
        for _ in range(4):
            t = rng.choice([u for u in topics if u != prev]); prev = t
            seq += [(t, i) for i in rng.choice(len(by_topic[t]), size=int(rng.integers(3, 7)), replace=False)]
        out.append(seq)
    return out

def pairs(seqs, index, X):
    xs, ys, lab, grp = [], [], [], []
    for g, seq in enumerate(seqs):
        for (ta, ia), (tb, ib) in zip(seq, seq[1:]):
            xs.append(X[index[(ta, ia)]]); ys.append(X[index[(tb, ib)]]); lab.append(ta != tb); grp.append(g)
    return pw.normalize(np.asarray(xs)), pw.normalize(np.asarray(ys)), np.asarray(lab), np.asarray(grp)

def logistic(F, y, steps=400, lr=.5, l2=1e-3):
    mu, sd = F.mean(0), F.std(0)+1e-6; Z = (F-mu)/sd; w = np.zeros(Z.shape[1]); b = 0.
    for _ in range(steps):
        p = 1/(1+np.exp(-(Z@w+b))); g = p-y; w -= lr*(Z.T@g/len(Z)+l2*w); b -= lr*g.mean()
    return lambda G: ((G-mu)/sd)@w+b

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--server', required=True); ap.add_argument('--model', required=True)
    ap.add_argument('--sentences', required=True); ap.add_argument('--out', required=True); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); by_topic = json.loads(Path(a.sentences).read_text()); topics = sorted(by_topic)
    texts = [s for t in topics for s in by_topic[t]]; index = {}; k = 0
    for t in topics:
        for i in range(len(by_topic[t])): index[(t, i)] = k; k += 1
    X = taps(a.server, a.model, texts, out/'taps.npz'); rng = np.random.default_rng(13)
    order = list(rng.permutation(topics)); train_t, test_t = order[:10], order[10:]
    xtr, ytr, ltr, _ = pairs(streams(by_topic, train_t, 120, rng), index, X); xte, yte, lte, _ = pairs(streams(by_topic, test_t, 60, rng), index, X)
    d = X.shape[1]; p0 = np.linalg.qr(np.random.default_rng(13).normal(size=(d, 16)))[0]; q0 = np.eye(16)
    res = {}; t0 = time.monotonic()
    for name, cfg in (('jepa_boot', BOOT | {'predictor_regularizer': 'ema'}), ('jepa_long', LONG | {'predictor_regularizer': 'ema'}),
                      ('jepa_sigreg', LONG | {'predictor_regularizer': 'sigreg', 'sigreg_projections': 32, 'sigreg_weight': 1.})):
        p, q, tgt, hist = pw.optimize(xtr, ytr, p0, q0, p0.copy(), p0.copy(), cfg)
        s = np.mean(((xte@p)@q - yte@tgt)**2, axis=1); ev = pw.evaluate(xte, yte, p, q, tgt, p0)
        res[name] = {'auroc': auroc(s, lte), 'prediction_mse': ev['prediction_mse'], 'copy_baseline_mse': ev['copy_baseline_mse'],
                     'effective_rank': ev['effective_rank'], 'steps': cfg['predictor_steps']}
    res['no_predictor'] = {'auroc': auroc(np.mean((xte@p0 - yte@p0)**2, axis=1), lte)}
    # Is the 16-dim projection the bottleneck? Same objective and control with a 128-dim projection.
    p1 = np.linalg.qr(np.random.default_rng(13).normal(size=(d, 128)))[0]; q1 = np.eye(128)
    p, q, tgt, _ = pw.optimize(xtr, ytr, p1, q1, p1.copy(), p1.copy(), LONG | {'predictor_regularizer': 'sigreg', 'sigreg_projections': 32, 'sigreg_weight': 1.})
    res['jepa_sigreg_128'] = {'auroc': auroc(np.mean(((xte@p)@q - yte@tgt)**2, axis=1), lte), 'steps': LONG['predictor_steps']}
    res['no_predictor_128'] = {'auroc': auroc(np.mean((xte@p1 - yte@p1)**2, axis=1), lte)}
    cos = lambda A, B: np.sum(A*B, 1)/(np.linalg.norm(A, axis=1)*np.linalg.norm(B, axis=1))
    res['raw_cosine'] = {'auroc': auroc(1-cos(xte, yte), lte)}
    W = np.linalg.solve(xtr.T@xtr+10.*np.eye(d), xtr.T@ytr); res['next_token'] = {'auroc': auroc(np.mean((xte@W-yte)**2, axis=1), lte)}
    f = logistic(np.abs(xtr-ytr), ltr.astype(float)); res['supervised'] = {'auroc': auroc(f(np.abs(xte-yte)), lte), 'uses_labels': True}
    doc = {'schema': 'v13-jepa-ablation-v1', 'experiment': 'blueprint §99 JEPA predictor helps', 'date': time.strftime('%Y-%m-%d'), 'platform': platform.platform(),
           'body': Path(a.model).name, 'tap_dim': d, 'topics': {'train': train_t, 'test': test_t}, 'sentences': len(texts),
           'pairs': {'train': int(len(xtr)), 'test': int(len(xte)), 'test_boundaries': int(lte.sum())}, 'boot_cfg': BOOT, 'long_cfg': LONG, 'arms': res,
           'seconds': round(time.monotonic()-t0, 1), 'claim_limit': 'one seed, 16 synthetic topics from C3, mean-pooled last-layer taps, task = topic shift only'}
    (out/'jepa_ablation.json').write_text(json.dumps(doc, indent=1)); print(json.dumps(res, indent=1)); return 0

if __name__ == '__main__':
    sys.exit(main())
