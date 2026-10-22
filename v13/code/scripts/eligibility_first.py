"""2026-10-22 (thread „STEP2-Nutzen Engpass“): does the answer carry the eligibility tool's decision when (1) a fixed reader
reads the rules instead of C3 (cfg eligibility_reader='fixed') and (2) the decision is the first visible sentence and the
body only explains it (cfg tool_answer_first)?

Thread Q's whole-turn measurement (eligibility_live.py, fresh seed 29) found C3 350M keeps its own decision next to the
TOOL_RESULT layer (answer text right 32/60; 53/60 only with the broker's late correction) and misreads rules (decision
UNKNOWN in 18 non-missing tasks, override values exact 5/15). Same tasks generator, same runtime path, same scoring as Q;
four arms per task (new session each):
  c3_alone          eligibility not enabled
  tool_model        Q's path: C3 reads rules + options (eligibility_reader=model, tool_answer_first=false)
  tool_fixed        fixed reader for rules, options too where the wording is covered (no C3 read call then)
  tool_fixed_first  tool_fixed + the decision sentence opens the answer, C3 continues
Age right replaced for SYSTEM eligibility only (as Q); everything else is the unchanged runtime path.
  capture   eligibility_first.py capture <installed_home> <seed> <n_per_kind> <out.json>
  prereg    eligibility_first.py prereg <dev.json> <prereg.json>
  evaluate  eligibility_first.py evaluate <prereg.json> <fresh.json> <report.json>
Dev seed 7 only catches wiring bugs; fresh seed 41 (15 per kind) runs once after the preregistration is pushed.
Claim limit: generated English tasks in the guard's wording (the fixed reader covers exactly this wording), regex answer
parser, cloud CPU, not a Redmi number, not STEP2."""
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from v13.agi import eligibility as E  # noqa: E402
import eligibility_live as Q  # noqa: E402
import utility_bench2 as U2  # noqa: E402

FRESH_SEED = 41
FRESH_PER_KIND = 15
KINDS = Q.KINDS
ARMS = {'c3_alone': None,
        'tool_model': {'eligibility_reader': 'model', 'tool_answer_first': False},
        'tool_fixed': {'eligibility_reader': 'fixed', 'tool_answer_first': False},
        'tool_fixed_first': {'eligibility_reader': 'fixed', 'tool_answer_first': True}}
TOOL_ARMS = [a for a, c in ARMS.items() if c]
CFG = Q.CFG
DECISION = (f"Fresh seed {FRESH_SEED}, {FRESH_PER_KIND} tasks per kind ({4*FRESH_PER_KIND} total), arms paired on the same task. "
            "FIRST_SUPPORTED iff, tool_fixed_first vs tool_model on the answer text: (a) net correct wins >= +10 AND two-sided "
            "sign test p < .05, (b) wrong_committed(tool_fixed_first) <= wrong_committed(tool_model), (c) tool_wrong(tool_fixed_first) "
            "== 0, (d) no kind loses more than 2 tasks net. FIXED_READER_SUPPORTED iff decision_correct(tool_fixed) >= "
            "decision_correct(tool_model) + 5 AND tool_wrong(tool_fixed) == 0. Reported, not part of the verdicts: c3_alone, "
            "shown_correct (with broker correction) per arm, per kind, model read calls, turn time.")


def capture(installed, seed, per_kind, path):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    from v13.agi import hub
    installed = Path(installed).resolve(); rows = []; tasks = Q.gen(seed, per_kind)
    with tempfile.TemporaryDirectory(prefix='v13-elig-first-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | CFG | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home); reg = hub(r).tools
        try:
            for task in tasks:
                row = {'task': task['id'], 'kind': task['kind'], 'oracle': task['oracle']}
                for arm, knobs in ARMS.items():
                    on = knobs is not None; reg.enable('eligibility', on); Q.approve_measurement(reg, on)
                    r.cfg.update(knobs or ARMS['tool_model'])
                    calls = []; pool_get = r.pool.get

                    def counted(role, _get=pool_get, _calls=calls):
                        _calls.append(role); return _get(role)
                    r.pool.get = counted  # count C3 fetches (the read call + the answer)
                    try: x = Q.task_turns(r, task)
                    finally: r.pool.get = pool_get
                    x['pool_gets'] = len(calls)
                    if on:
                        x['tool_wrong'] = bool(x['decision'] and x['decision']['action'] in ('A', 'B', 'NONE') and x['decision']['action'] != task['oracle'])
                        x['shown_correct'] = x['correct'] or bool(x['correction_applied'] and x['decision'] and x['decision']['action'] == task['oracle'])
                        x['values_exact'] = Q.values_exact(x, task)
                    row[arm] = x
                rows.append(row)
                print(json.dumps({'task': task['id'], 'oracle': task['oracle'], **{a: row[a]['parsed'] for a in ARMS},
                                  'dec': {a: (row[a]['decision'] or {}).get('action') for a in TOOL_ARMS}}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_ELIGIBILITY_FIRST', 'task_seed': seed, 'per_kind': per_kind,
                                                     'script_sha256': sha(__file__), 'code_sha256': code_sha(), 'cfg': CFG | U2.BENCH_CFG,
                                                     'tasks_sha256': hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest(),
                                                     'rows': rows}, indent=1))
        finally:
            r.close()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_sha():
    base = Path(__file__).resolve().parents[1]/'v13'
    out = {p: sha(base/p) for p in ('toolstep.py', 'agi/eligibility.py', 'agi/tools.py', 'transaction.py', 'runtime.py', 'broker.py', 'history.py', 'config.py')}
    out['scripts/eligibility_live.py'] = sha(Path(__file__).resolve().parent/'eligibility_live.py')
    return out


def pair(rs, a, b, key='correct'):
    w = sum(r[a][key] and not r[b][key] for r in rs); l = sum(r[b][key] and not r[a][key] for r in rs)
    return {'wins': w, 'losses': l, 'net': w-l, 'sign_test_p': round(Q.sign_p(w, l), 4)}


def summarize(rows):
    def block(rs):
        out = {'n': len(rs), 'correct': {a: sum(r[a]['correct'] for r in rs) for a in ARMS},
               'wrong_committed': {a: sum(r[a]['wrong_committed'] for r in rs) for a in ARMS},
               'unparsed': {a: sum(r[a]['parsed'] is None for r in rs) for a in ARMS},
               'turn_s_median': {a: sorted(r[a]['turn_s'] for r in rs)[len(rs)//2] for a in ARMS},
               'pool_gets': {a: sum(r[a]['pool_gets'] for r in rs) for a in ARMS}}
        for k in ('tool_wrong', 'shown_correct', 'correction_applied'):
            out[k] = {a: sum(bool(r[a][k]) for r in rs) for a in TOOL_ARMS}
        out['executed'] = {a: sum((r[a]['tool_call'] or {}).get('status') == 'EXECUTED' for r in rs) for a in TOOL_ARMS}
        out['decision_correct'] = {a: sum(bool(r[a]['decision'] and r[a]['decision']['action'] == r['oracle']) for r in rs) for a in TOOL_ARMS}
        out['decision_unknown'] = {a: sum(bool(r[a]['decision'] and r[a]['decision']['action'] == 'UNKNOWN') for r in rs) for a in TOOL_ARMS}
        out['values_exact'] = {a: sum(bool(r[a]['values_exact']) for r in rs) for a in TOOL_ARMS}
        out['first_vs_model'] = pair(rs, 'tool_fixed_first', 'tool_model')
        out['first_vs_c3'] = pair(rs, 'tool_fixed_first', 'c3_alone')
        out['fixed_vs_model'] = pair(rs, 'tool_fixed', 'tool_model')
        return out
    out = {'all': block(rows)}
    for k in KINDS:
        rs = [r for r in rows if r['kind'] == k]
        if rs: out[k] = block(rs)
    return out


def prereg(dev, out):
    d = json.loads(Path(dev).read_text())
    if d['task_seed'] == FRESH_SEED or d.get('script_sha256') != sha(__file__) or d.get('code_sha256') != code_sha():
        raise SystemExit('dev capture is fresh, or from another script/code version')
    body = {'schema': 'v13-eligibility-first-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'dev_seed': d['task_seed'], 'dev_sha256': sha(dev), 'dev': summarize(d['rows']), 'fresh_task_seed': FRESH_SEED,
            'fresh_per_kind': FRESH_PER_KIND, 'fresh_tasks_sha256': hashlib.sha256(json.dumps(Q.gen(FRESH_SEED, FRESH_PER_KIND), sort_keys=True).encode()).hexdigest(),
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
    res = summarize(rows); o = res['all']; fm = o['first_vs_model']
    drop = max(-res[k]['first_vs_model']['net'] for k in KINDS)
    first = {'a_net_and_sign': fm['net'] >= 10 and fm['sign_test_p'] < .05,
             'b_wrong_committed_not_higher': o['wrong_committed']['tool_fixed_first'] <= o['wrong_committed']['tool_model'],
             'c_tool_never_wrong': o['tool_wrong']['tool_fixed_first'] == 0, 'd_no_kind_loses_more_than_2': drop <= 2}
    fixed = {'decision_plus_5': o['decision_correct']['tool_fixed'] >= o['decision_correct']['tool_model']+5,
             'tool_never_wrong': o['tool_wrong']['tool_fixed'] == 0}
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'summary': res, 'max_kind_net_loss': drop,
            'first_criteria': first, 'first_verdict': 'FIRST_SUPPORTED' if all(first.values()) else 'NOT_SUPPORTED',
            'fixed_criteria': fixed, 'fixed_verdict': 'FIXED_READER_SUPPORTED' if all(fixed.values()) else 'NOT_SUPPORTED',
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
