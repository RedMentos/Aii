#!/usr/bin/env python3
"""WP-Z11 / STEP4 + §24.28B: a stronger frozen reference teacher (cloud only) behind the existing REFERENCE lane.

Self = real V13 turn with effort 'disabled' (C3 alone, deterministic); teacher = Runtime._teacher job after the self
answer (imported TEACHER GGUF). Arms off / on / on_repeat on utility_bench2.tasks(seed=23). Checks T1-T6 of
docs/proofs/continuation-20261022/z11-reference-teacher/PREREG.md (committed before the run).
Usage: z11_reference_teacher.py <installed_home_with_TEACHER> <out.json> [--limit N] [--z11b]
--z11b: WP-Z11b protocol (selections deferred until all self answers of the arm; leak chunks stored).
--z11c: WP-Z11c = z11b + leak check v2 (plain history text, quotes/markup ignored) on fresh seed 29.
--z11d: WP-Z11d = z11b + leak check v3 (word 8-gram shingles, minus self and task shingles) on fresh seed 31.
"""
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, digest  # noqa: E402
import utility_bench as U  # noqa: E402
import utility_bench2 as U2  # noqa: E402

SELECT_FIRST = 10


def wait(r, t0, limit=1500):
    while not r.idle():
        if time.monotonic() > t0+limit:
            r.cancel(); return False
        time.sleep(.1)
    return True


def norm(s):
    """WP-Z11c leak check v2: compare plain text, not JSON-escaped text; quote/markup characters and spacing ignored."""
    return re.sub(r'[\s"\'`*_\u201c\u201d\u201e\u2018\u2019]+', ' ', s).strip().lower()


def shingles(s, k=8):
    """WP-Z11d leak check v3: word 8-grams of the normalized text (no character-boundary artifacts)."""
    w = re.findall(r'[a-z0-9\u00c0-\u024f]+', norm(s)); return {' '.join(w[i:i+k]) for i in range(max(0, len(w)-k+1))}


def shared_chunks(a, b, n=40):
    return {a[i:i+n] for i in range(0, max(0, len(a)-n+1), 5)} & {b[i:i+n] for i in range(0, max(0, len(b)-n+1))}


def run_arm(installed, arm, fixtures, deferred=False, leak_v2=False, leak_v3=False):
    """deferred (WP-Z11b): human selections only after all self answers of the arm, so T3 sees the teacher alone."""
    from v13 import effort as EF
    from v13.config import initialize, save_config
    from v13.history import native_history
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-z11-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'history_turns': 8, 'teacher_enabled': arm != 'off'} | U2.BENCH_CFG)
        r = Runtime(home); EF.set_mode(r.store, 'disabled')
        gen0 = r.store.generation_id
        comp0 = r.store.one('SELECT count(*) AS n FROM sqlite_master')['n']
        try:
            for i, (fid, text, nums, checks) in enumerate(fixtures):
                r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); wait(r, t0, 900)
                a = audit_event(r.store, eid); out = a.get('output') or ''; meta = a.get('output_metadata') or {}
                ok, num = U.score(out, nums, checks)
                row = {'fixture': fid, 'arm': arm, 'self_output': out, 'self_pass': all(ok.values()) and all(num.values()),
                       'self_s': round(time.monotonic()-t0, 2), 'self_candidate_hash': meta.get('self_candidate_hash'), 'self_sha': digest(out)}
                exp = r.store.rows("SELECT payload FROM packets WHERE kind='ExperienceRecord' AND payload LIKE ?", ('%'+eid+'%',))
                row['teacher_seen_before_commit'] = [json.loads(x['payload']).get('teacher_seen_before_commit') for x in exp]
                if arm != 'off':
                    t1 = time.monotonic(); r.enqueue('teacher'); wait(r, t1)
                    msgs = r.store.rows('SELECT id,role,text,status,metadata FROM messages WHERE event_id=? ORDER BY id', (eid,))
                    own = [m for m in msgs if m['role'] == 'assistant']; tea = [m for m in msgs if m['role'] == 'teacher']
                    tt = tea[-1]['text'] if tea else ''; tm = json.loads(tea[-1]['metadata'] or '{}') if tea else {}
                    tok, tnum = U.score(tt, nums, checks)
                    hist, _ = native_history(r.store, r.session, 'z11-probe', 8)
                    htext = json.dumps([dict(h) if not isinstance(h, dict) else h for h in hist], default=str)
                    if leak_v3:
                        leak = (shingles(tt) & shingles('\n'.join(h['text'] for h in hist))) - shingles(out) - shingles(text)
                    elif leak_v2:
                        hplain = norm('\n'.join(h['text'] for h in hist)); leak = {c for c in shared_chunks(norm(tt), hplain) if c not in norm(out) and c not in norm(text)}
                    else:
                        leak = {c for c in shared_chunks(tt, htext) if c not in out and c not in text}
                    row.update({'teacher_status': tea[-1]['status'] if tea else None, 'teacher_text': tt, 'teacher_s': round(time.monotonic()-t1, 2),
                                'teacher_pass': all(tok.values()) and all(tnum.values()),
                                'own_answer_hash_before_teacher': tm.get('own_answer_hash_before_teacher'), 'reference_only': tm.get('reference_only'),
                                'not_fact': tm.get('not_fact'), 'teacher_after_self': bool(tea and own and tea[-1]['id'] > own[-1]['id']),
                                'history_teacher_leak_chunks': len(leak), 'history_roles': sorted({(h['role'] if isinstance(h, dict) else h['role']) for h in hist}) if hist else []})
                    row['history_teacher_leaks'] = sorted(leak)[:5]; row['_eid'] = eid
                    if not deferred:
                        select(r, row, i)
                rows.append(row)
                print(json.dumps({k: row.get(k) for k in ('arm', 'fixture', 'self_pass', 'teacher_pass', 'self_s', 'teacher_s', 'history_teacher_leak_chunks')}), flush=True)
            if deferred:
                for i, row in enumerate(rows):
                    if 'teacher_status' in row: select(r, row, i)
            for row in rows: row.pop('_eid', None)
            row0 = {'arm': arm, 'generation_before': gen0, 'generation_after': r.store.generation_id,
                    'component_generations': r.store.one("SELECT count(*) AS n FROM sqlite_master WHERE name LIKE '%generation%'")['n'], 'tables_before': comp0,
                    'tables_after': r.store.one('SELECT count(*) AS n FROM sqlite_master')['n']}
        finally:
            r.close()
    return rows, row0


def select(r, row, i):
    eid = row['_eid']; session = r.store.one('SELECT session_id FROM events WHERE id=?', (eid,))['session_id']
    if i < SELECT_FIRST and row['teacher_status'] == 'FINAL':
        try:
            r.memory.select(eid, session, 'teacher', None, None, 'fact', 'record')
            r.memory.select(eid, session, 'self', None, None, 'preference', 'record')
            row['selection_error'] = None
        except Exception as exc:
            row['selection_error'] = str(exc)[:200]
        dec = [json.loads(p['payload']) for p in r.store.rows("SELECT payload FROM packets WHERE event_id=? AND kind='HumanDecision' ORDER BY created", (eid,))]
        row['human_decisions'] = [{'kind': d.get('kind'), 'lane': (d.get('selection') or {}).get('lane'),
                                   'fact_authority': (d.get('selection') or {}).get('fact_authority')} for d in dec]
    x = r.memory.experience(eid, session)
    row['experience_fingerprint'] = x['fingerprint_sha256']; row['teacher_truth_authority'] = x['teacher_truth_authority']


def analyse(by, meta):
    off, on, rep = by.get('off', {}), by.get('on', {}), by.get('on_repeat', {})
    if not (off and on and rep): return {}
    t1 = all(r['own_answer_hash_before_teacher'] == r['self_sha'] == r['self_candidate_hash'] and r['teacher_after_self']
             and r['teacher_seen_before_commit'] and not any(r['teacher_seen_before_commit']) for r in on.values())
    t2 = all(r['history_teacher_leak_chunks'] == 0 for r in list(on.values())+list(rep.values()))
    t3 = sum(on[f]['self_output'] == off[f]['self_output'] for f in on)
    sel = [r for r in on.values() if 'human_decisions' in r]
    t4 = bool(sel) and all(r['selection_error'] is None and sorted(d['kind'] for d in r['human_decisions']) == ['fact', 'preference']
                           and any(d['lane'] == 'teacher' and d['fact_authority'] == 'HUMAN_SELECTED_NOT_AUTOMATIC_TRUTH' for d in r['human_decisions'])
                           and r['teacher_truth_authority'] is False for r in sel)
    t5 = sum(rep[f]['experience_fingerprint'] == on[f]['experience_fingerprint'] for f in rep)
    t6 = all(m['generation_before'] == m['generation_after'] and m['tables_before'] == m['tables_after'] for m in meta.values())
    crit = {'T1_self_fixed_before_teacher': {'value': '%d/%d' % (sum(1 for _ in on), len(on)), 'pass': t1},
            'T2_teacher_never_in_history': {'pass': t2},
            'T3_teacher_on_off_same_self': {'value': '%d/%d' % (t3, len(on)), 'pass': t3 == len(on)},
            'T4_preference_vs_fact_separate': {'value': len(sel), 'pass': t4},
            'T5_reproducible_fingerprint': {'value': '%d/%d' % (t5, len(rep)), 'pass': t5 == len(rep)},
            'T6_record_only_no_params': {'pass': t6}}
    better = sum(r['teacher_pass'] and not r['self_pass'] for r in on.values()); worse = sum(r['self_pass'] and not r['teacher_pass'] for r in on.values())
    return {'verdict': 'STEP4_EXIT_PASS' if all(c['pass'] for c in crit.values()) else 'STEP4_EXIT_FAIL', 'criteria': crit,
            'descriptive': {'self_passed': sum(r['self_pass'] for r in on.values()), 'teacher_passed': sum(r['teacher_pass'] for r in on.values()),
                            'teacher_better': better, 'teacher_worse': worse, 'teacher_final': sum(r['teacher_status'] == 'FINAL' for r in on.values()),
                            'mean_teacher_s': round(sum(r['teacher_s'] for r in on.values())/len(on), 1),
                            'mean_self_s': round(sum(r['self_s'] for r in on.values())/len(on), 1)}}


def main(installed, out, limit=None, deferred=False, seed=23, leak_v2=False, leak_v3=False):
    installed = Path(installed).resolve(); out = Path(out); fx = U2.tasks(seed=seed)
    if limit: fx = fx[:limit]
    by, meta, rows = {}, {}, []
    for arm, f in (('off', fx), ('on', fx), ('on_repeat', fx[:20])):
        rs, m = run_arm(installed, arm, f, deferred, leak_v2, leak_v3); rows += rs; meta[arm] = m; by[arm] = {r['fixture']: r for r in rs}
        atomic_write(out, json.dumps({'kind': 'V13_Z11_REFERENCE_TEACHER', 'seed': seed, 'leak_check': 'v3' if leak_v3 else 'v2' if leak_v2 else 'v1', **analyse(by, meta), 'arm_meta': meta,
                                      'teacher_model': json.loads((installed/'config/models.json').read_text()).get('teacher'),
                                      'rows': rows, 'phone_measured': False, 'deferred_selection': deferred,
                                      'prereg': 'docs/proofs/continuation-202610%s/PREREG.md' % ('26/z11d-reference-teacher' if leak_v3 else '26/z11c-reference-teacher' if leak_v2 else '26/z11b-reference-teacher' if deferred else '22/z11-reference-teacher')}, indent=1))
    print(json.dumps(analyse(by, meta), indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]; lim = None; z11c = '--z11c' in a; z11d = '--z11d' in a; deferred = '--z11b' in a or z11c or z11d
    for f in ('--z11b', '--z11c', '--z11d'):
        if f in a: a.remove(f)
    if '--limit' in a:
        i = a.index('--limit'); lim = int(a[i+1]); del a[i:i+2]
    main(a[0], a[1], lim, deferred, 31 if z11d else 29 if z11c else 23, z11c, z11d)
