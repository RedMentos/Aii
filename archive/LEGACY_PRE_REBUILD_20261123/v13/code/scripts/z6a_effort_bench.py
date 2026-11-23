#!/usr/bin/env python3
"""WP-Z6a / §24.23 Adaptive Reasoning Effort: fixed disabled/low/high/max vs adaptive on 60 WP-T3b tasks (real models).

Same bench mode and scoring as R4 (scripts/r4_wake_bench.py, scripts/utility_bench2.py); the arm only sets the effort
mode (`v13.effort.set_mode`) of a fresh home before the first turn. Preregistration:
docs/proofs/continuation-20261022/z6a-effort/PREREG.md (committed before the run).
Usage: z6a_effort_bench.py <installed_home> <out.json> [arm,arm,...] [--seed 23] [--limit N]
"""
import json
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
from r4_wake_bench import sign_test  # noqa: E402

ARMS = ('disabled', 'low', 'adaptive', 'high', 'max')
FIXED = ('disabled', 'low', 'high', 'max')


def run_arm(installed, arm, fixtures):
    from v13 import effort as EF
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-z6a-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0} | U2.BENCH_CFG)
        r = Runtime(home); EF.set_mode(r.store, arm)
        try:
            for fid, text, nums, checks in fixtures:
                r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); end = t0+900; answer_s = None
                while not r.idle():
                    if answer_s is None:
                        m = r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))
                        if m and m['status'] in ('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED'):
                            answer_s = round(time.monotonic()-t0, 2); r.cancel()  # prereg addendum: post-commit observers cut in all arms
                    if time.monotonic() > end:
                        r.cancel(); break
                    time.sleep(.1)
                a = audit_event(r.store, eid); out = a.get('output') or ''
                post = {json.loads(x['metrics']).get('id') for x in r.store.rows("SELECT metrics FROM telemetry WHERE kind='postcommit_offer' AND event_id=?", (eid,))}
                ok, num = U.score(out, nums, checks)
                ed = r.store.rows("SELECT payload FROM packets WHERE kind='EffortDecision' AND payload LIKE ? ORDER BY rowid DESC LIMIT 1", ('%'+eid+'%',))
                ed = json.loads(ed[0]['payload']) if ed else {}
                rows.append({'fixture': fid, 'arm': arm, 'pass': all(ok.values()) and all(num.values()),
                             'turn_s': answer_s if answer_s is not None else round(time.monotonic()-t0, 2), 'wall_s': round(time.monotonic()-t0, 2),
                             'status': a.get('status'), 'offers': sorted({o['role'] for o in a.get('offers', []) if o.get('packet_id') not in post}),
                             'postcommit_offers': len(post), 'effort': ed.get('effort'), 'band': (ed.get('plan') or {}).get('band'), 'wake': ed.get('wake'),
                             'constraints': ed.get('constraints'), 'output': out[:400]})
                print(json.dumps({k: rows[-1][k] for k in ('arm', 'fixture', 'pass', 'turn_s', 'offers', 'band')}), flush=True)
        finally:
            r.close()
    return rows


def paired(a, b):
    common = [f for f in a if f in b]
    w = sum(a[f]['pass'] and not b[f]['pass'] for f in common); l = sum(b[f]['pass'] and not a[f]['pass'] for f in common)
    return {'n': len(common), 'first_only_pass': w, 'second_only_pass': l, 'sign_test_p': round(sign_test(w, l), 4)}


def analyse(rows):
    by = {}
    for r in rows:
        by.setdefault(r['arm'], {})[r['fixture']] = r
    kind = lambda f: f.rstrip('0123456789')
    out = {'arms': {}}
    for arm, m in by.items():
        n = len(m); bands = {}
        for r in m.values(): bands[r['band']] = bands.get(r['band'], 0)+1
        out['arms'][arm] = {'n': n, 'passed': sum(r['pass'] for r in m.values()), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
                            'wake_rate': round(sum(bool(r['offers']) for r in m.values())/n, 3), 'bands': bands,
                            'by_kind': {k: sum(r['pass'] for f, r in m.items() if kind(f) == k) for k in sorted({kind(f) for f in m})},
                            'turn_s_by_kind': {k: round(sum(r['turn_s'] for f, r in m.items() if kind(f) == k)/max(1, sum(1 for f in m if kind(f) == k)), 2) for k in sorted({kind(f) for f in m})}}
    out['paired'] = {f'{x}_vs_adaptive': paired(by[x], by['adaptive']) for x in FIXED if x in by and 'adaptive' in by}
    if all(x in by for x in ARMS):
        ad = by['adaptive']; dis = by['disabled']; mx = by['max']; aa = out['arms']['adaptive']
        dominated = [x for x in FIXED if out['paired'][f'{x}_vs_adaptive']['first_only_pass'] > out['paired'][f'{x}_vs_adaptive']['second_only_pass']
                     and out['paired'][f'{x}_vs_adaptive']['sign_test_p'] < .05 and out['arms'][x]['mean_turn_s'] <= aa['mean_turn_s']]
        pd = out['paired']['disabled_vs_adaptive']
        a2 = not (pd['first_only_pass'] > pd['second_only_pass'] and pd['sign_test_p'] < .05)
        easy = [f for f in dis if dis[f]['pass']]; over = [f for f in easy if ad[f]['offers']]
        a3 = len(over) <= .5*len(easy)
        under = [f for f in ad if not ad[f]['pass'] and mx[f]['pass'] and (ad[f]['effort'] or 0) < (mx[f]['effort'] or 0)]
        wakes = [f for f in ad if ad[f]['offers']]; needed = [f for f in wakes if not dis[f]['pass'] and mx[f]['pass']]
        crit = {'A1_not_dominated': {'dominated_by': dominated, 'pass': not dominated},
                'A2_no_loss_vs_disabled': {'value': pd, 'pass': a2},
                'A3_little_overthinking': {'value': '%d/%d' % (len(over), len(easy)), 'pass': a3}}
        out['criteria'] = crit
        out['verdict'] = 'Z6A_EFFORT_ADAPTIVE_PASS' if all(c['pass'] for c in crit.values()) else 'Z6A_EFFORT_ADAPTIVE_FAIL'
        out['descriptive'] = {'underthinking': {'n': len(under), 'fixtures': under},
                              'escalation_calibration': {'adaptive_wakes': len(wakes), 'needed': len(needed),
                                                         'share': round(len(needed)/len(wakes), 3) if wakes else None}}
    return out


def main(installed, out, arms=None, seed=23, limit=None):
    installed = Path(installed).resolve(); out = Path(out); arms = arms.split(',') if arms else ARMS; fx = U2.tasks(seed=seed)
    if limit:
        fx = [f for i, f in enumerate(fx) if i % (len(fx)//limit) == 0][:limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows += run_arm(installed, arm, fx)
        atomic_write(out, json.dumps({'kind': 'V13_Z6A_EFFORT_BENCH', 'seed': seed, 'bench_cfg': U2.BENCH_CFG, 'fixtures': [f[0] for f in fx],
                                      **analyse(rows), 'rows': rows, 'phone_measured': False, 'canonical_gate_pass': False,
                                      'prereg': 'docs/proofs/continuation-20261022/z6a-effort/PREREG.md',
                                      'claim_limit': 'deterministic bench decoding, generated English tasks, regex checks, one seed, cloud CPU'}, indent=1))
    print(json.dumps({k: v for k, v in analyse(rows).items() if k != 'arms'}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]; lim = None; seed = 23
    for flag in ('--limit', '--seed'):
        if flag in a:
            i = a.index(flag); v = int(a[i+1]); del a[i:i+2]
            if flag == '--limit': lim = v
            else: seed = v
    main(a[0], a[1], a[2] if len(a) > 2 else None, seed, lim)
