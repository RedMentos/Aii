"""Run155: strict raw-log-to-report binding for Run151 paired native evidence.

Read-only independent review. Never modifies registered tasks, native artifacts,
model, frozen runtime, AGE0 delivery or original V13 gates.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

LOG = re.compile(r'RUN151_ROW (\d+) (CORRECT|MISMATCH|ABSTAIN) (CORRECT|MISMATCH|ABSTAIN) (CORRECT|MISMATCH|ABSTAIN) (None|-?\d+)')
GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def bind_rows(rows, log):
    """Reject missing, reordered, duplicated, corrupted or contradictory raw rows."""
    if not isinstance(rows, list) or len(rows) != 288:
        raise ValueError('report_rows')
    if not isinstance(log, str):
        raise ValueError('raw_log_type')
    raw = [line for line in log.splitlines() if line.startswith('RUN151_ROW ')]
    if len(raw) != 288:
        raise ValueError('raw_log_count')
    for idx, (row, line) in enumerate(zip(rows, raw)):
        m = LOG.fullmatch(line)
        if m is None:
            raise ValueError(f'raw_log_format:{idx}')
        if not isinstance(row, dict) or row.get('id') != idx:
            raise ValueError(f'report_row_order:{idx}')
        expected = (str(idx), row.get('new_check'), row.get('v3_check'),
                    row.get('old_check'), str(row.get('label')) if row.get('label') is not None else 'None')
        if m.groups() != expected:
            raise ValueError(f'raw_log_mismatch:{idx}')
    return {'rows_bound':288,'raw_log_order':'EXACT','raw_log_statuses':'EXACT'}


def audit(data, expected_sha):
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('artifact_sha256')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sorted(z.namelist()) != ['RUN151_C3_VARIED_NATIVE_REPORT.json','RUN151_VARIED_NATIVE_RAW.log']:
            raise ValueError('zip_members')
        report = json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'))
        log = z.read('RUN151_VARIED_NATIVE_RAW.log').decode('utf-8')
    if report.get('gates') != GATES or report.get('age0d_delivery') != 'OFF':
        raise ValueError('negative_gates')
    # Run154 performs registered task, model, runner, response and label checks.
    # Never accept an arbitrary self-hashed synthetic ZIP as native evidence.
    from scripts.age0d_run151_replication_compare_run154 import load
    verified = load(data, expected_sha)
    result = bind_rows(verified['rows'], log)
    return {'schema':'V13_RUN155_RUN151_RAWLOG_BINDING_REVIEW_V1',
            'artifact_sha256':expected_sha, 'evidence_class':'READ_ONLY_SOFTWARE_AUDIT_OF_LINUX_NATIVE_LOG',
            **result, 'overall_gate':'UNVERIFIED','gates':GATES,
            'limitations':['log binding is not a native rerun',
                           'raw log contains statuses, not raw model responses',
                           'original pinned ZIP hash and native provenance need independent verification',
                           'no Redmi, JEPA, learning or whole V13 claim']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=audit(a.artifact.read_bytes(),a.sha256)
    with a.output.open('x',encoding='utf-8') as f:
        f.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
        f.flush()
        import os
        os.fsync(f.fileno())
    print('RUN155_LOG_BINDING',result['rows_bound'],'PASS',result['overall_gate'])

if __name__=='__main__':main()
