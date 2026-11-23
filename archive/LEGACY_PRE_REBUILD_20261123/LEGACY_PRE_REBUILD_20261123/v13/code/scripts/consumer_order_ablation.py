"""Preregistered follow-up: force computation-before-decision key order.

The consumer-model ablation's options_first arm was a no-op: ``v13.common.dumps``
sends the JSON schema with ``sort_keys=True``, so llama-server always receives
(and the grammar always emits) ``action`` before ``options``; raw answers of both
orders were byte-identical. Here keys are aliased so that alphabetical order
equals the intended reasoning order (project, options[entity, cost, days, local,
remaining, eligible], action). Answers are de-aliased deterministically before
the unchanged scorer runs. Recorded consumer messages are replayed unchanged
(their system text still names the unaliased fields; a documented confound).
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import consumer_model_ablation as consumer
from scripts.rule_transport_ablation import FIXTURES
from tests.integration_step2_utility import SCHEMA
from v13.common import atomic_write, digest, dumps, file_hash
from v13.utility import score_decision

TOP = {'project': 'a_project', 'options': 'b_options', 'action': 'c_action'}
OPTION = {'entity': 'a_entity', 'cost': 'b_cost', 'days': 'c_days', 'local': 'd_local', 'remaining': 'e_remaining', 'eligible': 'f_eligible'}
ARMS = tuple(m+'/forced_order' for m in consumer.MODELS)


def forced_schema():
    out = json.loads(dumps(SCHEMA)); item = out['properties']['options']['items']
    item['properties'] = {OPTION[k]: v for k, v in item['properties'].items()}
    item['required'] = [OPTION[k] for k in item['required']]
    out['properties'] = {TOP[k]: v for k, v in out['properties'].items()}
    out['required'] = [TOP[k] for k in out['required']]
    return out


def dealias(raw):
    """Exact inverse rename; anything else is left for the scorer to reject."""
    try: answer = json.loads(raw)
    except ValueError: return raw
    if not isinstance(answer, dict): return raw
    back = {v: k for k, v in TOP.items()}; option_back = {v: k for k, v in OPTION.items()}
    answer = {back.get(k, k): v for k, v in answer.items()}
    if isinstance(answer.get('options'), list):
        answer['options'] = [{option_back.get(k, k): v for k, v in o.items()} if isinstance(o, dict) else o for o in answer['options']]
    return dumps(answer)


def binding(installed):
    found = consumer.binding(installed); path = Path(__file__).resolve()
    found['source_sha256'][str(path.relative_to(consumer.ROOT))] = file_hash(path)
    return found


def preregistration(installed, report_path, previous_path):
    base = consumer.preregistration(installed, report_path)
    previous = json.loads(Path(previous_path).read_text())
    if previous.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('Consumer-model ablation is not a complete recorded diagnosis')
    base.update(schema='CONSUMER_ORDER_ABLATION_PREREGISTRATION_V1', arm_order=list(ARMS),
                schemas_sha256={'forced_order': digest(dumps(forced_schema()))},
                previous_consumer_ablation={'path': str(Path(previous_path).resolve()), 'sha256': file_hash(previous_path),
                                            'options_first_arm': 'INVALID_NO_OP_SORTED_SCHEMA_KEYS'},
                binding=binding(installed))
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', type=Path, required=True)
    parser.add_argument('--rule-transport-report', type=Path, required=True)
    parser.add_argument('--consumer-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    registration = preregistration(args.installed_home, args.rule_transport_report, args.consumer_report)
    path = args.out.with_suffix('.preregistration.json'); args.out.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(path, dumps(registration))
    registration_sha = file_hash(path)
    if args.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(path), 'sha256': registration_sha})); return
    _, inputs = consumer.recorded_inputs(args.rule_transport_report)
    out = {'schema': 'CONSUMER_ORDER_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
           'preregistration_sha256': registration_sha, 'canonical_gate_pass': False, 'phone_measured': False}
    if args.out.exists():
        out = json.loads(args.out.read_text())
        if out.get('preregistration_sha256') != registration_sha: raise ValueError('Resume preregistration changed')
        if out.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in out['rows']}: raise ValueError('Resume recorded row bytes changed')
    atomic_write(args.out, dumps(out))
    done = {(r['fixture'], r['arm']) for r in out['rows']}
    work = args.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    original_schema, original_arms = consumer.schema, consumer.ARMS
    consumer.schema = lambda order: forced_schema()
    by_id = {f['id']: f for f in FIXTURES}
    try:
        for arm in ARMS:
            if all((f['id'], arm) in done for f in FIXTURES): continue
            if binding(args.installed_home) != registration['binding']:
                out['status'] = 'ARTIFACT_CHANGED'; atomic_write(args.out, dumps(out)); raise ValueError('Binding changed during ablation')
            home = work/arm.replace('/', '-')
            if home.exists(): shutil.rmtree(home)
            for row in consumer.run_arm(home, args.installed_home, arm, inputs, done):
                row['dealiased_answer'] = dealias(row['raw_answer'])
                if row['status'] == 'RECORDED': row['score'] = score_decision(row['dealiased_answer'], by_id[row['fixture']]['oracle'])
                try: row['action'] = json.loads(row['dealiased_answer']).get('action')
                except (ValueError, AttributeError): row['action'] = None
                out['rows'].append(row); out['row_sha256'][row['fixture']+'/'+arm] = digest(dumps(row))
                consumer.ARMS = ARMS; out['summary'] = consumer.aggregate(out['rows']); consumer.ARMS = original_arms
                atomic_write(args.out, dumps(out))
                print(dumps({'fixture': row['fixture'], 'arm': arm, 'status': row['status'], 'action': row['action'],
                             'utility': row['score']['utility']}), flush=True)
                if row['status'] == 'INTERRUPTED':
                    out['status'] = 'INTERRUPTED'; atomic_write(args.out, dumps(out)); raise KeyboardInterrupt
    finally:
        consumer.schema, consumer.ARMS = original_schema, original_arms
    out['installed_artifacts_unchanged'] = binding(args.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    consumer.ARMS = ARMS; out['summary'] = consumer.aggregate(out['rows']); consumer.ARMS = original_arms
    atomic_write(args.out, dumps(out))


if __name__ == '__main__': main()
