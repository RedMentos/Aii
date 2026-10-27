#!/usr/bin/env python3
"""WP-Z6i / §24.17 Deliberation trajectory / halting with real C3/B1/B2.

Blueprint §24.17: fixed depth baseline, post-hoc/simple halt readout, trained halt head, quality-vs-latency Pareto,
hard examples must not lose disproportionately by early exit, joint/trained halting only if it beats the post-hoc one.

Deliberation depth here is the number of targeted body re-entries after the first B1/B2 offers (focal loop, WP-T1).
Real runs (same bench handling as Z6a/Z6e: fresh home per arm, temperature 0, post-commit observers cut):
  c3    effort `disabled` (C_native only), reference
  scaf  effort `max`, shipped scaffold (Age 0 caps the focal loop at one cycle)
  d0    effort `max`, forced depth 0 (no re-entry)
  d1    effort `max`, forced depth 1 (one re-entry; target from the focal view, else B1)
  d2    effort `max`, forced depth 2 (bench lifts the Age-0 one-cycle cap; second re-entry goes to the other body)
Halting policies decide once, after the first B1/B2 offers, between halt (= d0 outcome) and continue (= d1 outcome);
their quality/latency is read from the deterministic d0/d1 runs of the same fixture (prefix identity is checked).
  posthoc  simple readout: continue iff the two first offers disagree (focal.disagreement >= BOOT disagreement_trigger)
  trained  real halt-head path: readout_worker.train on frozen C2 embeddings (input + .2 x B1/B2 trajectory, as
           learning.readout_embedding), labels from training seeds (continue iff d1 passes and d0 fails), scaffold
           label = posthoc; out of support / uncertain -> posthoc
Criteria: docs/proofs/continuation-20261027/z6i-halting/PREREG.md.
Usage: z6i_halting_bench.py run <installed_home> <out.json> <arm,arm,...> --seed N [--limit N]
       z6i_halting_bench.py analyse <test.json> <train.json> [<train.json> ...] <out.json>
"""
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, dumps  # noqa: E402
import utility_bench as U  # noqa: E402
from r4_wake_bench import sign_test  # noqa: E402
from z6e_wake_bench import fixtures, CLASS  # noqa: E402

ARMS = ('c3', 'scaf', 'd0', 'd1', 'd2')
EFFORT = {'c3': 'disabled', 'scaf': 'max', 'd0': 'max', 'd1': 'max', 'd2': 'max'}
DEPTH = {'d0': 0, 'd1': 1, 'd2': 2}
kind = lambda f: f.rstrip('0123456789')


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def force_depth(k):
    """Bench-only patch of the focal loop: exactly k re-entries (no stable stop, no Age-0 cycle cap); returns undo."""
    from v13 import focal as F
    orig_run, orig_choose, orig_delta = F.FocalLoop.run, F.choose, F.STABLE_DELTA
    state = {'n': 0}

    def run(self, e, version, offers, *, plan=None, **kw):
        plan = dict(plan or {}); plan['max_reentry'] = k; plan['focal_cycles'] = k+1; state['n'] = 0
        return orig_run(self, e, version, offers, plan=plan, **kw)

    def choose(view, target, queries_left):
        if queries_left > 0:
            if not target:
                target = 'B1_DETAIL' if state['n'] == 0 else 'B2_GIST'
            state['n'] += 1
            return ('QUERY_A' if target == 'B1_DETAIL' else 'QUERY_B'), 'BENCH_FORCED_DEPTH'
        return orig_choose(view, None, 0)
    F.FocalLoop.run, F.choose, F.STABLE_DELTA = run, choose, -1.

    def undo():
        F.FocalLoop.run, F.choose, F.STABLE_DELTA = orig_run, orig_choose, orig_delta
    return undo


def first_pair(offers, post):
    out = {}
    for o in offers:
        if o['packet_id'] in post or o['role'] in out: continue
        out[o['role']] = o
    return [out[r] for r in ('B1_DETAIL', 'B2_GIST') if r in out]


def run_arm(installed, arm, fx):
    from v13 import effort as EF
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    import utility_bench2 as U2
    rows = []; undo = force_depth(DEPTH[arm]) if arm in DEPTH else (lambda: None)
    try:
        with tempfile.TemporaryDirectory(prefix='v13-z6i-') as tmp:
            home = Path(tmp); cfg = initialize(home)
            for n in ('models', 'bin'):
                shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
            shutil.copyfile(installed/'config/models.json', home/'config/models.json')
            save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0} | U2.BENCH_CFG)
            r = Runtime(home); EF.set_mode(r.store, EFFORT[arm])
            try:
                for fid, text, nums, checks in fx:
                    r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); end = t0+900; answer_s = None
                    while not r.idle():
                        if answer_s is None:
                            m = r.store.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))
                            if m and m['status'] in ('FINAL', 'CANCELLED', 'DEADLINE', 'ERROR', 'INTERRUPTED'):
                                answer_s = round(time.monotonic()-t0, 2); r.cancel()
                        if time.monotonic() > end:
                            r.cancel(); break
                        time.sleep(.1)
                    a = audit_event(r.store, eid); out = a.get('output') or ''
                    post = {json.loads(x['metrics']).get('id') for x in r.store.rows("SELECT metrics FROM telemetry WHERE kind='postcommit_offer' AND event_id=?", (eid,))}
                    offers = [o for o in a.get('offers', []) if o['packet_id'] not in post]
                    pair = first_pair(offers, post); ok, num = U.score(out, nums, checks)
                    fr = r.store.rows("SELECT payload FROM packets WHERE kind='FocalCycle' AND event_id=? ORDER BY rowid", (eid,))
                    traj = [json.loads(x['payload']) for x in fr]
                    row = {'fixture': fid, 'arm': arm, 'pass': all(ok.values()) and all(num.values()),
                           'turn_s': answer_s if answer_s is not None else round(time.monotonic()-t0, 2), 'status': a.get('status'),
                           'offers': [o['role'] for o in offers], 'reentries': max(0, len(offers)-len(pair)),
                           'pair': [{'role': o['role'], 'summary_sha': h(dumps(o['offer'])), 'summary': (o['offer'].get('summary') or '')[:600]} for o in pair],
                           'focal_decisions': [t.get('decision') for t in traj], 'output': out[:400]}
                    if arm == 'd0' and len(pair) == 2:  # frozen C2 features of the real halt head (learning.readout_embedding)
                        try:
                            ctx = dumps({'input': text[:4000], 'trajectory_kind': 'TWO_FROZEN_BODY_OFFERS', 'offers': [{'role': o['role'], 'hypothesis': o['offer']} for o in pair]})
                            dl = time.monotonic()+120
                            src = r.learner.embedding(text, 'z6i-src-'+h(text), dl); trj = r.learner.embedding(ctx, 'z6i-ctx-'+h(ctx), dl)
                            row['embedding'] = [round(x, 6) for x in (list(src)+[.2*x for x in trj])]
                        except Exception as exc:
                            row['embedding_error'] = type(exc).__name__+': '+str(exc)[:200]
                    rows.append(row)
                    print(json.dumps({k: row[k] for k in ('arm', 'fixture', 'pass', 'turn_s', 'offers', 'reentries')}), flush=True)
            finally:
                r.close()
    finally:
        undo()
    return rows


# ---------------------------------------------------------------- analysis
def by_arm(rows):
    out = {}
    for r in rows: out.setdefault(r['arm'], {})[r['fixture']] = r
    return out


def disagree(pair):
    from v13.focal import disagreement, BOOT
    if len(pair) != 2: return None
    return disagreement(pair[0]['summary'], pair[1]['summary']) >= BOOT['disagreement_trigger']


def labels(rows):
    b = by_arm(rows); out = []
    for f in sorted(set(b.get('d0', {})) & set(b.get('d1', {}))):
        r0, r1 = b['d0'][f], b['d1'][f]
        if 'embedding' not in r0: continue
        out.append({'fixture': f, 'y': int(r1['pass'] and not r0['pass']), 'scaffold': int(bool(disagree(r0['pair']))), 'x': r0['embedding']})
    return out


def train_head(train_rows, workdir):
    from v13.readout_worker import train
    from v13.config import KNOBS
    L = [l for rows in train_rows for l in labels(rows)]
    ys = [l['y'] for l in L]
    info = {'n': len(L), 'continue_labels': sum(ys), 'halt_labels': len(ys)-sum(ys)}
    cfg = {k: v[0] for k, v in KNOBS.items()} | {'readout_steps': 480}
    try:
        m = train({'component': 'halt', 'config': cfg, 'embeddings': [l['x'] for l in L], 'labels': ys, 'scaffold_labels': [l['scaffold'] for l in L],
                   'context_hashes': [h(dumps(l['x'])) for l in L]}, workdir)
        info['metrics'] = {k: m[k] for k in ('held_out', 'effective_accuracy', 'scaffold_accuracy', 'accepted_test_count', 'missed_continue', 'commit_eligible', 'calibration_pass')}
        info['checkpoint'] = str(Path(workdir)/'candidate.npz'); info['status'] = 'TRAINED'
    except ValueError as exc:
        info['status'] = 'NOT_TRAINABLE'; info['error'] = str(exc)
    return info


def policy_rows(b, decide):
    """Per fixture: halt -> d0 outcome, continue -> d1 outcome."""
    out = {}
    for f in b['d0']:
        c = decide(f); src = b['d1'][f] if c else b['d0'][f]
        out[f] = {'pass': src['pass'], 'turn_s': src['turn_s'], 'continue': bool(c)}
    return out


def summ(m):
    n = len(m)
    return {'n': n, 'passed': sum(r['pass'] for r in m.values()), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
            'by_class': {CLASS[k]: sum(r['pass'] for f, r in m.items() if kind(f) == k) for k in CLASS if any(kind(f) == k for f in m)}}


def paired(a, b):
    common = [f for f in a if f in b]
    w = sum(a[f]['pass'] and not b[f]['pass'] for f in common); l = sum(b[f]['pass'] and not a[f]['pass'] for f in common)
    return {'n': len(common), 'first_only': w, 'second_only': l, 'p': round(sign_test(w, l), 4)}


def analyse(test_rows, train_rows, workdir):
    b = by_arm(test_rows); fx = sorted(b['d0'])
    prefix = {f: [p['summary_sha'] for p in b['d0'][f]['pair']] == [p['summary_sha'] for p in b['d1'][f]['pair']] for f in fx}
    head = train_head(train_rows, workdir)
    trained_dec = {}; accepted = 0
    if head['status'] == 'TRAINED':
        from v13.readout_worker import infer
        for f in fx:
            r0 = b['d0'][f]; base = bool(disagree(r0['pair']))
            if 'embedding' not in r0: trained_dec[f] = base; continue
            p = infer(r0['embedding'], head['checkpoint'])
            if p['in_support'] and p['confidence'] >= .6 and p['margin'] >= .1: trained_dec[f] = bool(p['index']); accepted += 1
            else: trained_dec[f] = base
    pol = {'posthoc': policy_rows(b, lambda f: bool(disagree(b['d0'][f]['pair'])))}
    if trained_dec: pol['trained'] = policy_rows(b, lambda f: trained_dec[f])
    arms = {a: {f: {'pass': r['pass'], 'turn_s': r['turn_s']} for f, r in b[a].items()} for a in b}
    allp = arms | pol
    out = {'arms': {a: summ(m) for a, m in allp.items()}, 'prefix_identical': sum(prefix.values()), 'prefix_n': len(fx), 'halt_head': head,
           'trained_accepted': accepted, 'continue_rate': {p: round(sum(r['continue'] for r in m.values())/len(m), 3) for p, m in pol.items()}}
    fixed = [a for a in ('d0', 'd1', 'd2') if a in arms]
    def dominated(p):
        s = out['arms'][p]; dom = []
        for a in fixed:
            pr = paired(arms[a], allp[p])
            if pr['first_only'] > pr['second_only'] and pr['p'] < .05 and out['arms'][a]['mean_turn_s'] <= s['mean_turn_s']: dom.append(a)
        return dom
    hard = [f for f in fx if 'c3' in arms and not arms['c3'][f]['pass']]
    def hard_loss(p):
        ref = arms['d2'] if 'd2' in arms else arms['d1']
        lost = lambda fs: sum(ref[f]['pass'] and not allp[p][f]['pass'] for f in fs)
        easy = [f for f in fx if f not in hard]
        return {'hard_n': len(hard), 'hard_lost': lost(hard), 'easy_n': len(easy), 'easy_lost': lost(easy),
                'pass': len(hard) == 0 or lost(hard)/len(hard) <= lost(easy)/max(1, len(easy))+.10}
    crit = {}
    for p in pol:
        crit[p] = {'K1_not_dominated_by_fixed_depth': {'dominated_by': dominated(p), 'pass': not dominated(p)},
                   'K2_hard_examples': hard_loss(p),
                   'K3_quality_near_best_fixed': {'policy': out['arms'][p]['passed'], 'best_fixed': max(out['arms'][a]['passed'] for a in fixed),
                                                  'pass': out['arms'][p]['passed'] >= max(out['arms'][a]['passed'] for a in fixed)-2},
                   'K4_cheaper_than_deepest': {'policy_s': out['arms'][p]['mean_turn_s'], 'deepest_s': out['arms'][fixed[-1]]['mean_turn_s'],
                                               'pass': out['arms'][p]['mean_turn_s'] < out['arms'][fixed[-1]]['mean_turn_s']}}
        crit[p]['pass'] = all(c['pass'] for c in crit[p].values())
    out['criteria'] = crit
    if 'trained' in pol:
        pr = paired(pol['trained'], pol['posthoc'])
        out['K5_trained_beats_posthoc'] = {'value': pr, 'trained_s': out['arms']['trained']['mean_turn_s'], 'posthoc_s': out['arms']['posthoc']['mean_turn_s'],
                                           'pass': crit['trained']['pass'] and ((pr['first_only'] > pr['second_only'] and pr['p'] < .05) or
                                                    (pr['first_only'] >= pr['second_only'] and out['arms']['trained']['mean_turn_s'] < .9*out['arms']['posthoc']['mean_turn_s']))}
    else:
        out['K5_trained_beats_posthoc'] = {'pass': False, 'status': head['status']}
    out['paired'] = {f'{x}_vs_{y}': paired(allp[x], allp[y]) for x, y in (('d1', 'd0'), ('d2', 'd1'), ('d2', 'd0'), ('c3', 'd0'), ('c3', 'posthoc'), ('scaf', 'd0'), ('scaf', 'd1'))
                     if x in allp and y in allp}
    pareto = []
    for a, s in out['arms'].items():
        if not any(t['passed'] >= s['passed'] and t['mean_turn_s'] <= s['mean_turn_s'] and (t['passed'] > s['passed'] or t['mean_turn_s'] < s['mean_turn_s'])
                   for x, t in out['arms'].items() if x != a): pareto.append(a)
    out['pareto_front'] = sorted(pareto)
    any_pass = any(crit[p]['pass'] for p in crit)
    out['verdict'] = 'Z6I_HALTING_PASS' if any_pass else 'Z6I_HALTING_FAIL'
    if out['prefix_identical'] < .9*len(fx): out['verdict'] = 'Z6I_INVALID_PREFIX'  # halting read from d0/d1 needs the same first offers
    out['trained_adoption'] = 'ADOPT_CANDIDATE' if out['K5_trained_beats_posthoc']['pass'] else 'KEEP_POSTHOC'
    out['rescue_headroom'] = {'d1_rescues_d0': [f for f in fx if b['d1'][f]['pass'] and not b['d0'][f]['pass']],
                              'd1_breaks_d0': [f for f in fx if b['d0'][f]['pass'] and not b['d1'][f]['pass']]}
    return out


def main_run(installed, out, arms, seed, limit=None):
    installed = Path(installed).resolve(); out = Path(out); fx = fixtures(seed)
    if limit: fx = [f for i, f in enumerate(fx) if i % (len(fx)//limit) == 0][:limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows += run_arm(installed, arm, fx)
        atomic_write(out, json.dumps({'kind': 'V13_Z6I_HALTING_RUN', 'seed': seed, 'fixtures': [f[0] for f in fx], 'rows': rows,
                                      'phone_measured': False, 'prereg': 'docs/proofs/continuation-20261027/z6i-halting/PREREG.md'}))


def main_analyse(test, trains, out):
    T = json.loads(Path(test).read_text()); R = [json.loads(Path(p).read_text())['rows'] for p in trains]
    with tempfile.TemporaryDirectory(prefix='v13-z6i-head-') as wd:
        res = analyse(T['rows'], R, wd)
    atomic_write(Path(out), json.dumps({'kind': 'V13_Z6I_HALTING', 'test_seed': T['seed'], 'train_seeds': [json.loads(Path(p).read_text())['seed'] for p in trains],
                                        **res, 'phone_measured': False, 'canonical_gate_pass': False,
                                        'prereg': 'docs/proofs/continuation-20261027/z6i-halting/PREREG.md',
                                        'claim_limit': 'deterministic bench decoding, generated English tasks, regex checks, cloud CPU, no energy; d2 lifts the Age-0 one-cycle cap'}, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ('halt_head',)}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'run':
        seed = int(a[a.index('--seed')+1]); lim = int(a[a.index('--limit')+1]) if '--limit' in a else None
        main_run(a[1], a[2], a[3].split(','), seed, lim)
    else:
        main_analyse(a[1], a[2:-1], a[-1])
