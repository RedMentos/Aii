"""R4 part 4: re-check C3 with the exact local `calc` tool instead of waking bodies.

Part 3: C3's digit-token uncertainty predicts its own errors (fresh AUROC .84), but bodies rarely fix them; most
C3 errors are sums/differences. The BOOT proposer in v13/toolstep.py only fires on a written-out expression,
which these tasks never contain. Here, per task (all real C3 LFM2.5-350M, R4 BENCH_CFG, observers off):
  pass 1  normal runtime turn (C3 answer + digit-token uncertainty via the part-3 measurement hook)
  pass 2  C3 writes one arithmetic expression through a JSON schema; v13.agi.tools.calc evaluates it exactly
  pass 3  fresh session, same runtime turn with the exact tool result appended to the user text
Policies derived per task (C3 is greedy and deterministic, so each pass is one recording):
  c3_alone          pass 1
  calc_always       pass 3 when calc returned a value, else pass 1
  calc_uncertain    pass 3 only when digit-token uncertainty >= threshold (and calc returned a value), else pass 1
Dev seed captures (7/11, exposed by parts 1-3) choose the primary policy and threshold; fresh seed 13 tests once.
  capture   r4_calc_recheck.py capture <installed_home> <seed> <out.json>
  prereg    r4_calc_recheck.py prereg <dev.json>... <prereg.json>
  evaluate  r4_calc_recheck.py evaluate <prereg.json> <fresh13.json> <report.json>
Claim limit: generated English tasks, regex checks, cloud CPU; the tool result enters as appended user text, not as
the runtime TOOL_RESULT layer; no runtime change follows from this script."""
import hashlib
import json
import math
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
import r4_c3_uncertainty_wake as W  # noqa: E402

EXPR_SYSTEM = ('Write the calculation that gives the number the question asks for, as one arithmetic expression. '
               'Use only numbers copied exactly from the text and the operators + - * /. Never write names, the result '
               'itself or an equals sign. A total adds all listed amounts. "How much more" is the larger number minus the '
               'smaller one. Example: "Items: pens 12 euros, ink 30 euros. Give the total." -> {"expression": "12 + 30"}. '
               'Example: "Rain: Oslo 31, Rome 75, Pisa 52. How much more in the wettest city than the driest?" -> '
               '{"expression": "75 - 31"}. Return JSON only.')
EXPR_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['expression'],
               'properties': {'expression': {'type': 'string', 'maxLength': 120}}}
RESULT_TEMPLATE = ('\n\nExact local calculator result: {expression} = {value}. If the text states a different number '
                   'for this, say clearly that it is wrong. Answer every part of the question.')
POLICIES = ('c3_alone', 'calc_always', 'calc_uncertain')
DECISION = ('On fresh seed 13 the preregistered primary policy is CALC_SUPPORTED when it passes at least 5 net more '
            'tasks than c3_alone (paired), the two-sided sign test gives p < .05, and no task kind loses more than 2 '
            'tasks against c3_alone. Otherwise NOT_SUPPORTED. The other policies are reported, not judged. '
            'No runtime change follows from this script.')


def wait(r, eid, t0):
    end = t0+900
    while not r.idle():
        if time.monotonic() > end:
            r.cancel(); break
        time.sleep(.1)


def turn(r, text, nums, checks, cap):
    from v13.proofs import audit_event
    before = len(cap.streams); r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); wait(r, eid, t0)
    a = audit_event(r.store, eid); out = a.get('output') or ''; ok, num = U.score(out, nums, checks); streams = cap.streams[before:]
    answer = next((s for s in reversed(streams) if ''.join(t['token'] for t in s).strip() == out.strip()), streams[-1] if streams else [])
    return {'pass': all(ok.values()) and all(num.values()), 'turn_s': round(time.monotonic()-t0, 2), 'status': a.get('status'),
            'features': W.features(answer), 'output': out[:400]}


def expression(r, text):
    from v13.agi.tools import calc
    t0 = time.monotonic(); runner = r.pool.get('C3_LANGUAGE')
    raw = ''.join(runner.generate([{'role': 'system', 'content': EXPR_SYSTEM}, {'role': 'user', 'content': text}],
                                  r.cancel_event, time.monotonic()+180, 96, EXPR_SCHEMA))
    out = {'raw': raw[:300], 'expression': None, 'value': None, 'error': None}
    try:
        out['expression'] = str(json.loads(raw)['expression']).split('=')[0].strip()  # tolerate a trailing "= result"
        if not re.search(r'\d\s*[-+*/]\s*\(?\s*\d', out['expression']):
            raise ValueError('no operator: a bare number is a claimed result, not a calculation')
        out['value'] = calc(out['expression'])
        if isinstance(out['value'], float):
            out['value'] = round(out['value'], 4)
    except Exception as exc:
        out['error'] = type(exc).__name__
    out['s'] = round(time.monotonic()-t0, 2); return out


def capture(installed, seed, path):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    installed = Path(installed).resolve(); cap = W._Capture(); cap.install(); rows = []
    with tempfile.TemporaryDirectory(prefix='v13-r4calc-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home)
        try:
            for fid, text, nums, checks in U2.tasks(seed):
                p1 = turn(r, text, nums, checks, cap); ex = expression(r, text); p3 = None
                if ex['value'] is not None:
                    p3 = turn(r, text+RESULT_TEMPLATE.format(expression=ex['expression'], value=ex['value']), nums, checks, cap)
                rows.append({'fixture': fid, 'pass1': p1, 'expression': ex, 'pass3': p3,
                             'expression_correct': ex['value'] is not None and any(abs(float(ex['value'])-n) < 1e-6 for n in nums)})
                print(json.dumps({'fixture': fid, 'p1': p1['pass'], 'expr': ex['expression'], 'value': ex['value'],
                                  'p3': None if p3 is None else p3['pass']}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_R4_CALC_RECHECK', 'task_seed': seed, 'script_sha256': sha(__file__), 'bench_cfg': U2.BENCH_CFG,
                                                     'expr_system': EXPR_SYSTEM, 'result_template': RESULT_TEMPLATE, 'rows': rows}, indent=1))
        finally:
            r.close()


def uncertain(row):
    return W.uncertainty(row['pass1'], 'digit_min_logprob') if row['pass1']['features'] else math.inf


def outcome(row, policy, threshold=None):
    """(pass, turn seconds, used calc) of one task under a policy."""
    p1 = row['pass1']; use = row['pass3'] is not None and (policy == 'calc_always' or (policy == 'calc_uncertain' and uncertain(row) >= threshold))
    if not use:
        extra = row['expression']['s'] if policy == 'calc_always' or (policy == 'calc_uncertain' and uncertain(row) >= threshold) else 0.
        return p1['pass'], p1['turn_s']+extra, False
    return row['pass3']['pass'], p1['turn_s']+row['expression']['s']+row['pass3']['turn_s'], True


def score(rows, policy, threshold=None):
    res = [outcome(r, policy, threshold) for r in rows]; kinds = {}
    for r, (ok, _, _) in zip(rows, res):
        k = r['fixture'].rstrip('0123456789'); kinds[k] = kinds.get(k, 0)+ok
    return {'pass': sum(o for o, _, _ in res), 'calc_turns': sum(u for _, _, u in res), 'mean_turn_s': round(sum(s for _, s, _ in res)/len(rows), 2), 'by_kind': kinds}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prereg(devs, out):
    rows = []; shas = {}
    for p in devs:
        d = json.loads(Path(p).read_text())
        if d['task_seed'] == 13 or len(d['rows']) != 60 or d.get('script_sha256') != sha(__file__):
            raise SystemExit('dev capture incomplete, fresh, or from another script version: '+p)
        rows += d['rows']; shas[str(d['task_seed'])] = sha(p)
    cands = sorted({uncertain(r) for r in rows if math.isfinite(uncertain(r))})+[math.inf]
    thr = max(cands, key=lambda t: (score(rows, 'calc_uncertain', t)['pass'], -score(rows, 'calc_uncertain', t)['calc_turns']))
    dev = {'c3_alone': score(rows, 'c3_alone'), 'calc_always': score(rows, 'calc_always'), 'calc_uncertain': score(rows, 'calc_uncertain', thr)}
    primary = 'calc_uncertain' if dev['calc_uncertain']['pass'] >= dev['calc_always']['pass'] else 'calc_always'
    body = {'schema': 'v13-r4-calc-recheck-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'dev_sha256': shas, 'dev': dev, 'dev_expression_correct': sum(r['expression_correct'] for r in rows),
            'threshold': thr, 'primary': primary, 'fresh_task_seed': 13, 'decision_rule': DECISION, 'script_sha256': sha(__file__),
            'part3_script_sha256': sha(W.__file__)}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['part3_script_sha256'] != sha(W.__file__):
        raise SystemExit('script changed since preregistration')
    d = json.loads(Path(fresh).read_text()); rows = d['rows']
    if d['task_seed'] != reg['fresh_task_seed'] or len(rows) != 60 or d.get('script_sha256') != reg['script_sha256']:
        raise SystemExit('fresh capture incomplete or wrong seed')
    thr = reg['threshold']; res = {p: score(rows, p, thr) for p in POLICIES}; prim = reg['primary']
    wins = sum(outcome(r, prim, thr)[0] and not r['pass1']['pass'] for r in rows); losses = sum(r['pass1']['pass'] and not outcome(r, prim, thr)[0] for r in rows)
    n = wins+losses; p = 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(wins, losses)+1))/2**n)
    drop = max(res['c3_alone']['by_kind'][k]-res[prim]['by_kind'].get(k, 0) for k in res['c3_alone']['by_kind'])
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'policies': res, 'primary': prim, 'threshold': thr,
            'paired_vs_c3': {'wins': wins, 'losses': losses, 'net': wins-losses, 'sign_test_p': round(p, 4)}, 'max_kind_drop': drop,
            'expression_correct': sum(r['expression_correct'] for r in rows), 'calc_errors': sum(r['expression']['value'] is None for r in rows),
            'verdict': 'CALC_SUPPORTED' if wins-losses >= 5 and p < .05 and drop <= 2 else 'NOT_SUPPORTED',
            'phone_measured': False, 'runtime_changed': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], int(a[2]), a[3])
    elif a[0] == 'prereg':
        prereg(a[1:-1], a[-1])
    else:
        evaluate(a[1], a[2], a[3])
