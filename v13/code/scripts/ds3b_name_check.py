"""WP-DS3b: uncertainty on names (not only digits) + a fixed answer<->tool cross-check (lab measurement, follow-up to WP-DS3).

WP-DS3 (NOT_SUPPORTED, +1 instead of +5): after the fixed recipe tool most remaining errors are confident; the answer has
the right number but names the wrong city ("Malmo had the most rain" when the recipe's largest item is Ghent), so
digit-token uncertainty cannot see them. Two additions, both scored on recorded turns:
  (a) entity uncertainty: min logprob over answer tokens that belong to a name. A name is a capitalised word that also
      occurs capitalised in the task text at a non-sentence-initial position (cities, people, months), so no task list
      is needed. Confidence c = exp(min(digit_min_logprob, entity_min_logprob)), AG9 calibrator per component as in DS3.
  (b) fixed cross-check of the answer against the tool result (no learning, no thresholds), only when the tool ran:
      the answer must contain the recipe value; for difference_max_min the clause that says "most/largest/highest..."
      must name the recipe's largest item (and some read item must be named at all); when the question asks whether a
      stated number is correct and the text states a different number than the recipe, the answer must say it is wrong.
      check_full additionally demands that every "name ... number" pair in a clause matches the read values and that the
      "least/smallest" clause names the recipe's smallest item (reported, not judged).
Policies per task (answer = pass3 when the tool ran, else pass1, as recipe_always):
  c3_alone, recipe_always   as in DS3
  ds3_digit       abstain when calibrated P(correct) from digit confidence < T (DS3 replicated, refitted on new dev)
  name_unc        abstain when calibrated P(correct) from digit+entity confidence < T
  check           abstain when the cross-check fails
  ds3b            abstain when check fails OR name_unc abstains                     (primary)
  check_repair    on a failed check answer with a fixed sentence built from the tool result (reported, not judged)
Strict scoring (reported): a compare answer also counts wrong when it binds a wrong number to a city or names a wrong
"most" or "least" city; the bench regex only checks the largest city and the difference.
  capture   ds3b_name_check.py capture <installed_home> <seed> <out.json>   (needs runtime branch with scripts/r4_typed_recipe.py)
  prereg    ds3b_name_check.py prereg <dev.json>... <prereg.json>
  evaluate  ds3b_name_check.py evaluate <prereg.json> <fresh.json>... <report.json>
Claim limit: generated English R4 tasks, regex checks, cloud CPU; "unsicher" is scored as an abstention; no runtime change."""
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.agi.metacog import Metacognition, BINS  # noqa: E402

LAMBDA = 1.; LAMBDA_REPORT = 2.
DEV_SEEDS = (41, 43); FRESH_SEEDS = (47, 53, 59)
EXPOSED = (7, 11, 13, 17, 19, 23, 29, 31, 37)  # earlier R4 runs; the cross-check wording was written while reading 7/11/17/31/37
POLICIES = ('c3_alone', 'recipe_always', 'ds3_digit', 'name_unc', 'check', 'ds3b', 'check_repair')
DECISION = ('Fresh seeds 47+53+59 (180 tasks), evaluated once. H1 entity signal: AUROC of digit+entity confidence for '
            '"final answer wrong" >= .70 and >= AUROC of digit confidence alone + .03. H2 cross-check: of the tool tasks whose '
            'check fails >= 70 % are wrong under recipe_always, and the check flags >= 50 % of the wrong recipe_always answers on '
            'tool tasks. H3 utility (primary ds3b, LAMBDA=1): ds3b >= recipe_always + 7, ds3b wrong <= 0.7 x recipe_always wrong, '
            'answered share >= .70. H4 kept answers: ds3b correct >= recipe_always correct - 9. DS3B_SUPPORTED when H1..H4 all '
            'pass, else the failing parts are named; H2 and H3 can pass without H1 (then the check alone carries it). '
            'check_repair, check_full, strict scoring and LAMBDA=2 are reported, not judged. No runtime change.')
MAX_WORDS = r'most|largest|highest|greatest|wettest|maximum|max'
MIN_WORDS = r'least|smallest|lowest|fewest|driest|minimum|min'
NEGATION = re.compile(r"(?i)\b(no|not|incorrect|wrong|error|mistake|discrepancy|does not match|doesn't match)\b")
NUM = re.compile(r'(?<![\d.,])\d+(?![\d])')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- capture (live model)
def turn(r, text, nums, checks, cap):
    """Like r4_calc_recheck.turn, but keeps the answer's token logprobs for the entity feature."""
    import utility_bench as U
    import r4_c3_uncertainty_wake as W
    import r4_calc_recheck as C
    from v13.proofs import audit_event
    before = len(cap.streams); r.session = r.store.new_session(); t0 = time.monotonic(); eid = r.submit(text); C.wait(r, eid, t0)
    a = audit_event(r.store, eid); out = a.get('output') or ''; ok, num = U.score(out, nums, checks); streams = cap.streams[before:]
    answer = next((s for s in reversed(streams) if ''.join(t['token'] for t in s).strip() == out.strip()), streams[-1] if streams else [])
    return {'pass': all(ok.values()) and all(num.values()), 'turn_s': round(time.monotonic()-t0, 2), 'status': a.get('status'),
            'features': W.features(answer), 'tokens': answer,
            'tokens_match_output': ''.join(t['token'] for t in answer).strip() == out.strip(), 'output': out}


def capture(installed, seed, path):
    import shutil
    import tempfile
    import utility_bench2 as U2
    import r4_c3_uncertainty_wake as W
    import r4_typed_recipe as T
    from v13.common import atomic_write
    from v13.config import initialize, save_config
    from v13.runtime import Runtime
    if seed in EXPOSED:
        raise SystemExit('seed already exposed')
    installed = Path(installed).resolve(); cap = W._Capture(); cap.install(); rows = []
    with tempfile.TemporaryDirectory(prefix='v13-ds3b-') as tmp:
        home = Path(tmp); cfg = initialize(home)
        for n in ('models', 'bin'):
            shutil.rmtree(home/n); (home/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', home/'config/models.json')
        save_config(home, cfg | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'history_turns': 0}
                    | U2.BENCH_CFG | {'observer_mode': 'off'})
        r = Runtime(home)
        try:
            for fid, text, nums, checks in U2.tasks(seed):
                p1 = turn(r, text, nums, checks, cap); ex = T.read(r, text); p3 = None
                if ex['value'] is not None:
                    p3 = turn(r, text+T.RESULT_TEMPLATE.format(label=ex['expression'], value=ex['value']), nums, checks, cap)
                rows.append({'fixture': fid, 'text': text, 'nums': nums, 'checks': checks, 'pass1': p1, 'expression': ex, 'pass3': p3,
                             'expression_correct': ex['value'] is not None and any(ex['value'] == n for n in nums)})
                print(json.dumps({'fixture': fid, 'p1': p1['pass'], 'op': ex['operation'], 'value': ex['value'],
                                  'p3': None if p3 is None else p3['pass']}), flush=True)
                atomic_write(Path(path), json.dumps({'kind': 'V13_DS3B_CAPTURE', 'task_seed': seed, 'script_sha256': sha(__file__),
                                                     'recipe_sha256': sha(T.__file__), 'bench_cfg': U2.BENCH_CFG, 'rows': rows}, indent=1))
        finally:
            r.close()


# ---------------------------------------------------------------- (a) entity uncertainty
def entity_words(text):
    """Capitalised words of the task text that are not sentence-initial (':' does not end a sentence)."""
    out = set()
    for m in re.finditer(r"[A-Z][a-z]+", text):
        before = text[:m.start()].rstrip()
        if before and before[-1] not in '.?!"' and not text[max(0, m.start()-1):m.start()].isalpha():
            out.add(m.group())
    return out


def entity_min_logprob(turn, text):
    toks = turn.get('tokens') or []
    if not toks:
        return 0.
    words = entity_words(text); s = ''.join(t['token'] for t in toks); spans = []
    for m in re.finditer(r"[A-Z][a-z]+", s):
        if m.group() in words:
            spans.append((m.start(), m.end()))
    lp = []; pos = 0
    for t in toks:
        a, b = pos, pos+len(t['token']); pos = b
        if any(a < y and x < b for x, y in spans):
            lp.append(t['logprob'])
    return min(lp) if lp else 0.


def conf(turn, text, use_entity):
    f = turn['features']
    if not f:
        return 1.
    lp = f['digit_min_logprob']
    if use_entity:
        lp = min(lp, entity_min_logprob(turn, text))
    return min(1., math.exp(lp))


def final(row):
    return ('after_tool', row['pass3']) if row['pass3'] is not None else ('no_tool', row['pass1'])


def calibrators(rows, use_entity):
    pairs = {}
    for r in rows:
        comp, t = final(r); pairs.setdefault(comp, []).append([conf(t, r['text'], use_entity), int(t['pass'])])
    return {k: Metacognition._fit(v) for k, v in sorted(pairs.items())}


def cal(tables, comp, c):
    t = tables.get(comp); return 1. if not t else t[min(BINS-1, int(c*BINS))]


# ---------------------------------------------------------------- (b) fixed cross-check
def clauses(answer):
    return [c for c in re.split(r'(?<=[.;!?])\s+|,\s+(?:and\s+|while\s+|but\s+)?|\s+(?:and|while|but|whereas)\s+', answer) if c.strip()]


def named(clause, names):
    """Read item names mentioned in the clause, in order of appearance."""
    hits = []
    for n in names:
        m = re.search(r'(?i)(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])', clause)
        if m:
            hits.append((m.start(), n))
    return [n for _, n in sorted(hits)]


def cross_check(row, full=False):
    """None when the tool did not run, else (ok, reason). Uses only the task text, the read values and the recipe result."""
    ex = row['expression']
    if row['pass3'] is None or ex.get('value') is None:
        return None
    ans = row['pass3']['output']; value = ex['value']; vals = ex['values'] or []
    names = [str(v.get('name', '')).strip() for v in vals if str(v.get('name', '')).strip()]
    numbers = {str(v.get('name', '')).strip().lower(): int(v['number']) for v in vals}
    if str(value) not in NUM.findall(ans):
        return False, 'value_missing'
    if ex['operation'] == 'difference_max_min':
        nums = [int(v['number']) for v in vals]; hi = names[nums.index(max(nums))]; lo = names[nums.index(min(nums))]
        if not named(ans, names):
            return False, 'no_item_named'
        for c in clauses(ans):
            got = named(c, names)
            if re.search(r'(?i)\b('+MAX_WORDS+r')\b', c) and got and got[0] != hi:
                return False, 'wrong_largest'
            if full and re.search(r'(?i)\b('+MIN_WORDS+r')\b', c) and got and got[0] != lo:
                return False, 'wrong_smallest'
        if hi.lower() not in ans.lower():
            return False, 'largest_not_named'
    if re.search(r'(?i)\bcorrect\?', row['text']):
        stated = [int(n) for n in NUM.findall(row['text'][:row['text'].rfind('?')+1]) if int(n) not in numbers.values()]
        if any(n != value for n in stated) and not NEGATION.search(ans):
            return False, 'stated_number_not_flagged'
    if full:
        for c in clauses(ans):
            got = named(c, names); ns = NUM.findall(c)
            if len(got) == 1 and ns and int(ns[0]) != numbers[got[0].lower()] and int(ns[0]) != value:
                return False, 'name_number_mismatch'
    return True, 'ok'


def repair_text(row):
    ex = row['expression']; vals = ex['values']; v = ex['value']
    if ex['operation'] == 'total':
        return f'The correct total is {v} euros. If the text states a different total, it is wrong.'
    nums = [int(x['number']) for x in vals]; hi = vals[nums.index(max(nums))]; lo = vals[nums.index(min(nums))]
    return f"{hi['name']} had the most ({hi['number']}), {lo['name']} the least ({lo['number']}); the difference is {v}."


def bench_score(text, row):
    nums = row['nums']; checks = row['checks']
    a = all(re.search(p, text or '') is not None for p in checks.values())
    n = all(re.search(r'(?<![\d.,])'+str(x)+r'(?![\d])', text or '') is not None for x in nums)
    return a and n


def strict_ok(row, answer, passed):
    """Bench pass AND, for compare tasks, every named city carries its true number and the 'least' clause names the true minimum."""
    if not passed or not row['fixture'].startswith('compare'):
        return passed
    truth = {c: int(v) for c, v in re.findall(r'([A-Z][a-z]+) (\d+)', row['text'].split(':', 1)[1])}
    lo = min(truth, key=truth.get); hi = max(truth, key=truth.get); diff = max(truth.values())-min(truth.values())
    for c in clauses(answer):
        got = named(c, list(truth)); ns = NUM.findall(c)
        if re.search(r'(?i)\b('+MAX_WORDS+r')\b', c) and got and got[0] != hi:
            return False
        if re.search(r'(?i)\b('+MIN_WORDS+r')\b', c) and got and got[0] != lo:
            return False
        if len(got) == 1 and ns and int(ns[0]) not in (truth[got[0]], diff):
            return False
    return True


# ---------------------------------------------------------------- policies and scoring
def decide(row, policy, reg):
    """(action, correct or None, answer text or None)."""
    comp, t = final(row); act = 'tool' if comp == 'after_tool' else 'answer'
    if policy == 'c3_alone':
        return 'answer', row['pass1']['pass'], row['pass1']['output']
    if policy == 'recipe_always':
        return act, t['pass'], t['output']
    chk = cross_check(row); failed = chk is not None and not chk[0]
    if policy == 'check_repair':
        if failed:
            txt = repair_text(row); return 'repair', bench_score(txt, row), txt
        return act, t['pass'], t['output']
    digit = cal(reg['calibrators_digit'], comp, conf(t, row['text'], False)) < reg['t_digit']
    ent = cal(reg['calibrators_entity'], comp, conf(t, row['text'], True)) < reg['t_entity']
    abstain = {'ds3_digit': digit, 'name_unc': ent, 'check': failed, 'ds3b': failed or ent}[policy]
    return ('abstain', None, None) if abstain else (act, t['pass'], t['output'])


def score(rows, policy, reg, lam=LAMBDA):
    outs = [decide(r, policy, reg) for r in rows]
    right = sum(o is True for _, o, _ in outs); wrong = sum(o is False for _, o, _ in outs); ab = sum(o is None for _, o, _ in outs)
    strict_right = sum(o is not None and strict_ok(r, txt, o) for r, (_, o, txt) in zip(rows, outs))
    strict_wrong = right+wrong-strict_right
    return {'correct': right, 'wrong': wrong, 'abstain': ab, 'repair': sum(a == 'repair' for a, _, _ in outs),
            'answered_share': round((right+wrong)/len(outs), 4), 'utility': round(right-lam*wrong, 3),
            'utility_lambda2': round(right-LAMBDA_REPORT*wrong, 3),
            'strict': {'correct': strict_right, 'wrong': strict_wrong, 'utility': strict_right-strict_wrong}}


def auroc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]; neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    return round(sum((p > n)+.5*(p == n) for p in pos for n in neg)/(len(pos)*len(neg)), 4)


def wrong_auroc(rows, use_entity):
    return auroc([-conf(final(r)[1], r['text'], use_entity) for r in rows], [not final(r)[1]['pass'] for r in rows])


def check_stats(rows, full=False):
    tool = [r for r in rows if cross_check(r) is not None]
    flagged = [r for r in tool if not cross_check(r, full)[0]]; wrong = [r for r in tool if not r['pass3']['pass']]
    reasons = {}
    for r in flagged:
        k = cross_check(r, full)[1]; reasons[k] = reasons.get(k, 0)+1
    return {'tool_tasks': len(tool), 'flagged': len(flagged), 'flagged_wrong': sum(not r['pass3']['pass'] for r in flagged),
            'recipe_wrong_on_tool': len(wrong), 'caught': sum(not cross_check(r, full)[0] for r in wrong),
            'precision': round(sum(not r['pass3']['pass'] for r in flagged)/len(flagged), 4) if flagged else None,
            'recall': round(sum(not cross_check(r, full)[0] for r in wrong)/len(wrong), 4) if wrong else None, 'reasons': reasons}


def load(paths, allowed):
    rows = []; shas = {}
    for p in paths:
        d = json.loads(Path(p).read_text())
        if d.get('kind') != 'V13_DS3B_CAPTURE' or len(d['rows']) != 60 or d['task_seed'] not in allowed:
            raise SystemExit('capture incomplete, wrong kind or wrong seed: '+p)
        rows += d['rows']; shas[str(d['task_seed'])] = sha(p)
    return rows, shas


def best_threshold(rows, tables, use_entity):
    grid = sorted({0.} | {v for t in tables.values() if t for v in t} | {1.01})
    key = 'calibrators_entity' if use_entity else 'calibrators_digit'; other = 'calibrators_digit' if use_entity else 'calibrators_entity'
    pol = 'name_unc' if use_entity else 'ds3_digit'

    def util(t):
        reg = {key: tables, other: {}, 't_entity': t, 't_digit': t}
        return score(rows, pol, reg)['utility']
    return max(grid, key=lambda t: (util(t), -t))


def prereg(devs, out):
    rows, shas = load(devs, DEV_SEEDS)
    td = calibrators(rows, False); te = calibrators(rows, True)
    reg = {'calibrators_digit': td, 'calibrators_entity': te, 't_digit': best_threshold(rows, td, False), 't_entity': best_threshold(rows, te, True)}
    body = {'schema': 'v13-ds3b-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'dev_sha256': shas, **reg,
            'lambda': LAMBDA, 'dev': {p: score(rows, p, reg) for p in POLICIES},
            'dev_auroc_wrong': {'digit': wrong_auroc(rows, False), 'digit_entity': wrong_auroc(rows, True)},
            'dev_check': check_stats(rows), 'dev_check_full': check_stats(rows, True),
            'fresh_task_seeds': list(FRESH_SEEDS), 'decision_rule': DECISION, 'script_sha256': sha(__file__)}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps({k: v for k, v in body.items() if not k.startswith('calibrators')}, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__):
        raise SystemExit('script changed since preregistration')
    rows, shas = load(fresh, FRESH_SEEDS)
    if sorted(shas) != sorted(map(str, FRESH_SEEDS)):
        raise SystemExit('need every fresh seed once')
    res = {p: score(rows, p, reg) for p in POLICIES}
    au_d = wrong_auroc(rows, False); au_e = wrong_auroc(rows, True); cs = check_stats(rows)
    B, R = res['ds3b'], res['recipe_always']
    h = {'H1_entity_signal': {'auroc_digit': au_d, 'auroc_digit_entity': au_e,
                              'pass': au_e is not None and au_d is not None and au_e >= .70 and au_e >= au_d+.03},
         'H2_cross_check': {**cs, 'pass': cs['precision'] is not None and cs['recall'] is not None and cs['precision'] >= .70 and cs['recall'] >= .50},
         'H3_utility': {'ds3b': B['utility'], 'recipe_always': R['utility'], 'ds3b_wrong': B['wrong'], 'recipe_wrong': R['wrong'],
                        'answered_share': B['answered_share'],
                        'pass': B['utility'] >= R['utility']+7 and B['wrong'] <= .7*R['wrong'] and B['answered_share'] >= .70},
         'H4_kept_answers': {'ds3b_correct': B['correct'], 'recipe_correct': R['correct'], 'pass': B['correct'] >= R['correct']-9}}
    by_kind = {}
    for r in rows:
        k = r['fixture'].rstrip('0123456789'); a, o, _ = decide(r, 'ds3b', reg); d = by_kind.setdefault(k, {'answer': 0, 'tool': 0, 'abstain': 0, 'correct': 0, 'wrong': 0})
        d[a] += 1; d['correct'] += o is True; d['wrong'] += o is False
    fails = [k for k, v in h.items() if not v['pass']]
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': shas, 'policies': res, 'hypotheses': h, 'check_full': check_stats(rows, True),
            'ds3b_by_kind': by_kind, 'verdict': 'DS3B_SUPPORTED' if not fails else 'NOT_SUPPORTED: '+', '.join(fails),
            'phone_measured': False, 'runtime_changed': False}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'capture':
        capture(a[1], int(a[2]), a[3])
    elif a[0] == 'prereg':
        prereg(a[1:-1], a[-1])
    else:
        evaluate(a[1], a[2:-1], a[-1])
