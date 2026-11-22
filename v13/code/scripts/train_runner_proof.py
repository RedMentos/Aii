#!/usr/bin/env python3
"""G-TRAIN-RUNNER-PROOF-001 (Blueprint §89 TrainRunnerProof) for the parameter path that actually trains on the phone:
the isolated NumPy route-head worker (v13.learning_worker, STEP5 external route head; no LLM weights).

Part 1 (real path): tests/integration_learning.py on a disposable brain with the pinned native Needle embeddings:
  shadow does not commit, explicit approval activates, restart uses the head, rollback removes it, integrity.
Part 2 (runner fuzz, same worker code, class-structured vectors of the real embedding width):
  gradient_reference_test   worker finite-difference check (< 1e-6)
  deterministic_seed_test   two runs -> byte-identical candidate.npz and identical metrics weights
  cancel_during_forward / cancel_during_backward / crash_during_checkpoint
                            SIGKILL at spread-out times while the worker runs (optimizer loop = forward+backward,
                            then np.savez, then atomic metrics.json): either no metrics.json, or metrics.json plus a
                            candidate that loads and equals the uninterrupted reference. A torn checkpoint never counts.
  resume_correctness        j steps, checkpoint, k steps == j+k steps continuous (allclose 1e-12)
  rollback_correctness      from part 1
  retention_suite_before_after  per-class held-out accuracy before/after (worker metric, retention_max_delta)
  step_latency_ms, examples_per_step, battery/thermal start/end, throttle hint (cpufreq), peak RSS
Writes a TrainRunnerProof packet (v13.contracts schema) and TRAIN_RUNNER_PROOF_PASS / _FAIL. Cloud runs are software
evidence (phone_measured=false); only a Termux run on the Redmi counts for the gate's device part.
  python3 scripts/train_runner_proof.py --installed-home ~/v13 --out DIR [--kills 24] [--skip-integration]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import numpy as np  # noqa: E402
from v13.common import atomic_write, dumps, file_hash  # noqa: E402
from v13.resources import device, snapshot  # noqa: E402

CFG = {'learning_steps': 6000, 'learning_rate': .05, 'eligibility_decay': .9, 'max_update_norm': .5, 'retention_max_delta': .1}


def data(dim, n_per=12, seed=7):
    rng = np.random.default_rng(seed); centers = rng.normal(size=(4, dim)); x = []; y = []
    for k in range(4):
        for _ in range(n_per):
            x.append(centers[k]+.6*rng.normal(size=dim)); y.append(k)
    order = rng.permutation(len(y)); x = np.asarray(x)[order]; y = np.asarray(y)[order]
    return x.tolist(), y.tolist()


def request(folder, x, y, cfg, checkpoint=None):
    req = {'config': cfg, 'embeddings': x, 'labels': y, 'scaffold_labels': [0]*len(y)}
    if checkpoint: req['active_checkpoint'] = str(checkpoint)
    p = folder/'request.json'; p.write_text(json.dumps(req)); return p


def worker(folder, req, kill_after=None):
    folder.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(APP))
    proc = subprocess.Popen([sys.executable, '-m', 'v13.learning_worker', str(req), str(folder)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if kill_after is not None:
        try:
            proc.wait(timeout=kill_after)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGKILL)
    proc.wait(); return proc.returncode


def load(folder):
    with np.load(folder/'candidate.npz', allow_pickle=False) as z: return z['route_w'].copy(), z['eligibility'].copy()


def thermal():
    temps = []
    for z in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try: temps.append(int(z.read_text())/1000)
        except (OSError, ValueError): pass
    freq = []
    for c in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq'):
        try: freq.append((int((c/'scaling_cur_freq').read_text()), int((c/'cpuinfo_max_freq').read_text())))
        except (OSError, ValueError): pass
    return {'max_zone_c': max(temps) if temps else None,
            'cpu_freq_ratio_min': round(min(a/b for a, b in freq), 3) if freq else None}


def fuzz(base, dim, kills):
    x, y = data(dim); out = {}
    ref = base/'ref'; t0 = time.monotonic(); rc = worker(ref, request(base, x, y, CFG)); ref_s = time.monotonic()-t0
    m = json.loads((ref/'metrics.json').read_text()); w_ref, tr_ref = load(ref)
    rep = base/'rep'; worker(rep, request(base, x, y, CFG))
    out['reference'] = {'exit': rc, 'seconds': round(ref_s, 3), 'metrics': {k: m[k] for k in ('gradient_check', 'finite_difference_max_error',
                         'deterministic_repeat', 'checkpoint_reload', 'loss_before', 'loss_after', 'held_out', 'retention_pass', 'trainable_parameter_count')}}
    out['gradient_reference_test'] = bool(m['gradient_check'])
    out['deterministic_seed_test'] = bool(m['deterministic_repeat'] and file_hash(ref/'candidate.npz') == file_hash(rep/'candidate.npz'))
    # import time (no optimizer yet) measured separately; kills spread over the optimizer loop (forward+backward are fused in
    # one NumPy objective call per step, so both cancel checks share these kills) plus a dense window at the very end
    # (np.savez + fsync + atomic metrics.json)
    t_imp = time.monotonic(); subprocess.run([sys.executable, '-c', 'import v13.learning_worker'], env=dict(os.environ, PYTHONPATH=str(APP)), check=True)
    t_imp = time.monotonic()-t_imp; loop = max(1e-3, ref_s-t_imp)
    spread = [t_imp+loop*(i+.5)/kills for i in range(kills)] + [t_imp+loop*(.9+.1*(i+.5)/8) for i in range(8)]
    torn = 0; clean = 0; partial_ok = 0; outcomes = []
    for i, t in enumerate(spread):
        f = base/('kill%02d' % i); worker(f, request(base, x, y, CFG), kill_after=t)
        has_m = (f/'metrics.json').exists(); has_c = (f/'candidate.npz').exists(); ok = None
        if has_m:
            try:
                w, tr = load(f); ok = bool(np.array_equal(w, w_ref) and np.array_equal(tr, tr_ref))
            except Exception:
                ok = False
            partial_ok += ok; torn += not ok
        else:
            clean += 1  # nothing a caller would accept (learning.py reads metrics.json first)
        outcomes.append({'kill_after_s': round(t, 4), 'loop_fraction': round((t-t_imp)/loop, 3), 'metrics': has_m, 'candidate_file': has_c, 'complete_and_equal': ok})
    out['kills'] = {'n': len(spread), 'import_s': round(t_imp, 3), 'no_metrics_left': clean, 'complete_equal': partial_ok, 'torn_accepted': torn, 'rows': outcomes}
    inloop = [o for o in outcomes if o['loop_fraction'] < .9]; end = [o for o in outcomes if o['loop_fraction'] >= .9]
    out['cancel_during_forward'] = out['cancel_during_backward'] = bool(inloop) and all(o['complete_and_equal'] is not False for o in inloop)
    out['crash_during_checkpoint'] = bool(end) and torn == 0
    out['note_forward_backward'] = 'forward and backward are one fused NumPy call per step; both checks use the same in-loop kills'
    # resume: j + k == j+k
    j, k = 2500, 3500; a = base/'res_a'; worker(a, request(base, x, y, dict(CFG, learning_steps=j)))
    b = base/'res_b'; worker(b, request(base, x, y, dict(CFG, learning_steps=k), checkpoint=a/'candidate.npz'))
    wb, tb = load(b)
    out['resume_correctness'] = bool(np.allclose(wb, w_ref, atol=1e-12, rtol=0) and np.allclose(tb, tr_ref, atol=1e-12, rtol=0))
    held = m['held_out'] or {}
    out['retention_suite_before_after'] = {'per_class': held.get('per_class'), 'retention_pass': m['retention_pass']}
    out['step_latency_ms'] = round(1000*ref_s/CFG['learning_steps'], 3); out['examples_per_step'] = int(.75*len(y))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--installed-home'); ap.add_argument('--out', required=True)
    ap.add_argument('--kills', type=int, default=24); ap.add_argument('--skip-integration', action='store_true'); ap.add_argument('--dim', type=int, default=0)
    a = ap.parse_args(argv); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    s0 = snapshot(out); th0 = thermal(); t0 = time.monotonic(); report = {'schema': 'V13_TRAIN_RUNNER_PROOF_V1', 'device': device()}
    integ = None
    if not a.skip_integration:
        if not a.installed_home: ap.error('--installed-home required unless --skip-integration')
        ip = out/'integration_learning.json'
        rc = subprocess.run([sys.executable, str(APP/'tests/integration_learning.py'), '--installed-home', str(Path(a.installed_home).expanduser()),
                             '--out', str(ip)], env=dict(os.environ, PYTHONPATH=str(APP)), stdin=subprocess.DEVNULL).returncode
        integ = json.loads(ip.read_text()) if ip.exists() else {'error': 'no report', 'exit': rc}
    dim = a.dim or ((integ or {}).get('manifest', {}).get('metrics', {}).get('embedding_dim') or 64)
    with tempfile.TemporaryDirectory(prefix='v13-trp-') as tmp:
        fz = fuzz(Path(tmp), int(dim), a.kills)
    s1 = snapshot(out); th1 = thermal()
    ichecks = (integ or {}).get('checks') or {}
    checks = {'gradient_reference_test': fz['gradient_reference_test'], 'deterministic_seed_test': fz['deterministic_seed_test'],
              'cancel_during_forward': fz['cancel_during_forward'], 'cancel_during_backward': fz['cancel_during_backward'],
              'crash_during_checkpoint': fz['crash_during_checkpoint'], 'resume_correctness': fz['resume_correctness'],
              'rollback_correctness': bool(ichecks.get('rollback')) if integ else None,
              'real_path_shadow_approve_restart': bool(ichecks) and all(ichecks.get(k) for k in ('shadow_does_not_commit', 'explicit_activation', 'restart_uses_head', 'integrity')) if integ else None,
              'retention_suite_before_after': bool(fz['retention_suite_before_after']['retention_pass'])}
    required = [k for k, v in checks.items() if v is not None]
    verdict = 'TRAIN_RUNNER_PROOF_PASS' if all(checks[k] for k in required) and integ is not None else 'TRAIN_RUNNER_PROOF_FAIL' if not all(checks[k] for k in required) else 'TRAIN_RUNNER_PROOF_PARTIAL_NO_INTEGRATION'
    phone = bool(device().get('android'))
    packet = {'trainable_parameter_count': int(fz['reference']['metrics']['trainable_parameter_count']),
              'runner_revision': 'learning_worker@' + file_hash(APP/'v13/learning_worker.py')[:16], 'device': device(), 'checks': checks}
    report.update(verdict=verdict, packet=packet, integration=integ, fuzz=fz, phone_measured=phone,
                  measurements={'step_latency_ms': fz['step_latency_ms'], 'examples_per_step': fz['examples_per_step'],
                                'battery_delta_percent': (s0['battery_percent'] or 0)-(s1['battery_percent'] or 0) if s0['battery_percent'] is not None and s1['battery_percent'] is not None else None,
                                'battery_temp_start_c': s0['battery_temperature_c'], 'battery_temp_end_c': s1['battery_temperature_c'],
                                'thermal_start': th0, 'thermal_end': th1, 'throttle_hint': (th1['cpu_freq_ratio_min'] or 1) < .6 if th1['cpu_freq_ratio_min'] else None,
                                'energy_delta': 'battery percent only; no energy counter readable without root' if phone else None,
                                'peak_rss_mb': round(s1['own_peak_rss_bytes']/2**20, 1), 'seconds': round(time.monotonic()-t0, 1)},
                  scope='STEP5 external route head (NumPy) only; not body/LLM weights (those have no phone train runner)',
                  canonical_gate_pass=False)
    atomic_write(out/'train-runner-proof.json', dumps(report)); print(json.dumps({'verdict': verdict, 'checks': checks}, indent=1))
    return 0 if verdict == 'TRAIN_RUNNER_PROOF_PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
