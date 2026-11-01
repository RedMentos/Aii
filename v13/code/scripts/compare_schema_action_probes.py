#!/usr/bin/env python3
"""Compare two completed generic native probes without rerunning or retuning cases."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write, file_hash


def compare(baseline, candidate):
    paths = [Path(baseline), Path(candidate)]
    reports = [json.loads(p.read_text()) for p in paths]
    left, right = reports
    checks = {'both_complete': all(r['status'] == 'DIAGNOSTIC_COMPLETE' and len(r['rows']) == 32 for r in reports),
              'cases_and_oracles_identical': left['cases'] == right['cases'],
              'arms_identical': left['arms'] == right['arms'],
              'binding_identical_except_model': {k:v for k,v in left['binding'].items() if k != 'model_sha256'} == {k:v for k,v in right['binding'].items() if k != 'model_sha256'},
              'both_artifacts_unchanged': all(r.get('artifacts_unchanged') for r in reports),
              'both_servers_reaped': all(r.get('server_reaped') for r in reports)}
    matched = []
    for a, b in zip(left['rows'], right['rows']):
        wa = json.loads(a['completion_request_wire']); wb = json.loads(b['completion_request_wire'])
        matched.append(a['case'] == b['case'] and a['arm'] == b['arm']
                       and a['messages'] == b['messages'] and wa == wb
                       and a['status'] == b['status'] == 'RECORDED')
    checks['all_native_request_payloads_identical'] = len(matched) == 32 and all(matched)
    result = {'status': 'COMPARABLE' if all(checks.values()) else 'NOT_COMPARABLE',
              'checks': checks, 'canonical_gate_pass': False, 'phone_measured': False,
              'latency_comparison_valid': False, 'models': []}
    for path, report in zip(paths, reports):
        expected = {c['id']:c['expected'] for c in report['cases']}
        model = {'report': str(path), 'report_sha256': file_hash(path),
                 'model_sha256': report['binding']['model_sha256'], 'arms': {}}
        for arm in report['arms']:
            groups = {}
            for group in ('copy', 'decision'):
                rows = [x for x in report['rows'] if x['arm'] == arm and x['case'].startswith(group+'_')]
                fields = ['action'] if arm == 'action_only' else ['action', 'remaining', 'eligible']
                groups[group] = {'n':len(rows),
                    'all_requested_fields_exact':sum(x.get('score', {}).get('all_requested_fields_exact', False) for x in rows),
                    'field_exact': {field:sum(x.get('score',{}).get('parsed',{}).get(field) == expected[x['case']][field] for x in rows) for field in fields},
                    'errors': [{'case':x['case'], 'raw_answer':x.get('raw_answer'),
                                'expected':{f:expected[x['case']][f] for f in fields},
                                'parsed':x.get('score',{}).get('parsed')} for x in rows if not x.get('score',{}).get('all_requested_fields_exact')]}
            model['arms'][arm] = groups
        result['models'].append(model)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True);p.add_argument('--candidate', required=True);p.add_argument('--out', required=True)
    args = p.parse_args();result = compare(args.baseline, args.candidate)
    atomic_write(args.out, json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'status':result['status'], 'checks':result['checks']}))
    return 0 if result['status'] == 'COMPARABLE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
