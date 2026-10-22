"""WP-DS3c: when the fixed answer<->tool cross-check fails, answer with a fixed sentence from the tool result instead of
saying "unsicher" (lab measurement, follow-up to WP-DS3b).

WP-DS3b (bench-results/ds3b-name-check-20261022): the cross-check found 18 of 21 wrong tool answers; abstaining on a failed
check gave 143 vs 130 points, a fixed tool sentence instead of abstaining 162 (reported only, because the DS3b sentence
was written next to the bench regex and said "euros"). This package tests that idea on its own:
  * unit-free tool sentences (repair_text below), the same for every task family;
  * strict scoring as primary (a compare answer that names a wrong "most"/"least" item or binds a wrong number to an item
    counts as wrong), so a sentence that only satisfies the regex is not enough;
  * a second, new task family F (bakeries, trip costs, team points, parcel weights; new wording and units) that no
    earlier script saw, next to fresh R4 seeds.
Policies on the recorded turns (answer = pass3 when the tool ran, else pass1):
  recipe_always   tool answer as written by C3
  check           "unsicher" when ds3b_name_check.cross_check fails                 (DS3b)
  check_repair    fixed tool sentence when the check fails                           (primary)
  capture   ds3c_tool_answer.py capture <installed_home> <family r4|f> <seed> <out.json>
  prereg    ds3c_tool_answer.py prereg <dev_f.json> <prereg.json>     (dev = family F seed 69: generator + checks sanity only)
  evaluate  ds3c_tool_answer.py evaluate <prereg.json> <fresh.json>... <report.json>
Claim limit: generated English tasks, regex checks, cloud CPU, the tool sentence is fixed text (no model); no runtime change."""
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ds3b_name_check as D  # noqa: E402

LAMBDA = 1.
DEV_F = (69,); FRESH = {'r4': (61, 67), 'f': (71, 73)}
USED = D.EXPOSED+D.DEV_SEEDS+D.FRESH_SEEDS
POLICIES = ('recipe_always', 'check', 'check_repair')
DECISION = ('Fresh R4 seeds 61+67 and family-F seeds 71+73 (120 tasks each), evaluated once; scoring strict, LAMBDA=1. '
            'H1 (R4): check_repair strict utility >= check strict utility + 6 and check_repair strict wrong <= check strict wrong + 2. '
            'H2 (F, transfer of the check): of the F tool tasks whose check fails >= 70 % are wrong (strict) under recipe_always, '
            'and the check flags >= 50 % of the strict-wrong recipe_always answers on F tool tasks. '
            'H3 (F): check_repair strict utility >= recipe_always strict utility + 5 and >= check strict utility. '
            'H4 (both): every strict-wrong repair sentence comes from a wrong value read (expression not correct). '
            'DS3C_SUPPORTED when H1..H4 all pass, else the failing parts are named. Bench-regex scoring and LAMBDA=2 reported only.')
F_SHOPS = ('Alder', 'Birch', 'Cedar', 'Maple', 'Willow', 'Hazel', 'Rowan', 'Aspen', 'Laurel', 'Juniper')
F_TEAMS = ('Falcons', 'Otters', 'Badgers', 'Herons', 'Lynxes', 'Ravens', 'Wolves', 'Foxes', 'Bisons', 'Eagles')
F_COSTS = ('hotel', 'fuel', 'food', 'museum tickets', 'parking', 'ferry', 'souvenirs', 'bike rental')
F_PARCELS = ('books', 'lamp', 'shoes', 'blender', 'tent', 'kettle', 'toolbox', 'rug')
ERR = r"(?i)\b(no|not correct|incorrect|wrong|error|mistake|does not match|doesn't match)\b"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def word(n):
    return r'\b'+str(n)+r'\b'


def tasks_f(seed, per_kind=15):
    """Family F: new wording and units; same two recipes (difference_max_min, total) under the R4 BOOT rule."""
    rng = random.Random(seed*7919+1); out = []
    for i in range(per_kind):
        s = rng.sample(F_SHOPS, 3); v = rng.sample(range(20, 160), 3); hi = s[v.index(max(v))]; d = max(v)-min(v)
        out.append(('shop%02d' % i, 'Cakes sold this week: '+', '.join('%s %d' % x for x in zip(s, v))+'. Which bakery sold the most cakes, '
                    'and how many more than the bakery that sold the fewest?', [d], {'shop': '(?i)'+hi, 'diff': word(d)}))
    for i in range(per_kind):
        it = rng.sample(F_COSTS, 3); v = [rng.randint(15, 240) for _ in it]; true = sum(v); wrong = true+rng.choice([-30, -15, 15, 30])
        out.append(('trip%02d' % i, 'Trip costs: '+', '.join('%s %d euros' % x for x in zip(it, v))+'. The planner wrote that the trip cost %d euros. '
                    'Is that correct? What is the sum?' % wrong, [true], {'total': word(true), 'flags_error': ERR}))
    for i in range(per_kind):
        t = rng.sample(F_TEAMS, 4); v = rng.sample(range(30, 99), 4); hi = t[v.index(max(v))]; d = max(v)-min(v)
        out.append(('team%02d' % i, 'Season points: '+', '.join('%s %d' % x for x in zip(t, v))+'. Which team has the most points, and how '
                    'many points more than the last team?', [d], {'team': '(?i)'+hi, 'diff': word(d)}))
    for i in range(per_kind):
        it = rng.sample(F_PARCELS, 3); v = [rng.randint(2, 40) for _ in it]; true = sum(v)
        out.append(('parcel%02d' % i, 'Parcel weights in kilograms: '+', '.join('%s %d' % x for x in zip(it, v))+'. What is the total weight?',
                    [true], {'total': word(true)}))
    return out


def tasks(family, seed):
    import utility_bench2 as U2
    return U2.tasks(seed) if family == 'r4' else tasks_f(seed)


def capture(installed, family, seed, path):
    """Same capture as ds3b_name_check.capture (real C3 turns with token logprobs, typed read + recipe) on either family."""
    import shutil
    import tempfile
    import utility_bench2 as U2
    import r4_c3_uncertainty_wake as W
    import r4_typed_recipe as T
    from v13.common import atomic_write
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    if family == 'r4' and seed in USED:
        raise SystemExit('R4 seed already used')
    installed = Path(installed).resolve(); cap = W._Capture(); cap.install(); rows = []
    with tempfile.TemporaryDirectory(prefix='v13-ds3c-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home)
        try:
            for fid, text, nums, checks in tasks(family, seed):
                p1 = D.turn(r, text, nums, checks, cap); ex = T.read(r, text); p3 = None
                if ex['value'] is not None:
                    p3 = D.turn(r, text+T.RESULT_TEMPLATE.format(label=ex['expression'], value=ex['value']), nums, checks, cap)
                rows.append({'fixture': fid, 'text': text, 'nums': nums, 'checks': checks, 'pass1': p1, 'expression': ex, 'pass3': p3,
                             'expression_correct': ex['value'] is not None and any(ex['value'] == n for n in nums)})
                print(json.dumps({'fixture': fid, 'p1': p1['pass'], 'op': ex['operation'], 'value': ex['value'],
                                  'p3': None if p3 is None else p3['pass']}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_DS3C_CAPTURE', 'family': family, 'task_seed': seed, 'script_sha256': sha(__file__),
                                                     'recipe_sha256': sha(T.__file__), 'bench_cfg': U2.BENCH_CFG, 'rows': rows}, indent=1))
        finally:
            r.close()


def stated_numbers(row):
    t = row['text']; read = {int(v['number']) for v in row['expression']['values'] or []}
    if not re.search(r'(?i)\bcorrect\?', t):
        return []
    return [int(n) for n in D.NUM.findall(t[:t.rfind('?')+1]) if int(n) not in read]


def repair_text(row):
    """Unit-free fixed sentence from the executed recipe."""
    ex = row['expression']; vals = [v for v in ex['values'] if str(v.get('name', '')).strip().lower() not in ('total', 'sum')]; v = ex['value']
    if ex['operation'] == 'total':
        stated = [n for n in stated_numbers(row) if n != v]
        head = f'No, the stated number {stated[0]} is wrong. ' if stated else ''
        return head+f'The exact total is {v}.'
    nums = [int(x['number']) for x in vals]; hi = vals[nums.index(max(nums))]; lo = vals[nums.index(min(nums))]
    return f"{hi['name']} has the largest value ({hi['number']}) and {lo['name']} the smallest ({lo['number']}); the difference is {v}."


DIFF_KINDS = ('compare', 'shop', 'team')


def strict(row, text, passed):
    if not passed or not row['fixture'].startswith(DIFF_KINDS):
        return passed
    return D.strict_ok(dict(row, fixture='compare00'), text, passed)


def decide(row, policy):
    """(action, bench pass or None, strict pass or None)."""
    comp, t = D.final(row); act = 'tool' if comp == 'after_tool' else 'answer'
    chk = D.cross_check(row); failed = chk is not None and not chk[0]
    if policy != 'recipe_always' and failed:
        if policy == 'check':
            return 'abstain', None, None
        txt = repair_text(row); b = D.bench_score(txt, row); return 'repair', b, strict(row, txt, b)
    return act, t['pass'], strict(row, t['output'], t['pass'])


def score(rows, policy):
    outs = [decide(r, policy) for r in rows]
    def tally(i):
        right = sum(o[i] is True for o in outs); wrong = sum(o[i] is False for o in outs)
        return {'correct': right, 'wrong': wrong, 'utility': right-LAMBDA*wrong, 'utility_lambda2': right-2*wrong}
    return {'strict': tally(2), 'bench': tally(1), 'abstain': sum(a == 'abstain' for a, _, _ in outs), 'repair': sum(a == 'repair' for a, _, _ in outs)}


def check_stats_strict(rows):
    tool = [r for r in rows if D.cross_check(r) is not None]
    wrong = [r for r in tool if not strict(r, r['pass3']['output'], r['pass3']['pass'])]
    flagged = [r for r in tool if not D.cross_check(r)[0]]
    fw = sum(r in wrong for r in flagged); caught = sum(not D.cross_check(r)[0] for r in wrong)
    return {'tool_tasks': len(tool), 'flagged': len(flagged), 'flagged_wrong_strict': fw, 'recipe_wrong_strict_on_tool': len(wrong), 'caught': caught,
            'precision': round(fw/len(flagged), 4) if flagged else None, 'recall': round(caught/len(wrong), 4) if wrong else None}


def repair_errors(rows):
    bad = [r for r in rows if decide(r, 'check_repair')[0] == 'repair' and decide(r, 'check_repair')[2] is False]
    return {'repair_wrong': len(bad), 'repair_wrong_with_correct_read': sum(bool(r['expression_correct']) for r in bad),
            'fixtures': [r['fixture'] for r in bad]}


def load(paths, family, seeds):
    rows = []; shas = {}
    for p in paths:
        d = json.loads(Path(p).read_text())
        if d.get('kind') != 'V13_DS3C_CAPTURE' or d['family'] != family or d['task_seed'] not in seeds or len(d['rows']) != 60:
            raise SystemExit('capture incomplete, wrong kind/family/seed: '+p)
        rows += d['rows']; shas[f"{family}{d['task_seed']}"] = sha(p)
    return rows, shas


def by_family(paths):
    out = {'r4': [], 'f': []}
    for p in paths:
        out[json.loads(Path(p).read_text())['family']].append(p)
    return out


def prereg(dev, out):
    rows, shas = load([dev], 'f', DEV_F)
    body = {'schema': 'v13-ds3c-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'dev_sha256': shas,
            'dev_f': {p: score(rows, p) for p in POLICIES}, 'dev_f_check': check_stats_strict(rows), 'dev_f_repair_errors': repair_errors(rows),
            'fresh_seeds': FRESH, 'decision_rule': DECISION, 'script_sha256': sha(__file__), 'ds3b_sha256': sha(D.__file__)}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['ds3b_sha256'] != sha(D.__file__):
        raise SystemExit('scripts changed since preregistration')
    fam = by_family(fresh); R, shr = load(fam['r4'], 'r4', FRESH['r4']); F, shf = load(fam['f'], 'f', FRESH['f'])
    if len(shr) != 2 or len(shf) != 2:
        raise SystemExit('need every fresh seed once')
    res = {'r4': {p: score(R, p) for p in POLICIES}, 'f': {p: score(F, p) for p in POLICIES}}
    sr = {p: v['strict'] for p, v in res['r4'].items()}; sf = {p: v['strict'] for p, v in res['f'].items()}
    cf = check_stats_strict(F); er = repair_errors(R+F)
    h = {'H1_r4_repair_vs_abstain': {'repair': sr['check_repair'], 'check': sr['check'],
                                      'pass': sr['check_repair']['utility'] >= sr['check']['utility']+6 and sr['check_repair']['wrong'] <= sr['check']['wrong']+2},
         'H2_f_check_transfer': {**cf, 'pass': cf['precision'] is not None and cf['recall'] is not None and cf['precision'] >= .70 and cf['recall'] >= .50},
         'H3_f_repair_utility': {'repair': sf['check_repair'], 'recipe_always': sf['recipe_always'], 'check': sf['check'],
                                 'pass': sf['check_repair']['utility'] >= sf['recipe_always']['utility']+5 and sf['check_repair']['utility'] >= sf['check']['utility']},
         'H4_repair_errors_only_from_reads': {**er, 'pass': er['repair_wrong_with_correct_read'] == 0}}
    fails = [k for k, v in h.items() if not v['pass']]
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': {**shr, **shf}, 'policies': res, 'check_r4': check_stats_strict(R), 'hypotheses': h,
            'verdict': 'DS3C_SUPPORTED' if not fails else 'NOT_SUPPORTED: '+', '.join(fails), 'phone_measured': False, 'runtime_changed': False}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], a[2], int(a[3]), a[4])
    elif a[0] == 'prereg':
        prereg(a[1], a[2])
    else:
        evaluate(a[1], a[2:-1], a[-1])
