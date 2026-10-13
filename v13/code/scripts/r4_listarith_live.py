"""R4 part 6: `list_arith` in the real runtime tool path (ToolStep -> C5 EXTERNAL_TOOL -> TOOL_RESULT layer -> body).

Part 5 (r4_typed_recipe.py) appended the exact value as user text. Here nothing is appended: per task two runtime turns
on the same C3 LFM2.5-350M (R4 BENCH_CFG, observers off, new session each):
  c3_alone     list_arith not enabled (ToolStep never reads values, no model call)
  tool_active  list_arith enabled by the user AND the SYSTEM-origin policy approved. Age 0 forbids SYSTEM tool choice, so
               the measurement replaces the Age verdict for list_arith only (step 'age_right_measurement'); everything
               else (schema, enable, number guard, C5 gate, TOOL_RESULT layer, broker) is the unchanged runtime path.
Task sets (all from utility_bench2.tasks(seed), checks unchanged): 'orig' = 60 tasks as generated; 'match' = the
summary/compare tasks with a reworded question the BOOT wording rule still recognises; 'nomatch' = compare tasks reworded so
the rule does not fire (expected: no proposal, no extra model call, no harm). Summary tasks cannot be in 'nomatch': their data
line itself says "Total:", so the rule fires on the data, not on the question (a known weakness of the BOOT rule).
  capture   r4_listarith_live.py capture <installed_home> <seed> <out.json> [limit]
  prereg    r4_listarith_live.py prereg <dev.json> <prereg.json>
  evaluate  r4_listarith_live.py evaluate <prereg.json> <fresh.json> <report.json>
Dev seed 7 (exposed by parts 3-5) is only for catching wiring bugs; fresh seed 19 tests once.
Claim limit: generated English tasks, regex checks, cloud CPU, Age right replaced for the measurement; not a Redmi number."""
import hashlib
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
import utility_bench2 as U2  # noqa: E402
import utility_bench as U  # noqa: E402

FRESH_SEED = 19
ARMS = ('c3_alone', 'tool_active')
SUMMARY_Q = 'Is the summary line correct? Give the correct total.'
COMPARE_Q = 'Which city had the most rain, and how many millimetres more than the city with the least?'
REWORD = {'match': {'summary': 'Does that line add up? Tell me the right sum of the items.',
                    'compare': 'Which city was the wettest, and how much more rain did it get than the driest city?'},
          'nomatch': {'compare': 'Which city was the wettest, and by how many millimetres did it exceed the driest one?'}}
DECISION = (f"Fresh seed {FRESH_SEED}, set 'orig', 60 tasks: tool_active vs c3_alone paired on the same task. TOOL_PATH_SUPPORTED "
            "iff net wins >= +5 AND two-sided sign test p < .05 AND no task kind loses more than 2. Reported, not part of the verdict: "
            "set 'match' (same direction expected), set 'nomatch' (expected 0 proposals and |net| <= 2), value correctness, guard refusals, "
            "C5 tool selections, pass including the broker correction line.")


def task_sets(seed):
    orig = U2.tasks(seed); out = {'orig': orig}
    for name, q in REWORD.items():
        rows = []
        for fid, text, nums, checks in orig:
            kind = fid.rstrip('0123456789')
            if kind in q:
                old = SUMMARY_Q if kind == 'summary' else COMPARE_Q
                assert text.endswith(old), fid
                rows.append((fid, text[:-len(old)]+q[kind], nums, checks))
        out[name] = rows
    return out


def approve_measurement(reg, on):
    """Replace only the Age verdict for SYSTEM-origin list_arith; schema/enable/guard decisions stay the runtime's."""
    if not hasattr(reg, '_policy_orig'):
        reg._policy_orig = reg._policy
    orig = reg._policy_orig

    def policy(spec, origin, args, confirmed=False):
        status, why, steps = orig(spec, origin, args, confirmed)
        if not (on and spec.name == 'list_arith' and origin == 'SYSTEM' and spec.name in reg.box.load()[0]['enabled']):
            return status, why, steps
        if any(not ok for name, ok in steps if name != 'c5'):
            return status, why, steps
        return 'APPROVED', 'AGE_RIGHT_MEASUREMENT', [s for s in steps if s[0] != 'c5']+[['c5', True], ['age_right_measurement', True]]
    reg._policy = policy


def turn(r, text, nums, checks):
    from v13.proofs import audit_event
    r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); end = t0+900
    while not r.idle():
        if time.monotonic() > end:
            r.cancel(); break
        time.sleep(.1)
    a = audit_event(r.store, eid); out = a.get('output') or ''; meta = a.get('output_metadata') or {}
    ok, num = U.score(out, nums, checks)
    prop = r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ToolProposal' ORDER BY rowid DESC LIMIT 1", (eid,))
    prop = json.loads(prop['payload']) if prop else None
    refused = r.store.one("SELECT metrics FROM telemetry WHERE event_id=? AND kind='tool_step_unavailable' LIMIT 1", (eid,))
    brk = r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='OutputBrokerDecision' ORDER BY rowid DESC LIMIT 1", (eid,))
    corr = [x for x in (json.loads(brk['payload']).get('late') or []) if x.get('kind') == 'CORRECTION' and x.get('applied')] if brk else []
    return {'pass': all(ok.values()) and all(num.values()), 'assertions': ok, 'numbers': num, 'turn_s': round(time.monotonic()-t0, 2),
            'status': a.get('status'), 'tool_call': meta.get('tool_call'), 'tool_shadow': meta.get('tool_shadow'),
            'proposal': None if prop is None else {'tool': prop.get('tool'), 'policy': prop.get('policy_status'), 'args': prop.get('args')},
            'guard_refused': refused is not None, 'output': out[:400], 'correction': corr[:1]}


def capture(installed, seed, path, limit=None):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    from v13.agi import hub, listarith
    installed = Path(installed).resolve(); rows = []; sets = task_sets(seed)
    with tempfile.TemporaryDirectory(prefix='v13-r4live-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home); reg = hub(r).tools
        try:
            for set_name in ('orig', 'match', 'nomatch'):
                for fid, text, nums, checks in sets[set_name][:limit]:
                    row = {'set': set_name, 'fixture': fid, 'operation': listarith.operation(text), 'true': nums}
                    for arm in ARMS:
                        on = arm == 'tool_active'; reg.enable('list_arith', on); approve_measurement(reg, on)
                        row[arm] = turn(r, text, nums, checks)
                    a = row['tool_active']; v = (a['tool_call'] or {})
                    row['value'] = None
                    if a['proposal'] and a['proposal']['tool'] == 'list_arith':
                        try:
                            row['value'] = listarith.tool(**a['proposal']['args'])
                        except Exception:
                            row['value'] = None
                    row['value_correct'] = row['value'] is not None and row['value'] in nums
                    rows.append(row)
                    print(json.dumps({'set': set_name, 'fixture': fid, 'op': row['operation'], 'c3': row['c3_alone']['pass'],
                                      'tool': a['pass'], 'value': row['value'], 'call': v.get('status'), 'refused': a['guard_refused']}), flush=True)
                    atomic_write(Path(path), json.dumps({'kind': 'V13_R4_LISTARITH_LIVE', 'task_seed': seed, 'script_sha256': sha(__file__),
                                                         'code_sha256': code_sha(), 'bench_cfg': U2.BENCH_CFG, 'rows': rows}, indent=1))
        finally:
            r.close()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_sha():
    base = Path(__file__).resolve().parents[1]/'v13'
    return {p: sha(base/p) for p in ('toolstep.py', 'agi/listarith.py', 'agi/tools.py', 'transaction.py', 'runtime.py', 'broker.py')}


def sign_p(w, l):
    n = w+l
    return 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(w, l)+1))/2**n)


def summarize(rows):
    out = {}
    for s in ('orig', 'match', 'nomatch'):
        rs = [r for r in rows if r['set'] == s]
        if not rs:
            continue
        w = sum(r['tool_active']['pass'] and not r['c3_alone']['pass'] for r in rs); l = sum(r['c3_alone']['pass'] and not r['tool_active']['pass'] for r in rs)
        kinds = {}
        for r in rs:
            k = kinds.setdefault(r['fixture'].rstrip('0123456789'), {'c3_alone': 0, 'tool_active': 0, 'value_correct': 0, 'n': 0})
            k['n'] += 1; k['c3_alone'] += r['c3_alone']['pass']; k['tool_active'] += r['tool_active']['pass']; k['value_correct'] += r['value_correct']
        out[s] = {'n': len(rs), 'c3_alone': sum(r['c3_alone']['pass'] for r in rs), 'tool_active': sum(r['tool_active']['pass'] for r in rs),
                  'wins': w, 'losses': l, 'net': w-l, 'sign_test_p': round(sign_p(w, l), 4), 'by_kind': kinds,
                  'proposals': sum(bool(r['tool_active']['proposal']) for r in rs), 'tool_executed': sum((r['tool_active']['tool_call'] or {}).get('status') == 'EXECUTED' for r in rs),
                  'guard_refused': sum(r['tool_active']['guard_refused'] for r in rs), 'value_correct': sum(r['value_correct'] for r in rs),
                  'pass_with_correction': sum(r['tool_active']['pass'] or bool(r['tool_active']['correction']) and r['value_correct'] for r in rs),
                  'turn_s_median': {a: sorted(r[a]['turn_s'] for r in rs)[len(rs)//2] for a in ARMS}}
    return out


def prereg(dev, out):
    d = json.loads(Path(dev).read_text())
    if d['task_seed'] == FRESH_SEED or d.get('script_sha256') != sha(__file__) or d.get('code_sha256') != code_sha():
        raise SystemExit('dev capture is fresh, or from another script/code version')
    body = {'schema': 'v13-r4-listarith-live-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'dev_seed': d['task_seed'], 'dev_sha256': sha(dev), 'dev': summarize(d['rows']), 'fresh_task_seed': FRESH_SEED,
            'arms': ARMS, 'reword': REWORD, 'decision_rule': DECISION, 'script_sha256': sha(__file__), 'code_sha256': code_sha()}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['code_sha256'] != code_sha():
        raise SystemExit('script or runtime code changed since preregistration')
    d = json.loads(Path(fresh).read_text()); rows = d['rows']
    if d['task_seed'] != FRESH_SEED or d.get('script_sha256') != reg['script_sha256'] or d.get('code_sha256') != reg['code_sha256'] \
            or sum(r['set'] == 'orig' for r in rows) != 60:
        raise SystemExit('fresh capture incomplete or wrong seed/script/code')
    res = summarize(rows); o = res['orig']
    drop = max(k['c3_alone']-k['tool_active'] for k in o['by_kind'].values())
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'sets': res, 'max_kind_drop': drop,
            'verdict': 'TOOL_PATH_SUPPORTED' if o['net'] >= 5 and o['sign_test_p'] < .05 and drop <= 2 else 'NOT_SUPPORTED',
            'age_right_replaced_for_measurement': True, 'phone_measured': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], int(a[2]), a[3], int(a[4]) if len(a) > 4 else None)
    elif a[0] == 'prereg':
        prereg(a[1], a[2])
    else:
        evaluate(a[1], a[2], a[3])
