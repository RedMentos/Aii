#!/usr/bin/env python3
"""WP-Z3b: fixed rule parser vs. C3 as rule reader, on the canonical cohort and on reworded rules.

Z3 (NO_CONSUMER_PATH) showed: C3 reads budget, deadline and option values without error but returns
local_only = true in 117/117 rows; a deterministic parser reads the canonical wording perfectly
(tool_only 117/117). On a fixed wording a parser wins trivially, so this run adds a paraphrase cohort:
the same 39 fixtures (same values, same oracles) with every private rule sentence reworded in forms
the fixed parser was never written for (including negated yes/no rules). Only there can C3 as a
reader show value beyond a parser.

Native call groups per fixture and seed (C3 LFM2.5-350M only, cold calls):
  c3_extract  the Z3 extraction call, byte-identical system prompt and schema
  c3_rules    a focused rule reader: budget, deadline, local_only only (wording-agnostic instructions)

Scored arms (deterministic post-processing; one native call feeds several arms, so guard
differences are not confounded by sampling):
  parser_only        fixed anchored parser for every value, no model (baseline)
  x_anchored_strict  Z3 c3_extract_tool_strict replicated (anchored guard = a parser)
  x_parser_bool      C3 numbers/options, local_only from the fixed parser, anchored strict guard
  x_grounded         C3 values, wording-independent guards only (numbers must occur in a quote,
                     every number in the quotes must be accounted for, options in their own clause)
  x_hybrid           parser value where the parser reads exactly one value, else x_grounded value
  r_grounded         focused-reader values, same wording-independent guards, options parsed
  r_hybrid           parser first, focused reader as fallback, same guards
Oracle lookup only after the last runner returned. Diagnostic, no gate promotion.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import random
import re
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
APP = HERE.parents[3]
Z3_DIR = HERE.parent / 'z3-c3-consumer'
sys.path.insert(0, str(APP))
from v13.common import atomic_write, dumps, file_hash, digest
from v13.resources import device


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Z = _load('z3_c3_consumer_isolation', Z3_DIR / 'c3_consumer_isolation.py')
A, G, E = Z.A, Z.G, Z.E

VERSION = 'V13_Z3B_PARSER_VS_READER_V1'
PARA_SEED = 20261021
SEEDS = [13, 14, 15]
CALL_ORDER = ['c3_extract', 'c3_rules']
ARMS = {'parser_only': None, 'x_anchored_strict': 'c3_extract', 'x_parser_bool': 'c3_extract',
        'x_grounded': 'c3_extract', 'x_hybrid': 'c3_extract', 'r_grounded': 'c3_rules', 'r_hybrid': 'c3_rules'}
C3_ARMS = [a for a in ARMS if a != 'parser_only']
COHORTS = ['canonical', 'paraphrase']
RULES = ('budget', 'deadline', 'local_only')
CONFLICT = 'CONFLICT'

# Reworded rule sentences. None of them contains the anchored rule forms ("budget N euros",
# "deadline N days", "local-only requirement: x"); test_z3b checks the parser reads none of them.
TEMPLATES = {
    'budget': ['We can spend at most {v} euros on this.',
               'The money available is capped at {v} euros.',
               'Spending must stay within {v} euros.',
               'Our financial limit is {v} EUR.'],
    'deadline': ['It has to be finished within {v} days.',
                 'The work must be done in no more than {v} days.',
                 'We have {v} days at most to complete it.',
                 'Completion is required after {v} days at the latest.'],
    'local_true': ['Only local providers are allowed.',
                   'The chosen option must be local.',
                   'Non-local options are not permitted.',
                   'We may only work with a local option.'],
    'local_false': ['Non-local options are fine too.',
                    'There is no requirement for the option to be local.',
                    'Whether the option is local does not matter.',
                    'Remote options are allowed as well.'],
}

RULES_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': list(RULES),
                'properties': {'budget': {'type': ['integer', 'null']}, 'deadline': {'type': ['integer', 'null']},
                               'local_only': {'type': ['boolean', 'null']}}}
RULES_SYSTEM = ('You read project rules from supplied sources and return the required JSON only. Do not decide and do '
                'not report option facts. budget is the maximum money in euros, deadline the maximum number of days. '
                'local_only is true if the sources say that only local options are allowed or that the chosen option '
                'must be local; it is false if the sources say that non-local or remote options are allowed or that '
                'locality does not matter. Rules may be worded in any way. If a rule is not stated, return null for it. '
                'If the sources state two different values for the same rule, return null for that rule. '
                'Never invent a rule.')
_NUMBER = re.compile(r'\b\d+\b')
_PROJECT = re.compile(r'^Project (\w+)\.')


# ---------------------------------------------------------------- cohorts

def truth_rules(fixture):
    """Values behind the canonical sources (None = missing, CONFLICT = two values)."""
    values = G.facts(s['text'] for s in fixture['sources'])
    return {r: (CONFLICT if len(values[r]) > 1 else next(iter(values[r])) if values[r] else None) for r in RULES}


def paraphrase_source(text, rng):
    """Reword every rule clause of one canonical private source; values unchanged."""
    m = re.fullmatch(r'Project (\w+)\.((?: [^.]+\.)*)', text)
    if not m:
        raise ValueError('Unexpected canonical source form')
    out, used = ['Project ' + m.group(1) + '.'], {}
    for clause in re.findall(r' ([^.]+\.)', m.group(2)):
        for rule, pattern in G.PATTERNS.items():
            hit = pattern.fullmatch(clause)
            if hit:
                break
        else:
            raise ValueError('Unknown rule clause: ' + clause)
        key = rule if rule != 'local_only' else 'local_' + hit.group(1)
        choices = [i for i in range(len(TEMPLATES[key])) if i != used.get(key)]  # a repeated rule gets another form
        pick = rng.choice(choices)
        used[key] = pick
        out.append(TEMPLATES[key][pick].format(v=hit.group(1)))
    return ' '.join(out)


def cohorts():
    base = A.strict_json((Z.FIX / 'generated/fixtures.json').read_text())
    if dumps(base) != dumps(G.generate()):
        raise ValueError('Saved private cohort differs from its generator')
    rng = random.Random(PARA_SEED)
    canonical, para = [], []
    for f in base['fixtures']:
        truth = truth_rules(f)
        canonical.append(dict(copy.deepcopy(f), cohort='canonical', truth_rules=truth))
        p = copy.deepcopy(f)
        p['sources'] = [G.source(s['owner'], paraphrase_source(s['text'], rng)) for s in f['sources']]
        p.update(id=f['id'] + '_para', cohort='paraphrase', truth_rules=truth, canonical_id=f['id'])
        if p['oracle'] != oracle_from_truth(p):
            raise ValueError('Paraphrase changed the oracle')
        for key in ('visibility_proof', 'paired_actions'):
            p.pop(key, None)  # canonical-wording proofs; the oracle above is the binding
        para.append(p)
    return canonical + para


def oracle_from_truth(fixture):
    truth = fixture['truth_rules']
    if any(truth[r] is None or truth[r] == CONFLICT for r in RULES):
        return {'project': fixture['public']['project'], 'action': 'UNKNOWN',
                'options': [dict(o, remaining=None, eligible=None) for o in fixture['public']['options']]}
    return G.solve(fixture['public'], truth)


# ---------------------------------------------------------------- deterministic readers and guards

def parser_rules(texts):
    """Fixed anchored parser: exactly one value -> value, several -> CONFLICT, none -> None."""
    out = {}
    for rule in RULES:
        values = set().union(*(E.stated_values(rule, t) for t in texts))
        out[rule] = CONFLICT if len(values) > 1 else next(iter(values)) if values else None
    return out


def numbers(quotes):
    return {int(n) for q in quotes for n in _NUMBER.findall(q)}


def grounded_decide(reader, options, current, quotes, hybrid):
    """Wording-independent guards around reader values (hybrid: parser value first).

    numeric rule  must occur as a number in a verified quote (grounding)
    all numbers   every number in the verified quotes must be one of the accepted numeric rules,
                  otherwise a rule value is unaccounted (e.g. a second, contradicting budget) -> UNKNOWN
    options       must be stated inside their own clause (v2 option guard)
    local_only    no wording-independent check exists; taken as read
    """
    parsed = parser_rules([current, *quotes])
    rules, rejected = {}, []
    for rule in RULES:
        if hybrid and parsed[rule] == CONFLICT:
            rules[rule] = None
            rejected.append(rule + ':parser_conflict')
            continue
        if hybrid and parsed[rule] is not None:
            rules[rule] = parsed[rule]
            continue
        v = reader.get(rule)
        if v is None:
            rules[rule] = None
        elif rule == 'local_only':
            rules[rule] = v if type(v) is bool else None
        elif type(v) is not int or v < 0 or v not in numbers(quotes):
            rules[rule] = None
            rejected.append(rule + ':not_grounded')
        else:
            rules[rule] = v
    accepted = {rules[r] for r in ('budget', 'deadline') if rules[r] is not None}
    if numbers(quotes) - accepted:
        rejected.append('unaccounted_number')
        rules = {r: None for r in RULES}
    for o in options:
        if not E.option_stated(o, [current, *quotes]):
            rejected.append(o['entity'] + ':option_not_stated')
            rules['budget'] = None
    action, out = E.recipe(rules['budget'], rules['deadline'], rules['local_only'], options)
    return {'action': action, 'options': out, 'rejected': rejected, 'rules_used': rules,
            'revision': 'z3b-grounded' + ('-hybrid' if hybrid else '')}


def parser_bool_decide(extracted, options, current, quotes):
    """C3 numbers and options, local_only replaced by the fixed parser, Z3 strict guard."""
    parsed = parser_rules([current, *quotes])['local_only']
    rules = {'budget': extracted['budget'], 'deadline': extracted['deadline'],
             'local_only': parsed if type(parsed) is bool else None}
    return Z.strict_decide(rules, options, current, quotes)


def project_of(current):
    m = _PROJECT.match(current)
    return m.group(1) if m else ''


# ---------------------------------------------------------------- scoring

def summarize_answer(raw, oracle):
    return Z.summarize_answer(raw, oracle)


def read_accuracy(values, truth):
    """Per-rule read check against the truth (CONFLICT and missing expect null)."""
    out = {}
    for rule in RULES:
        want = None if truth[rule] in (None, CONFLICT) else truth[rule]
        got = values.get(rule) if isinstance(values, dict) else None
        out[rule] = type(got) is type(want) and got == want
    return out


# ---------------------------------------------------------------- native run

def run_fixture_group(runtime, fixture, group, seed, row_seconds, tokens):
    deadline = time.monotonic() + row_seconds
    current, quotes, _ = Z.consumer_view(runtime, fixture)
    texts = [q['text'] for q in quotes]
    user = json.dumps({'current_source': current, 'verified_quotes': texts}, ensure_ascii=False)
    calls, rows = [], {}
    base = {'fixture': fixture['id'], 'kind': fixture['kind'], 'cohort': fixture['cohort'], 'seed': seed,
            'group': group, 'adapter': VERSION, 'delivered_quotes': quotes, 'gate_promotion': False}
    try:
        if group == 'c3_extract':
            messages = [{'role': 'system', 'content': E.EXTRACT_SYSTEM}, {'role': 'user', 'content': user}]
            raw = Z.call(runtime, 'C3_LANGUAGE', messages, deadline, tokens, E.EXTRACT_SCHEMA, seed, calls)
            x = A.strict_json(raw)
            if set(x) != set(E.EXTRACT_SCHEMA['required']) or sorted(o.get('entity') for o in x['options']) != ['A', 'B']:
                raise ValueError('extract_schema')
            options = sorted(x['options'], key=lambda o: o['entity'])
            reader = {k: x[k] for k in RULES}
            results = {'x_anchored_strict': Z.strict_decide(reader, options, current, texts),
                       'x_parser_bool': parser_bool_decide(reader, options, current, texts),
                       'x_grounded': grounded_decide(reader, options, current, texts, False),
                       'x_hybrid': grounded_decide(reader, options, current, texts, True)}
            for arm, result in results.items():
                rows[arm] = {'raw_answer': Z.tool_answer(x['project'], result), 'extracted': x, 'tool': result}
        elif group == 'c3_rules':
            messages = [{'role': 'system', 'content': RULES_SYSTEM}, {'role': 'user', 'content': user}]
            raw = Z.call(runtime, 'C3_LANGUAGE', messages, deadline, tokens, RULES_SCHEMA, seed, calls)
            x = A.strict_json(raw)
            if set(x) != set(RULES):
                raise ValueError('rules_schema')
            options = Z.parse_options(current)
            for arm, hybrid in (('r_grounded', False), ('r_hybrid', True)):
                result = grounded_decide(x, options, current, texts, hybrid)
                rows[arm] = {'raw_answer': Z.tool_answer(project_of(current), result), 'extracted': x, 'tool': result}
        else:
            raise ValueError('Unknown call group')
        status = 'RECORDED'
    except Exception as exc:
        status = 'ERROR'
        rows = {a: {'raw_answer': '', 'extracted': None, 'error_type': type(exc).__name__, 'error': str(exc)[:500]}
                for a, g in ARMS.items() if g == group}
    out = []
    for arm, row in rows.items():
        # Oracle and truth only after the runner returned.
        out.append(base | row | {'arm': arm, 'status': status, 'calls': calls,
                                 'read_ok': read_accuracy(row.get('extracted'), fixture['truth_rules'])}
                   | summarize_answer(row['raw_answer'], fixture['oracle']))
    return out


def parser_row(fixture, seed):
    current = G.render_current(fixture['public'])
    texts = [s['text'] for s in fixture['sources']]
    parsed = parser_rules([current, *texts])
    result = grounded_decide({r: None for r in RULES}, Z.parse_options(current), current, texts, True)
    raw = Z.tool_answer(fixture['public']['project'], result)
    return ({'fixture': fixture['id'], 'kind': fixture['kind'], 'cohort': fixture['cohort'], 'seed': seed,
             'group': None, 'arm': 'parser_only', 'status': 'RECORDED', 'calls': [], 'gate_promotion': False,
             'raw_answer': raw, 'tool': result,
             'read_ok': read_accuracy({r: (None if v == CONFLICT else v) for r, v in parsed.items()}, fixture['truth_rules'])}
            | summarize_answer(raw, fixture['oracle']))


def source_bindings():
    paths = [Path(__file__), Z3_DIR / 'c3_consumer_isolation.py', Z3_DIR / 'eligibility_v2_vendored.py',
             Z.FIX / 'runtime_adapter.py', Z.FIX / 'generate_fixtures.py', Z.FIX / 'prepare_pilot.py',
             Z.FIX / 'generated/fixtures.json', APP / 'v13/runners.py', APP / 'v13/models.py', APP / 'v13/runtime.py',
             APP / 'v13/store.py', APP / 'v13/utility.py', APP / 'v13/config.py']
    return {str(p.relative_to(APP)): file_hash(p) for p in paths}


def registration(installed, row_seconds=90, tokens=256):
    fixtures = cohorts()
    return {'schema': VERSION + '_REGISTRATION', 'status': 'REGISTERED_NOT_RUN',
            'scope': 'CANONICAL_39_PLUS_PARAPHRASE_39_EXACT_SOURCES_C3_READER_VS_FIXED_PARSER',
            'cohort_sha256': digest(dumps(fixtures)), 'fixture_ids': [f['id'] for f in fixtures],
            'paraphrase_seed': PARA_SEED, 'templates': TEMPLATES, 'seeds': SEEDS, 'arms': ARMS,
            'call_order': CALL_ORDER, 'row_seconds': row_seconds, 'tokens': tokens,
            'max_native_calls': len(fixtures) * len(SEEDS) * len(CALL_ORDER),
            'rules_system_sha256': digest(RULES_SYSTEM), 'rules_schema_sha256': digest(dumps(RULES_SCHEMA)),
            'config': A.CONFIG, 'source_bindings': source_bindings(),
            'installed_bindings': Z.installed_bindings(Path(installed)), 'device': device(),
            'decision_rule': DECISION_RULE, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
            'gate_promotion': False}


def run_registered(installed, prereg, out):
    current = registration(installed, prereg['row_seconds'], prereg['tokens'])
    current['device'] = prereg['device']
    if dumps(current) != dumps(prereg):
        raise ValueError('Registration binding changed; refusing inference')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    fixtures = {f['id']: f for f in cohorts()}
    rows = []
    report = {'schema': VERSION + '_REPORT', 'status': 'RUNNING', 'registration_sha256': digest(dumps(prereg)),
              'device': device(), 'phone_measured': device()['android'], 'gate_promotion': False}
    try:
        for seed in prereg['seeds']:
            for group in prereg['call_order']:
                runtime = Z.prepare_home(out / 'homes' / f'{group}_s{seed}', Path(installed), seed)
                try:
                    for fid in prereg['fixture_ids']:
                        if source_bindings() != prereg['source_bindings']:
                            raise ValueError('Registered source changed during run')
                        rows.extend(run_fixture_group(runtime, fixtures[fid], group, seed,
                                                      prereg['row_seconds'], prereg['tokens']))
                        atomic_write(out / 'rows.partial.json', dumps(rows))
                finally:
                    runtime.close()
                shutil.rmtree(out / 'homes' / f'{group}_s{seed}', ignore_errors=True)
            rows.extend(parser_row(fixtures[fid], seed) for fid in prereg['fixture_ids'])
        shutil.rmtree(out / 'homes', ignore_errors=True)
        report['final_bindings_unchanged'] = source_bindings() == prereg['source_bindings']
        expected = {(fid, a, s) for fid in prereg['fixture_ids'] for a in prereg['arms'] for s in prereg['seeds']}
        actual = [(r['fixture'], r['arm'], r['seed']) for r in rows]
        report['coverage_complete'] = len(actual) == len(set(actual)) and set(actual) == expected
        report['status'] = 'RECORDED' if report['coverage_complete'] and report['final_bindings_unchanged'] else 'NOT_CONFIRMED'
    except BaseException as exc:
        report.update(status='INTERRUPTED', error_type=type(exc).__name__, error=str(exc)[:500])
        raise
    finally:
        report['rows'] = len(rows)
        atomic_write(out / 'rows.json', dumps(rows))
        report['rows_sha256'] = file_hash(out / 'rows.json')
        report['summary'] = summarize(rows, prereg)
        atomic_write(out / 'report.json', dumps(report))
    return report


# ---------------------------------------------------------------- decision rule (registered)

DECISION_RULE = {
    'carries': 'decision_exact >= 0.80 and wrong_commit <= 0.05, pooled over 3 seeds x 39 fixtures of one cohort',
    'gain': 'paired bootstrap (over fixtures, seeds averaged) of arm - parser_only on the paraphrase cohort: 95% CI lower bound > 0',
    'order': ['C3_READER_BEATS_PARSER: some C3 arm carries on paraphrase AND carries on canonical',
              'C3_READER_PARTIAL_GAIN: some C3 arm has gain AND wrong_commit <= 0.05 on both cohorts',
              'PARSER_SUFFICIENT_NO_C3_GAIN: otherwise'],
    'secondary': 'x_parser_bool carries on canonical -> BOOL_PARSER_FIX_CONFIRMED else BOOL_PARSER_FIX_NOT_CONFIRMED',
    'no_rerun': 'no rerun with changed prompts, templates or guards under this registration',
}


def _rate(rows, key):
    return sum(bool(r[key]) for r in rows) / len(rows) if rows else 0.


def paired_ci(rows, a, b, draws=5000, seed=20261021):
    """Pair by canonical fixture id within one cohort (rows filtered by the caller)."""
    return Z.paired_ci(rows, a, b, 'decision_exact', draws, seed)


def arm_stats(rs, seeds):
    controls = [r for r in rs if r['kind'] in ('missing_rule', 'contradictory_rule')]
    decided = [r for r in rs if r['kind'] not in ('missing_rule', 'contradictory_rule')]
    reads = {rule: sum(bool(r['read_ok'][rule]) for r in rs) / len(rs) if rs else 0. for rule in RULES}
    return {'rows': len(rs), 'errors': sum(r['status'] != 'RECORDED' for r in rs),
            'decision_exact': _rate(rs, 'decision_exact'), 'wrong_commit': _rate(rs, 'wrong_commit'),
            'action_correct': _rate(rs, 'action_correct'),
            'strict_exact': sum(bool(r['score'].get('exact')) for r in rs) / len(rs) if rs else 0.,
            'decision_exact_by_seed': {str(s): _rate([r for r in rs if r['seed'] == s], 'decision_exact') for s in seeds},
            'decided_cases_decision_exact': _rate(decided, 'decision_exact'),
            'decided_cases_wrong_commit': _rate(decided, 'wrong_commit'),
            'unknown_controls_correct': _rate(controls, 'action_correct'),
            'unknown_controls_wrong_commit': _rate(controls, 'wrong_commit'),
            'reader_rule_read_ok': reads}


def summarize(rows, prereg):
    stats = {c: {a: arm_stats([r for r in rows if r['arm'] == a and r['cohort'] == c], prereg['seeds'])
                 for a in prereg['arms']} for c in COHORTS}
    para_rows = [dict(r, fixture=r['fixture'].removesuffix('_para')) for r in rows if r['cohort'] == 'paraphrase']
    paired = {a: paired_ci(para_rows, a, 'parser_only') for a in C3_ARMS}

    def carries(cohort, arm):
        x = stats[cohort].get(arm, {})
        return bool(x.get('rows')) and x['decision_exact'] >= .8 and x['wrong_commit'] <= .05

    def gain(arm):
        p = paired.get(arm)
        return (p is not None and p['ci95'][0] > 0 and stats['paraphrase'][arm]['wrong_commit'] <= .05
                and stats['canonical'][arm]['wrong_commit'] <= .05)

    beats = [a for a in C3_ARMS if carries('paraphrase', a) and carries('canonical', a)]
    partial = [a for a in C3_ARMS if gain(a)]
    verdict = ('C3_READER_BEATS_PARSER' if beats else 'C3_READER_PARTIAL_GAIN' if partial
               else 'PARSER_SUFFICIENT_NO_C3_GAIN')
    secondary = 'BOOL_PARSER_FIX_CONFIRMED' if carries('canonical', 'x_parser_bool') else 'BOOL_PARSER_FIX_NOT_CONFIRMED'
    return {'cohorts': stats, 'paired_paraphrase_vs_parser': paired, 'arms_beating_parser': beats,
            'arms_partial_gain': partial, 'verdict': verdict, 'secondary': secondary,
            'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register')
    reg.add_argument('--installed', type=Path, required=True)
    reg.add_argument('--out', type=Path, required=True)
    exp = sub.add_parser('export-cohort')
    exp.add_argument('--out', type=Path, required=True)
    run = sub.add_parser('run')
    run.add_argument('--installed', type=Path, required=True)
    run.add_argument('--registration', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command in ('register', 'export-cohort') and args.out.exists():
        raise FileExistsError('Output already exists')
    if args.command == 'export-cohort':
        atomic_write(args.out, dumps(cohorts()))
        print(dumps({'fixtures': len(cohorts()), 'cohort_sha256': digest(dumps(cohorts()))}))
        return 0
    if args.command == 'register':
        result = registration(args.installed)
        atomic_write(args.out, dumps(result))
        print(dumps({'status': result['status'], 'registration_sha256': digest(dumps(result)),
                     'max_native_calls': result['max_native_calls']}))
        return 0
    report = run_registered(args.installed, A.strict_json(args.registration.read_text()), args.out)
    print(dumps({'status': report['status'], 'rows': report['rows'], 'verdict': report['summary']['verdict'],
                 'secondary': report['summary']['secondary']}))
    return 0 if report['status'] == 'RECORDED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
