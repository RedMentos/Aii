#!/usr/bin/env python3
"""WP-Z12c: slot-wise World-JEPA (v13/world_jepa_slots.py) on the Z12b file world, real counterfactuals, real world process.

Data collection is Z12b's (scripts/z12b_world_jepa.py: same world, same actions, same held-out (op, slot) choice per seed).
New: the model, compositional held-out retrieval as a criterion, confidence with the model's own typical error, and an
attribution control that gets no action information anywhere (Z12b's per-operation threshold handed it the action).
Criteria C1-C7: docs/proofs/continuation-20261027/z12c-slot-world-jepa/PREREG.md.

  z12c_slot_world_jepa.py <out.json> [--seeds 201,202,203] [--train 4000] [--cf 150] [--attr 300] [--steps 3000]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile
import time
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location('z12b', Path(__file__).with_name('z12b_world_jepa.py'))
z12b = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(z12b)
ACTIONS, OPS, SLOTS, NOOP = z12b.ACTIONS, z12b.OPS, z12b.SLOTS, z12b.NOOP
UNTOUCHED = len(OPS)
PCT = 99   # attribution thresholds: percentile of the model's own errors on clean validation transitions


def slot_action(i):
    """(SLOTS, ops+1): op one-hot on the slot the action touches, UNTOUCHED everywhere else (noop: everywhere)."""
    v = np.zeros((SLOTS, len(OPS)+1)); v[:, UNTOUCHED] = 1.; o, s = ACTIONS[i]
    if s is not None: v[s] = 0.; v[s, OPS.index(o)] = 1.
    return v


def untouched_all(n): v = np.zeros((n, SLOTS, len(OPS)+1)); v[:, :, UNTOUCHED] = 1.; return v


def cf_eval(m, cf, mode, *, calibrated=True):
    """Retrieve counterfactuals; ablation controls have no calibrated confidence.

    calibrated=False is for deliberately uncalibrated NO_ACTION/SHUFFLED_ACTION
    controls only: their predictions and errors are measured, but they must
    never claim MODEL_SIMULATION authority or synthesize error calibration.
    """
    recs = []
    for st in cf:
        A = np.array([slot_action(c['a']) for c in st['cands']]); A = untouched_all(len(A)) if mode == 'zero' else A
        X = np.repeat(st['x'][None], len(A), 0); p, _ = m.predict(X, A)
        X2 = np.array([c['x2'] for c in st['cands']]); zt = m.latent(X2)
        if calibrated:
            conf, lab = m.confidence(X, A)
        else:
            conf = np.zeros(len(A))
            lab = ['SIMULATION_UNCERTAIN'] * len(A)
        err = m.slot_errors(X, A, X2).mean(1)
        P, T = p.reshape(len(A), -1), zt.reshape(len(A), -1)
        for k, c in enumerate(st['cands']):
            j = int(np.argmin(((T-P[k])**2).sum(1)))
            recs.append({'held': c['held'], 'noop': c['a'] == NOOP, 'ok': st['cands'][j]['snap'] == c['snap'],
                         'err': float(err[k]), 'conf': float(conf[k]), 'label': lab[k]})
    return recs


def mono_cf(m, cf):
    """Z12b monolithic model on the same data (information only)."""
    recs = []
    for st in cf:
        A = np.array([z12b.onehot(c['a']) for c in st['cands']]); X = np.repeat(st['x'][None], len(A), 0)
        p, _ = m.predict(X, A); zt = m.latent(np.array([c['x2'] for c in st['cands']]))
        for k, c in enumerate(st['cands']):
            j = int(np.argmin(((zt-p[k])**2).sum(1))); recs.append({'held': c['held'], 'ok': st['cands'][j]['snap'] == c['snap']})
    return recs


def thresholds(m, val):
    """JEPA: per operation for the touched slot, one for the worst untouched slot. Control: one for the worst slot."""
    A = np.array([slot_action(r['a']) for r in val]); X = np.array([r['x'] for r in val]); X2 = np.array([r['x2'] for r in val])
    e = m.slot_errors(X, A, X2); cls = A.argmax(2); unt = np.where(cls == UNTOUCHED, e, -np.inf).max(1)
    th = {'untouched': float(np.percentile(unt, PCT))}
    for j, o in enumerate(OPS): th[o] = float(np.percentile(e[cls == j], PCT)) if (cls == j).any() else float('inf')
    return th


def threshold_control(m0, val):
    X = np.array([r['x'] for r in val]); X2 = np.array([r['x2'] for r in val])
    return float(np.percentile(m0.slot_errors(X, untouched_all(len(X)), X2).max(1), PCT))


def attr_eval(rows, decide):
    res = {'own_only': [], 'world_only': [], 'both': [], 'none': []}
    for r, cls in zip(rows, decide):
        if r['ambiguous']: continue
        k = ('both' if r['world_changed'] else 'own_only') if r['a'] != NOOP else ('world_only' if r['world_changed'] else 'none')
        res[k].append(cls)
    rate = lambda k, c: round(sum(x == c for x in res[k])/max(1, len(res[k])), 4)
    out = {'n': {k: len(v) for k, v in res.items()}, 'own_only_self': rate('own_only', 'SELF'), 'world_only_world': rate('world_only', 'WORLD_INVOLVED'),
           'both_world': rate('both', 'WORLD_INVOLVED'), 'none_self': rate('none', 'SELF')}
    out['balanced'] = round((out['own_only_self']+out['world_only_world'])/2, 4); return out


def attr_jepa(m, rows, th):
    A = np.array([slot_action(r['a']) for r in rows]); e = m.slot_errors(np.array([r['x'] for r in rows]), A, np.array([r['x2'] for r in rows]))
    cls = A.argmax(2); out = []
    for ei, ci in zip(e, cls):
        ok = all(d <= (th['untouched'] if c == UNTOUCHED else th[OPS[c]]) for d, c in zip(ei, ci))
        out.append('SELF' if ok else 'WORLD_INVOLVED')
    return out


def attr_control(m0, rows, th0):
    e = m0.slot_errors(np.array([r['x'] for r in rows]), untouched_all(len(rows)), np.array([r['x2'] for r in rows])).max(1)
    return ['SELF' if d <= th0 else 'WORLD_INVOLVED' for d in e]


def run_seed(seed, args):
    from v13.world_jepa import WorldJEPA
    from v13.world_jepa_slots import SlotWorldJEPA
    work = Path(tempfile.mkdtemp(prefix='z12c-%d-' % seed)); rng = random.Random(seed)
    held = set(rng.sample(range(NOOP), 4))
    t = time.time(); train = z12b.collect_train(work, seed, args.train, held)
    cf = z12b.collect_cf(work, seed, args.cf, held); attr = z12b.collect_attr(work, seed, args.attr, held); t_collect = time.time()-t
    nv = len(train)//10; fit, val = train[:-nv], train[-nv:]; val_clean = [r for r in val if not r['world']]
    X = np.array([r['x'] for r in fit]); A = np.array([slot_action(r['a']) for r in fit]); X2 = np.array([r['x2'] for r in fit])
    Xv = np.array([r['x'] for r in val_clean]); Av = np.array([slot_action(r['a']) for r in val_clean]); X2v = np.array([r['x2'] for r in val_clean])
    perm = np.random.default_rng(seed).permutation(len(A))
    t = time.time()
    m = SlotWorldJEPA(SLOTS, seed=seed).fit(X, A, X2, steps=args.steps).calibrate(Xv, Av, X2v)
    m0 = SlotWorldJEPA(SLOTS, seed=seed, ensemble=1).fit(X, untouched_all(len(A)), X2, steps=args.steps)
    ms = SlotWorldJEPA(SLOTS, seed=seed, ensemble=1).fit(X, A[perm], X2, steps=args.steps)
    t_fit = time.time()-t
    mono = WorldJEPA(seed=seed, ensemble=1).fit(X, np.array([z12b.onehot(r['a']) for r in fit]), X2, steps=args.steps)
    rec = cf_eval(m, cf, 'own')
    rec0 = cf_eval(m0, cf, 'zero', calibrated=False)
    recs = cf_eval(ms, cf, 'own', calibrated=False)
    recm = mono_cf(mono, cf)
    cov = lambda rs: [r for r in rs if not r['held']]; hel = lambda rs: [r for r in rs if r['held']]
    acc = lambda rs: round(float(np.mean([r['ok'] for r in rs])), 4) if rs else None
    th = thresholds(m, val_clean); th0 = threshold_control(m0, val_clean)
    per_op = {}
    for o in OPS:
        rs = [r for r, c in zip(rec, [c for st in cf for c in st['cands']]) if ACTIONS[c['a']][0] == o]
        per_op[o] = {'covered': acc(cov(rs)), 'held_out': acc(hel(rs))}
    return {
        'seed': seed, 'held_out_actions': [list(ACTIONS[i]) for i in sorted(held)], 'n_train': len(fit), 'n_val_clean': len(val_clean),
        'seconds_collect': round(t_collect, 1), 'seconds_fit_3_models': round(t_fit, 1), 'history': m.history[-3:],
        'cf_retrieval': {'jepa_covered': acc(cov(rec)), 'jepa_held_out': acc(hel(rec)),
                         'no_action_covered': acc(cov(rec0)), 'no_action_held_out': acc(hel(rec0)),
                         'shuffled_action_covered': acc(cov(recs)), 'shuffled_action_held_out': acc(hel(recs)),
                         'z12b_monolithic_covered_info': acc(cov(recm)), 'z12b_monolithic_held_out_info': acc(hel(recm)),
                         'n_covered': len(cov(rec)), 'n_held_out': len(hel(rec)), 'per_op': per_op},
        'errors': {'covered_mean': round(float(np.mean([r['err'] for r in cov(rec)])), 4), 'held_out_mean': round(float(np.mean([r['err'] for r in hel(rec)])), 4)},
        'confidence': {'covered_mean': round(float(np.mean([r['conf'] for r in cov(rec)])), 4), 'held_out_mean': round(float(np.mean([r['conf'] for r in hel(rec)])), 4),
                       'uncertain_frac': round(float(np.mean([r['label'] == 'SIMULATION_UNCERTAIN' for r in rec])), 4),
                       'op_err': [round(float(v), 4) for v in m.op_err]},
        '_conf_err': [[r['conf'], r['err']] for r in rec],
        'collapse': m.collapse_stats(X2),
        'attribution': {'theta': {k: round(v, 4) for k, v in th.items()}, 'theta_control': round(th0, 4),
                        'jepa': attr_eval(attr, attr_jepa(m, attr, th)), 'no_action': attr_eval(attr, attr_control(m0, attr, th0))},
    }


def criteria(seeds):
    pool = lambda k: float(np.mean([s['cf_retrieval'][k] for s in seeds]))  # equal per-seed n for covered; held-out n varies a little
    ce = [x for s in seeds for x in s['_conf_err']]
    j = {k: float(np.mean([s['attribution']['jepa'][k] for s in seeds])) for k in ('own_only_self', 'world_only_world', 'none_self', 'balanced')}
    c = float(np.mean([s['attribution']['no_action']['balanced'] for s in seeds]))
    rho = z12b.spearman([x[0] for x in ce], [x[1] for x in ce])
    best_ctrl = max(pool('no_action_covered'), pool('shuffled_action_covered'))
    return {
        'C1_cf_retrieval_covered': pool('jepa_covered') >= .80 and all(s['cf_retrieval']['jepa_covered'] >= .70 for s in seeds),
        'C2_cf_retrieval_held_out_combinations': pool('jepa_held_out') >= .70 and pool('jepa_held_out') >= max(pool('no_action_held_out'), pool('shuffled_action_held_out'))+.30,
        'C3_controls_fail': pool('no_action_covered') <= .40 and pool('shuffled_action_covered') <= .40 and pool('jepa_covered')-best_ctrl >= .30,
        'C4_no_collapse': all(s['collapse']['effective_rank'] >= 3 and s['collapse']['min_std'] >= .05 for s in seeds),
        'C5_confidence_tracks_error': rho <= -.30,
        'C6_attribution_jepa': j['own_only_self'] >= .90 and j['world_only_world'] >= .90 and j['none_self'] >= .80,
        'C7_action_free_control_worse': c <= j['balanced']-.20,
    }, {'pooled_cf': {k: round(pool(k), 4) for k in ('jepa_covered', 'jepa_held_out', 'no_action_covered', 'no_action_held_out', 'shuffled_action_covered',
                                                   'shuffled_action_held_out', 'z12b_monolithic_covered_info', 'z12b_monolithic_held_out_info')},
        'spearman_conf_err_all': round(rho, 4), 'attribution_jepa': {k: round(v, 4) for k, v in j.items()}, 'attribution_no_action_balanced': round(c, 4)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out')
    ap.add_argument('--seeds', default='201,202,203'); ap.add_argument('--train', type=int, default=4000)
    ap.add_argument('--cf', type=int, default=150); ap.add_argument('--attr', type=int, default=300); ap.add_argument('--steps', type=int, default=3000)
    args = ap.parse_args()
    seeds = [run_seed(int(s), args) for s in args.seeds.split(',')]
    crit, summary = criteria(seeds)
    for s in seeds: s.pop('_conf_err')
    out = {'kind': 'V13_Z12C_SLOT_WORLD_JEPA', 'prereg': 'docs/proofs/continuation-20261027/z12c-slot-world-jepa/PREREG.md', 'args': vars(args),
           'seeds': seeds, 'summary': summary, 'criteria': crit,
           'verdict': 'Z12C_SLOT_WORLD_JEPA_PASS' if all(crit.values()) else 'Z12C_SLOT_WORLD_JEPA_FAIL',
           'claim_limit': 'small file world with synthetic content on the cloud machine; slots independent (no interaction modelled); '
                          'no phone measurement; SHADOW module, not wired into the runtime'}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False)); print(out['verdict'], json.dumps(summary), json.dumps(crit))


if __name__ == '__main__':
    main()
