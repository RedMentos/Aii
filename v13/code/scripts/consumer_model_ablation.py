"""Preregistered consumer ablation: does another/larger answer model stop choosing NONE?

The rule-transport ablation (docs/proofs/continuation-20261012/
rule-transport-ablation/BEFUND.md) delivered the complete hash-checked earlier
rules to C3 (wholesale_control) and C3 (LFM2.5-350M) still answered NONE in all
eight rows. This ablation replays exactly those recorded consumer messages
(byte-identical, digest-bound) to three answer models and two schema key
orders. Only the consumer changes; no producer is re-run.

The installed C3 role is served by another installed file through the
ModelManager router for the ablation only (no config change). A model swap in
production needs its own bound comparison; this is a diagnosis, not a choice.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import source_handoff_ablation as handoff
from scripts.rule_transport_ablation import FIXTURES
from tests.integration_step2_utility import SCHEMA, installed_links
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision

ROOT = Path(__file__).resolve().parents[1]
MODELS = ('C3_LANGUAGE', 'B2_GIST', 'B1_DETAIL')  # installed file serving the consumer: 350M, Qwen3.5-0.8B, LFM2.5-1.2B
ORDERS = ('action_first', 'options_first')
ARMS = tuple(m+'/'+o for m in MODELS for o in ORDERS)
CONFIG = handoff.CONFIG | {'observer_tokens': 256}
SOURCE_ARM = 'wholesale_control'


def schema(order):
    """Same constraints; only property/required order changes (grammar key order)."""
    if order == 'action_first': return SCHEMA
    out = json.loads(dumps(SCHEMA)); props = SCHEMA['properties']
    out['properties'] = {k: props[k] for k in ('project', 'options', 'action')}
    out['required'] = ['project', 'options', 'action']
    return out


def recorded_inputs(report_path):
    report = json.loads(Path(report_path).read_text())
    if report.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('Rule-transport ablation is not a complete recorded diagnosis')
    rows = {r['fixture']: r for r in report['rows'] if r['arm'] == SOURCE_ARM}
    if set(rows) != {f['id'] for f in FIXTURES}: raise ValueError('Wholesale consumer inputs incomplete')
    for fixture_id, row in rows.items():
        if report['row_sha256'][fixture_id+'/'+SOURCE_ARM] != digest(dumps(row)): raise ValueError('Recorded consumer row changed')
    return report, {k: rows[k]['consumer_messages'] for k in rows}


def binding(installed):
    found = handoff.binding(installed)
    for path in (Path(__file__).resolve(), ROOT/'scripts/rule_transport_ablation.py'):
        found['source_sha256'][str(path.relative_to(ROOT))] = file_hash(path)
    found['source_scope'] += '_PLUS_CONSUMER_ABLATION_HARNESS'
    return found


def preregistration(installed, report_path):
    report, inputs = recorded_inputs(report_path)
    return {'schema': 'CONSUMER_MODEL_ABLATION_PREREGISTRATION_V1',
            'source_report': {'path': str(Path(report_path).resolve()), 'sha256': file_hash(report_path),
                              'preregistration_sha256': report['preregistration_sha256'], 'arm': SOURCE_ARM},
            'consumer_messages_sha256': {k: digest(dumps(v)) for k, v in sorted(inputs.items())},
            'fixtures_sha256': digest(dumps(FIXTURES)), 'arm_order': list(ARMS),
            'schemas_sha256': {o: digest(dumps(schema(o))) for o in ORDERS}, 'config': CONFIG, 'consumer_sampling_seed': 13,
            'native_oracle_visibility': False, 'primary_metric': 'non-NONE decisions and exact decisions per arm; mean strict utility',
            'decision_rule': 'a consumer/schema arm counts as fixing the NONE failure only if it makes >=3/4 exact decisions on the four rows whose oracle action is A or B, and >=3/4 UNKNOWN on the four missing/corrupt rows',
            'scope': 'CONSUMER_DIAGNOSIS_ONLY_NOT_A_MODEL_CHOICE', 'canonical_gate_pass': False, 'binding': binding(installed)}


def run_arm(home, installed, arm, inputs, rows_done):
    model_role, order = arm.split('/')
    initialize(home); save_config(home, CONFIG); installed_links(home, installed)
    r = Runtime(home); out = []
    try:
        target = r.models.path_for(model_role)
        r.models.router = lambda role: target if role == 'C3_LANGUAGE' else None
        for fixture in FIXTURES:
            if (fixture['id'], arm) in rows_done: continue
            row = {'fixture': fixture['id'], 'arm': arm, 'control': fixture['control'], 'consumer_model_role': model_role,
                   'consumer_model_sha256': file_hash(target), 'schema_order': order, 'raw_answer': '', 'status': 'RUNNING',
                   'oracle_visible_to_native': False}
            started = time.monotonic()
            try:
                runner = r.pool.get('C3_LANGUAGE'); deadline = time.monotonic()+CONFIG['deadline_seconds']
                for chunk in runner.generate(inputs[fixture['id']], r.cancel_event, deadline, CONFIG['answer_tokens'], schema(order), seed=13):
                    row['raw_answer'] += chunk
                row['consumer_metrics'] = dict(runner.last_metrics)
                row['score'] = score_decision(row['raw_answer'], fixture['oracle'])
                row['status'] = 'RECORDED' if runner.last_metrics.get('status') == 'FINAL' else 'STRUCTURAL_FAIL'
            except (Exception, KeyboardInterrupt) as exc:
                row.update(status='INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR', error_type=type(exc).__name__,
                           error=str(exc)[:500], score={'utility': 0., 'exact': False, 'contradictions': ['inference_failed']})
            row['elapsed_s'] = time.monotonic()-started
            try: row['action'] = json.loads(row['raw_answer']).get('action')
            except (ValueError, AttributeError): row['action'] = None
            out.append(row)
            yield row
            if row['status'] == 'INTERRUPTED': return
    finally:
        r.close()


def aggregate(rows):
    result = {}
    by_id = {f['id']: f for f in FIXTURES}
    for arm in ARMS:
        items = [r for r in rows if r['arm'] == arm]
        decidable = [r for r in items if by_id[r['fixture']]['oracle']['action'] in ('A', 'B')]
        unknown = [r for r in items if by_id[r['fixture']]['oracle']['action'] == 'UNKNOWN']
        exact_decidable = sum(bool(r['score']['exact']) for r in decidable)
        unknown_ok = sum(r.get('action') == 'UNKNOWN' for r in unknown)
        result[arm] = {'rows': len(items), 'mean_strict_utility': sum(r['score']['utility'] for r in items)/len(items) if items else None,
                       'exact_decisions': sum(bool(r['score']['exact']) for r in items), 'actions': [r.get('action') for r in items],
                       'non_none_actions': sum(r.get('action') not in (None, 'NONE') for r in items),
                       'exact_on_decidable': exact_decidable, 'unknown_on_missing_or_corrupt': unknown_ok,
                       'passes_decision_rule': len(decidable) == 4 and len(unknown) == 4 and exact_decidable >= 3 and unknown_ok >= 3,
                       'structural_failures': sum(r['status'] != 'RECORDED' for r in items)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', type=Path, required=True)
    parser.add_argument('--rule-transport-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    registration = preregistration(args.installed_home, args.rule_transport_report)
    path = args.out.with_suffix('.preregistration.json'); args.out.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(path, dumps(registration))
    registration_sha = file_hash(path)
    if args.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(path), 'sha256': registration_sha})); return
    _, inputs = recorded_inputs(args.rule_transport_report)
    if args.out.exists():
        out = json.loads(args.out.read_text())
        if out.get('preregistration_sha256') != registration_sha: raise ValueError('Resume preregistration changed')
        if out.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in out['rows']}: raise ValueError('Resume recorded row bytes changed')
    else:
        out = {'schema': 'CONSUMER_MODEL_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
               'preregistration_sha256': registration_sha, 'canonical_gate_pass': False, 'phone_measured': False}
        atomic_write(args.out, dumps(out))
    done = {(r['fixture'], r['arm']) for r in out['rows']}
    work = args.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    for arm in ARMS:
        if all((f['id'], arm) in done for f in FIXTURES): continue
        if binding(args.installed_home) != registration['binding']:
            out['status'] = 'ARTIFACT_CHANGED'; atomic_write(args.out, dumps(out)); raise ValueError('Binding changed during ablation')
        home = work/arm.replace('/', '-')
        if home.exists(): shutil.rmtree(home)  # only an unfinished isolated scratch arm
        for row in run_arm(home, args.installed_home, arm, inputs, done):
            out['rows'].append(row); out['row_sha256'][row['fixture']+'/'+arm] = digest(dumps(row))
            out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))
            print(dumps({'fixture': row['fixture'], 'arm': arm, 'status': row['status'], 'action': row.get('action'),
                         'utility': row['score']['utility']}), flush=True)
            if row['status'] == 'INTERRUPTED':
                out['status'] = 'INTERRUPTED'; atomic_write(args.out, dumps(out)); raise KeyboardInterrupt
    out['installed_artifacts_unchanged'] = binding(args.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))


if __name__ == '__main__': main()
