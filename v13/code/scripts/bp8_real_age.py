#!/usr/bin/env python3
"""WP-BP8b: Age reopening with an independent noise signal on REAL weight learning (G-AGE-REOPEN-001, real part).
Real body B1 (LFM2.5-1.2B) LoRA in windows (v13/lora_session.py); step size = base lr x plasticity from the real AgeControl (or a fixed value).
Stream per seed: learn (facts A true) -> noisy (A true + facts B with freshly randomised WRONG answers each window) -> shift (user corrects A: new answers).
After each window: competence on the CURRENT truth of A (teacher-forced token accuracy, 2 interleaved halves -> independent noise signal).
Arms: boot | noise_mad (noise_aware, no signal) | noise_indep (noise_aware + signal) | fixed_permissive (1.0) | fixed_conservative (0.45).
Usage: python3 scripts/bp8_real_age.py --master DIR --out DIR --seed 1 [--arms ...] [--windows 6] [--steps-per-window 2] [--smoke]
"""
import argparse, json, sys, tempfile, time, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

ARMS = ('boot', 'noise_mad', 'noise_indep', 'fixed_permissive', 'fixed_conservative')
FIXED = {'fixed_permissive': 1.0, 'fixed_conservative': 0.45}

def build_stream(pool, seed, n_a=6, n_b=6):
    """Returns dict: A facts (q, true answer, paraphrase), B questions, new answers for A (shift), pool of wrong answers."""
    rng = np.random.default_rng(seed); idx = rng.permutation(len(pool)).tolist()
    A = idx[:n_a]; B = idx[n_a:n_a + n_b]; C = idx[n_a + n_b:n_a + n_b + n_a]
    return {'A': [(pool[i][0], pool[i][1], pool[i][3][0]) for i in A], 'A_new': [(pool[i][0], pool[j][1], pool[i][3][0]) for i, j in zip(A, C)],
            'B': [pool[i][0] for i in B], 'wrong_pool': [pool[i][1] for i in idx[n_a + n_b:]]}

def probes_for(facts):
    """facts: list of (q, answer, paraphrase) -> interleaved probes (question, answer), (paraphrase, answer)."""
    return [p for q, a, para in facts for p in ((q, a), (para, a))]

def window_items(phase, stream, rng, window):
    A = [{'memory_id': 'a%d' % i, 'prompt': q, 'target': a} for i, (q, a, _) in enumerate(stream['A'])]
    if phase == 'learn': return A
    if phase == 'noisy':
        wrong = rng.permutation(len(stream['wrong_pool'])).tolist()
        return A + [{'memory_id': 'b%d_%d' % (i, window), 'prompt': q, 'target': stream['wrong_pool'][wrong[i % len(wrong)]]} for i, q in enumerate(stream['B'])]
    return [{'memory_id': 'a%d' % i, 'prompt': q, 'target': a} for i, (q, a, _) in enumerate(stream['A_new'])]

def summarize(trace, windows):
    """trace: list of (phase, err, plasticity). Returns mean error per phase and windows needed in shift until err < .2 (windows+1 = never)."""
    by = {p: [e for ph, e, _ in trace if ph == p] for p in ('learn', 'noisy', 'shift')}
    rec = next((k + 1 for k, e in enumerate(by['shift']) if e < .2), windows + 1)
    return {'learn_err': float(np.mean(by['learn'])), 'noisy_err': float(np.mean(by['noisy'])), 'shift_err': float(np.mean(by['shift'])),
            'recovery_windows': rec, 'mean_plasticity': {p: float(np.mean([pl for ph, _, pl in trace if ph == p])) for p in by}}

def run_arm(arm, S, stream, a):
    from v13 import ablation99 as A99
    from v13.age import AgeControl
    import bj1_body_jepa as J
    rng = np.random.default_rng(a.seed * 7 + 1)
    ctl = None; tmp = None
    if arm in ('boot', 'noise_mad', 'noise_indep'):
        tmp = tempfile.TemporaryDirectory(); store, cfg = A99._store(Path(tmp.name)); cfg['user_stage_cap'] = 5
        cfg['age_plasticity_policy'] = 'noise_aware' if arm != 'boot' else 'boot'; ctl = AgeControl(store, cfg, build_ceiling=5)
    sess = S(a.master, Path(a.out) / 'work' / ('s%d-%s' % (a.seed, arm)), anchors=J.ANCHORS, cfg={'threads': a.threads, 'lr': a.lr, 'seed': a.seed, 'anchors_per_step': 6})
    trace = []; prev = None; fails = 0; novel = True; w = 0
    for phase in ('learn', 'noisy', 'shift'):
        probes = probes_for(stream['A_new'] if phase == 'shift' else stream['A'])
        for _ in range(a.windows):
            p = ctl.plasticity('language', novel_domain=novel, repeated_errors=fails) if ctl else FIXED[arm]
            items = window_items(phase, stream, rng, w)
            for _s in range(a.steps_per_window): sess.step(items, p)
            comp, nsig = sess.competence(probes); err = 1 - comp
            novel = prev is not None and err > 2 * prev and err > .1
            passed = prev is None or err <= prev * 1.1 + .02; fails = 0 if passed else fails + 1
            if ctl:
                m = {'experience': (w + 1) * a.steps_per_window, 'competence': comp, 'stability': .9, 'retention': comp, 'calibration': .8, 'memory_health': .97,
                     'safe_self_control': .999, 'regression_pass': passed}
                if arm == 'noise_indep': m['noise_signal'] = nsig
                ctl.record('language', m, evidence_id='bp8r-%d-%s' % (w, arm))
            trace.append((phase, err, p)); prev = err; w += 1
            print(json.dumps({'arm': arm, 'window': w, 'phase': phase, 'err': round(err, 4), 'noise_signal': round(nsig, 4), 'plasticity': p}), flush=True)
    if ctl: ctl.s.close()
    res = summarize(trace, a.windows); res['trace'] = [(ph, round(e, 4), p) for ph, e, p in trace]; del sess
    return res

def main():
    import bj1_body_jepa as J
    from v13.lora_session import LoraSession
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True); ap.add_argument('--out', required=True); ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arms', default=','.join(ARMS)); ap.add_argument('--threads', type=int, default=4); ap.add_argument('--windows', type=int, default=6)
    ap.add_argument('--steps-per-window', type=int, default=2); ap.add_argument('--lr', type=float, default=1e-3); ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    if a.smoke: a.windows = 2; a.steps_per_window = 1
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); stream = build_stream(J.POOL, a.seed)
    rep = {'schema': 'v13-bp8b-real-age-v1', 'seed': a.seed, 'platform': platform.platform(), 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'windows': a.windows, 'steps_per_window': a.steps_per_window, 'lr': a.lr, 'arms': {}}
    path = out / ('bp8b-seed%d.json' % a.seed)
    for arm in a.arms.split(','):
        t = time.monotonic(); rep['arms'][arm] = run_arm(arm, LoraSession, stream, a); rep['arms'][arm]['wall_seconds'] = round(time.monotonic() - t, 1)
        path.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(str(path))

if __name__ == '__main__':
    main()
