#!/usr/bin/env python3
"""WP-Z6 §24.25 Observer-Pass Utility: does the pre-answer observer pass earn its mobile price? (real models)

Arms (fresh home each, one session per task, bench decoding as R4/Z6a):
  none      no pre-answer observer pass (effort plan 'high', wake forced to none)
  A         only B1_DETAIL observes (wake forced to detail; re-entries to B2 blocked)
  B         only B2_GIST observes (wake forced to gist; re-entries to B1 blocked)
  AB        both observe every event (wake forced to both): the always-pass scaffold
  adaptive  the runtime's own adaptive path: effort 'adaptive' + learned observer frequency (`:jef active`, §24.25 -> WP-D)
Arms none/A/B/AB share effort 'high' so they differ only in which bodies observe. Late watch off and post-commit
observers cut at FINAL in every arm (answer time = time to FINAL).
Tasks: utility_bench2 kinds (summary/long/notes/compare, fresh seed) + a two-turn 'correction' kind (a later message
corrects an earlier fact; history_turns 2 in all arms). Preregistration:
docs/proofs/continuation-20261026/z6-observer-utility/PREREG.md (committed before the run).
Usage: z6_observer_utility.py <installed_home> <out.json> [arm,arm,...] [--seed 59] [--limit N]
"""
import json
import random
import re
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

ARMS = ('none', 'A', 'B', 'AB', 'adaptive')
FORCED = {'none': 'none', 'A': 'detail', 'B': 'gist', 'AB': 'both'}
ALLOWED = {'none': set(), 'A': {'B1_DETAIL'}, 'B': {'B2_GIST'}, 'AB': {'B1_DETAIL', 'B2_GIST'}, 'adaptive': {'B1_DETAIL', 'B2_GIST'}}
CONFLICT_KINDS = ('summary', 'notes', 'correction')
CONFLICT_WORDS = re.compile(r'(?i)\b(incorrect|not correct|wrong|error|mistake|mismatch|does not match|doesn\'t match|differ\w*|disagree\w*|'
                            r'contradict\w*|conflict\w*|inconsisten\w*|correct(?:ed|ion)|changed|moved|updated|newer|more recent|latest)\b')
MONTHS = ('May', 'June', 'July', 'September')
GOODS = ('boxes', 'pallets', 'crates', 'parcels')
TIME_RATIO = .8   # adaptive must cost at most 80 % of the AB answer time to count as cheaper
ALPHA = .05


def correction_tasks(seed, n=15):
    """Two turns: a fact, then a correction of one part of it and a question about both parts."""
    rng = random.Random(seed*1000+17); out = []
    for i in range(n):
        city = rng.choice(U2.CITIES); month = rng.choice(MONTHS); goods = rng.choice(GOODS); qty = rng.randint(14, 96)
        d1, d2 = rng.sample(range(2, 28), 2)
        first = f'Project note: the delivery of {qty} {goods} to {city} is planned for {d1} {month}.'
        second = f'Correction: the delivery to {city} was moved. It is now on {d2} {month}. How many {goods} go to {city}, and on which day?'
        out.append((f'correction{i:02d}', [first, second], [qty, d2], {'qty': U2.word(qty), 'day': U2.word(d2), 'old_day_absent': None},
                    {'old': d1, 'new': d2}))
    return out


def fixtures(seed, limit=None):
    fx = [(f, [t], nums, checks, None) for f, t, nums, checks in U2.tasks(seed=seed)]+correction_tasks(seed)
    if limit:
        fx = [f for i, f in enumerate(fx) if i % max(1, len(fx)//limit) == 0][:limit]
    return fx


def score(fid, out, nums, checks, extra):
    c = {k: v for k, v in checks.items() if v is not None}
    ok, num = U.score(out, nums, c)
    passed = all(ok.values()) and all(num.values())
    if extra:  # correction: the old day must not be given as the answer day
        passed = passed and not re.search(r'\bon\s+'+str(extra['old'])+r'\b', out)
    return passed


def kind(f): return f.rstrip('0123456789')


def wait(r, eid, t0, limit=900):
    answer_s = None; end = t0+limit
    while not r.idle():
        if answer_s is None:
            m = r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))
            if m and m['status'] in ('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED'):
                answer_s = round(time.monotonic()-t0, 2); r.cancel()
        if time.monotonic() > end:
            r.cancel(); break
        time.sleep(.1)
    return answer_s if answer_s is not None else round(time.monotonic()-t0, 2)


def run_arm(installed, arm, fx):
    from v13 import effort as EF, jefbridge, latewatch
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    rows = []; real_decide = EF.decide
    if arm in FORCED:
        def decide(mode, sig, **limits):
            plan = real_decide(mode, sig, **limits); plan['wake'] = FORCED[arm]; return plan
        EF.decide = decide
    try:
        with tempfile.TemporaryDirectory(prefix='v13-z6obs-') as tmp:
            home = Path(tmp); cfg = initialize(home)
            for n in ('models', 'bin'):
                shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
            shutil.copyfile(installed/'config/models.json', home/'config/models.json')
            save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 2} | U2.BENCH_CFG)
            r = Runtime(home); latewatch.set_mode(r.store, 'off')
            EF.set_mode(r.store, 'adaptive' if arm == 'adaptive' else 'high')
            if arm == 'adaptive': jefbridge.controller(r).set_mode('ACTIVE', 'EXPLICIT_HUMAN')
            real_offer = r.cognition.offer

            def offer(role, *a, **k):
                if role not in ALLOWED[arm]: raise RuntimeError('Z6_ARM_ROLE_BLOCKED')
                return real_offer(role, *a, **k)
            r.cognition.offer = offer
            try:
                for fid, turns, nums, checks, extra in fx:
                    r.session = r.store.new_session(); pre = []
                    for t in turns[:-1]:  # earlier turns: answered normally, not scored
                        t0 = time.monotonic(); e0 = r.submit(t); wait(r, e0, t0); pre.append(e0)
                    t0 = time.monotonic(); eid = r.submit(turns[-1]); turn_s = wait(r, eid, t0)
                    a = audit_event(r.store, eid); out = a.get('output') or ''; meta = a.get('output_metadata') or {}
                    post = {json.loads(x['metrics']).get('id') for x in r.store.rows("SELECT metrics FROM telemetry WHERE kind='postcommit_offer' AND event_id=?", (eid,))}
                    offers = [o for o in a.get('offers', []) if o.get('packet_id') not in post]
                    texts = [json.dumps(o.get('offer', {}), ensure_ascii=False) for o in offers]
                    ed = r.store.rows("SELECT payload FROM packets WHERE kind='EffortDecision' AND payload LIKE ? ORDER BY rowid DESC LIMIT 1", ('%'+eid+'%',))
                    ed = json.loads(ed[0]['payload']) if ed else {}
                    focal = meta.get('focal') or {}
                    rows.append({'fixture': fid, 'kind': kind(fid), 'arm': arm, 'pass': score(fid, out, nums, checks, extra), 'turn_s': turn_s,
                                 'status': a.get('status'), 'offer_roles': sorted({o['role'] for o in offers}), 'n_offers': len(offers),
                                 'selected': len(meta.get('selected_offer_ids') or []), 'reentries': max(0, len(offers)-len({o['role'] for o in offers})),
                                 'observer_flags_conflict': any(CONFLICT_WORDS.search(t) or '"needs_reentry": true' in t for t in texts),
                                 'contested': 'CONTESTED' in (focal.get('inquisition') or []),
                                 'observer_mentions_new_value': bool(extra) and any(re.search(r'\b'+str(extra['new'])+r'\b', t) for t in texts),
                                 'blocked_roles': r.store.one("SELECT COUNT(*) n FROM telemetry WHERE event_id=? AND metrics LIKE '%Z6_ARM_ROLE_BLOCKED%'", (eid,))['n'],
                                 'wake': ed.get('wake'), 'band': (ed.get('plan') or {}).get('band'), 'jef_observer': meta.get('jef_observer'),
                                 'observer_schedule': meta.get('observer_schedule'), 'output': out[:400]})
                    print(json.dumps({k: rows[-1][k] for k in ('arm', 'fixture', 'pass', 'turn_s', 'offer_roles', 'reentries')}), flush=True)
                rep = jefbridge.controller(r).report().get('observer_utility')
            finally:
                r.close()
    finally:
        EF.decide = real_decide
    return rows, rep


def paired(a, b):
    common = [f for f in a if f in b]
    w = sum(a[f]['pass'] and not b[f]['pass'] for f in common); l = sum(b[f]['pass'] and not a[f]['pass'] for f in common)
    return {'n': len(common), 'first_only_pass': w, 'second_only_pass': l, 'sign_test_p': round(sign_test(w, l), 4)}


def analyse(rows):
    by = {}
    for r in rows: by.setdefault(r['arm'], {})[r['fixture']] = r
    out = {'arms': {}}
    for arm, m in by.items():
        n = len(m); conf = [r for r in m.values() if r['kind'] in CONFLICT_KINDS]; corr = [r for r in m.values() if r['kind'] == 'correction']
        out['arms'][arm] = {'n': n, 'passed': sum(r['pass'] for r in m.values()), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
                            'by_kind': {k: sum(r['pass'] for r in m.values() if r['kind'] == k) for k in sorted({r['kind'] for r in m.values()})},
                            'observer_turns': sum(bool(r['n_offers']) for r in m.values()), 'offers': sum(r['n_offers'] for r in m.values()),
                            'reentries': sum(r['reentries'] for r in m.values()),
                            'conflict_detection': '%d/%d' % (sum(r['observer_flags_conflict'] or r['contested'] for r in conf), len(conf)),
                            'correction_pickup_answer': '%d/%d' % (sum(r['pass'] for r in corr), len(corr)),
                            'correction_seen_by_observer': '%d/%d' % (sum(r['observer_mentions_new_value'] for r in corr), len(corr))}
    if 'none' in by:
        nb = by['none']; any_pass = {f for f in nb if any(by[a].get(f, {}).get('pass') for a in by)}
        for arm, m in by.items():
            if arm == 'none': continue
            out['arms'][arm]['unnecessary_observer_turns'] = '%d/%d' % (sum(bool(m[f]['n_offers']) for f in m if nb.get(f, {}).get('pass')), sum(1 for f in m if nb.get(f, {}).get('pass')))
            out['arms'][arm]['extra_turn_s_vs_none'] = round(out['arms'][arm]['mean_turn_s']-out['arms']['none']['mean_turn_s'], 2)
        for arm, m in by.items():
            out['arms'][arm]['missed_useful'] = sorted(f for f in m if not m[f]['pass'] and f in any_pass and not nb[f]['pass'])
    out['paired'] = {f'{x}_vs_none': paired(by[x], by['none']) for x in ARMS if x != 'none' and x in by and 'none' in by}
    if 'adaptive' in by and 'AB' in by: out['paired']['adaptive_vs_AB'] = paired(by['adaptive'], by['AB'])
    if all(a in by for a in ARMS):
        p = out['paired']['AB_vs_none']; q = out['paired']['adaptive_vs_AB']
        o1 = p['first_only_pass'] > p['second_only_pass'] and p['sign_test_p'] < ALPHA
        o2 = not (q['second_only_pass'] > q['first_only_pass'] and q['sign_test_p'] < ALPHA) and out['arms']['adaptive']['mean_turn_s'] <= TIME_RATIO*out['arms']['AB']['mean_turn_s']
        o3 = not (p['second_only_pass'] > p['first_only_pass'] and p['sign_test_p'] < ALPHA)
        out['criteria'] = {'O1_always_pass_beats_none': o1, 'O2_adaptive_cheaper_not_worse': o2, 'O3_always_pass_does_not_hurt': o3}
        out['verdict'] = ('ADAPTIVE_PREFERRED' if o2 and (o1 or o3) else 'ALWAYS_PASS_JUSTIFIED' if o1 else 'ALWAYS_PASS_NOT_JUSTIFIED')
    return out


def main(installed, out, arms=None, seed=59, limit=None):
    installed = Path(installed).resolve(); out = Path(out); arms = arms.split(',') if arms else ARMS; fx = fixtures(seed, limit)
    prev = json.loads(out.read_text()) if out.exists() else {'rows': [], 'jef_reports': {}}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]; reps = {k: v for k, v in prev.get('jef_reports', {}).items() if k not in arms}
    for arm in arms:
        rr, rep = run_arm(installed, arm, fx); rows += rr; reps[arm] = rep
        atomic_write(out, json.dumps({'kind': 'V13_Z6_OBSERVER_UTILITY', 'seed': seed, 'bench_cfg': U2.BENCH_CFG, 'fixtures': [f[0] for f in fx],
                                      **analyse(rows), 'jef_reports': reps, 'rows': rows, 'phone_measured': False, 'canonical_gate_pass': False,
                                      'not_measured_cloud': ['energy', 'thermal', 'memory_bandwidth', 'page_faults'],
                                      'prereg': 'docs/proofs/continuation-20261026/z6-observer-utility/PREREG.md',
                                      'claim_limit': 'deterministic bench decoding, generated English tasks, regex checks, one seed, cloud CPU'}, indent=1))
    print(json.dumps({k: v for k, v in analyse(rows).items()}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]; lim = None; seed = 59
    for flag in ('--limit', '--seed'):
        if flag in a:
            i = a.index(flag); v = int(a[i+1]); del a[i:i+2]
            if flag == '--limit': lim = v
            else: seed = v
    main(a[0], a[1], a[2] if len(a) > 2 else None, seed, lim)
