"""Thread Q: `eligibility` in the real runtime tool path (ToolStep -> C5 EXTERNAL_TOOL -> TOOL_RESULT layer -> body -> broker).

WP-W2c/W2d measured the rule-anchored recipe offline and with recorded producer handoffs (wrong committed decisions -> 0).
Here it runs inside normal runtime turns on C3 LFM2.5-350M (observers off, R4 BENCH_CFG, history_turns 2, new session per
task), per task two arms:
  c3_alone     eligibility not enabled (ToolStep never reads values, no extra model call)
  tool_active  eligibility enabled by the user AND the SYSTEM-origin policy approved. Age 0 forbids SYSTEM tool choice, so
               the measurement replaces the Age verdict for eligibility only (step 'age_right_measurement'); schema, enable,
               C3 typed read, rule-anchored guard, C5 gate, TOOL_RESULT layer and broker stay the unchanged runtime path.
Generated tasks (English, the guard's wording), four kinds:
  complete   one turn: rules + options + question
  missing    one turn: one rule left out -> the right answer is UNKNOWN
  earlier    two turns: turn 1 states the rules, turn 2 the options ("Apply earlier project rules.")
  override   two turns: turn 2 changes one earlier rule; tasks are drawn so the stale rule gives a different decision
Scoring: v13.agi.eligibility.answer_action (fixed parser) on the body's answer -> A|B|NONE|UNKNOWN|None.
  correct          parsed decision == oracle action
  wrong_committed  parsed decision in A/B/NONE and != oracle (the harmful case)
  tool_wrong       tool_active only: the recipe's own decision was A/B/NONE and != oracle
  shown_correct    tool_active only: correct, or the broker's late correction (applied) states the oracle decision
  capture   eligibility_live.py capture <installed_home> <seed> <n_per_kind> <out.json>
  prereg    eligibility_live.py prereg <dev.json> <prereg.json>
  evaluate  eligibility_live.py evaluate <prereg.json> <fresh.json> <report.json>
Dev seed 7 is only for catching wiring bugs; fresh seed 29 (15 per kind) is run once after the preregistration is pushed.
Claim limit: generated English tasks in the guard's wording, regex parser, cloud CPU, Age right replaced for the
measurement; not a Redmi number and not STEP2 (one body, no B1/B2 transport)."""
import hashlib
import json
import math
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from v13.agi import eligibility as E  # noqa: E402
import utility_bench2 as U2  # noqa: E402

FRESH_SEED = 29
FRESH_PER_KIND = 15
KINDS = ('complete', 'missing', 'earlier', 'override')
ARMS = ('c3_alone', 'tool_active')
NAMES = ('Aster', 'Birch', 'Cobalt', 'Delta', 'Ember', 'Fjord', 'Garnet', 'Heron', 'Iris', 'Juniper', 'Kestrel', 'Larch',
         'Marlow', 'Nimbus', 'Onyx', 'Pike', 'Quarry', 'Raven', 'Sorrel', 'Thistle', 'Umbra', 'Vesper', 'Willow', 'Xenon')
QUESTIONS = ('Compute remaining budget and eligibility; choose cheapest eligible.',
             'Which option should we choose? Pick the cheapest eligible option and give the remaining budget.')
CFG = {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 2, 'observer_mode': 'off'}
DECISION = (f"Fresh seed {FRESH_SEED}, {FRESH_PER_KIND} tasks per kind ({4*FRESH_PER_KIND} total), tool_active vs c3_alone paired "
            "on the same task. TOOL_LIVE_SUPPORTED iff (a) net correct wins >= +10 AND two-sided sign test p < .05, (b) "
            "wrong_committed(tool_active) <= wrong_committed(c3_alone), (c) tool_wrong == 0 (the recipe never commits a wrong "
            "decision), and (d) no kind loses more than 2 tasks net. Second verdict, fixed in advance as well: TOOL_SHOWN_SUPPORTED "
            "iff shown_correct(tool_active) vs correct(c3_alone) (what the user sees including the broker's late correction) has "
            "net wins >= +10 AND sign test p < .05 AND (c). Dev seed 7 showed the 350M body often keeps its own decision next to the "
            "TOOL_RESULT layer, so the first verdict may fail while the second passes; both are reported. Reported, not part of the "
            "verdicts: per kind, proposals, executed calls, read failures, guard refusals, values read exactly, turn time.")


def rules_text(p, r, omit=None):
    s = [f'Project {p}.']
    if omit != 'budget': s.append(f"Budget {r['budget']} euros.")
    if omit != 'deadline': s.append(f"Deadline {r['deadline']} days.")
    if omit != 'local_only': s.append(f"Local-only requirement: {'true' if r['local_only'] else 'false'}.")
    return ' '.join(s)


def options_text(opts):
    return ' '.join(f"Option {o['entity']}: cost {o['cost']} euros, duration {o['days']} days, local {'true' if o['local'] else 'false'}."
                    for o in opts)


def oracle(r, opts):
    return E.recipe(r.get('budget'), r.get('deadline'), r.get('local_only'), opts)[0]


def gen(seed, per_kind):
    """Tasks with balanced oracle actions (A/B/NONE) for complete/earlier/override; UNKNOWN for missing."""
    rnd = random.Random(seed); rows = []; names = list(NAMES); rnd.shuffle(names)
    for kind in KINDS:
        targets = ['UNKNOWN']*per_kind if kind == 'missing' else [('A', 'B', 'NONE')[i % 3] for i in range(per_kind)]
        for i, want in enumerate(targets):
            while True:
                r = {'budget': rnd.randrange(40, 91), 'deadline': rnd.randrange(3, 11), 'local_only': rnd.random() < .5}
                opts = [{'entity': e, 'cost': rnd.randrange(30, 96), 'days': rnd.randrange(2, 13), 'local': rnd.random() < .5} for e in 'AB']
                if opts[0]['cost'] == opts[1]['cost']: continue
                idx = KINDS.index(kind)*per_kind+i; p = names[idx % len(names)]+(str(idx//len(names)+1) if idx >= len(names) else ''); q = rnd.choice(QUESTIONS)
                if kind == 'missing':
                    omit = rnd.choice(('budget', 'deadline', 'local_only')); full = oracle(r, opts)
                    if full == 'UNKNOWN': continue
                    turns = [rules_text(p, r, omit)+' '+options_text(opts)+' '+q]; truth = dict(r, **{omit: None}); act = 'UNKNOWN'
                elif oracle(r, opts) != want and kind != 'override': continue
                elif kind == 'complete':
                    turns = [rules_text(p, r)+' '+options_text(opts)+' '+q]; truth = r; act = want
                elif kind == 'earlier':
                    turns = [rules_text(p, r)+' Please keep these rules for later.', f'Project {p}. Apply earlier project rules. '+options_text(opts)+' '+q]
                    truth = r; act = want
                else:
                    k = rnd.choice(('budget', 'deadline', 'local_only'))
                    v = (not r[k]) if k == 'local_only' else rnd.randrange(40, 91) if k == 'budget' else rnd.randrange(3, 11)
                    new = dict(r, **{k: v})
                    if oracle(new, opts) != want or oracle(r, opts) == want: continue
                    phrase = {'budget': f'budget {v} euros', 'deadline': f'deadline {v} days', 'local_only': f"local-only requirement: {'true' if v else 'false'}"}[k]
                    turns = [rules_text(p, r)+' Please keep these rules for later.',
                             f'Project {p}. Apply earlier project rules, but now {phrase}. '+options_text(opts)+' '+q]
                    truth = new; act = want
                rows.append({'id': f'{kind}{i:02d}', 'kind': kind, 'project': p, 'turns': turns, 'oracle': act,
                             'truth': {'options': opts, **{k: truth.get(k) for k in ('budget', 'deadline', 'local_only')}}})
                break
    return rows


def approve_measurement(reg, on):
    """Replace only the Age verdict for SYSTEM-origin eligibility; schema/enable/guard decisions stay the runtime's."""
    if not hasattr(reg, '_policy_orig'):
        reg._policy_orig = reg._policy
    orig = reg._policy_orig

    def policy(spec, origin, args, confirmed=False):
        status, why, steps = orig(spec, origin, args, confirmed)
        if not (on and spec.name == 'eligibility' and origin == 'SYSTEM' and spec.name in reg.box.load()[0]['enabled']):
            return status, why, steps
        if any(not ok for name, ok in steps if name != 'c5'):
            return status, why, steps
        return 'APPROVED', 'AGE_RIGHT_MEASUREMENT', [s for s in steps if s[0] != 'c5']+[['c5', True], ['age_right_measurement', True]]
    reg._policy = policy


def run_turn(r, text):
    from v13.proofs import audit_event
    t0 = time.monotonic(); eid = r.submit(text); end = t0+900
    while not r.idle():
        if time.monotonic() > end:
            r.cancel(); break
        time.sleep(.1)
    return eid, audit_event(r.store, eid), round(time.monotonic()-t0, 2)


def task_turns(r, task):
    r.session = r.store.new_session(); first = []
    for text in task['turns'][:-1]:
        _, a, s = run_turn(r, text); first.append({'status': a.get('status'), 'turn_s': s})
    eid, a, s = run_turn(r, task['turns'][-1]); out = a.get('output') or ''; meta = a.get('output_metadata') or {}
    prop = r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ToolProposal' ORDER BY rowid DESC LIMIT 1", (eid,))
    prop = json.loads(prop['payload']) if prop else None
    fails = [json.loads(x['metrics']).get('stage') for x in r.store.rows("SELECT metrics FROM telemetry WHERE event_id=? AND kind='tool_step_unavailable'", (eid,))]
    brk = r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='OutputBrokerDecision' ORDER BY rowid DESC LIMIT 1", (eid,))
    corr = [x for x in (json.loads(brk['payload']).get('late') or []) if x.get('kind') == 'CORRECTION' and x.get('applied')] if brk else []
    decision = None
    if prop and prop.get('tool') == 'eligibility':
        try: decision = E.tool(**prop['args'])
        except Exception: decision = None
    parsed = E.answer_action(out)
    return {'parsed': parsed, 'correct': parsed == task['oracle'], 'wrong_committed': parsed in ('A', 'B', 'NONE') and parsed != task['oracle'],
            'status': a.get('status'), 'turn_s': s, 'first_turns': first, 'output': out[:500],
            'tool_call': meta.get('tool_call'), 'tool_shadow': meta.get('tool_shadow'), 'tool_failures': fails,
            'proposal': None if prop is None else {'tool': prop.get('tool'), 'policy': prop.get('policy_status'), 'args': prop.get('args')},
            'decision': None if decision is None else {'action': decision['action'], 'rejected': decision['rejected']},
            'correction_applied': bool(corr)}


def values_exact(row, task):
    p = row['proposal']
    if not p or p['tool'] != 'eligibility': return None
    a = p['args']; t = task['truth']; o = t['options']
    got = (a['a_cost'], a['a_days'], a['a_local'], a['b_cost'], a['b_days'], a['b_local'], a.get('budget'), a.get('deadline'), a.get('local_only'))
    return got == (o[0]['cost'], o[0]['days'], o[0]['local'], o[1]['cost'], o[1]['days'], o[1]['local'], t['budget'], t['deadline'], t['local_only'])


def capture(installed, seed, per_kind, path):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    from v13.agi import hub
    installed = Path(installed).resolve(); rows = []; tasks = gen(seed, per_kind)
    with tempfile.TemporaryDirectory(prefix='v13-elig-live-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | CFG | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home); reg = hub(r).tools
        try:
            for task in tasks:
                row = {'task': task['id'], 'kind': task['kind'], 'oracle': task['oracle']}
                for arm in ARMS:
                    on = arm == 'tool_active'; reg.enable('eligibility', on); approve_measurement(reg, on)
                    row[arm] = task_turns(r, task)
                a = row['tool_active']
                a['tool_wrong'] = bool(a['decision'] and a['decision']['action'] in ('A', 'B', 'NONE') and a['decision']['action'] != task['oracle'])
                a['shown_correct'] = a['correct'] or bool(a['correction_applied'] and a['decision'] and a['decision']['action'] == task['oracle'])
                row['values_exact'] = values_exact(a, task)
                rows.append(row)
                print(json.dumps({'task': task['id'], 'oracle': task['oracle'], 'c3': row['c3_alone']['parsed'], 'tool': a['parsed'],
                                  'decision': (a['decision'] or {}).get('action'), 'call': (a['tool_call'] or {}).get('status'),
                                  'fails': a['tool_failures'], 'values_exact': row['values_exact']}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_ELIGIBILITY_LIVE', 'task_seed': seed, 'per_kind': per_kind,
                                                     'script_sha256': sha(__file__), 'code_sha256': code_sha(), 'cfg': CFG | U2.BENCH_CFG,
                                                     'tasks_sha256': hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest(),
                                                     'rows': rows}, indent=1))
        finally:
            r.close()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_sha():
    base = Path(__file__).resolve().parents[1]/'v13'
    return {p: sha(base/p) for p in ('toolstep.py', 'agi/eligibility.py', 'agi/tools.py', 'transaction.py', 'runtime.py', 'broker.py', 'history.py')}


def sign_p(w, l):
    n = w+l
    return 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(w, l)+1))/2**n)


def summarize(rows):
    def block(rs):
        w = sum(r['tool_active']['correct'] and not r['c3_alone']['correct'] for r in rs)
        l = sum(r['c3_alone']['correct'] and not r['tool_active']['correct'] for r in rs)
        a = [r['tool_active'] for r in rs]
        sw = sum(r['tool_active']['shown_correct'] and not r['c3_alone']['correct'] for r in rs)
        sl = sum(r['c3_alone']['correct'] and not r['tool_active']['shown_correct'] for r in rs)
        return {'n': len(rs), 'correct': {arm: sum(r[arm]['correct'] for r in rs) for arm in ARMS},
                'wrong_committed': {arm: sum(r[arm]['wrong_committed'] for r in rs) for arm in ARMS},
                'unparsed': {arm: sum(r[arm]['parsed'] is None for r in rs) for arm in ARMS},
                'wins': w, 'losses': l, 'net': w-l, 'sign_test_p': round(sign_p(w, l), 4),
                'tool_wrong': sum(x['tool_wrong'] for x in a), 'shown_correct': sum(x['shown_correct'] for x in a),
                'shown_wins': sw, 'shown_losses': sl, 'shown_net': sw-sl, 'shown_sign_test_p': round(sign_p(sw, sl), 4),
                'proposals': sum(bool(x['proposal']) for x in a), 'executed': sum((x['tool_call'] or {}).get('status') == 'EXECUTED' for x in a),
                'read_failures': sum('elig_read' in x['tool_failures'] for x in a),
                'decision_unknown': sum(bool(x['decision'] and x['decision']['action'] == 'UNKNOWN') for x in a),
                'decision_correct': sum(bool(x['decision'] and x['decision']['action'] == r['oracle']) for x, r in zip(a, rs)),
                'values_exact': sum(bool(r['values_exact']) for r in rs), 'corrections': sum(x['correction_applied'] for x in a),
                'turn_s_median': {arm: sorted(r[arm]['turn_s'] for r in rs)[len(rs)//2] for arm in ARMS}}
    out = {'all': block(rows)}
    for k in KINDS:
        rs = [r for r in rows if r['kind'] == k]
        if rs: out[k] = block(rs)
    return out


def prereg(dev, out):
    d = json.loads(Path(dev).read_text())
    if d['task_seed'] == FRESH_SEED or d.get('script_sha256') != sha(__file__) or d.get('code_sha256') != code_sha():
        raise SystemExit('dev capture is fresh, or from another script/code version')
    body = {'schema': 'v13-eligibility-live-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'dev_seed': d['task_seed'], 'dev_sha256': sha(dev), 'dev': summarize(d['rows']), 'fresh_task_seed': FRESH_SEED,
            'fresh_per_kind': FRESH_PER_KIND, 'fresh_tasks_sha256': hashlib.sha256(json.dumps(gen(FRESH_SEED, FRESH_PER_KIND), sort_keys=True).encode()).hexdigest(),
            'arms': ARMS, 'kinds': KINDS, 'cfg': CFG | U2.BENCH_CFG, 'decision_rule': DECISION, 'script_sha256': sha(__file__), 'code_sha256': code_sha()}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['code_sha256'] != code_sha():
        raise SystemExit('script or runtime code changed since preregistration')
    d = json.loads(Path(fresh).read_text()); rows = d['rows']
    if d['task_seed'] != FRESH_SEED or d['per_kind'] != FRESH_PER_KIND or d.get('script_sha256') != reg['script_sha256'] \
            or d.get('code_sha256') != reg['code_sha256'] or d.get('tasks_sha256') != reg['fresh_tasks_sha256'] or len(rows) != 4*FRESH_PER_KIND:
        raise SystemExit('fresh capture incomplete or wrong seed/script/code/tasks')
    res = summarize(rows); o = res['all']
    drop = max(-res[k]['net'] for k in KINDS)
    crit = {'a_net_and_sign': o['net'] >= 10 and o['sign_test_p'] < .05,
            'b_wrong_committed_not_higher': o['wrong_committed']['tool_active'] <= o['wrong_committed']['c3_alone'],
            'c_tool_never_wrong': o['tool_wrong'] == 0, 'd_no_kind_loses_more_than_2': drop <= 2}
    shown = {'net_and_sign': o['shown_net'] >= 10 and o['shown_sign_test_p'] < .05, 'c_tool_never_wrong': o['tool_wrong'] == 0}
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'summary': res, 'criteria': crit, 'max_kind_net_loss': drop,
            'verdict': 'TOOL_LIVE_SUPPORTED' if all(crit.values()) else 'NOT_SUPPORTED', 'shown_criteria': shown,
            'shown_verdict': 'TOOL_SHOWN_SUPPORTED' if all(shown.values()) else 'NOT_SUPPORTED',
            'age_right_replaced_for_measurement': True, 'phone_measured': False, 'step2_changed': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], int(a[2]), int(a[3]), a[4])
    elif a[0] == 'prereg':
        prereg(a[1], a[2])
    else:
        evaluate(a[1], a[2], a[3])
