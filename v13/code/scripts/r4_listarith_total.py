"""R4 part 7: list_arith drops read items named total/sum (agi/listarith.AGGREGATE), re-measured live on fresh seed 23.

Part 6 (r4_listarith_live.py, TOOL_PATH_SUPPORTED on seed 19) found one wrong tool value per seed: C3 read the stated
summary line "Total: X" as one more item. Dev evidence is counterfactual and deterministic: the recipe re-applied to the
values C3 already read on seeds 7 and 19 (no new model call). The fresh run reuses part 6's capture unchanged.
  prereg    r4_listarith_total.py prereg <part6_dev7.json> <part6_fresh19.json> <prereg.json>
  capture   r4_listarith_live.py capture <installed_home> 23 <out.json>
  evaluate  r4_listarith_total.py evaluate <prereg.json> <fresh23.json> <report.json>
Claim limit as part 6: generated English tasks, regex checks, cloud CPU, Age verdict replaced for the measurement."""
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write  # noqa: E402
from v13.agi import listarith  # noqa: E402
import r4_listarith_live as M  # noqa: E402

FRESH_SEED = 23
DECISION = (f"Fresh seed {FRESH_SEED}, set 'orig', 60 tasks, part-6 capture: FIX_SUPPORTED iff every executed list_arith value is "
            "correct (value_correct == proposals) AND tool_active vs c3_alone net wins >= +5 AND sign test p < .05 AND no task kind "
            "loses more than 2. Sets 'match'/'nomatch' reported as in part 6.")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def recheck(path):
    rows = json.loads(Path(path).read_text())['rows']; n = old = new = 0
    for r in rows:
        p = r['tool_active']['proposal']
        if not p:
            continue
        n += 1; old += r['value_correct']
        try:
            new += listarith.tool(**p['args']) in r['true']
        except ValueError:
            pass
    return {'proposals': n, 'value_correct_part6': old, 'value_correct_fixed': new}


def prereg(dev7, fresh19, out):
    body = {'schema': 'v13-r4-listarith-total-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'counterfactual': {'seed7': recheck(dev7) | {'sha256': sha(dev7)}, 'seed19': recheck(fresh19) | {'sha256': sha(fresh19)}},
            'fresh_task_seed': FRESH_SEED, 'decision_rule': DECISION, 'script_sha256': sha(__file__),
            'capture_script_sha256': sha(M.__file__), 'code_sha256': M.code_sha()}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['capture_script_sha256'] != sha(M.__file__) or reg['code_sha256'] != M.code_sha():
        raise SystemExit('script or runtime code changed since preregistration')
    d = json.loads(Path(fresh).read_text()); rows = d['rows']
    if d['task_seed'] != FRESH_SEED or d.get('script_sha256') != reg['capture_script_sha256'] or d.get('code_sha256') != reg['code_sha256'] \
            or sum(r['set'] == 'orig' for r in rows) != 60:
        raise SystemExit('fresh capture incomplete or wrong seed/script/code')
    res = M.summarize(rows); o = res['orig']
    drop = max(k['c3_alone']-k['tool_active'] for k in o['by_kind'].values())
    ok = o['value_correct'] == o['proposals'] and o['net'] >= 5 and o['sign_test_p'] < .05 and drop <= 2
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'sets': res, 'max_kind_drop': drop,
            'verdict': 'FIX_SUPPORTED' if ok else 'NOT_SUPPORTED', 'age_right_replaced_for_measurement': True, 'phone_measured': False}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'prereg':
        prereg(a[1], a[2], a[3])
    else:
        evaluate(a[1], a[2], a[3])
