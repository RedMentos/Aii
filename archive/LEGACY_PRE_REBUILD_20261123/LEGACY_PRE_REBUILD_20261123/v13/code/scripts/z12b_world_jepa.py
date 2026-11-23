#!/usr/bin/env python3
"""WP-Z12b: action-grounded World-JEPA (v13/world_jepa.py) on real file actions with real counterfactuals.

Own actions are real file operations on 6 slots in a folder (atomic write like the WP-K sandbox, append, remove, noop);
an independent OS process ("world", own seed, own wall clock) writes/appends/removes/blocks files in the same folder.
Counterfactuals are executed for real: the folder is copied once per candidate action and the action runs in the copy.
Ground truth for attribution comes from the world's own log (start/end time, whether its operation changed anything).
Criteria W1-W6: docs/proofs/continuation-20261026/z12b-world-jepa/PREREG.md.

  z12b_world_jepa.py <out.json> [--seeds 101,102,103] [--train 4000] [--cf 150] [--attr 300] [--steps 3000]
  z12b_world_jepa.py --world <schedule.json>
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SLOTS = 6
OPS = ('write_short', 'write_long', 'write_digits', 'append', 'remove')
ACTIONS = [(o, s) for o in OPS for s in range(SLOTS)]+[('noop', None)]
NOOP = len(ACTIONS)-1
WORDS = 'haus baum licht wasser stein wolke garten fenster brief nacht morgen kaffee tisch regen vogel sonne'.split()


def text(kind, rng):
    if kind == 'write_short': return ' '.join(rng.choice(WORDS)+rng.choice('aeiou') for _ in range(rng.randint(2, 4)))
    if kind == 'write_long':
        w = [rng.choice(WORDS) for _ in range(rng.randint(20, 40))]
        return '\n'.join(' '.join(w[i:i+8]) for i in range(0, len(w), 8))
    if kind == 'write_digits': return ' '.join(str(rng.randint(0, 99999)) for _ in range(rng.randint(5, 12)))
    return ' '.join(rng.choice(WORDS) for _ in range(rng.randint(2, 4)))  # append line


def path(root, s): return Path(root)/('slot%d.txt' % s)


def snap_slot(p):
    try:
        if p.is_dir(): return ('D',)
        return ('F', hashlib.sha256(p.read_bytes()).hexdigest()[:16])
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        return ('E',)


def snapshot(root): return tuple(snap_slot(path(root, s)) for s in range(SLOTS))


def features(root):
    out = []
    for s in range(SLOTS):
        p = path(root, s); f = [0.]*10
        try:
            if p.is_dir(): f[1] = 1.
            elif p.exists():
                t = p.read_text(errors='replace'); n = max(1, len(t)); h = hashlib.sha256(t.encode()).digest()
                f[0] = 1.; f[2] = np.log1p(len(t))/8; f[3] = sum(c.islower() for c in t)/n; f[4] = sum(c.isdigit() for c in t)/n
                f[5] = sum(c.isspace() for c in t)/n; f[6] = min(t.count('\n')+1, 10)/5; f[7:10] = [b/127.5-1 for b in h[:3]]
        except OSError:
            pass
        out += f
    return np.array(out)


def do(root, op, s, rng):
    """One real file operation. Returns True if it raised nothing (it may still change nothing)."""
    if op == 'noop': return True
    p = path(root, s)
    try:
        if op.startswith('write'):
            tmp = p.with_name(p.name+'.tmp%d' % os.getpid()); tmp.write_text(text(op, rng)); os.replace(tmp, p)
        elif op == 'append':
            old = p.read_text() if p.exists() else ''
            tmp = p.with_name(p.name+'.tmp%d' % os.getpid()); tmp.write_text(old+('\n' if old else '')+text(op, rng)); os.replace(tmp, p)
        elif op == 'remove':
            if p.is_dir(): p.rmdir()
            else: p.unlink()
        elif op == 'block':
            if p.is_file(): p.unlink()
            p.mkdir()
        return True
    except OSError:
        for t in Path(root).glob(p.name+'.tmp*'): t.unlink(missing_ok=True)
        return False


def onehot(i):
    v = np.zeros(len(OPS)+1+SLOTS); o, s = ACTIONS[i]
    v[(OPS+('noop',)).index(o)] = 1.
    if s is not None: v[len(OPS)+1+s] = 1.
    return v


# -- world process ----------------------------------------------------------------------------------------------
def world_main(schedule_path):
    sch = json.loads(Path(schedule_path).read_text()); rng = random.Random(sch['seed']); log = open(sch['log'], 'a')
    for it in sch['items']:
        delay = sch['t0']+it['at']-time.time()
        if delay > 0: time.sleep(delay)
        p = path(sch['root'], it['slot']); before = snap_slot(p); t0 = time.time()
        ok = do(sch['root'], it['op'], it['slot'], rng); t1 = time.time()
        log.write(json.dumps({'op': it['op'], 'slot': it['slot'], 't0': t0, 't1': t1, 'ok': ok, 'changed': snap_slot(p) != before})+'\n'); log.flush()
    log.close()


def start_world(root, seed, duration, rate, work):
    rng = random.Random(seed); t = .2; items = []
    while t < duration:
        t += rng.expovariate(1/rate)
        items.append({'at': t, 'slot': rng.randrange(SLOTS), 'op': rng.choices(['write_short', 'write_long', 'write_digits', 'append', 'remove', 'block'], [3, 2, 2, 3, 3, 1])[0]})
    sch = {'root': str(root), 'seed': seed+7, 'log': str(work/('world-%d.log' % seed)), 't0': time.time()+.3, 'items': items}
    (work/('world-%d.json' % seed)).write_text(json.dumps(sch))
    proc = subprocess.Popen([sys.executable, __file__, '--world', str(work/('world-%d.json' % seed))])
    return proc, sch


def read_log(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).exists() else []


def touched(log, a, b):
    ev = [e for e in log if e['t0'] <= b and e['t1'] >= a]
    return bool(ev), any(e['changed'] for e in ev)


# -- phases -----------------------------------------------------------------------------------------------------
def collect_train(work, seed, n, held):
    root = work/'live'; root.mkdir(); rng = random.Random(seed); arng = random.Random(seed+1)
    covered = [i for i in range(NOOP) if i not in held]
    proc, sch = start_world(root, seed, duration=n*.02+30, rate=.15, work=work)
    time.sleep(.35); rows = []
    for _ in range(n):
        i = NOOP if arng.random() < 1/8 else arng.choice(covered)
        a0 = time.time(); x = features(root); o, s = ACTIONS[i]; do(root, o, s, rng); x2 = features(root); a1 = time.time()
        rows.append({'x': x, 'a': i, 'x2': x2, 'a0': a0, 'a1': a1}); time.sleep(.005)
    proc.terminate(); proc.wait()
    log = read_log(sch['log'])
    for r in rows: r['world'], r['world_changed'] = touched(log, r['a0'], r['a1'])
    return rows


def collect_cf(work, seed, n_states, held):
    """States from a private walk with the training policy (no world); 6 candidate actions each, executed for real in copies."""
    root = work/'cfwalk'; root.mkdir(); rng = random.Random(seed+2); out = []
    covered = [i for i in range(NOOP) if i not in held]
    for _ in range(30): o, s = ACTIONS[rng.choice(covered)]; do(root, o, s, rng)
    while len(out) < n_states:
        for _ in range(3):
            o, s = ACTIONS[NOOP if rng.random() < 1/8 else rng.choice(covered)]; do(root, o, s, rng)
        x = features(root); cands = rng.sample(range(len(ACTIONS)), 6); outs = []
        for i in cands:
            cp = work/'cf_copy'; shutil.rmtree(cp, ignore_errors=True); shutil.copytree(root, cp)
            o, s = ACTIONS[i]; do(cp, o, s, rng); outs.append({'a': i, 'x2': features(cp), 'snap': snapshot(cp), 'held': i in held})
        out.append({'x': x, 'cands': outs})
    shutil.rmtree(work/'cf_copy', ignore_errors=True)
    return out


def collect_attr(work, seed, n, held):
    root = work/'attr'; root.mkdir(); rng = random.Random(seed+3); arng = random.Random(seed+4)
    covered = [i for i in range(NOOP) if i not in held]
    for _ in range(30): o, s = ACTIONS[rng.choice(covered)]; do(root, o, s, rng)  # same warm-up as the counterfactual walk
    proc, sch = start_world(root, seed+50, duration=n*.06+30, rate=.12, work=work)
    time.sleep(.35); rows = []
    for _ in range(n):
        i = NOOP if arng.random() < 1/3 else arng.choice(covered)
        a0 = time.time(); x = features(root); ax = time.time(); o, s = ACTIONS[i]; do(root, o, s, rng); time.sleep(.04)
        b0 = time.time(); x2 = features(root); a1 = time.time()
        rows.append({'x': x, 'a': i, 'x2': x2, 'a0': a0, 'ax': ax, 'b0': b0, 'a1': a1}); time.sleep(.01)
    proc.terminate(); proc.wait()
    log = [e for e in read_log(sch['log']) if e['changed']]
    for r in rows:  # a world change counts only if it lies wholly between the two reads; one overlapping a read is ambiguous
        r['world_changed'] = any(e['t0'] > r['ax'] and e['t1'] < r['b0'] for e in log)
        r['ambiguous'] = any(e['t0'] <= r['ax'] and e['t1'] >= r['a0'] or e['t0'] <= r['a1'] and e['t1'] >= r['b0'] for e in log)
    return rows


# -- evaluation -------------------------------------------------------------------------------------------------
def norm_err(m, p, zt): return (((p-zt)/m.zsd)**2).mean(-1)


def cf_eval(m, cf, counts, mode):
    """mode: 'own' (true actions), 'zero' (action input zeroed). Returns per-query records."""
    recs = []
    for st in cf:
        A = np.array([onehot(c['a']) for c in st['cands']]); A = np.zeros_like(A) if mode == 'zero' else A
        X = np.repeat(st['x'][None], len(A), 0); p, _ = m.predict(X, A); zt = m.latent(np.array([c['x2'] for c in st['cands']]))
        conf, lab = m.confidence(X, A, [counts[c['a']] for c in st['cands']])
        for k, c in enumerate(st['cands']):
            j = int(np.argmin(((zt-p[k])**2).sum(1)))
            recs.append({'held': c['held'], 'ok': st['cands'][j]['snap'] == c['snap'], 'err': float(norm_err(m, p[k], zt[k])),
                         'conf': float(conf[k]), 'label': lab[k]})
    return recs


def ridge_cf(train, cf):
    X = np.array([r['x'] for r in train]); A = np.array([onehot(r['a']) for r in train]); X2 = np.array([r['x2'] for r in train])
    mu, sd = X2.mean(0), X2.std(0)+1e-3; F = np.c_[X, A, np.ones(len(X))]
    W = np.linalg.solve(F.T@F+1e-2*np.eye(F.shape[1]), F.T@((X2-mu)/sd)); ok = []
    for st in cf:
        outs = (np.array([c['x2'] for c in st['cands']])-mu)/sd
        for c in st['cands']:
            if c['held']: continue
            p = np.r_[st['x'], onehot(c['a']), 1.]@W; j = int(np.argmin(((outs-p)**2).sum(1))); ok.append(st['cands'][j]['snap'] == c['snap'])
    return float(np.mean(ok))


def op_of(i): return ACTIONS[i][0]


def theta_of(m, val, zero):
    """95th percentile of the model's own clean validation errors, per operation (noop, write_short, ...)."""
    A = np.array([onehot(r['a']) for r in val]); A = np.zeros_like(A) if zero else A
    p, _ = m.predict(np.array([r['x'] for r in val]), A); e = norm_err(m, p, m.latent(np.array([r['x2'] for r in val])))
    return {o: float(np.percentile([d for r, d in zip(val, e) if op_of(r['a']) == o], 95)) for o in OPS+('noop',)}


def attr_eval(m, rows, theta, zero):
    A = np.array([onehot(r['a']) for r in rows]); A = np.zeros_like(A) if zero else A
    p, _ = m.predict(np.array([r['x'] for r in rows]), A); e = norm_err(m, p, m.latent(np.array([r['x2'] for r in rows])))
    res = {'own_only': [], 'world_only': [], 'both': [], 'none': []}
    for r, d in zip(rows, e):
        if r['ambiguous']: continue
        cls = 'SELF' if d <= theta[op_of(r['a'])] else 'WORLD_INVOLVED'
        k = ('both' if r['world_changed'] else 'own_only') if r['a'] != NOOP else ('world_only' if r['world_changed'] else 'none')
        res[k].append(cls)
    rate = lambda k, c: round(sum(x == c for x in res[k])/max(1, len(res[k])), 4)
    out = {'n': {k: len(v) for k, v in res.items()}, 'own_only_self': rate('own_only', 'SELF'), 'world_only_world': rate('world_only', 'WORLD_INVOLVED'),
           'both_world': rate('both', 'WORLD_INVOLVED'), 'none_self': rate('none', 'SELF')}
    out['balanced'] = round((out['own_only_self']+out['world_only_world'])/2, 4); return out


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b)); return float(np.corrcoef(ra, rb)[0, 1])


def run_seed(seed, args):
    from v13.world_jepa import WorldJEPA
    work = Path(tempfile.mkdtemp(prefix='z12b-%d-' % seed)); rng = random.Random(seed)
    held = set(rng.sample(range(NOOP), 4))
    t = time.time(); train = collect_train(work, seed, args.train, held)
    cf = collect_cf(work, seed, args.cf, held); attr = collect_attr(work, seed, args.attr, held); t_collect = time.time()-t
    nv = len(train)//10; fit, val = train[:-nv], train[-nv:]; val_clean = [r for r in val if not r['world']]
    X = np.array([r['x'] for r in fit]); A = np.array([onehot(r['a']) for r in fit]); X2 = np.array([r['x2'] for r in fit])
    counts = [sum(r['a'] == i for r in fit) for i in range(len(ACTIONS))]
    perm = np.random.default_rng(seed).permutation(len(A))
    t = time.time()
    m = WorldJEPA(seed=seed).fit(X, A, X2, steps=args.steps)
    m0 = WorldJEPA(seed=seed, ensemble=1).fit(X, np.zeros_like(A), X2, steps=args.steps)
    ms = WorldJEPA(seed=seed, ensemble=1).fit(X, A[perm], X2, steps=args.steps)
    t_fit = time.time()-t
    rec = cf_eval(m, cf, counts, 'own'); rec0 = cf_eval(m0, cf, counts, 'zero'); recs = cf_eval(ms, cf, counts, 'own')
    cov = lambda rs: [r for r in rs if not r['held']]
    acc = lambda rs: round(float(np.mean([r['ok'] for r in rs])), 4)
    covered = cov(rec)
    th, th0 = theta_of(m, val_clean, False), theta_of(m0, val_clean, True)
    return {
        'seed': seed, 'held_out_actions': [list(ACTIONS[i]) for i in sorted(held)], 'n_train': len(fit), 'n_val_clean': len(val_clean),
        'world_touched_train_frac': round(float(np.mean([r['world'] for r in train])), 4),
        'seconds_collect': round(t_collect, 1), 'seconds_fit_3_models': round(t_fit, 1), 'history': m.history[-3:],
        'cf_retrieval': {'jepa_covered': acc(covered), 'jepa_held_out': acc([r for r in rec if r['held']]),
                         'no_action_covered': acc(cov(rec0)), 'shuffled_action_covered': acc(cov(recs)), 'ridge_obs_covered_info': ridge_cf(fit, cf),
                         'n_covered': len(covered), 'n_held_out': len(rec)-len(covered)},
        'errors': {'covered_mean': round(float(np.mean([r['err'] for r in covered])), 4), 'held_out_mean': round(float(np.mean([r['err'] for r in rec if r['held']])), 4)},
        'confidence': {'covered_mean': round(float(np.mean([r['conf'] for r in covered])), 4),
                       'held_out_all_uncertain': all(r['label'] == 'SIMULATION_UNCERTAIN' for r in rec if r['held']),
                       'covered_uncertain_frac': round(float(np.mean([r['label'] == 'SIMULATION_UNCERTAIN' for r in covered])), 4)},
        '_conf_err': [[r['conf'], r['err']] for r in covered],
        'collapse': m.collapse_stats(X2),
        'attribution': {'theta': {k: round(v, 4) for k, v in th.items()}, 'jepa': attr_eval(m, attr, th, False), 'no_action': attr_eval(m0, attr, th0, True)},
    }


def criteria(seeds):
    pool = lambda k: float(np.mean([s['cf_retrieval'][k] for s in seeds]))  # equal per-seed n
    ce = [x for s in seeds for x in s['_conf_err']]
    j = {k: float(np.mean([s['attribution']['jepa'][k] for s in seeds])) for k in ('own_only_self', 'world_only_world', 'none_self', 'balanced')}
    c = float(np.mean([s['attribution']['no_action']['balanced'] for s in seeds]))
    rho = spearman([x[0] for x in ce], [x[1] for x in ce])
    return {
        'W1_cf_retrieval_covered': pool('jepa_covered') >= .80 and all(s['cf_retrieval']['jepa_covered'] >= .70 for s in seeds),
        'W2_controls_fail': pool('no_action_covered') <= .40 and pool('shuffled_action_covered') <= .40 and pool('jepa_covered')-max(pool('no_action_covered'), pool('shuffled_action_covered')) >= .30,
        'W3_no_collapse': all(s['collapse']['effective_rank'] >= 4 and s['collapse']['min_std'] >= .05 for s in seeds),
        'W4_confidence_tracks_error': rho <= -.30 and all(s['confidence']['held_out_all_uncertain'] for s in seeds),
        'W5_attribution_jepa': j['own_only_self'] >= .90 and j['world_only_world'] >= .90 and j['none_self'] >= .80,
        'W6_no_action_attribution_worse': c <= j['balanced']-.20,
    }, {'pooled_cf': {k: round(pool(k), 4) for k in ('jepa_covered', 'jepa_held_out', 'no_action_covered', 'shuffled_action_covered', 'ridge_obs_covered_info')},
        'spearman_conf_err_covered': round(rho, 4), 'attribution_jepa': {k: round(v, 4) for k, v in j.items()}, 'attribution_no_action_balanced': round(c, 4)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out', nargs='?'); ap.add_argument('--world')
    ap.add_argument('--seeds', default='101,102,103'); ap.add_argument('--train', type=int, default=4000)
    ap.add_argument('--cf', type=int, default=150); ap.add_argument('--attr', type=int, default=300); ap.add_argument('--steps', type=int, default=3000)
    args = ap.parse_args()
    if args.world: return world_main(args.world)
    seeds = [run_seed(int(s), args) for s in args.seeds.split(',')]
    crit, summary = criteria(seeds)
    for s in seeds: s.pop('_conf_err')
    out = {'kind': 'V13_Z12B_WORLD_JEPA', 'prereg': 'docs/proofs/continuation-20261026/z12b-world-jepa/PREREG.md', 'args': vars(args),
           'seeds': seeds, 'summary': summary, 'criteria': crit,
           'verdict': 'Z12B_WORLD_JEPA_PASS' if all(crit.values()) else 'Z12B_WORLD_JEPA_FAIL',
           'claim_limit': 'small file world with synthetic content on the cloud machine; no phone measurement; SHADOW module, not wired into the runtime'}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False)); print(out['verdict'], json.dumps(summary), json.dumps(crit))


if __name__ == '__main__':
    main()
