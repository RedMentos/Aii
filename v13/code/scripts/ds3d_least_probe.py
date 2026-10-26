"""WP-DS3d: a second fixed probe for the "least/smallest" item (and name<->number pairs) before the DS3c tool sentence.

WP-DS3c (DS3C_SUPPORTED): on a failed answer<->tool cross-check, the recipe's fixed sentence beats saying "unsicher".
Under strict scoring the core check still missed 8 of 19 wrong R4 tool answers: they name the right largest item and the
right difference but a wrong "least" city or a wrong number for a city. ds3b_name_check.cross_check(full=True) already
has that probe (written 2026-10-22 before any DS3c capture; reported, never judged). Here it is judged:
  core_repair   DS3c policy: tool sentence when cross_check(full=False) fails
  full_repair   tool sentence when cross_check(full=True) fails                     (primary)
Captures: ds3c_tool_answer.py capture (same runtime, families r4 and f). Dev = all DS3c captures (R4 61/67, F 69/71/73).
  prereg    ds3d_least_probe.py prereg <dev.json>... <prereg.json>
  evaluate  ds3d_least_probe.py evaluate <prereg.json> <fresh.json>... <report.json>
Claim limit: generated English tasks, strict regex/rule scoring, cloud CPU; no runtime change by this script."""
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ds3b_name_check as D  # noqa: E402
import ds3c_tool_answer as C  # noqa: E402

DEV = {'r4': (61, 67), 'f': (69, 71, 73)}; FRESH = {'r4': (79, 83), 'f': (89, 97)}
POLICIES = ('recipe_always', 'core_repair', 'full_repair')
DECISION = ('Fresh R4 seeds 79+83 and family-F seeds 89+97 (120 tasks each), evaluated once, strict scoring, LAMBDA=1. '
            'H1 (R4): full_repair utility >= core_repair utility + 5. H2 (R4): full_repair wrong <= core_repair wrong - 3. '
            'H3 (F): full_repair utility >= core_repair utility - 1 (no loss on the new family). H4 (both): no wrong tool '
            'sentence with a correct value read. DS3D_SUPPORTED when H1..H4 all pass, else the failing parts are named. '
            'Bench-regex scoring reported only. No runtime change.')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def decide(row, policy):
    """(action, strict pass or None, value read correct)."""
    comp, t = D.final(row); act = 'tool' if comp == 'after_tool' else 'answer'
    if policy != 'recipe_always':
        chk = D.cross_check(row, full=policy == 'full_repair')
        if chk is not None and not chk[0]:
            txt = C.repair_text(row); b = D.bench_score(txt, row); return 'repair', C.strict(row, txt, b), bool(row['expression_correct'])
    return act, C.strict(row, t['output'], t['pass']), None


def score(rows, policy):
    outs = [decide(r, policy) for r in rows]
    right = sum(o[1] is True for o in outs); wrong = sum(o[1] is False for o in outs)
    return {'correct': right, 'wrong': wrong, 'utility': right-wrong, 'repair': sum(o[0] == 'repair' for o in outs),
            'bad_repair_good_read': sum(o[0] == 'repair' and o[1] is False and o[2] for o in outs)}


def load(paths, allowed):
    out = {'r4': [], 'f': []}; shas = {}
    for p in paths:
        d = json.loads(Path(p).read_text())
        if d.get('kind') != 'V13_DS3C_CAPTURE' or d['task_seed'] not in allowed[d['family']] or len(d['rows']) != 60:
            raise SystemExit('capture incomplete, wrong kind or seed: '+p)
        out[d['family']] += d['rows']; shas[f"{d['family']}{d['task_seed']}"] = sha(p)
    if sorted(shas) != sorted(f'{f}{s}' for f, ss in allowed.items() for s in ss):
        raise SystemExit('need every seed once')
    return out, shas


def table(rows):
    return {f: {p: score(rs, p) for p in POLICIES} for f, rs in rows.items()}


def prereg(devs, out):
    rows, shas = load(devs, DEV)
    body = {'schema': 'v13-ds3d-prereg-v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'dev_sha256': shas,
            'dev': table(rows), 'fresh_seeds': FRESH, 'decision_rule': DECISION, 'script_sha256': sha(__file__),
            'helper_sha256': {'ds3b': sha(D.__file__), 'ds3c': sha(C.__file__)}}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


def evaluate(reg_path, fresh, out):
    reg = json.loads(Path(reg_path).read_text())
    if reg['script_sha256'] != sha(__file__) or reg['helper_sha256'] != {'ds3b': sha(D.__file__), 'ds3c': sha(C.__file__)}:
        raise SystemExit('scripts changed since preregistration')
    rows, shas = load(fresh, FRESH); res = table(rows); R, F = res['r4'], res['f']
    h = {'H1_r4_utility': {'full': R['full_repair'], 'core': R['core_repair'], 'pass': R['full_repair']['utility'] >= R['core_repair']['utility']+5},
         'H2_r4_wrong': {'full_wrong': R['full_repair']['wrong'], 'core_wrong': R['core_repair']['wrong'], 'pass': R['full_repair']['wrong'] <= R['core_repair']['wrong']-3},
         'H3_f_no_loss': {'full': F['full_repair'], 'core': F['core_repair'], 'pass': F['full_repair']['utility'] >= F['core_repair']['utility']-1},
         'H4_sentences_safe': {'bad_repair_good_read': R['full_repair']['bad_repair_good_read']+F['full_repair']['bad_repair_good_read'],
                               'pass': R['full_repair']['bad_repair_good_read']+F['full_repair']['bad_repair_good_read'] == 0}}
    bench = {f: {p: C.score(rs, 'recipe_always' if p == 'recipe_always' else 'check_repair')['bench'] for p in ('recipe_always', 'core_repair')} for f, rs in rows.items()}
    fails = [k for k, v in h.items() if not v['pass']]
    body = {'prereg_sha256': sha(reg_path), 'fresh_sha256': shas, 'policies': res, 'bench_core_reference': bench, 'hypotheses': h,
            'verdict': 'DS3D_SUPPORTED' if not fails else 'NOT_SUPPORTED: '+', '.join(fails), 'phone_measured': False, 'runtime_changed': False}
    Path(out).write_text(json.dumps(body, indent=1)); print(json.dumps(body, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'prereg':
        prereg(a[1:-1], a[-1])
    else:
        evaluate(a[1], a[2:-1], a[-1])
