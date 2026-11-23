"""Measure real durable C5 fixed-output turns. No neural latency claim."""
import argparse
import json
from pathlib import Path
import shlex
import statistics
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import APP, atomic_write, file_hash
from v13.operator import Operator
from v13.resources import device
from v13.runtime import Runtime


def run(out, turns=32):
    report = {'status': 'RUNNING', 'scope': 'REAL_DURABLE_FIXED_POLICY_NO_MODEL_CALLS',
              'device': device(), 'source_hashes': {str(p.relative_to(APP)): file_hash(p) for p in (APP / 'v13').glob('*.py')},
              'collector_sha256': file_hash(Path(__file__)), 'rows': [],
              'native_kv_warmth': 'UNAVAILABLE_NO_NATIVE_MODEL', 'redmi_proof': False}
    def save():
        atomic_write(Path(out), json.dumps(report, ensure_ascii=False, indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix='v13-fixed-latency-') as folder:
        home = Path(folder)
        r = Runtime(home)
        try:
            op = Operator(r)
            answer = 'Feste freigegebene Antwort. 🍎'
            rid = op.run(':rules fixed ' + shlex.quote('Latenz-Test?') + ' ' + shlex.quote(answer)).split(';')[0]
            op.run(':approve ' + rid)
            rule_version = r.store.generation()['rule_version']
            for i in range(turns):
                if i == turns // 2:
                    r.close()
                    r = Runtime(home)
                start = time.monotonic_ns()
                eid = r.submit('Latenz-Test?')
                until = time.monotonic() + 15
                while not r.idle() and time.monotonic() < until:
                    time.sleep(.001)
                row = r.last_answer()
                if not r.idle() or not row or row['event_id'] != eid:
                    raise RuntimeError('Actual coordinator turn did not finish')
                meta = json.loads(row['metadata'])
                refs = meta['context_source_refs']
                report['rows'].append({'index': i, 'event_id': eid, 'status': row['status'],
                    'answer_sha256': meta['self_candidate_hash'], 'exact_answer': row['text'] == answer,
                    'model_generated': meta['model_generated'], 'output_authority': meta['output_authority'],
                    'rule_version_matches': meta['output_policy']['rule_version'] == rule_version,
                    'source_lineage_valid': all(r.store.read_source(ref) is not None for ref in refs),
                    'runtime_duration_s': meta['duration_s'], 'submit_to_first_output_s': (meta['first_output_monotonic_ns'] - start) / 1e9,
                    'stage_marks_s': meta['stage_marks_s'], 'native_pressure': meta['native_pressure'],
                    'live_native_pids': r.pool.pids() + r.needle.pids(),
                    'restart_first_turn': i in (0, turns // 2)})
                save()
            report['integrity_errors'] = r.store.integrity(True)
            report['checks'] = {
                'all_actual_turns_final_exact': len(report['rows']) == turns and all(x['status'] == 'FINAL' and x['exact_answer'] for x in report['rows']),
                'operator_authority_no_model': all(not x['model_generated'] and x['output_authority'] == 'APPROVED_FIXED_RULE' for x in report['rows']),
                'restart_source_rule_binding': all(x['rule_version_matches'] and x['source_lineage_valid'] for x in report['rows']),
                'no_native_processes': all(not x['live_native_pids'] for x in report['rows']),
                'integrity': not report['integrity_errors'],
                'source_unchanged': report['source_hashes'] == {str(p.relative_to(APP)): file_hash(p) for p in (APP / 'v13').glob('*.py')},
            }
            values = sorted(x['runtime_duration_s'] for x in report['rows'])
            report['measured_runtime_seconds'] = {'median': statistics.median(values), 'p95': values[min(len(values) - 1, int(len(values) * .95))], 'max': max(values)}
            report['status'] = 'FIXED_POLICY_RUNTIME_PASS' if all(report['checks'].values()) else 'FIXED_POLICY_RUNTIME_FAIL'
        finally:
            r.close()
            save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--turns', type=int, default=32, choices=range(2, 129))
    args = parser.parse_args()
    result = run(args.out, args.turns)
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'measured_runtime_seconds')}))
    sys.exit(0 if result['status'] == 'FIXED_POLICY_RUNTIME_PASS' else 2)
