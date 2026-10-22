#!/usr/bin/env python3
"""WP-Z8b / G-AGE-REOPEN-001: does Age plasticity re-open on a real change, stay closed under noise, re-close after
re-learning, and survive a restart?  Real AgeControl on a real Store (SQLite) driving an NLMS learner on a synthetic
stream; the learner/stream helpers are the ones of the §99 ablation (v13/ablation99.py), only the phases are longer and
a settle phase follows the target shift.

Phases: learn (stable target w) -> noisy (10 % adversarial labels + extra noise) -> shift (new target w2) -> settle (w2).
Arms: noise_aware (user default since 2026-10-22), noise_no_reopen (same policy, reopen signals novelty/repeated errors
held at 0), boot, stable_reopen, fixed_conservative (.45), fixed_permissive (1.0).
`noise_aware_restart` = noise_aware with the Store closed and a fresh AgeControl opened from disk in the middle of the shift.
Preregistration: docs/proofs/continuation-20261022/z8-age-reopen/PREREG.md (committed before the run).
  python3 scripts/z8_age_reopen.py --out DIR [--seeds 20]
"""
import argparse, json, math, random, statistics, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import ablation99 as A  # noqa: E402
from v13 import age as AGE  # noqa: E402
from v13.age import AgeControl  # noqa: E402

class AgeV2(AgeControl):
    """WP-Z8c candidate `noise_aware_v2` (script only): novelty/new-modality floors act after the noise damping, and
    persistent errors (>= PERSISTENT_ERRORS in a row) reopen undamped; isolated failures stay damped as in noise_aware."""
    def plasticity(self, capability='system', novel_domain=False, repeated_errors=0, new_modality=False):
        st = self.state()[0]; sub = self._subject(st, capability); stage = sub['stage']; stab = sub['maturity']['stability']
        p = AGE.PLASTICITY_BASE[stage]*(1-.3*stab); nzs = sub.get('noise') or {}
        nz = nzs.get('mad', 0.) if nzs.get('n', 0) >= AGE.NOISE_MIN_N else 0.
        damp = 1/(1+nz/AGE.NOISE_REF); p *= .5+.5*damp; n = int(repeated_errors)
        if n > 0: p += min(.3, .1*n)*(1. if n >= AGE.PERSISTENT_ERRORS else damp)
        if novel_domain: p = max(p, .8)
        if new_modality: p = 1.
        return round(min(1., p), 6)

PHASES = ((0, 600, 'learn'), (600, 1000, 'noisy'), (1000, 1600, 'shift'), (1600, 2200, 'settle'))
RESTART_AT = 1300; WINDOW = 50; LR = .3
POLICY = {'noise_aware': 'noise_aware', 'noise_aware_restart': 'noise_aware', 'noise_no_reopen': 'noise_aware',
          'boot': 'boot', 'stable_reopen': 'stable_reopen', 'v2': 'noise_aware', 'v2_no_reopen': 'noise_aware', 'v2_restart': 'noise_aware'}
FIXED = {'fixed_conservative': .45, 'fixed_permissive': 1.}
ARMS = tuple(POLICY) + tuple(FIXED)
NO_REOPEN = ('noise_no_reopen', 'v2_no_reopen'); RESTART = ('noise_aware_restart', 'v2_restart')

def stream(seed):
    rng = random.Random(seed); w = A._vec(rng); w2 = A._vec(rng); out = []
    for t in range(PHASES[-1][1]):
        phase = next(p for a, b, p in PHASES if a <= t < b); true = w2 if phase in ('shift', 'settle') else w
        x = [rng.gauss(0, 1) for _ in range(A.DIM)]; y = A._dot(true, x)+rng.gauss(0, A.NOISE)
        if phase == 'noisy': y = A._dot(A._vec(rng), x)*2 if rng.random() < .1 else A._dot(true, x)+rng.gauss(0, 1.)
        out.append({'t': t, 'phase': phase, 'x': x, 'y': y, 'w': true})
    return out

def open_ctl(home, policy, arm=''):
    store, cfg = A._store(Path(home)); cfg['user_stage_cap'] = 5; cfg['age_plasticity_policy'] = policy
    return (AgeV2 if arm.startswith('v2') else AgeControl)(store, cfg, build_ceiling=5)

def run(st, arm, home):
    ctl = open_ctl(home, POLICY[arm], arm) if arm in POLICY else None
    theta = [0.]*A.DIM; prev_err = None; prev_theta = list(theta); fails = 0; novel = True; win = []
    p_used = []; errs = []; stages = []; restarted = False
    for ev in st:
        if arm in RESTART and ev['t'] == RESTART_AT and not restarted:
            ctl.s.close(); ctl = open_ctl(home, POLICY[arm], arm); restarted = True
        if ctl: p = ctl.plasticity('language', novel_domain=novel and arm not in NO_REOPEN, repeated_errors=0 if arm in NO_REOPEN else fails)
        else: p = FIXED[arm]
        p_used.append(p); theta = A._nlms(theta, ev['x'], ev['y'], LR*p); e = A._err(theta, ev['w']); errs.append(e); win.append(e)
        if (ev['t']+1) % WINDOW == 0:
            err = A._mean(win); win = []
            novel = prev_err is not None and err > 2*prev_err and err > .1
            passed = prev_err is None or err <= prev_err*1.1+.02; fails = 0 if passed else fails+1
            if ctl:
                drift = math.sqrt(sum((a-b)**2 for a, b in zip(theta, prev_theta)))/max(1e-9, math.sqrt(A._dot(theta, theta)))
                comp = max(0., 1-err)
                ctl.record('language', {'experience': ev['t']+1, 'competence': comp, 'stability': max(0., 1-drift), 'retention': comp,
                                        'calibration': .8, 'memory_health': .97, 'safe_self_control': .999, 'regression_pass': passed},
                           evidence_id='z8-'+str(ev['t']))
                stages.append(ctl.state()[0]['capabilities']['language']['stage'])
            prev_err = err; prev_theta = list(theta)
    transitions = None
    if ctl:
        transitions = ctl.s.db.execute("SELECT count(*) FROM telemetry WHERE kind='age_transition'").fetchone()[0]; ctl.s.close()
    seg = lambda xs, a, b: A._mean(xs[a:b])
    return {'p': {'learn_end': seg(p_used, 500, 600), 'noisy': seg(p_used, 600, 1000), 'shift_start': seg(p_used, 1000, 1100),
                  'settle_end': seg(p_used, 2100, 2200)},
            'err': {'learn': seg(errs, 0, 600), 'noisy': seg(errs, 600, 1000), 'shift_250': seg(errs, 1000, 1250), 'shift': seg(errs, 1000, 1600),
                    'settle': seg(errs, 1600, 2200)},
            'stages': stages, 'noisy_stage_changes': sum(1 for i in range(1, len(stages)) if stages[i] != stages[i-1] and 600 <= (i+1)*WINDOW-1 < 1000+WINDOW),
            'max_stage': max(stages) if stages else None, 'age_transition_events': transitions,
            'p_trace_every_25': [round(x, 9) for x in p_used[::25]]}

def verdict(raw, seeds, arm='noise_aware'):
    na = raw[arm]; nr = raw[arm.replace('noise_aware', 'noise')+'_no_reopen']; rs = raw[arm+'_restart']; n = len(seeds)
    k1 = sum(r['p']['shift_start'] >= 1.25*r['p']['learn_end'] for r in na)
    k2_seeds = sum(a['err']['shift_250'] < b['err']['shift_250'] for a, b in zip(na, nr))
    k2_rel = 1-statistics.mean(r['err']['shift_250'] for r in na)/statistics.mean(r['err']['shift_250'] for r in nr)
    k3 = statistics.median(r['p']['noisy']/r['p']['learn_end'] for r in na)
    k4 = statistics.median(r['p']['settle_end']/r['p']['shift_start'] for r in na)
    k5 = all(a == b for a, b in zip(na, rs))
    k6 = statistics.median(r['noisy_stage_changes'] for r in na)
    crit = {'K1_reopens_on_shift': {'value': '%d/%d' % (k1, n), 'pass': k1 >= math.ceil(.8*n)},
            'K2_reopen_helps': {'value': {'seeds_better': '%d/%d' % (k2_seeds, n), 'mean_error_reduction': round(k2_rel, 4)},
                                'pass': k2_seeds >= math.ceil(.75*n) and k2_rel >= .10},
            'K3_noise_no_false_reopen': {'value': round(k3, 4), 'pass': k3 <= 1.25},
            'K4_recloses_after_relearn': {'value': round(k4, 4), 'pass': k4 <= .8},
            'K5_restart_identical': {'value': k5, 'pass': k5},
            'K6_no_stage_flapping_under_noise': {'value': k6, 'pass': k6 <= 2}}
    if arm == 'v2':
        k7 = statistics.mean(r['err']['noisy'] for r in na)/statistics.mean(r['err']['noisy'] for r in raw['noise_aware'])-1
        crit['K7_noise_benefit_kept'] = {'value': round(k7, 4), 'pass': k7 <= .10}
        return ('Z8C_V2_PASS' if all(c['pass'] for c in crit.values()) else 'Z8C_V2_FAIL'), crit
    return ('Z8_AGE_REOPEN_PASS' if all(c['pass'] for c in crit.values()) else 'Z8_AGE_REOPEN_FAIL'), crit

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--seeds', type=int, default=20)
    ap.add_argument('--first-seed', type=int, default=101); ap.add_argument('--candidate', action='store_true', help='WP-Z8c: also run noise_aware_v2 arms'); a = ap.parse_args()
    seeds = list(range(a.first_seed, a.first_seed+a.seeds)); base = Path(tempfile.mkdtemp(prefix='z8-')); t0 = time.monotonic()
    arms = ARMS if a.candidate else tuple(x for x in ARMS if not x.startswith('v2'))
    raw = {arm: [] for arm in arms}
    for s in seeds:
        st = stream(s)
        for arm in arms: raw[arm].append(run(st, arm, base/('%s-%d' % (arm, s))))
    v, crit = verdict(raw, seeds)
    if a.candidate: v2, crit2 = verdict(raw, seeds, 'v2'); v = {'noise_aware': v, 'v2': v2}; crit = {'noise_aware': crit, 'v2': crit2}
    summ = {arm: {k: {kk: round(statistics.mean(r[k][kk] for r in rs), 4) for kk in rs[0][k]} for k in ('p', 'err')} for arm, rs in raw.items()}
    for arm, rs in raw.items(): summ[arm]['max_stage_median'] = statistics.median(r['max_stage'] for r in rs) if rs[0]['max_stage'] is not None else None
    doc = {'schema': 'v13-z8-age-reopen-v1', 'gate': 'G-AGE-REOPEN-001', 'verdict': v, 'criteria': crit, 'seeds': seeds, 'summary': summ,
           'prereg': 'docs/proofs/continuation-20261022/z8-age-reopen/PREREG.md', 'seconds': round(time.monotonic()-t0, 1),
           'claim_limit': 'synthetic linear NLMS stream with the real AgeControl/Store; no language model, no phone',
           'phone_measured': False, 'raw': raw}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out/'z8.json').write_text(json.dumps(doc, indent=1)+'\n')
    print(json.dumps({'verdict': v, 'criteria': crit}, indent=1)); return 0

if __name__ == '__main__':
    sys.exit(main())
