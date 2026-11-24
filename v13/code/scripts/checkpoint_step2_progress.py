#!/usr/bin/env python3
"""Checkpoint the existing STEP2 cohort at complete fixture boundaries.

Development helper, not a model capability or a proof gate. The optional
writeback uses the explicitly supplied current upload helper and versioned
plan. Any uncertain or failed write stops the loop; it is never retried blindly.
"""
import argparse
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13.common import atomic_write, file_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--zip', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--initial-rows', type=int, required=True)
    parser.add_argument('--upload-helper')
    parser.add_argument('--upload-plan')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if bool(args.upload_helper) != bool(args.upload_plan):
        parser.error('Upload helper and versioned plan required together')
    receipt = Path(args.receipt).resolve()
    report_path = Path(args.report).resolve()
    if not report_path.is_relative_to(APP):
        parser.error('Proof report must be in the captured source tree')
    zip_path = Path(args.zip).resolve()
    if zip_path.is_relative_to(APP) or receipt.is_relative_to(APP):
        parser.error('Archive and private receipt must be outside source tree')
    plan = json.loads(Path(args.upload_plan).read_text()) if args.upload_plan else None
    if plan:
        expected_paths = {str(zip_path), str(APP / 'BUILD_STATE.json')}
        if {item['local_path'] for item in plan['uploads']} != expected_paths:
            parser.error('Plan must update exactly this source archive and BUILD_STATE')
        if any(item.get('purpose') != 'replace_library_file' or type(item.get('expected_current_version')) is not int for item in plan['uploads']):
            parser.error('Exact existing identities and integer version guards required')
    last = args.initial_rows
    last_status = 'RUNNING'
    if receipt.exists():
        prior = json.loads(receipt.read_text())
        if prior.get('status') != 'SAVED':
            parser.error('Previous write outcome uncertain; inspect before another write')
        last = prior['rows']
        last_status = prior.get('proof_status', 'RUNNING')
        if plan:plan = prior['next_upload_plan']
    while True:
        report = json.loads(report_path.read_text())
        rows = len(report['rows'])
        if report.get('proof_version') != 3 or not args.initial_rows <= rows <= 70:
            raise ValueError('Unexpected STEP2 cohort or row count')
        changed = [name for name, digest in report['source_hashes'].items() if file_hash(APP / name) != digest]
        if changed:
            raise ValueError('Frozen source changed: ' + ', '.join(changed))
        finished = report['status'] not in {'RUNNING', 'DIAGNOSTIC_INCOMPLETE'}
        boundary = rows // 7 > last // 7
        if (rows > last and boundary) or (finished and (rows > last or report['status'] != last_status)):
            state_path = APP / 'BUILD_STATE.json'
            state = json.loads(state_path.read_text())
            state['checkpoint_time_utc'] = datetime.now(timezone.utc).isoformat()
            state['active_test_sessions']['step2_closed_native'].update(
                status=report['status'], recorded_rows=rows, complete_denominator=70,
                report_sha256=file_hash(report_path), source_frozen=True)
            state['checkpoint_kind'] = 'AUTOMATIC_STEP2_PROGRESS_CHECKPOINT'
            for path in (state_path, APP / 'docs/BUILD_STATE.json'):
                atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False) + '\n')
            output = subprocess.check_output([sys.executable, str(APP / 'scripts/package_source.py'), '--out', str(zip_path)], text=True)
            packed = json.loads(output)
            with zipfile.ZipFile(zip_path) as archive:
                frozen_bytes = archive.read('V13-Phone/' + report_path.relative_to(APP).as_posix())
            captured = json.loads(frozen_bytes)
            record = {'status': 'LOCAL_CAPTURED', 'rows': len(captured['rows']), 'proof_status': captured['status'], 'complete_denominator': 70,
                      'report_sha256': hashlib.sha256(frozen_bytes).hexdigest(), 'archive': packed,
                      'canonical_architecture_complete': False}
            if plan:
                record['status'] = 'WRITE_OUTCOME_UNCERTAIN'
                atomic_write(receipt, json.dumps(record, indent=2) + '\n')
                result = subprocess.run([sys.executable, args.upload_helper], input=json.dumps(plan), text=True, capture_output=True)
                raw = receipt.with_suffix('.writeback.json')
                atomic_write(raw, result.stdout)
                if result.returncode:
                    raise RuntimeError('Writeback failed or uncertain; inspect private receipt')
                saved = json.loads(result.stdout)['results']
                if len(saved) != len(plan['uploads']) or any(item.get('status') != 'succeeded' or item.get('local_metadata_applied') is not True for item in saved):
                    raise RuntimeError('Partial/uncertain writeback; no automatic retry')
                for item, result_item in zip(plan['uploads'], saved):
                    if result_item.get('library_file_id') != item['library_file_id']:
                        raise RuntimeError('Writeback identity mismatch')
                    item['expected_current_version'] = result_item['current_version_number']
                record['next_upload_plan'] = plan
            record['status'] = 'SAVED'
            atomic_write(receipt, json.dumps(record, indent=2) + '\n')
            last = record['rows']
            last_status = record['proof_status']
            print(json.dumps({'status': 'CHECKPOINT_SAVED', 'rows': last, 'archive_sha256': packed['sha256']}), flush=True)
        if finished or args.once:
            return 0
        time.sleep(30)


if __name__ == '__main__':
    raise SystemExit(main())
