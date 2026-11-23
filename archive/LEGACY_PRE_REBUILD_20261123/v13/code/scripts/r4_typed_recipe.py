"""R4 part 5: typed values + fixed recipe instead of a C3-written expression (follow-up to part 4).

Part 4: C3 writes sum expressions correctly (15/15) but max-minus-min differences almost never (1/15). As in WP-W2,
a fixed BOOT rule picks the operation from the question wording, the model only reads one typed number per item
through a JSON schema, and a fixed recipe computes the value (total = sum, difference_max_min = max - min). Number guard as in WP-W2:
every number must occur as an exact token in the task text, else no tool result. Pass 1 and pass 3 are the part-4 runtime
turns (C3 LFM2.5-350M, R4 BENCH_CFG, observers off); policies c3_alone / calc_always / calc_uncertain are scored by
r4_calc_recheck.score with the extraction stored under the same 'expression' key.
  capture   r4_typed_recipe.py capture <installed_home> <seed> <out.json>
  prereg    r4_typed_recipe.py prereg <dev.json>... <prereg.json>
  evaluate  r4_typed_recipe.py evaluate <prereg.json> <fresh.json> <report.json>
Dev seeds 7 and 11 choose primary policy and threshold; fresh seed 17 tests once (seed 13 was exposed by part 4).
Claim limit: generated English tasks, regex checks, cloud CPU; tool result enters as appended user text; no runtime change."""
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
import utility_bench2 as U2  # noqa: E402
import r4_c3_uncertainty_wake as W  # noqa: E402
import r4_calc_recheck as C  # noqa: E402

FRESH_SEED = 17
# Dev rounds on seeds 7/11: C3 350M picks the operation unreliably (always "total", or always "none" after a prompt
# change) while it reads the numbers correctly. So, like the BOOT regex proposer in v13/toolstep.py, a fixed rule picks the
# operation from the question wording and C3 only reads typed values.
OPERATIONS = ((re.compile(r'(?i)\bhow (?:many|much)\b[^.?]*\b(?:more|less|fewer)\b[^.?]*\bthan\b'), 'difference_max_min'),
              (re.compile(r'(?i)\b(?:total|sum)\b'), 'total'))
READ_SYSTEM = ('Read the numbers in the text. Return JSON only. values: every listed item with its name and its number '
               'copied exactly from the text. Never calculate anything yourself.')
READ_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['values'], 'properties': {
    'values': {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'number'],
                                                          'properties': {'name': {'type': 'string', 'maxLength': 40}, 'number': {'type': 'integer'}}}}}}


def operation(text):
    return next((op for rx, op in OPERATIONS if rx.search(text)), 'none')


RESULT_TEMPLATE = ('\n\nExact local calculator result: {label} = {value}. If the text states a different number for this, '
                   'say clearly that it is wrong. Answer every part of the question.')
DECISION = C.DECISION.replace('seed 13', f'seed {FRESH_SEED}')


def recipe(operation, values, text):
    """Fixed recipe with WP-W2 style number guard; returns (value, label) or raises ValueError."""
    if operation == 'none':
        raise ValueError('no operation')
    nums = [int(v['number']) for v in values]
    if len(nums) < 2:
        raise ValueError('fewer than two values')
    tokens = set(re.findall(r'(?<![\d.])\d+(?!\d|\.\d)', text))  # a sentence-final period is not a decimal point
    if any(str(n) not in tokens for n in nums):
        raise ValueError('number not in text')
    names = [str(v.get('name', '')).strip()[:40] for v in values]
    if operation == 'total':
        return sum(nums), ' + '.join(f'{n} {x}' if n else str(x) for n, x in zip(names, nums))
    hi = max(range(len(nums)), key=lambda i: nums[i]); lo = min(range(len(nums)), key=lambda i: nums[i])
    # Name the largest and smallest item: dev round 3 showed C3 keeps the right difference but names the wrong item.
    return nums[hi]-nums[lo], f'largest {names[hi]} {nums[hi]} - smallest {names[lo]} {nums[lo]}'


def read(r, text):
    t0 = time.monotonic()
    if operation(text) == 'none':  # no tool use proposed: C3 is not asked to read values
        return {'raw': '', 'operation': 'none', 'values': None, 'expression': None, 'value': None, 'error': 'ValueError: no operation', 's': 0.}
    runner = r.pool.get('C3_LANGUAGE')
    raw = ''.join(runner.generate([{'role': 'system', 'content': READ_SYSTEM}, {'role': 'user', 'content': text}],
                                  r.cancel_event, time.monotonic()+180, 160, READ_SCHEMA))
    out = {'raw': raw[:400], 'operation': operation(text), 'values': None, 'expression': None, 'value': None, 'error': None}
    try:
        d = json.loads(raw); out['values'] = d['values']
        out['value'], out['expression'] = recipe(out['operation'], d['values'], text)
    except Exception as exc:
        out['error'] = type(exc).__name__+': '+str(exc)[:80]
    out['s'] = round(time.monotonic()-t0, 2); return out


def capture(installed, seed, path):
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    installed = Path(installed).resolve(); cap = W._Capture(); cap.install(); rows = []
    with tempfile.TemporaryDirectory(prefix='v13-r4typed-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home)
        try:
            for fid, text, nums, checks in U2.tasks(seed):
                p1 = C.turn(r, text, nums, checks, cap); ex = read(r, text); p3 = None
                if ex['value'] is not None:
                    p3 = C.turn(r, text+RESULT_TEMPLATE.format(label=ex['expression'], value=ex['value']), nums, checks, cap)
                rows.append({'fixture': fid, 'pass1': p1, 'expression': ex, 'pass3': p3,
                             'expression_correct': ex['value'] is not None and any(ex['value'] == n for n in nums)})
                print(json.dumps({'fixture': fid, 'p1': p1['pass'], 'op': ex['operation'], 'expr': ex['expression'], 'value': ex['value'],
                                  'err': ex['error'], 'p3': None if p3 is None else p3['pass']}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_R4_TYPED_RECIPE', 'task_seed': seed, 'script_sha256': sha(__file__),
                                                     'bench_cfg': U2.BENCH_CFG, 'rows': rows}, indent=1))
        finally:
            r.close()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prereg(devs, out):
    rows = []; shas = {}
    for p in devs:
        d = json.loads(Path(p).read_text())
        if d['task_seed'] in (13, FRESH_SEED) or len(d['rows']) != 60 or d.get('script_sha256') != sha(__file__):
            raise SystemExit('dev capture incomplete, exposed/fresh, or from another script version: '+p)
        rows += d['rows']; shas[str(d['task_seed'])] = sha(p)
    cands = sorted({C.uncertain(r) for r in rows if math.isfinite(C.uncertain(r))})+[math.inf]
    thr = max(cands, key=lambda t: (C.score(rows, 'calc_uncertain', t)['pass'], -C.score(rows, 'calc_uncertain', t)['calc_turns']))
    dev = {p: C.score(rows, p, thr) for p in C.POLICIES}
    primary = 'calc_uncertain' if dev['calc_uncertain']['pass'] >= dev['calc_always']['pass'] else 'calc_always'
    body = {'schema': 'v13-r4-typed-recipe-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'dev_sha256': shas, 'dev': dev, 'dev_value_correct': sum(r['expression_correct'] for r in rows), 'threshold': thr,
            'primary': primary, 'fresh_task_seed': FRESH_SEED, 'decision_rule': DECISION, 'script_sha256': sha(__file__),
            'helper_sha256': {'r4_calc_recheck': sha(C.__file__), 'r4_c3_uncertainty_wake': sha(W.__file__)}}
    atomic_write(Path(out), json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['helper_sha256'] != {'r4_calc_recheck': sha(C.__file__), 'r4_c3_uncertainty_wake': sha(W.__file__)}:
        raise SystemExit('scripts changed since preregistration')
    d = json.loads(Path(fresh).read_text()); rows = d['rows']
    if d['task_seed'] != FRESH_SEED or len(rows) != 60 or d.get('script_sha256') != reg['script_sha256']:
        raise SystemExit('fresh capture incomplete or wrong seed/script')
    thr = reg['threshold']; prim = reg['primary']; res = {p: C.score(rows, p, thr) for p in C.POLICIES}
    wins = sum(C.outcome(r, prim, thr)[0] and not r['pass1']['pass'] for r in rows); losses = sum(r['pass1']['pass'] and not C.outcome(r, prim, thr)[0] for r in rows)
    n = wins+losses; p = 1. if n == 0 else min(1., 2*sum(math.comb(n, i) for i in range(min(wins, losses)+1))/2**n)
    drop = max(res['c3_alone']['by_kind'][k]-res[prim]['by_kind'].get(k, 0) for k in res['c3_alone']['by_kind'])
    by_kind_values = {}
    for r in rows:
        k = r['fixture'].rstrip('0123456789'); by_kind_values[k] = by_kind_values.get(k, 0)+r['expression_correct']
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': sha(fresh), 'policies': res, 'primary': prim, 'threshold': thr,
            'paired_vs_c3': {'wins': wins, 'losses': losses, 'net': wins-losses, 'sign_test_p': round(p, 4)}, 'max_kind_drop': drop,
            'value_correct_by_kind': by_kind_values, 'tool_refused': sum(r['expression']['value'] is None for r in rows),
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
