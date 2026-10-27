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
  d0r   repeat of d0 (noise band: llama threads make temperature-0 offers vary slightly)
Halting policies are live arms (effort `max`): they decide once, before the focal loop, between depth 0 (halt) and depth 1
(continue) from the first B1/B2 offers.
  posthoc  simple readout: continue iff the two first offers disagree (focal.disagreement >= BOOT disagreement_trigger)
  trained  real halt-head path: readout_worker.train on frozen C2 embeddings (input + .2 x B1/B2 trajectory, as
           learning.readout_embedding), labels from training seeds (continue iff d1 passes and d0 fails), scaffold
           label = posthoc; out of support / uncertain -> posthoc
Criteria: docs/proofs/continuation-20261027/z6i-halting/PREREG.md.
Usage: z6i_halting_bench.py run <installed_home> <out.json> <arm,arm,...> --seed N [--limit N] [--checkpoint candidate.npz]
       z6i_halting_bench.py train <train.json> [<train.json> ...] <head_dir>
       z6i_halting_bench.py analyse <test.json> <out.json> [<head_dir>/head.json]
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

ARMS = ('c3', 'scaf', 'd0', 'd0r', 'd1', 'd2', 'posthoc', 'trained')
EFFORT = {'c3': 'disabled', 'scaf': 'max', 'd0': 'max', 'd0r': 'max', 'd1': 'max', 'd2': 'max', 'posthoc': 'max', 'trained': 'max'}
DEPTH = {'d0': 0, 'd0r': 0, 'd1': 1, 'd2': 2}
kind = lambda f: f.rstrip('0123456789')


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def force_depth(k):
    """Bench-only patch of the focal loop: exactly k re-entries (no stable stop, no Age-0 cycle cap); returns undo.
    k may be a callable (loop, first offers, event) -> depth, decided once before the focal loop (live halting policy)."""
    from v13 import focal as F
    orig_run, orig_choose, orig_delta = F.FocalLoop.run, F.choose, F.STABLE_DELTA
    state = {'n': 0, 'decisions': []}

    def run(self, e, version, offers, *, plan=None, **kw):
        d = k(self, offers, e) if callable(k) else k; state['decisions'].append(d)
        plan = dict(plan or {}); plan['max_reentry'] = d; plan['focal_cycles'] = d+1; state['n'] = 0
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
    undo.state = state
    return undo


def pair_of(offers):
    out = {}
    for o in offers:
        out.setdefault(o['role'], o)
    return [out[r] for r in ('B1_DETAIL', 'B2_GIST') if r in out]


def posthoc_decide(loop, offers, e):
    p = pair_of(offers)
    return int(bool(disagree([{'summary': o['offer'].get('summary') or ''} for o in p])))


def head_features(learner, text, pair, deadline):
    """Frozen C2 features of the real halt head (learning.readout_embedding): source + .2 x trajectory context."""
    ctx = dumps({'input': text[:4000], 'trajectory_kind': 'TWO_FROZEN_BODY_OFFERS', 'offers': [{'role': o['role'], 'hypothesis': o['offer']} for o in pair]})
    src = learner.embedding(text, 'z6i-src-'+h(text), deadline); trj = learner.embedding(ctx, 'z6i-ctx-'+h(ctx), deadline)
    return [round(x, 6) for x in (list(src)+[.2*x for x in trj])]


def trained_decider(checkpoint):
    from v13.readout_worker import infer
    log = []

    def decide(loop, offers, e):
        p = pair_of(offers); base = posthoc_decide(loop, offers, e)
        if len(p) != 2: log.append('NO_PAIR'); return base
        try:
            x = head_features(loop.r.learner, loop.s.read_source(e['source_ref']), p, time.monotonic()+120)
            q = infer(x, checkpoint)
        except Exception as exc:
            log.append('ERROR '+type(exc).__name__); return base
        if q['in_support'] and q['confidence'] >= .6 and q['margin'] >= .1: log.append('HEAD'); return int(q['index'])
        log.append('FALLBACK'); return base
    decide.log = log
    return decide


def first_pair(offers, post):
    out = {}
    for o in offers:
        if o['packet_id'] in post or o['role'] in out: continue
        out[o['role']] = o
    return [out[r] for r in ('B1_DETAIL', 'B2_GIST') if r in out]


def run_arm(installed, arm, fx, checkpoint=None):
    from v13 import effort as EF
    from v13.config import initialize, save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    import utility_bench2 as U2
    rows = []; dec = {'posthoc': posthoc_decide, 'trained': trained_decider(checkpoint) if arm == 'trained' else None}.get(arm)
    undo = force_depth(DEPTH[arm]) if arm in DEPTH else force_depth(dec) if dec else (lambda: None)
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
                    st = getattr(undo, 'state', None)
                    if st and st['decisions']: row['depth_decision'] = st['decisions'][-1]; st['decisions'].clear()
                    if dec is not None and getattr(dec, 'log', None): row['head_use'] = dec.log[-1]
                    if arm == 'd0' and len(pair) == 2:  # training features for the halt head
                        try:
                            row['embedding'] = head_features(r.learner, text, pair, time.monotonic()+120)
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


def summ(m):
    n = len(m)
    return {'n': n, 'passed': sum(r['pass'] for r in m.values()), 'mean_turn_s': round(sum(r['turn_s'] for r in m.values())/n, 2),
            'mean_reentries': round(sum(r.get('reentries', 0) for r in m.values())/n, 3),
            'by_class': {CLASS[k]: sum(r['pass'] for f, r in m.items() if kind(f) == k) for k in CLASS if any(kind(f) == k for f in m)}}


def paired(a, b):
    common = [f for f in a if f in b]
    w = sum(a[f]['pass'] and not b[f]['pass'] for f in common); l = sum(b[f]['pass'] and not a[f]['pass'] for f in common)
    return {'n': len(common), 'first_only': w, 'second_only': l, 'p': round(sign_test(w, l), 4)}


def analyse(test_rows, head=None):
    b = by_arm(test_rows); fx = sorted(b['d0']); out = {'arms': {a: summ(m) for a, m in b.items()}, 'halt_head': head}
    fixed = [a for a in ('d0', 'd1', 'd2') if a in b]; pol = [a for a in ('posthoc', 'trained') if a in b]
    if 'd0r' in b:
        flips = sum(b['d0'][f]['pass'] != b['d0r'][f]['pass'] for f in fx)
        out['noise_band'] = {'d0_vs_d0r_flips': flips, 'paired': paired(b['d0'], b['d0r']),
                             'first_offer_text_identical': sum([p['summary'] for p in b['d0'][f]['pair']] == [p['summary'] for p in b['d0r'][f]['pair']] for f in fx)}
    hard = [f for f in fx if 'c3' in b and not b['c3'][f]['pass']]; ref = b['d2'] if 'd2' in b else b['d1']
    def dominated(p):
        s = out['arms'][p]; dom = []
        for a in fixed:
            pr = paired(b[a], b[p])
            if pr['first_only'] > pr['second_only'] and pr['p'] < .05 and out['arms'][a]['mean_turn_s'] <= s['mean_turn_s']: dom.append(a)
        return dom
    def hard_loss(p):
        lost = lambda fs: sum(ref[f]['pass'] and not b[p][f]['pass'] for f in fs); easy = [f for f in fx if f not in hard]
        return {'hard_n': len(hard), 'hard_lost': lost(hard), 'easy_n': len(easy), 'easy_lost': lost(easy),
                'pass': len(hard) == 0 or lost(hard)/len(hard) <= lost(easy)/max(1, len(easy))+.10}
    crit = {}
    for p in pol:
        best = max(out['arms'][a]['passed'] for a in fixed)
        crit[p] = {'K1_not_dominated_by_fixed_depth': {'dominated_by': dominated(p), 'pass': not dominated(p)},
                   'K2_hard_examples': hard_loss(p),
                   'K3_quality_near_best_fixed': {'policy': out['arms'][p]['passed'], 'best_fixed': best, 'pass': out['arms'][p]['passed'] >= best-2},
                   'K4_cheaper_than_deepest': {'policy_s': out['arms'][p]['mean_turn_s'], 'deepest_s': out['arms'][fixed[-1]]['mean_turn_s'],
                                               'pass': out['arms'][p]['mean_turn_s'] < out['arms'][fixed[-1]]['mean_turn_s']}}
        crit[p]['pass'] = all(c['pass'] for c in crit[p].values())
        crit[p]['continue_rate'] = round(sum(bool(r.get('depth_decision')) for r in b[p].values())/len(b[p]), 3)
        if p == 'trained': crit[p]['head_use'] = {u: sum(r.get('head_use') == u for r in b[p].values()) for u in ('HEAD', 'FALLBACK', 'NO_PAIR')}
    out['criteria'] = crit
    if 'trained' in b and 'posthoc' in b:
        pr = paired(b['trained'], b['posthoc']); ts, ps = out['arms']['trained']['mean_turn_s'], out['arms']['posthoc']['mean_turn_s']
        out['K5_trained_beats_posthoc'] = {'value': pr, 'trained_s': ts, 'posthoc_s': ps, 'pass': crit['trained']['pass'] and (
            (pr['first_only'] > pr['second_only'] and pr['p'] < .05) or (pr['first_only'] >= pr['second_only'] and ts < .9*ps))}
    else:
        out['K5_trained_beats_posthoc'] = {'pass': False, 'status': (head or {}).get('status', 'NOT_RUN')}
    out['paired'] = {f'{x}_vs_{y}': paired(b[x], b[y]) for x, y in (('d1', 'd0'), ('d2', 'd1'), ('d2', 'd0'), ('c3', 'd0'), ('c3', 'posthoc'), ('c3', 'trained'),
                     ('scaf', 'd0'), ('scaf', 'd1'), ('posthoc', 'd0'), ('posthoc', 'd1')) if x in b and y in b}
    S = out['arms']
    out['pareto_front'] = sorted(a for a, s in S.items() if not any(t['passed'] >= s['passed'] and t['mean_turn_s'] <= s['mean_turn_s'] and
                                 (t['passed'] > s['passed'] or t['mean_turn_s'] < s['mean_turn_s']) for x, t in S.items() if x != a))
    out['verdict'] = 'Z6I_HALTING_PASS' if any(crit[p]['pass'] for p in crit) else 'Z6I_HALTING_FAIL'
    out['trained_adoption'] = 'ADOPT_CANDIDATE' if out['K5_trained_beats_posthoc']['pass'] else 'KEEP_POSTHOC'
    out['rescue_headroom'] = {'d1_rescues_d0': [f for f in fx if 'd1' in b and b['d1'][f]['pass'] and not b['d0'][f]['pass']],
                              'd1_breaks_d0': [f for f in fx if 'd1' in b and b['d0'][f]['pass'] and not b['d1'][f]['pass']]}
    return out


def main_run(installed, out, arms, seed, limit=None, checkpoint=None):
    installed = Path(installed).resolve(); out = Path(out); fx = fixtures(seed)
    if limit: fx = [f for i, f in enumerate(fx) if i % (len(fx)//limit) == 0][:limit]
    prev = json.loads(out.read_text()) if out.exists() else {'rows': []}
    rows = [r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows += run_arm(installed, arm, fx, checkpoint)
        atomic_write(out, json.dumps({'kind': 'V13_Z6I_HALTING_RUN', 'seed': seed, 'fixtures': [f[0] for f in fx], 'rows': rows, 'checkpoint': checkpoint,
                                      'phone_measured': False, 'prereg': 'docs/proofs/continuation-20261027/z6i-halting/PREREG.md'}))


def main_train(trains, outdir):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    R = [json.loads(Path(p).read_text())['rows'] for p in trains]; info = train_head(R, outdir)
    info['train_files'] = [str(p) for p in trains]
    atomic_write(Path(outdir)/'head.json', json.dumps(info, indent=1)); print(json.dumps(info, indent=1))


def main_analyse(test, out, head=None):
    T = json.loads(Path(test).read_text()); H = json.loads(Path(head).read_text()) if head else None
    res = analyse(T['rows'], H)
    atomic_write(Path(out), json.dumps({'kind': 'V13_Z6I_HALTING', 'test_seed': T['seed'], **res, 'phone_measured': False, 'canonical_gate_pass': False,
                                        'prereg': 'docs/proofs/continuation-20261027/z6i-halting/PREREG.md',
                                        'claim_limit': 'deterministic bench decoding (llama threads still vary slightly), generated English tasks, regex checks, cloud CPU, no energy; d2 lifts the Age-0 one-cycle cap'}, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'halt_head'}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'run':
        seed = int(a[a.index('--seed')+1]); lim = int(a[a.index('--limit')+1]) if '--limit' in a else None
        ck = a[a.index('--checkpoint')+1] if '--checkpoint' in a else None
        main_run(a[1], a[2], a[3].split(','), seed, lim, ck)
    elif a[0] == 'train':
        main_train(a[1:-1], a[-1])
    else:
        main_analyse(a[1], a[2], a[3] if len(a) > 3 else None)
