"""WP-J B3-H3 L1 attempt 7 (WP-Z4e): the attempt-5 recipe with five times the data on one fresh seed (power), private view.

Attempt 6 (bench-results/b3-l1-v6-20261022) found LATENT 1.5-5.6 points ahead of the attribute words on private/escalate
and 0.3-3.6 points on private/apologize on every fresh seed, but with 120 test rows per split the paired mean - 2 se rule
was cleared only sometimes. This run keeps the recipe UNCHANGED (b3_l1_v5_bench.run_task: recv_cond aux bridge + readout
refit, gate, baselines, 60/20/20 splits, 5 paired split seeds, canon rule) and changes only:
  - N = 3000 rows (600 test rows per split) on one new data seed (20261301), new B1/B2 states;
  - private view, target tasks escalate and apologize only (action and the shared view were measured four times already).
Preregistration: docs/proofs/b3-l1-v7-20261027/PREREG.md.
Usage: b3_l1_v7_bench.py <home> <out_dir> [threads] [seeds]
Claim limits: as attempt 5 (L1 receiver-adapter read only, synthetic templates, oracle EXACT span, Linux CPU, not Redmi)."""
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
import b3_l1_v4_bench as V4
import b3_l1_v5_bench as V5
import b3_l1_v6_bench as V6
from v13 import b3bridge as BB

SEED_DATA = 20261301; N = 3000; TASKS = ('escalate', 'apologize')


def main(home, out, threads=4, seeds=5):
    V3.N = N
    home = Path(home); out = Path(out); out.mkdir(parents=True, exist_ok=True); rows = V3.make(SEED_DATA)
    olds = {'attempt3': V3.make(), 'attempt4': V3.make(V4.SEED_DATA), 'attempt5': V3.make(V5.SEED_DATA)}
    olds.update({f'attempt6_{s}': V3.make(s) for s in V6.SEEDS})  # V3.N is 3000 here, a superset of each old 600-row set
    overlap = {f'same_sender_text_as_{k}': sum(r['text'] in {o['text'] for o in v} for r in rows) for k, v in olds.items()}
    b1 = next((home/'models/body').glob('*.gguf')); b2 = next((home/'models/gist').glob('*.gguf')); cache = out/'states.npz'; t = time.time()
    data_sha = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    if cache.exists():
        c = np.load(cache); d = {k: c[k] for k in c.files}
    else:
        Hs, Ms = H2.tokens(home, b1, [r['text'] for r in rows], threads)
        sp, _ = H2.pooled(home, b1, [r['text'] for r in rows], threads)
        rp, lat_p = H2.pooled(home, b2, [r['private'] for r in rows], threads)
        cs, lat_c = H2.pooled(home, b2, [r['cue_span'] for r in rows], threads)
        d = {'Hs': Hs.astype(np.float16), 'Ms': Ms, 'send_pool': sp, 'recv_private': rp, 'cue_span': cs, 'lat': np.array([lat_p, lat_c])}
        np.savez_compressed(cache, **d)
    Hs = d['Hs'].astype(np.float32); Ms = d['Ms']; emb_s = time.time()-t
    mu, V = H2.pca(d['cue_span'], V3.R*2); exact = (d['cue_span']-mu)@V.T; exact_bytes = float(np.mean([len(r['cue_span'].encode()) for r in rows]))
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    rep = {'kind': 'B3_L1_V7_POWER_FRESH_SEED', 'script_sha256': sha(__file__), 'v5_script_sha256': sha(V5.__file__), 'bridge_sha256': sha(BB.__file__),
           'model_sha256': {'sender': sha(b1), 'receiver': sha(b2)}, 'data_seed': SEED_DATA, 'data_sha256': data_sha, 'n': len(rows), 'overlap': overlap,
           'seeds': seeds, 'states_seconds': round(emb_s, 1), 'label_balance': {k: np.bincount([r[k] for r in rows]).tolist() for k in TASKS},
           'views': {'private': {}}, 'claim_limit': 'as attempt 5: L1 receiver-adapter read only; synthetic templates; EXACT span oracle-selected; Linux CPU cloud, not Redmi; LATENT authority stays 0'}
    lat = []
    for task in TASKS:
        r_, br = V5.run_task(task, rows, d['recv_private'].astype(np.float64), d['send_pool'].astype(np.float64), Hs, Ms, exact, exact_bytes, seeds, lat)
        rep['views']['private'][task] = r_
        print('private', task, json.dumps({c: v['mean'] for c, v in r_['acc'].items()}), 'canon', r_['canon_verdict'], 'strict', r_['strict_verdict'], flush=True)
        if r_['canon_verdict'] == 'PASS':
            br.save(out/f'bridge_private_{task}_B1_TO_B2', 'bench:'+b1.name, 'bench:'+b2.name, {'l1_gate': r_['l1_gates']['attr_words'], 'task': f'private/{task}'})
        (out/'report.json').write_text(json.dumps(rep, indent=1, default=float))
    target = [f'private/{t}' for t, x in rep['views']['private'].items() if x['canon_verdict'] == 'PASS']
    rep['summary'] = {'canon_l1_pass': target, 'strict_scalar_pass': [f'private/{t}' for t, x in rep['views']['private'].items() if x['strict_verdict'] == 'PASS'],
                      'verdict': ('L1 PASS (private view) on '+', '.join(target)) if target else 'L1 FAIL on all target tasks (private view)'}
    rep['seconds'] = round(time.time()-t, 1)
    (out/'report.json').write_text(json.dumps(rep, indent=1, default=float)); print(json.dumps(rep['summary']))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4, int(sys.argv[4]) if len(sys.argv) > 4 else 5)
