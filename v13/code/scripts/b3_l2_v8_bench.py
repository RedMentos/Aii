"""WP-Z4f B3 L2 prefix SHADOW for private/escalate and private/apologize (cloud bench, preregistered).

B3 L1 attempt 7 (bench-results/b3-l1-v7-20261027) replicated the canon L1 PASS on both tasks on two fresh 3000-row seeds. Per
B3-H8 the next allowed experiment is the L2 prefix SHADOW test. This script is scripts/b3_l2_prefix_bench.py (WP-Z4b, action)
transplanted to the attempt-7 recipe, changing only:
  - data: V3.make(20261301), N = 3000 rows (600 test rows per split), the staged attempt-7 states (states.npz);
  - bridge: attempt-7 recipe (V5.train_bridge with recv_cond + refit_readout, aux U/F, 60/20/20 splits, 5 seeds), retrained per seed;
  - tasks escalate and apologize (yes/no), text baselines SYMBOLIC = 'Suggested answer: <yes|no>.' and SYMBOLIC_ATTR as in L1;
  - only the PCA_ALIGN variant (EXACT_ALIGN was exploratory and never passed); same calibration, same readout, same gate.
Message z[K=4, r=8] -> PCA_ALIGN into the receiver's native input-embedding space -> calibration -> 4 prefix slots (llama.cpp
batch.embd, frozen Qwen3.5-0.8B Q4_0) -> mean of the receiver's final states over its OWN private-view tokens -> L1 NO_MESSAGE readout.
Usage: b3_l2_v8_bench.py <work_dir> <states.npz> <model.gguf> <runner_binary> <backend_dir> <out_dir> [threads] [seeds]
Preregistration: docs/proofs/b3-l2-v8-20261029/PREREG.md. Claim limits: synthetic templates, frozen bodies, Linux CPU, not Redmi,
LATENT authority 0, runtime unchanged."""
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import b3_h2_bench as H2
import b3_l1_v3_bench as V3
import b3_l1_v5_bench as V5
import b3_l2_prefix_bench as L2
from v13 import b3bridge as BB

DATA_SEED = 20261301; N = 3000; TASKS = ('escalate', 'apologize'); K = L2.K; R = L2.R; PCA_RECV = H2.PCA_RECV
SYM_TEXT = 'Suggested answer: {}.'; ATTR_TEXT = L2.ATTR_TEXT


def one_seed(task, seed, rows, y, k, topic, T, recv, send_pool, Hs, Ms, run, E, S_off, S_exact, tok_shared, priv, work, scramble):
    """All channels for one (task, seed); returns a plain dict (saved as checkpoint)."""
    n = len(rows); g = np.random.default_rng(seed); idx = g.permutation(n); tr, va, te = idx[:n*3//5], idx[n*3//5:n*4//5], idx[n*4//5:]
    U = T[:, 0]; F = T[:, 1]
    mu, V = H2.pca(recv[tr], PCA_RECV); Xr = (recv-mu)@V.T; Xr_tr, Xr_va, Xr_te = H2.std(Xr[tr], Xr[va], Xr[te])
    Wn, bn = H2.sel_head(Xr_tr, y[tr], Xr_va, y[va], k); A = (T-T[tr].mean(0))/T[tr].std(0)
    br, _ = V5.train_bridge(Hs, Ms, Xr_tr, Xr_va, y, tr, va, k, (Wn, bn), seed, A, recv_cond=Xr.shape[1])
    br.refit_readout(Hs[tr], Ms[tr], Xr_tr, y[tr], Xr_va, Hs[va], Ms[va], y[va])
    l1 = float((br.logits(Hs[te], Ms[te], Xr_te).argmax(1) == y[te]).mean()); Z = BB.to_bf16(br.encode(Hs, Ms))
    smu, SV = H2.pca(send_pool[tr], PCA_RECV); Xs = (send_pool-smu)@SV.T; Xs_tr, Xs_va, Xs_all = H2.std(Xs[tr], Xs[va], Xs)
    Ws, bs = H2.sel_head(Xs_tr, y[tr], Xs_va, y[va], k); sym = H2.probs(Ws, bs, Xs_all).argmax(1); lv = []
    for v in (U, F):
        l_ = V3.tertile(v, tr); Wa, ba = H2.sel_head(Xs_tr, l_[tr], Xs_va, l_[va], 3); lv.append(H2.probs(Wa, ba, Xs_all).argmax(1))
    sym_t = [SYM_TEXT.format(V3.YESNO[i]) for i in sym]; att_t = [ATTR_TEXT.format(V3.LEVEL[a], V3.LEVEL[b]) for a, b in zip(*lv)]
    ts, ta = run.tokenize(sym_t), run.tokenize(att_t)
    S_sym = run.run([(E[t], p) for t, p in zip(ts, priv)]); S_att = run.run([(E[t], p) for t, p in zip(ta, priv)])
    acc = {}
    for name, S in (('PREFIX_OFF', S_off), ('EXACT', S_exact), ('SYMBOLIC', S_sym), ('SYMBOLIC_ATTR', S_att)):
        acc[name] = L2.acc_of(L2.readout(S, y, tr, va, te, k), S[te], y[te])
    ns = L2.native_stats(E, [tok_shared[i] for i in tr]); fo = L2.readout(S_off, topic, tr, va, te, 3); a_off = L2.acc_of(fo, S_off[te], topic[te])
    P, al = L2.pca_align(Z, ns, tr); S = run.run([(P[i], priv[i]) for i in range(n)]); f = L2.readout(S, y, tr, va, te, k)
    acc['PREFIX'] = L2.acc_of(f, S[te], y[te])
    perm = g.permutation(len(te)); S_sh = run.run([(P[te][perm][i], priv[j]) for i, j in enumerate(te)]); acc['PREFIX_SHUFFLED'] = L2.acc_of(f, S_sh, y[te])
    Dv = P[te]-ns['mu']; rz = g.normal(size=Dv.shape)*ns['dim_std']; rz *= np.linalg.norm(Dv, axis=2, keepdims=True)/np.linalg.norm(rz, axis=2, keepdims=True)
    S_rd = run.run([(ns['mu']+rz[i], priv[j]) for i, j in enumerate(te)]); acc['PREFIX_RANDOM'] = L2.acc_of(f, S_rd, y[te])
    ft = L2.readout(S, topic, tr, va, te, 3); out = {'acc': acc, 'l1_latent': l1, 'role_drop': a_off-L2.acc_of(ft, S[te], topic[te]),
        'role_off_head_on_prefix': L2.acc_of(fo, S[te], topic[te]), 'drift_cos': float(np.mean(np.sum(S[te]*S_off[te], 1))),
        'packet': L2.packet(P, ns, tr, al['geometry_error']), 'align': al, 'full_readout_prefix': L2.acc_of(L2.readout_full(S, y, tr, va, te, k), S[te], y[te]),
        'full_readout_symbolic': L2.acc_of(L2.readout_full(S_sym, y, tr, va, te, k), S_sym[te], y[te])}
    if seed == 0:
        again = run.run([(P[i], priv[i]) for i in te[:8]]); out['reproducible'] = bool(np.array_equal(again, S[te[:8]]))
    return out


def main(work, states, model, binary, backend_dir, out, threads=4, seeds=5):
    import os
    work = Path(work); out = Path(out); work.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    scramble = os.environ.get('B3V8_SMOKE') == '1'  # plumbing smoke on SCRAMBLED labels (numbers meaningless)
    V3.N = N; rows = V3.make(DATA_SEED); c = np.load(states); d = {kk: c[kk] for kk in c.files}; Hs = d['Hs'].astype(np.float32); Ms = d['Ms']
    recv = d['recv_private'].astype(np.float64); send_pool = d['send_pool'].astype(np.float64); n = len(rows)
    run = L2.Runner(binary, model, backend_dir, work, threads); E = L2.token_embd(model); priv = [r['private'] for r in rows]
    tok_shared = run.tokenize([r['shared'] for r in rows]); tok_cue = run.tokenize([r['cue_span'] for r in rows])
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    cache = work/'channels.npz'
    if cache.exists(): z = np.load(cache); S_off, S_exact = z['off'], z['exact']
    else:
        S_off = run.run([(np.zeros((0, 1024)), t) for t in priv]); S_exact = run.run([(E[tc], t) for tc, t in zip(tok_cue, priv)]); np.savez(cache, off=S_off, exact=S_exact)
    rep = {'kind': 'B3_L2_V8_PREFIX_SHADOW_PRIVATE', 'script_sha256': sha(__file__), 'l2_script_sha256': sha(L2.__file__), 'bridge_sha256': sha(BB.__file__),
           'runner_source_sha256': sha(Path(__file__).parent/'native/b3_prefix_embd.cpp'), 'runner_binary_sha256': sha(binary), 'receiver_sha256': sha(model),
           'states_sha256': sha(states), 'data_seed': DATA_SEED, 'n': n, 'K': K, 'r': R, 'seeds': seeds, 'smoke_scrambled_labels': scramble,
           'runner_check_prefix_off_vs_l1_cache_max_rel_l2': float(np.max(np.linalg.norm(S_off-recv/np.linalg.norm(recv, axis=1, keepdims=True), axis=1))),
           'claim_limit': 'L2 prefix SHADOW on synthetic private/escalate, private/apologize; frozen B1/B2; Linux CPU cloud, not Redmi; LATENT authority 0; runtime unchanged', 'tasks': {}}
    U = np.array([r['U'] for r in rows], float); F = np.array([r['F'] for r in rows], float); T = np.c_[U, F]; topic = np.array([r['topic'] for r in rows])
    l1_ref = json.loads((Path(__file__).resolve().parents[2]/'bench-results/b3-l1-v7-20261027/seed20261301/report.json').read_text())['views']['private']
    bytes_base = {'PREFIX': K*R*2, 'PREFIX_OFF': 0, 'PREFIX_SHUFFLED': K*R*2, 'PREFIX_RANDOM': K*R*2, 'EXACT': float(np.mean([len(r['cue_span'].encode()) for r in rows])),
                  'SYMBOLIC': float(np.mean([len(w) for w in V3.YESNO])), 'SYMBOLIC_ATTR': float(np.mean([len(f'urgency {a}, frustration {b}') for a in V3.LEVEL for b in V3.LEVEL]))}
    for task in TASKS:
        y = np.array([r[task] for r in rows]); k = int(y.max())+1
        if scramble: y = np.random.default_rng(1).permutation(y)
        res = []
        for seed in range(seeds):
            ck = work/f'ckpt_{task}_{seed}.json'
            if ck.exists(): res.append(json.loads(ck.read_text())); continue
            r_ = one_seed(task, seed, rows, y, k, topic, T, recv, send_pool, Hs, Ms, run, E, S_off, S_exact, tok_shared, priv, work, scramble)
            ck.write_text(json.dumps(r_, default=float)); res.append(r_)
            print(task, seed, {c_: round(v_, 3) for c_, v_ in r_['acc'].items()}, 'L1', round(r_['l1_latent'], 3), flush=True)
        names = list(res[0]['acc']); acc = {c_: [r_['acc'][c_] for r_ in res] for c_ in names}
        nr = float(np.mean([r_['packet']['norm_ratio'] for r_ in res])); rd = float(np.mean([r_['role_drop'] for r_ in res]))
        gate = BB.l2_gate({'acc': acc, 'bytes': bytes_base, 'role_drop': rd, 'norm_ratio': round(nr, 4), 'reproducible': bool(res[0].get('reproducible', False))})
        st = lambda v: {'mean': round(float(np.mean(v)), 4), 'sd': round(float(np.std(v)), 4), 'per_seed': [round(x, 4) for x in v]}
        l1 = [r_['l1_latent'] for r_ in res]; ref = l1_ref[task]['acc']['LATENT']['per_seed'][:seeds]
        rep['tasks'][task] = {'acc': {c_: st(v_) for c_, v_ in acc.items()}, 'L1_adapter_read': st(l1), 'l1_reproduction_attempt7': {'identical': [round(x, 4) for x in l1] == ref, 'attempt7': ref},
            'paired_PREFIX_minus_PREFIX_OFF': BB.paired(acc['PREFIX'], acc['PREFIX_OFF']), 'paired_PREFIX_minus_L1': BB.paired(acc['PREFIX'], l1),
            'paired_PREFIX_minus_SYMBOLIC_ATTR': BB.paired(acc['PREFIX'], acc['SYMBOLIC_ATTR']),
            'role_drop': round(rd, 4), 'drift_cos_prefixed_vs_off': st([r_['drift_cos'] for r_ in res]), 'topic_acc_prefix_off_head_on_prefixed_states': st([r_['role_off_head_on_prefix'] for r_ in res]),
            'exploratory_full_readout': {'PREFIX': st([r_['full_readout_prefix'] for r_ in res]), 'SYMBOLIC': st([r_['full_readout_symbolic'] for r_ in res])},
            'calibration_packet_per_seed': [r_['packet'] for r_ in res], 'l2_gate': gate, 'verdict': gate['verdict']}
        print(task, json.dumps({c_: round(float(np.mean(v_)), 4) for c_, v_ in acc.items()}), 'L1', round(float(np.mean(l1)), 4), 'gate', gate['verdict'], flush=True)
    target = [f'private/{t}' for t, x in rep['tasks'].items() if x['verdict'] == 'PASS']
    rep['summary'] = {'l2_pass': target, 'verdict': ('L2 PASS (private view) on '+', '.join(target)) if target else 'L2 FAIL on all target tasks',
                      'consequence': 'L3 tiny-residual SHADOW test allowed for the passing tasks (new prereg, replication first); LATENT authority stays 0; runtime unchanged' if target
                      else 'B3_LATENT stays at L1_shadow; L3 locked; LATENT authority 0'}
    rep['seconds'] = round(time.time()-t0, 1); rep['runner_calls'] = run.calls
    (out/'report.json').write_text(json.dumps(rep, indent=1, default=float)); print(json.dumps(rep['summary']))


if __name__ == '__main__':
    a = sys.argv[1:]; main(*a[:6], int(a[6]) if len(a) > 6 else 4, int(a[7]) if len(a) > 7 else 5)
