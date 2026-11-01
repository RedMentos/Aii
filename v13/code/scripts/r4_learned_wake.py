"""R4 part 2: learned calibrated wake head from paired R4 labels, tested counterfactually on fresh tasks.

Head: logistic regression on the 7 runtime effort signals (v13.effort.signals with the scaffold route), standardized,
L2, plain gradient descent. Label per training task: 1 if always_ab passes and C3 alone fails (waking both bodies
rescues it), else 0. Policy: wake both bodies when p >= .5, otherwise answer with C3 alone.
Counterfactual test: on fresh tasks (different generator seed) C3 alone and always_ab are both run for every task,
so the policy's outcome per task is read from the arm it would have chosen (no extra model run).
  prereg:   r4_learned_wake.py prereg --train R4.json --fresh-seed 11 --out PREREG.json
  evaluate: r4_learned_wake.py evaluate --prereg PREREG.json --fresh FRESH_R4.json --out REPORT.json
Claim limit: generated tasks, regex checks, one fresh seed; turn time is the measured time of the chosen arm."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13 import effort as EF  # noqa: E402
from v13.cognition import scaffold_route  # noqa: E402
import utility_bench2 as U2  # noqa: E402

KEYS = ('novelty', 'uncertainty', 'conflict', 'salience', 'epistemic_risk', 'detail_need', 'gist_need')
DECISION = ('ADOPT_AS_SHADOW_CANDIDATE only if on the fresh tasks the learned policy passes more tasks than C3 alone '
            '(paired, at least 3 net) AND at least as many as the shipped heuristic; otherwise NOT_SUPPORTED. '
            'No runtime change follows from this script either way.')


def features(text):
    sig = EF.signals(text, scaffold_route(text))
    return [float(sig[k]) for k in KEYS]


def by_arm(doc):
    out = {}
    for r in doc['rows']:
        out.setdefault(r['arm'], {})[r['fixture']] = r
    return out


def fit(x, y, l2=1., steps=2000, lr=.1):
    n, d = len(x), len(x[0])
    mu = [sum(r[j] for r in x)/n for j in range(d)]
    sd = [max(1e-6, math.sqrt(sum((r[j]-mu[j])**2 for r in x)/n)) for j in range(d)]
    z = [[(r[j]-mu[j])/sd[j] for j in range(d)] for r in x]
    w, b = [0.]*d, math.log((sum(y)+.5)/(n-sum(y)+.5))
    for _ in range(steps):
        gw, gb = [l2*wj/n for wj in w], 0.
        for zi, yi in zip(z, y):
            p = 1/(1+math.exp(-(b+sum(a*c for a, c in zip(w, zi)))))
            for j in range(d):
                gw[j] += (p-yi)*zi[j]/n
            gb += (p-yi)/n
        w = [wj-lr*g for wj, g in zip(w, gw)]; b -= lr*gb
    return {'keys': list(KEYS), 'mean': mu, 'std': sd, 'w': w, 'b': b, 'threshold': .5, 'l2': l2, 'steps': steps, 'lr': lr}


def prob(head, x):
    z = [(v-m)/s for v, m, s in zip(x, head['mean'], head['std'])]
    return 1/(1+math.exp(-(head['b']+sum(a*c for a, c in zip(head['w'], z)))))


def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def prereg(train, fresh_seed, out):
    doc = json.loads(Path(train).read_text()); arms = by_arm(doc); c, ab = arms['c_native_only'], arms['always_ab']
    fx = {f[0]: f for f in U2.tasks(doc.get('task_seed', 7))}
    ids = [f for f in doc['fixtures'] if f in c and f in ab]
    x = [features(fx[f][1]) for f in ids]; y = [int(ab[f]['pass'] and not c[f]['pass']) for f in ids]
    head = fit(x, y)
    train_policy = sum((ab if prob(head, xi) >= .5 else c)[f]['pass'] for f, xi in zip(ids, x))
    fresh = U2.tasks(fresh_seed)
    reg = {'schema': 'v13-r4-learned-wake-prereg-v1', 'train_report_sha256': hashlib.sha256(Path(train).read_bytes()).hexdigest(),
           'train_task_seed': doc.get('task_seed', 7), 'train_n': len(ids), 'train_positives': sum(y),
           'train_policy_pass': train_policy, 'train_c_native_pass': sum(c[f]['pass'] for f in ids),
           'head': head, 'fresh_task_seed': fresh_seed, 'fresh_fixtures_sha256': sha_json([list(f[:2]) for f in fresh]),
           'fresh_arms_required': ['c_native_only', 'always_ab', 'heuristic'], 'decision_rule': DECISION,
           'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path(out).write_text(json.dumps(reg, indent=1)+'\n'); print(json.dumps({k: reg[k] for k in ('train_n', 'train_positives', 'train_policy_pass', 'train_c_native_pass')}))


def sign_p(w, l):
    n = w+l
    return 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(w, l)+1))/2**n)


def evaluate(prereg_path, fresh_path, out):
    reg = json.loads(Path(prereg_path).read_text()); doc = json.loads(Path(fresh_path).read_text())
    if doc.get('task_seed') != reg['fresh_task_seed']:
        raise ValueError('Fresh run uses another task seed than preregistered')
    fx = {f[0]: f for f in U2.tasks(reg['fresh_task_seed'])}
    if sha_json([list(fx[f][:2]) for f in fx]) != reg['fresh_fixtures_sha256']:
        raise ValueError('Fresh fixtures changed')
    arms = by_arm(doc); c, ab, h = (arms[a] for a in reg['fresh_arms_required'])
    ids = [f for f in fx if f in c and f in ab and f in h]
    choice = {f: prob(reg['head'], features(fx[f][1])) >= reg['head']['threshold'] for f in ids}
    learned = {f: (ab if choice[f] else c)[f] for f in ids}
    oracle = sum(c[f]['pass'] or ab[f]['pass'] for f in ids)
    def summary(m):
        return {'pass': sum(m[f]['pass'] for f in ids), 'pass_rate': round(sum(m[f]['pass'] for f in ids)/len(ids), 3),
                'mean_turn_s': round(sum(m[f]['turn_s'] for f in ids)/len(ids), 2)}
    def pair(a, b):
        w = sum(a[f]['pass'] and not b[f]['pass'] for f in ids); l = sum(b[f]['pass'] and not a[f]['pass'] for f in ids)
        return {'first_only': w, 'second_only': l, 'net': w-l, 'sign_test_p': round(sign_p(w, l), 4)}
    res = {'n': len(ids), 'policies': {'c_native_only': summary(c), 'heuristic': summary(h), 'always_ab': summary(ab),
                                       'learned_head': summary(learned) | {'wake_rate': round(sum(choice.values())/len(ids), 3)}},
           'oracle_pass': oracle,
           'paired': {'learned_vs_c_native': pair(learned, c), 'learned_vs_heuristic': pair(learned, h)}}
    lc, lh = res['paired']['learned_vs_c_native'], res['paired']['learned_vs_heuristic']
    res['verdict'] = 'ADOPT_AS_SHADOW_CANDIDATE' if lc['net'] >= 3 and lh['net'] >= 0 else 'NOT_SUPPORTED'
    report = {'schema': 'v13-r4-learned-wake-report-v1', 'prereg_sha256': hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest(),
              'fresh_report_sha256': hashlib.sha256(Path(fresh_path).read_bytes()).hexdigest(), **res,
              'wake_choices': {f: choice[f] for f in ids}, 'phone_measured': False, 'canonical_gate_pass': False}
    Path(out).write_text(json.dumps(report, indent=1)+'\n'); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prereg'); p.add_argument('--train', required=True); p.add_argument('--fresh-seed', type=int, required=True); p.add_argument('--out', required=True)
    e = sub.add_parser('evaluate'); e.add_argument('--prereg', required=True); e.add_argument('--fresh', required=True); e.add_argument('--out', required=True)
    a = ap.parse_args()
    prereg(a.train, a.fresh_seed, a.out) if a.cmd == 'prereg' else evaluate(a.prereg, a.fresh, a.out)
