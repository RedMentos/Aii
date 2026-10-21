#!/usr/bin/env python3
"""WP-Z3: isolate the STEP2 consumer. Identical exact sources, different consumers.

Every arm receives the same current source and the same two exact private
source quotations (the pilot's exact_source_control delivery, all 39 fixtures
of the saved private cohort). Only the consumer differs:

  c3_direct              C3 LFM2.5-350M answers the decision schema itself (pilot control at scale)
  b2_direct              B2 Qwen3.5-0.8B as answering body, same messages
  b1_direct              B1 LFM2.5-1.2B as answering body, same messages
  c3_extract_tool        C3 only extracts typed values; vendored eligibility-v2 (live ToolStep path) decides
  c3_extract_tool_strict same extraction call; v2 plus a same-revision check (one stated value per rule)
  tool_label_c3          deterministic parse + strict recipe; C3 gets the readable result line and must answer
  tool_only              deterministic parse + strict recipe, no model (ceiling, 0 native calls)

c3_extract_tool and c3_extract_tool_strict score the SAME native extraction
call, so the guard difference is not confounded by sampling. Oracle lookup
happens only after the last runner returned. Diagnostic, no gate promotion.
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
FIX = APP / 'docs/proofs/continuation-20261016/step2-private-fixtures'
sys.path.insert(0, str(APP))
from v13.common import atomic_write, dumps, file_hash, digest
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision
from v13.resources import device


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = _load('step2_private_adapter', FIX / 'runtime_adapter.py')
G = A.G
E = _load('eligibility_v2_vendored', HERE / 'eligibility_v2_vendored.py')

VERSION = 'V13_Z3_C3_CONSUMER_ISOLATION_V1'
ROLE = {'c3_direct': 'C3_LANGUAGE', 'b2_direct': 'B2_GIST', 'b1_direct': 'B1_DETAIL',
        'c3_extract': 'C3_LANGUAGE', 'tool_label_c3': 'C3_LANGUAGE'}
# Scored arms -> native call group. Both extract arms share one call.
ARMS = {'c3_direct': 'c3_direct', 'b2_direct': 'b2_direct', 'b1_direct': 'b1_direct',
        'c3_extract_tool': 'c3_extract', 'c3_extract_tool_strict': 'c3_extract',
        'tool_label_c3': 'tool_label_c3', 'tool_only': None}
CALL_ORDER = ['c3_direct', 'b2_direct', 'b1_direct', 'c3_extract', 'tool_label_c3']
SEEDS = [13, 14, 15]
TOOL_LINE_KEY = 'tool_result'
_OPTION = re.compile(r'\bOption (A|B): cost (\d+) euros, duration (\d+) days, local (true|false)\.')


def parse_options(current):
    found = [{'entity': e, 'cost': int(c), 'days': int(d), 'local': l == 'true'} for e, c, d, l in _OPTION.findall(current)]
    if sorted(o['entity'] for o in found) != ['A', 'B']:
        raise ValueError('Current source does not state both options')
    return sorted(found, key=lambda o: o['entity'])


def strict_decide(rules, options, current, quotes):
    """eligibility-v2 plus same-revision consistency: a rule stated with more than one
    value across current source and verified quotes (no current override) is unavailable."""
    texts = [current, *quotes]
    result = E.decide(rules, options, current, quotes)
    conflicts = []
    for rule in ('budget', 'deadline', 'local_only'):
        if E.stated_values(rule, current):
            continue  # current-source rules override earlier ones (v2 semantics)
        values = set().union(*(E.stated_values(rule, t) for t in texts))
        if len(values) > 1:
            conflicts.append(rule + ':contradictory_sources')
    if conflicts:
        action, out = E.recipe(None, None, None, options)
        result = {'action': action, 'options': out, 'rejected': result['rejected'] + conflicts,
                  'revision': E.REVISION + '+same-revision-strict'}
    else:
        result = dict(result, revision=E.REVISION + '+same-revision-strict')
    return result


def deterministic(current, quotes):
    """No model: rules read only directly after their rule words; one value each or unavailable."""
    texts = [current, *quotes]
    rules = {}
    for rule in ('budget', 'deadline', 'local_only'):
        values = set().union(*(E.stated_values(rule, t) for t in texts))
        rules[rule] = next(iter(values)) if len(values) == 1 else None
    return strict_decide(rules, parse_options(current), current, quotes)


def tool_answer(project, result):
    return dumps({'project': project, 'action': result['action'], 'options': result['options']})


def decision_exact(score):
    checks = score.get('field_checks') or {}
    return bool(checks) and all(v for k, v in checks.items() if k != 'project')


def summarize_answer(raw, oracle):
    score = score_decision(raw, oracle)
    try:
        action = json.loads(raw).get('action')
    except (ValueError, TypeError, AttributeError):
        action = None
    wrong_commit = action in ('A', 'B', 'NONE') and action != oracle['action']
    return {'score': score, 'decision_exact': decision_exact(score), 'answer_action': action,
            'action_correct': action == oracle['action'], 'wrong_commit': wrong_commit}


def prepare_home(home, installed, seed):
    home.mkdir(parents=True, exist_ok=False)
    initialize(home)
    save_config(home, A.CONFIG | {'seed': seed})
    for name in ('models', 'bin'):
        (home / name).rmdir()
        (home / name).symlink_to((installed / name).resolve(), target_is_directory=True)
    shutil.copyfile(installed / 'config/models.json', home / 'config/models.json')
    A.disable_background_sleep(home)
    return Runtime(home)


def call(runtime, role, messages, deadline, tokens, schema, seed, transcript):
    """Cold native call (pool unloaded afterwards); captured prompt is the exact argument."""
    entry = {'role': role, 'messages': copy.deepcopy(messages), 'max_tokens': tokens,
             'schema_sha256': digest(dumps(schema)), 'seed': seed, 'raw': '', 'status': 'RUNNING'}
    transcript.append(entry)
    runner = None
    try:
        runner = runtime.pool.get(role)
        for chunk in runner.generate(messages, runtime.cancel_event, deadline, tokens, schema, seed=seed):
            entry['raw'] += chunk
            if len(entry['raw'].encode()) > 32768:
                raise ValueError('Native output exceeded bounded cap')
        entry['metrics'] = {k: copy.deepcopy(runner.last_metrics.get(k)) for k in
                            ('status', 'actual_model', 'duration_s', 'generated_tokens', 'prompt_tokens',
                             'sampled_peak_rss_bytes', 'ttft_s')}
        if entry['metrics'].get('status') != 'FINAL':
            raise ValueError('Runner did not finish FINAL')
        entry['status'] = 'FINAL'
        return entry['raw']
    except BaseException as exc:
        entry.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:500])
        raise
    finally:
        runtime.pool.unload()


def consumer_view(runtime, fixture):
    event, private = A.insert_sources(runtime, fixture)
    quotes = [{'source_ref': copy.deepcopy(s['source_ref']), 'text': runtime.store.read_source(s['source_ref'])}
              for s in private]
    messages = A.consumer_messages(runtime, event, quotes)
    current = runtime.store.read_source(event['source_ref'])
    return current, quotes, messages


def run_fixture_group(runtime, fixture, group, seed, row_seconds, tokens):
    """One native call group for one fixture; returns scored arm rows."""
    deadline = time.monotonic() + row_seconds
    current, quotes, messages = consumer_view(runtime, fixture)
    texts = [q['text'] for q in quotes]
    calls, rows = [], {}
    base = {'fixture': fixture['id'], 'kind': fixture['kind'], 'seed': seed, 'group': group, 'adapter': VERSION,
            'delivered_quotes': quotes, 'gate_promotion': False}
    try:
        if group in ('c3_direct', 'b2_direct', 'b1_direct'):
            raw = call(runtime, ROLE[group], messages, deadline, tokens, A.DECISION_SCHEMA, seed, calls)
            rows[group] = {'raw_answer': raw}
        elif group == 'c3_extract':
            user = json.dumps({'current_source': current, 'verified_quotes': texts}, ensure_ascii=False)
            ext_messages = [{'role': 'system', 'content': E.EXTRACT_SYSTEM}, {'role': 'user', 'content': user}]
            raw = call(runtime, ROLE[group], ext_messages, deadline, tokens, E.EXTRACT_SCHEMA, seed, calls)
            extracted = A.strict_json(raw)
            if set(extracted) != set(E.EXTRACT_SCHEMA['required']) or sorted(o.get('entity') for o in extracted['options']) != ['A', 'B']:
                raise ValueError('extract_schema')
            options = sorted(extracted['options'], key=lambda o: o['entity'])
            rules = {k: extracted[k] for k in ('budget', 'deadline', 'local_only')}
            v2 = E.decide(rules, options, current, texts)
            strict = strict_decide(rules, options, current, texts)
            rows['c3_extract_tool'] = {'raw_answer': tool_answer(extracted['project'], v2), 'extracted': extracted, 'tool': v2}
            rows['c3_extract_tool_strict'] = {'raw_answer': tool_answer(extracted['project'], strict), 'extracted': extracted, 'tool': strict}
        elif group == 'tool_label_c3':
            result = deterministic(current, texts)
            user = json.loads(messages[1]['content']) | {TOOL_LINE_KEY: E.label(result)}
            label_messages = [messages[0], {'role': 'user', 'content': dumps(user)}]
            raw = call(runtime, ROLE[group], label_messages, deadline, tokens, A.DECISION_SCHEMA, seed, calls)
            rows['tool_label_c3'] = {'raw_answer': raw, 'tool': result}
        else:
            raise ValueError('Unknown call group')
        status = 'RECORDED'
    except Exception as exc:
        status = 'ERROR'
        names = [a for a, g in ARMS.items() if g == group]
        rows = {a: {'raw_answer': '', 'error_type': type(exc).__name__, 'error': str(exc)[:500]} for a in names}
    out = []
    for arm, row in rows.items():
        # Oracle only after the runner returned.
        out.append(base | row | {'arm': arm, 'status': status, 'calls': calls} | summarize_answer(row['raw_answer'], fixture['oracle']))
    return out


def source_bindings():
    paths = [Path(__file__), HERE / 'eligibility_v2_vendored.py', FIX / 'runtime_adapter.py',
             FIX / 'generate_fixtures.py', FIX / 'prepare_pilot.py', FIX / 'generated/fixtures.json',
             APP / 'v13/runners.py', APP / 'v13/models.py', APP / 'v13/runtime.py', APP / 'v13/store.py',
             APP / 'v13/utility.py', APP / 'v13/config.py']
    return {str(p.relative_to(APP)): file_hash(p) for p in paths}


def installed_bindings(installed):
    full = A.installed_bindings(installed)
    # Paths stay local; hashes and sizes are the binding.
    return {'models': {r: {k: v for k, v in m.items() if k != 'path'} for r, m in full['models'].items()},
            'runner_sha256': full['runner']['sha256'], 'runtime_libraries': full['runtime_libraries'],
            'models_manifest_sha256': full['models_manifest_sha256']}


def registration(installed, row_seconds=90, tokens=256):
    fixtures = A.strict_json((FIX / 'generated/fixtures.json').read_text())
    if dumps(fixtures) != dumps(G.generate()):
        raise ValueError('Saved private cohort differs from its generator')
    ids = [f['id'] for f in fixtures['fixtures']]
    return {'schema': VERSION + '_REGISTRATION', 'status': 'REGISTERED_NOT_RUN',
            'scope': 'FULL_39_FIXTURE_PRIVATE_COHORT_EXACT_SOURCES_CONSUMER_ISOLATION',
            'fixtures_sha256': digest(dumps(fixtures)), 'fixture_ids': ids, 'seeds': SEEDS,
            'arms': ARMS, 'call_order': CALL_ORDER, 'row_seconds': row_seconds, 'tokens': tokens,
            'max_native_calls': len(ids) * len(SEEDS) * len(CALL_ORDER),
            'config': A.CONFIG, 'source_bindings': source_bindings(),
            'installed_bindings': installed_bindings(Path(installed)), 'device': device(),
            'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED', 'gate_promotion': False}


def run_registered(installed, prereg, out, row_seconds=None):
    current = registration(installed, prereg['row_seconds'], prereg['tokens'])
    current['device'] = prereg['device']  # device is informative; code/model bytes are the binding
    if dumps(current) != dumps(prereg):
        raise ValueError('Registration binding changed; refusing inference')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    fixtures = {f['id']: f for f in A.strict_json((FIX / 'generated/fixtures.json').read_text())['fixtures']}
    rows = []
    report = {'schema': VERSION + '_REPORT', 'status': 'RUNNING', 'registration_sha256': digest(dumps(prereg)),
              'device': device(), 'phone_measured': device()['android'], 'gate_promotion': False}
    try:
        for seed in prereg['seeds']:
            for group in prereg['call_order']:
                runtime = prepare_home(out / 'homes' / f'{group}_s{seed}', Path(installed), seed)
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
            for fid in prereg['fixture_ids']:
                f = fixtures[fid]
                current = G.render_current(f['public'])
                texts = [s['text'] for s in f['sources']]
                rows.append({'fixture': fid, 'kind': f['kind'], 'seed': seed, 'group': None, 'arm': 'tool_only',
                             'status': 'RECORDED', 'calls': [], 'gate_promotion': False,
                             'raw_answer': tool_answer(f['public']['project'], deterministic(current, texts))}
                            | summarize_answer(tool_answer(f['public']['project'], deterministic(current, texts)), f['oracle']))
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


def _rate(rows, key):
    return sum(bool(r[key]) for r in rows) / len(rows) if rows else 0.


def paired_ci(rows, a, b, key='decision_exact', draws=5000, seed=20261021):
    """Bootstrap over fixtures (seeds averaged inside a fixture): mean(a) - mean(b), 95 % CI."""
    def per_fixture(arm):
        by = {}
        for r in rows:
            if r['arm'] == arm:
                by.setdefault(r['fixture'], []).append(bool(r[key]))
        return {k: sum(v) / len(v) for k, v in by.items()}
    pa, pb = per_fixture(a), per_fixture(b)
    ids = sorted(set(pa) & set(pb))
    if not ids:
        return None
    diffs = [pa[i] - pb[i] for i in ids]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(diffs) for _ in ids) / len(ids) for _ in range(draws))
    return {'delta': sum(diffs) / len(diffs), 'ci95': [boots[int(.025 * draws)], boots[int(.975 * draws) - 1]], 'n_fixtures': len(ids)}


def summarize(rows, prereg):
    arms = {}
    for arm in prereg['arms']:
        rs = [r for r in rows if r['arm'] == arm]
        controls = [r for r in rs if r['kind'] in ('missing_rule', 'contradictory_rule')]
        decided = [r for r in rs if r['kind'] not in ('missing_rule', 'contradictory_rule')]
        seeds = {}
        for s in prereg['seeds']:
            ss = [r for r in rs if r['seed'] == s]
            seeds[str(s)] = _rate(ss, 'decision_exact')
        arms[arm] = {'rows': len(rs), 'errors': sum(r['status'] != 'RECORDED' for r in rs),
                     'strict_exact': sum(bool(r['score'].get('exact')) for r in rs) / len(rs) if rs else 0.,
                     'decision_exact': _rate(rs, 'decision_exact'), 'decision_exact_by_seed': seeds,
                     'action_correct': _rate(rs, 'action_correct'), 'wrong_commit': _rate(rs, 'wrong_commit'),
                     'mean_utility': sum(r['score']['utility'] for r in rs) / len(rs) if rs else 0.,
                     'decided_cases_decision_exact': _rate(decided, 'decision_exact'),
                     'unknown_controls_correct': _rate(controls, 'action_correct'),
                     'unknown_controls_wrong_commit': _rate(controls, 'wrong_commit')}
    def ok(arm):
        x = arms.get(arm, {})
        return x.get('decision_exact', 0.) >= .8 and x.get('wrong_commit', 1.) <= .05
    if ok('c3_direct'):
        verdict = 'C3_SUFFICIENT'
    elif ok('b1_direct') or ok('b2_direct'):
        verdict = 'BODY_REPLACES_C3_FOR_DECISIONS'
    elif ok('c3_extract_tool_strict') or ok('c3_extract_tool'):
        verdict = 'TOOL_COMPLEMENTS_C3'
    elif ok('tool_label_c3'):
        verdict = 'C3_ONLY_AS_FORMATTER'
    else:
        verdict = 'NO_CONSUMER_PATH'
    return {'arms': arms, 'verdict': verdict,
            'paired': {f'{a}-c3_direct': paired_ci(rows, a, 'c3_direct') for a in prereg['arms'] if a != 'c3_direct'},
            'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register')
    reg.add_argument('--installed', type=Path, required=True)
    reg.add_argument('--out', type=Path, required=True)
    run = sub.add_parser('run')
    run.add_argument('--installed', type=Path, required=True)
    run.add_argument('--registration', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'register':
        if args.out.exists():
            raise FileExistsError('Registration already exists')
        result = registration(args.installed)
        atomic_write(args.out, dumps(result))
        print(dumps({'status': result['status'], 'registration_sha256': digest(dumps(result)),
                     'max_native_calls': result['max_native_calls']}))
        return 0
    report = run_registered(args.installed, A.strict_json(args.registration.read_text()), args.out)
    print(dumps({'status': report['status'], 'rows': report['rows'], 'verdict': report['summary']['verdict']}))
    return 0 if report['status'] == 'RECORDED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
