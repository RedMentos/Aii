#!/usr/bin/env python3
"""Isolated STEP2 private-source runner adapter; no old-cohort gate promotion.

Real Runtime/Store and runner generate() boundary, without cognition Offer/state
claims. Register before native inference. Tests replace only pool.get().generate.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
APP = HERE.parents[3]
sys.path.insert(0, str(APP))
from v13.common import atomic_write, dumps, file_hash, digest
from v13.config import initialize, save_config, DEFAULTS
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import Store
from v13.sleep import POLICY_KEY, default_policy
from v13.memory_server import runtime_library_hashes
from v13.utility import score_decision
from v13.resources import device

spec = importlib.util.spec_from_file_location('step2_private_geometry', HERE / 'generate_fixtures.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
pilot_spec = importlib.util.spec_from_file_location('step2_private_pilot', HERE / 'prepare_pilot.py')
P = importlib.util.module_from_spec(pilot_spec)
pilot_spec.loader.exec_module(P)

VERSION = 'V13_STEP2_PRIVATE_RUNTIME_ADAPTER_V1'
# These names deliberately do not claim the historical seven channel/state arms.
VARIANTS = {
    'b1_model_quotes': {'roles': ['B1_DETAIL'], 'delivery': 'MODEL_VALIDATED_QUOTES'},
    'b2_model_quotes': {'roles': ['B2_GIST'], 'delivery': 'MODEL_VALIDATED_QUOTES'},
    'paired_model_quotes': {'roles': list(G.ROLES), 'delivery': 'MODEL_VALIDATED_QUOTES'},
    'same_policy_dual': {'roles': ['B1_DETAIL', 'B1_DETAIL'], 'delivery': 'MODEL_VALIDATED_QUOTES'},
    'no_message': {'roles': list(G.ROLES), 'delivery': 'NONE'},
    'exact_source_control': {'roles': [], 'delivery': 'EXACT_SOURCE_CONTROL'},
}
SOURCE_REF_SCHEMA = {'type': 'object', 'additionalProperties': False,
    'required': ['source_id', 'sha256', 'char_start', 'char_end', 'modality'],
    'properties': {'source_id': {'type': 'string'}, 'sha256': {'type': 'string'},
                   'char_start': {'type': 'integer'}, 'char_end': {'type': 'integer'},
                   'modality': {'type': 'string', 'enum': ['text']}}}
QUOTE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['quotes'],
    'properties': {'quotes': {'type': 'array', 'maxItems': 4, 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['source_ref', 'text'],
        'properties': {'source_ref': SOURCE_REF_SCHEMA, 'text': {'type': 'string'}}}}}}
DECISION_SCHEMA = {'type': 'object', 'additionalProperties': False,
    'required': ['project', 'action', 'options'], 'properties': {
        'project': {'type': 'string'}, 'action': {'type': 'string', 'enum': ['A', 'B', 'NONE', 'UNKNOWN']},
        'options': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['entity', 'cost', 'remaining', 'days', 'local', 'eligible'],
            'properties': {'entity': {'type': 'string', 'enum': ['A', 'B']}, 'cost': {'type': 'integer'},
                'remaining': {'type': ['integer', 'null']}, 'days': {'type': 'integer'},
                'local': {'type': 'boolean'}, 'eligible': {'type': ['boolean', 'null']}}}}}}
PRODUCER_SYSTEM = G.PRODUCER_SYSTEM + (
    ' Return only JSON {"quotes":[{"source_ref":{...},"text":"exact quotation"}]}. '
    'Copy the supplied SourceRef and its complete source text unchanged, or return an empty quotes array. '
    'Never quote a source that was not supplied to you. No answer, explanation or summary fields.')
CONFIG = DEFAULTS | {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False,
    'history_turns': 0, 'memory_top_k': 0, 'memory_embedding': 'off', 'observer_mode': 'off',
    'body_residency_mb': 0, 'b2_state_slots': 0, 'b2_control': 'two_body'}


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def insert_sources(runtime, fixture):
    """Coordinator-only source registry. Neither runner receives this combined map."""
    event = runtime.store.event(runtime.session, G.render_current(fixture['public']))
    private = []
    for source in fixture['sources']:
        G.checked_source(source)
        ref = runtime.store.source(source['text'], kind='STEP2_PRIVATE_' + source['owner'])
        if ref['sha256'] != source['sha256']:
            raise ValueError('Private source bytes changed')
        private.append({'owner': source['owner'], 'source_ref': ref})
    return event, private


def producer_messages(runtime, event, private, role):
    if role not in G.ROLES:
        raise ValueError('Unknown producer role')
    # Store validates every byte immediately before it enters a runner prompt.
    return [{'role': 'system', 'content': PRODUCER_SYSTEM}, {'role': 'user', 'content': dumps({
        'role': role, 'current_source': runtime.store.read_source(event['source_ref']),
        'private_sources': [{'source_ref': copy.deepcopy(s['source_ref']),
                             'text': runtime.store.read_source(s['source_ref'])}
                            for s in private if s['owner'] == role]})}]


def validate_model_quotes(runtime, raw, private, role):
    """Require visibility AND actual Store provenance; no hidden-source recovery."""
    if role not in G.ROLES:
        raise ValueError('Unknown producer role')
    obj = strict_json(raw)
    if type(obj) is not dict or set(obj) != {'quotes'} or type(obj['quotes']) is not list or len(obj['quotes']) > 4:
        raise ValueError('Invalid producer quotation envelope')
    allowed = {s['source_ref']['source_id']: s['source_ref'] for s in private if s['owner'] == role}
    quotes, seen = [], set()
    for quote in obj['quotes']:
        if type(quote) is not dict or set(quote) != {'source_ref', 'text'}:
            raise ValueError('Only model-produced SourceRef and exact text may be delivered')
        ref, text = quote['source_ref'], quote['text']
        if type(ref) is not dict or set(ref) != set(SOURCE_REF_SCHEMA['required']):
            raise ValueError('Invalid SourceRef schema')
        if any(type(ref[key]) is not str for key in ('source_id', 'sha256', 'modality')):
            raise ValueError('Invalid SourceRef identity types')
        if type(ref['char_start']) is not int or type(ref['char_end']) is not int:
            raise ValueError('SourceRef offsets must be integers')
        # Complete source quotes keep the parser contract narrow; no span repair.
        if ref != allowed.get(ref.get('source_id')):
            raise ValueError('SourceRef outside producer visibility or changed')
        if type(text) is not str or not text or runtime.store.read_source(ref) != text:
            raise ValueError('Quotation differs from Store bytes')
        key = dumps(quote)
        if key in seen:
            raise ValueError('Duplicate quotation in one producer output')
        seen.add(key)
        quotes.append(copy.deepcopy(quote))
    return quotes


def consumer_messages(runtime, event, quotes):
    verified = []
    for quote in quotes:
        if runtime.store.read_source(quote['source_ref']) != quote['text']:
            raise ValueError('Validated quotation changed before consumer call')
        if quote not in verified:
            verified.append(copy.deepcopy(quote))
    return [{'role': 'system', 'content': G.SYSTEM}, {'role': 'user', 'content': dumps({
        'current_source': runtime.store.read_source(event['source_ref']), 'verified_quotes': verified})}]


def generate(runtime, role, messages, deadline, tokens, schema, transcript, progress=None, event_id=None):
    """Single native runner boundary; captured prompts are the exact arguments."""
    call = {'role': role, 'messages': copy.deepcopy(messages), 'max_tokens': tokens,
            'schema_sha256': digest(dumps(schema)), 'seed': CONFIG['seed'], 'raw': '', 'status': 'RUNNING'}
    transcript.append(call)
    if progress:
        progress()
    runner, mid = None, None
    try:
        runner = runtime.pool.get(role)
        mid = runtime.store.message(runtime.session, event_id, 'assistant', status='DRAFT', metadata={
            'proof_kind': VERSION, 'producer_role': role, 'runner_messages_sha256': digest(dumps(messages))})
        for chunk in runner.generate(messages, runtime.cancel_event, deadline, tokens, schema, seed=CONFIG['seed']):
            call['raw'] += chunk
            runtime.store.append_message(mid, chunk)
            if progress:
                progress()
            if len(call['raw'].encode()) > 32768:
                raise ValueError('Native output exceeded bounded adapter cap')
        call['metrics'] = copy.deepcopy(runner.last_metrics)
        if call['metrics'].get('status') != 'FINAL':
            raise ValueError('Runner did not finish FINAL')
        call['status'] = 'FINAL'
        runtime.store.finish_message(mid, 'FINAL', {'proof_kind': VERSION, 'runner': call['metrics']})
        return call['raw']
    except BaseException as exc:
        call.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:500],
                    metrics=copy.deepcopy(runner.last_metrics) if runner else {})
        if mid is not None:
            runtime.store.finish_message(mid, 'ERROR', {'proof_kind': VERSION, 'error_type': type(exc).__name__})
        raise
    finally:
        # Independent cold native calls prevent implicit prompt-cache/history
        # transfer, including between the two identical B1-private calls.
        runtime.pool.unload()
        if progress:
            progress()


def run_row(runtime, fixture, variant, row_seconds=90, producer_tokens=256, consumer_tokens=256,
            record=None):
    if variant not in VARIANTS:
        raise ValueError('Unsupported variant')
    runtime.require_idle()
    if runtime.cfg != CONFIG:
        raise ValueError('Runtime config differs from fixed adapter policy')
    started = time.monotonic()
    deadline = started + row_seconds
    row = {'fixture': fixture['id'], 'kind': fixture['kind'], 'variant': variant, 'status': 'RUNNING',
           'calls': [], 'delivered_quotes': [], 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
           'gate_promotion': False, 'adapter': VERSION, 'evidence_level': 'UNCLASSIFIED_RUNNER_BOUNDARY'}
    progress = (lambda: record(row)) if record else None
    generation = runtime.store.generation_id
    try:
        event, private = insert_sources(runtime, fixture)
        row.update(event=event, private_registry=private)
        quotes = []
        for role in VARIANTS[variant]['roles']:
            messages = producer_messages(runtime, event, private, role)
            raw = generate(runtime, role, messages, deadline, producer_tokens, QUOTE_SCHEMA,
                           row['calls'], progress, event['event_id'])
            valid = validate_model_quotes(runtime, raw, private, role)
            row['calls'][-1]['validated_quotes'] = valid
            quotes.extend(valid)
        delivery = VARIANTS[variant]['delivery']
        if delivery == 'NONE':
            quotes = []
        elif delivery == 'EXACT_SOURCE_CONTROL':
            quotes = [{'source_ref': copy.deepcopy(s['source_ref']),
                       'text': runtime.store.read_source(s['source_ref'])} for s in private]
        messages = consumer_messages(runtime, event, quotes)
        row['delivered_quotes'] = json.loads(messages[1]['content'])['verified_quotes']
        row['delivery_origin'] = delivery
        row['raw_answer'] = generate(runtime, 'C3_LANGUAGE', messages, deadline, consumer_tokens,
                                     DECISION_SCHEMA, row['calls'], progress, event['event_id'])
        # Oracle lookup happens only after the last runner has returned.
        row['score'] = score_decision(row['raw_answer'], fixture['oracle'])
        row['checks'] = {'generation_unchanged': generation == runtime.store.generation_id,
                         'store_integrity': not runtime.store.integrity(True),
                         'all_calls_final': all(c['status'] == 'FINAL' for c in row['calls'])}
        row['status'] = 'RECORDED' if all(row['checks'].values()) else 'STRUCTURAL_FAIL'
    except Exception as exc:
        row.update(status='ERROR', error_type=type(exc).__name__, error=str(exc)[:500],
                   score={'utility': 0., 'exact': False, 'contradictions': ['inference_or_structure_failed']})
    finally:
        row['elapsed_s'] = time.monotonic() - started
        if progress:
            progress()
    return row


def source_bindings():
    paths = list((APP / 'v13').rglob('*.py')) + list((APP / 'specs').rglob('*.json'))
    paths += [Path(__file__), HERE / 'generate_fixtures.py', HERE / 'prepare_pilot.py',
              APP / 'tests/integration_step2_utility.py']
    return {str(p.relative_to(APP)): file_hash(p) for p in sorted(set(paths))}


def installed_bindings(installed):
    models = ModelManager(installed)
    artifacts = {}
    for role in (*G.ROLES, 'C3_LANGUAGE'):
        path = models.path_for(role).resolve()
        artifacts[role] = {'path': str(path), 'sha256': file_hash(path), 'size': path.stat().st_size,
                           'revision': models.revision(role)}
    runner = Path(os.environ.get('V13_LLAMA_SERVER', str(installed / 'bin/llama-server'))).resolve()
    return {'models': artifacts, 'runner': {'path': str(runner), 'sha256': file_hash(runner)},
            'runtime_libraries': runtime_library_hashes(runner),
            'models_manifest_sha256': file_hash(installed / 'config/models.json'),
            # Bind loader/backend settings without writing credentials or other
            # environment values into the published registration.
            'native_environment_sha256': {k: digest(v) for k, v in sorted(os.environ.items())
                if k.startswith(('V13_', 'LD_', 'GGML_', 'OMP_', 'OPENBLAS_', 'MKL_'))}}


def registration(installed, fixture_doc, fixture_ids=None, variants=None, row_seconds=90,
                 producer_tokens=256, consumer_tokens=256):
    """No inference. Register exact finite row coverage and immutable conditions."""
    if not 5 <= row_seconds <= 600 or not 32 <= producer_tokens <= 256 or not 16 <= consumer_tokens <= 1024:
        raise ValueError('Adapter bounds outside declared limits')
    full_doc = G.generate()
    if dumps(fixture_doc) == dumps(full_doc):
        scope = 'FULL_39_FIXTURE_NEW_PRIVATE_ADAPTER_BENCHMARK'
    elif dumps(fixture_doc) == dumps(P.select_pilot(full_doc)):
        scope = 'THREE_COMPLEMENTARY_CASE_DIAGNOSTIC_NOT_FULL_STEP2'
    else:
        raise ValueError('Adapter requires the saved fixed private fixture cohort or exact diagnostic pilot')
    all_ids = [f['id'] for f in fixture_doc['fixtures']]
    ids = all_ids if fixture_ids is None else list(fixture_ids)
    arms = list(VARIANTS) if variants is None else list(variants)
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(all_ids):
        raise ValueError('Unknown or duplicate fixture selection')
    if not arms or len(arms) != len(set(arms)) or not set(arms) <= set(VARIANTS):
        raise ValueError('Unknown or duplicate variant selection')
    return {'schema': VERSION + '_REGISTRATION', 'status': 'REGISTERED_NOT_RUN',
        'scope': scope,
        'fixtures_sha256': digest(dumps(fixture_doc)), 'source_bindings': source_bindings(),
        'installed_bindings': installed_bindings(Path(installed)), 'config': CONFIG,
        'device': device(),
        'fixture_ids': ids, 'variants': {name: VARIANTS[name] for name in arms},
        'variant_order': arms, 'row_order': [[fid, name] for fid in ids for name in arms],
        'row_seconds': row_seconds, 'producer_tokens': producer_tokens, 'consumer_tokens': consumer_tokens,
        'max_rows': len(ids) * len(arms),
        'max_native_calls': len(ids) * sum(len(VARIANTS[v]['roles']) + 1 for v in arms),
        'max_total_row_seconds': len(ids) * len(arms) * row_seconds,
        'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED', 'gate_promotion': False,
        'numeric_utility_gate': ('NO_UTILITY_PROMOTION_FOR_DIAGNOSTIC_PILOT' if scope.startswith('THREE_')
                                 else 'NOT_DEFINED_FOR_THIS_NEW_ADAPTER'),
        'unimplemented_controls': ['historical_CONTROL_channel', 'historical_SOURCE_EXACT_channel',
                                   'persisted_dual_timescale_state', 'prompt_only_retention_ablation'],
        'claim_limits': ['New fixture/quotation transport, not historical70 replication or native retained Offers.',
                         'Exact-source control is deterministic transport, never model-produced evidence.',
                         'Same-policy duplicates B1-private input only and delivers no B2-private source.',
                         'Software fake-runner scores are not native utility or phone measurements.']}


def prepare_home(home, installed):
    # Every row starts with a new DB. No persistent cross-variant source/history.
    home.mkdir(exist_ok=False, parents=True)
    initialize(home)
    save_config(home, CONFIG)
    for name in ('models', 'bin'):
        (home / name).rmdir()
        (home / name).symlink_to((installed / name).resolve(), target_is_directory=True)
    shutil.copyfile(installed / 'config/models.json', home / 'config/models.json')
    disable_background_sleep(home)
    return Runtime(home)


def disable_background_sleep(home):
    # Policy is installed before Runtime starts its real coordinator worker.
    # This adapter measures no autonomous sleep, replay or retained body state.
    store = Store(home)
    try:
        store.set_state(POLICY_KEY, default_policy() | {'enabled': False})
    finally:
        store.close()


def run_registered(installed, fixture_doc, prereg, out):
    current = registration(installed, fixture_doc, prereg['fixture_ids'], prereg['variant_order'],
                           prereg['row_seconds'], prereg['producer_tokens'], prereg['consumer_tokens'])
    if dumps(current) != dumps(prereg):
        raise ValueError('Registration binding changed; refusing inference')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    fixtures = {f['id']: f for f in fixture_doc['fixtures']}
    report = {'schema': VERSION + '_REPORT', 'status': 'RUNNING', 'registration_sha256': digest(dumps(prereg)),
              'rows': [], 'scope': prereg['scope'], 'gate_promotion': False,
              'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
              'evidence_level': 'NATIVE_RUNNER_BOUNDARY', 'device': device(),
              'phone_measured': device()['android']}
    atomic_write(out / 'registration.json', dumps(prereg))
    try:
        for fid in prereg['fixture_ids']:
            for variant in prereg['variant_order']:
                # Recheck source bindings before EVERY row; results are never
                # continued on changed code, settings, artifacts or model files.
                if source_bindings() != prereg['source_bindings'] or installed_bindings(Path(installed)) != prereg['installed_bindings']:
                    raise ValueError('Registered source or installed artifact changed during cohort')
                name = fid + '__' + variant
                runtime = prepare_home(out / 'homes' / name, Path(installed))
                try:
                    row = run_row(runtime, fixtures[fid], variant, prereg['row_seconds'],
                                  prereg['producer_tokens'], prereg['consumer_tokens'],
                                  record=lambda snapshot: atomic_write(out / (name + '.partial.json'), dumps(snapshot)))
                finally:
                    runtime.close()
                row['process_releases'] = list(runtime.pool.release_history)
                row['processes_reaped'] = bool(row['process_releases']) and all(
                    release.get('process_reaped') for release in row['process_releases'])
                if not row['processes_reaped']:
                    row['status'] = 'STRUCTURAL_FAIL'
                row['evidence_level'] = 'NATIVE_RUNNER_BOUNDARY'
                report['rows'].append(row)
                atomic_write(out / (name + '.json'), dumps(row))
                atomic_write(out / 'report.json', dumps(report))
        expected = {(f, v) for f in prereg['fixture_ids'] for v in prereg['variants']}
        actual = [(r['fixture'], r['variant']) for r in report['rows']]
        report['coverage_complete'] = len(actual) == len(set(actual)) and set(actual) == expected
        report['final_bindings_unchanged'] = (source_bindings() == prereg['source_bindings'] and
            installed_bindings(Path(installed)) == prereg['installed_bindings'])
        report['status'] = ('RECORDED' if report['coverage_complete'] and all(r['status'] == 'RECORDED'
                             for r in report['rows']) and report['final_bindings_unchanged'] else 'NOT_CONFIRMED')
    except BaseException as exc:
        report.update(status='INTERRUPTED', error_type=type(exc).__name__, error=str(exc)[:500])
        raise
    finally:
        report['row_sha256'] = {r['fixture'] + ':' + r['variant']: digest(dumps(r)) for r in report['rows']}
        atomic_write(out / 'report.json', dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register')
    reg.add_argument('--installed', type=Path, required=True)
    reg.add_argument('--fixtures', type=Path, default=HERE / 'generated/fixtures.json')
    reg.add_argument('--out', type=Path, required=True)
    reg.add_argument('--fixture-id', action='append')
    reg.add_argument('--variant', choices=list(VARIANTS), action='append')
    reg.add_argument('--row-seconds', type=int, default=90)
    reg.add_argument('--producer-tokens', type=int, default=256)
    reg.add_argument('--consumer-tokens', type=int, default=256)
    run = sub.add_parser('run')
    run.add_argument('--installed', type=Path, required=True)
    run.add_argument('--fixtures', type=Path, default=HERE / 'generated/fixtures.json')
    run.add_argument('--registration', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    fixtures = strict_json(args.fixtures.read_text())
    if args.command == 'register':
        if args.out.exists():
            raise FileExistsError('Registration already exists')
        result = registration(args.installed, fixtures, args.fixture_id, args.variant,
                              args.row_seconds, args.producer_tokens, args.consumer_tokens)
        atomic_write(args.out, dumps(result))
        print(dumps({'status': result['status'], 'registration_sha256': digest(dumps(result)),
                     'scope': result['scope'], 'max_rows': result['max_rows'],
                     'max_native_calls': result['max_native_calls']}))
    else:
        result = run_registered(args.installed, fixtures, strict_json(args.registration.read_text()), args.out)
        print(dumps({'status': result['status'], 'scope': result['scope'],
                     'rows': len(result['rows']), 'gate_promotion': False}))
        return 0 if result['status'] == 'RECORDED' else 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
