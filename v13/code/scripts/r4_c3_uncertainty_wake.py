"""R4 part 3: C3 token uncertainty as wake signal (follow-up to Thread G's R4 parts 1 and 2).

Part 2 found that 6 of the 7 runtime effort signals are constant on the R4 tasks and suggested C3 logit
uncertainty instead. This script re-runs the R4 arm `c_native_only` (same runtime, BENCH_CFG, fresh home)
on the train seed 7 and fresh seed 11 tasks and records the native token log-probabilities of the C3 answer.
The only intervention is a measurement hook inside this process: `n_probs=1` is added to C3's streamed
answer request and `completion_probabilities` are copied from the stream. Greedy decoding is unchanged;
answers are compared byte for byte with the recorded R4 outputs.

Features (frozen): min, mean and 10th-percentile token logprob, share of tokens with p < .5,
min logprob over tokens containing a digit, token count. Selection on seed 7 only: the single feature with
the best AUROC for "C3 alone fails" (lower logprob = more uncertain), threshold maximising the counterfactual
policy pass (wake both bodies when uncertain: read always_ab's recorded outcome; else C3's), ties to fewer
wakes. Seed 11 is evaluated once with the frozen feature/threshold.
  capture   r4_c3_uncertainty_wake.py capture <installed_home> <seed> <out.json>
  prereg    r4_c3_uncertainty_wake.py prereg <capture7.json> <r4_seed7.json> <prereg.json>
  evaluate  r4_c3_uncertainty_wake.py evaluate <prereg.json> <capture11.json> <r4_seed11.json> <report.json>
Claim limit: generated English tasks, regex checks, cloud CPU, one fresh seed; turn time of the chosen arm is the
recorded R4 time; no runtime change follows from this script."""
import hashlib
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
import utility_bench as U  # noqa: E402
import utility_bench2 as U2  # noqa: E402

FEATURES = ('min_logprob', 'mean_logprob', 'p10_logprob', 'share_below_half', 'digit_min_logprob', 'tokens')
# Direction: True = larger value means more uncertain.
UNCERTAIN_HIGH = {'min_logprob': False, 'mean_logprob': False, 'p10_logprob': False, 'share_below_half': True,
                  'digit_min_logprob': False, 'tokens': True}
DECISION = ('SIGNAL_SUPPORTED if on seed 11 the frozen feature has AUROC >= .70 for C3-alone failure and the 95 % '
            'bootstrap lower bound (2000 resamples, seed 11) is > .50. POLICY_SUPPORTED if on seed 11 the frozen '
            'policy passes at least 3 net more tasks than C3 alone (paired) AND at least as many as the shipped '
            'heuristic (Thread G rule). Otherwise NOT_SUPPORTED for that part. No runtime change either way.')


class _Capture:
    """Measurement hook: per streamed C3 answer, the token logprobs as llama-server reports them."""
    def __init__(self):
        self.streams = []; self.active = False

    def install(self):
        from v13 import runners as R
        orig_wire, orig_json, cap = R.wire_json, R.json, self

        def wire(v):
            if isinstance(v, dict) and 'prompt' in v:
                cap.active = bool(v.get('stream')) and 'json_schema' not in v
                if cap.active:
                    v = dict(v); v['n_probs'] = 1; cap.streams.append([])
            return orig_wire(v)

        class Shim:
            def __getattr__(self, name):
                return getattr(orig_json, name)

            def loads(self, s, *a, **k):
                d = orig_json.loads(s, *a, **k)
                if isinstance(d, dict) and cap.active and cap.streams and d.get('completion_probabilities'):
                    cap.streams[-1].extend({'token': x.get('token', ''), 'logprob': x['logprob']}
                                           for x in d['completion_probabilities'] if isinstance(x.get('logprob'), (int, float)))
                return d
        R.wire_json = wire; R.json = Shim()


def features(tokens):
    lp = [t['logprob'] for t in tokens]
    if not lp:
        return None
    s = sorted(lp); digits = [t['logprob'] for t in tokens if any(c.isdigit() for c in t['token'])]
    return {'min_logprob': s[0], 'mean_logprob': sum(lp)/len(lp), 'p10_logprob': s[int(.1*(len(s)-1))],
            'share_below_half': sum(v < math.log(.5) for v in lp)/len(lp),
            'digit_min_logprob': min(digits) if digits else 0., 'tokens': float(len(lp))}


def capture(installed, seed, out):
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    installed = Path(installed).resolve(); cap = _Capture(); cap.install(); rows = []
    with tempfile.TemporaryDirectory(prefix='v13-r4c-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home)
        try:
            for fid, text, nums, checks in U2.tasks(seed):
                before = len(cap.streams); r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); end = t0+900
                while not r.idle():
                    if time.monotonic() > end:
                        r.cancel(); break
                    time.sleep(.1)
                a = audit_event(r.store, eid); out_text = a.get('output') or ''; ok, num = U.score(out_text, nums, checks)
                streams = cap.streams[before:]
                # The answer stream is the one whose tokens reproduce the final output; else the last one.
                answer = next((s for s in reversed(streams) if ''.join(t['token'] for t in s).strip() == out_text.strip()), streams[-1] if streams else [])
                rows.append({'fixture': fid, 'pass': all(ok.values()) and all(num.values()), 'turn_s': round(time.monotonic()-t0, 2),
                             'status': a.get('status'), 'streams': len(streams), 'answer_stream_matches_output': ''.join(t['token'] for t in answer).strip() == out_text.strip(),
                             'features': features(answer), 'tokens': answer, 'output': out_text[:400]})
                print(json.dumps({k: rows[-1][k] for k in ('fixture', 'pass', 'turn_s', 'streams', 'answer_stream_matches_output')}), flush=True)
                atomic_write(Path(out), json.dumps({'kind': 'V13_R4_C3_UNCERTAINTY_CAPTURE', 'task_seed': seed, 'bench_cfg': U2.BENCH_CFG, 'rows': rows}, indent=1))
        finally:
            r.close()


def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]; neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    return sum((p > n) + .5*(p == n) for p in pos for n in neg)/(len(pos)*len(neg))


def uncertainty(row, feature):
    v = row['features'][feature] if row['features'] else 0.
    return v if UNCERTAIN_HIGH[feature] else -v


def by_arm(doc):
    out = {}
    for r in doc['rows']:
        out.setdefault(r['arm'], {})[r['fixture']] = r
    return out


def policy(cap_rows, r4, feature, threshold):
    arms = by_arm(r4); res = {'pass': 0, 'woke': 0, 'turn_s': 0.}
    for row in cap_rows:
        wake = uncertainty(row, feature) >= threshold; src = arms['always_ab' if wake else 'c_native_only'][row['fixture']]
        res['pass'] += src['pass']; res['woke'] += wake; res['turn_s'] += src['turn_s']
    res['turn_s'] = round(res['turn_s']/len(cap_rows), 2); return res


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(cap_rows, r4):
    c = by_arm(r4)['c_native_only']
    return {'identical_output': sum(r['output'] == c[r['fixture']]['output'][:400] for r in cap_rows),
            'pass_agrees': sum(r['pass'] == c[r['fixture']]['pass'] for r in cap_rows), 'n': len(cap_rows)}


def prereg(cap7, r4_7, out):
    doc = json.loads(Path(cap7).read_text()); r4 = json.loads(Path(r4_7).read_text()); rows = doc['rows']
    if doc['task_seed'] != 7 or any(r['features'] is None for r in rows):
        raise SystemExit('seed 7 capture incomplete')
    labels = [not r['pass'] for r in rows]
    table = {f: auroc([uncertainty(r, f) for r in rows], labels) for f in FEATURES}
    feature = max(FEATURES, key=lambda f: (table[f] or 0, -FEATURES.index(f)))
    candidates = sorted({uncertainty(r, feature) for r in rows}) + [math.inf]
    best = max(candidates, key=lambda t: (policy(rows, r4, feature, t)['pass'], -policy(rows, r4, feature, t)['woke']))
    body = {'schema': 'v13-r4-c3-uncertainty-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'train_capture_sha256': sha(cap7), 'train_r4_sha256': sha(r4_7), 'identity_vs_r4': identity(rows, r4),
            'train_auroc': table, 'feature': feature, 'threshold': best, 'train_policy': policy(rows, r4, feature, best),
            'train_c_native_pass': sum(r['pass'] for r in rows), 'fresh_task_seed': 11, 'decision_rule': DECISION,
            'script_sha256': sha(__file__)}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, cap11, r4_11, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__):
        raise SystemExit('script changed since preregistration')
    doc = json.loads(Path(cap11).read_text()); r4 = json.loads(Path(r4_11).read_text()); rows = doc['rows']
    if doc['task_seed'] != reg['fresh_task_seed']:
        raise SystemExit('fresh capture uses another task seed')
    f, t = reg['feature'], reg['threshold']; labels = [not r['pass'] for r in rows]; scores = [uncertainty(r, f) for r in rows]
    value = auroc(scores, labels); import random; rng = random.Random(11); boot = []
    for _ in range(2000):
        idx = [rng.randrange(len(rows)) for _ in rows]; v = auroc([scores[i] for i in idx], [labels[i] for i in idx])
        if v is not None:
            boot.append(v)
    boot.sort(); lo = boot[int(.025*len(boot))]; arms = by_arm(r4)
    pol = policy(rows, r4, f, t); c3 = sum(arms['c_native_only'][r['fixture']]['pass'] for r in rows)
    heur = sum(arms['heuristic'][r['fixture']]['pass'] for r in rows); ab = sum(arms['always_ab'][r['fixture']]['pass'] for r in rows)
    net = 0
    for r in rows:
        wake = uncertainty(r, f) >= t; src = arms['always_ab' if wake else 'c_native_only'][r['fixture']]
        net += int(src['pass']) - int(arms['c_native_only'][r['fixture']]['pass'])
    rescuable = [r['fixture'] for r in rows if not arms['c_native_only'][r['fixture']]['pass'] and arms['always_ab'][r['fixture']]['pass']]
    body = {'prereg_sha256': sha(reg_path), 'fresh_capture_sha256': sha(cap11), 'fresh_r4_sha256': sha(r4_11),
            'identity_vs_r4': identity(rows, r4), 'feature': f, 'threshold': t, 'fresh_auroc_all_features': {k: auroc([uncertainty(r, k) for r in rows], labels) for k in FEATURES},
            'fresh_auroc': value, 'fresh_auroc_ci95_low': lo, 'policy': pol, 'policy_net_vs_c3': net,
            'c_native_pass': c3, 'heuristic_pass': heur, 'always_ab_pass': ab, 'rescuable': rescuable,
            'woke_on_rescuable': sum(uncertainty(r, f) >= t for r in rows if r['fixture'] in rescuable),
            'signal_verdict': 'SIGNAL_SUPPORTED' if value is not None and value >= .7 and lo > .5 else 'NOT_SUPPORTED',
            'policy_verdict': 'POLICY_SUPPORTED' if net >= 3 and pol['pass'] >= heur else 'NOT_SUPPORTED',
            'phone_measured': False, 'runtime_changed': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps({k: v for k, v in body.items() if k != 'fresh_auroc_all_features'}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], int(a[2]), a[3])
    elif a[0] == 'prereg':
        prereg(a[1], a[2], a[3])
    else:
        evaluate(a[1], a[2], a[3], a[4])
