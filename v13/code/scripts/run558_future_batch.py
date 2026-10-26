#!/usr/bin/env python3
"""Run558: strict schedule-derived FUTURE_003..024 STEP2 batches.

Plan and tests are source-only. Native execute is an opt-in, separately
preregistered operation with installed original model/runner SHA preflight.
No registered Run491/500/504 fixture, stage or batch is modified here.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import run500_step2_stage_map as stages
import run502_step2_batch as serial
import run504_remaining980_schedule as schedule

ALLOWED = tuple(f'FUTURE_{i:03d}' for i in range(3, 25))
require = serial.require
digest = serial.digest
run_child = serial.run_child
append_progress = serial.append_progress


def load_exact(path, expected, reason):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), reason)
    require(json.loads(path.read_text(encoding='utf-8')) == expected, reason)


def plan(work, batch_id):
    require(batch_id in ALLOWED, 'FUTURE_003_TO_024_ONLY')
    work = Path(work)
    full = stages.registration()
    future = schedule.registration()
    load_exact(work / 'RUN500_STAGE_MAP.json', full, 'FROZEN_STAGE_MAP_REQUIRED')
    load_exact(work / 'RUN504_SCHEDULE.json', future, 'FROZEN_FUTURE_SCHEDULE_REQUIRED')
    require(future['full_stage_map_sha256'] == schedule.digest(full) and
            future['remaining_planned_rows'] == 980 and
            future['batch_count'] == 24, 'FUTURE_SCHEDULE_DRIFT')
    batch = future['batches'][int(batch_id[-3:]) - 1]
    require(batch['id'] == batch_id and batch['native_executed'] is False and
            len(batch['stage_ids']) in (1, 3), 'FUTURE_BATCH_DRIFT')
    selected = [stages.choose(full, sid) for sid in batch['stage_ids']]
    require([stage['fixture_ids'] for stage in selected] == batch['fixture_pairs'],
            'FROZEN_STAGE_PAIR_DRIFT')
    keys = [tuple(key) for stage in selected for key in stage['row_keys']]
    require(len(keys) == len(set(keys)) == batch['expected_rows'] and
            batch['row_keys_sha256'] == schedule.digest([list(key) for key in keys]),
            'FROZEN_BATCH_ROW_COVERAGE_DRIFT')
    prior_ids = [sid for prior in future['batches'][:2] for sid in prior['stage_ids']]
    prior_keys = {tuple(key) for sid in prior_ids
                  for key in stages.choose(full, sid)['row_keys']}
    require(not set(batch['stage_ids']).intersection(prior_ids) and
            not set(keys).intersection(prior_keys) and
            not set(batch['stage_ids']).intersection(future['reserved_stage_ids']),
            'FROZEN_PRIOR_BATCH_OVERLAP')
    return {
        'schema': 'V13_RUN558_FUTURE_BATCH_V1', 'status': 'SOURCE_ONLY_NO_NATIVE',
        'batch_id': batch_id, 'source_schedule_sha256': schedule.digest(future),
        'full_stage_map_sha256': schedule.digest(full),
        'stage_ids': list(batch['stage_ids']),
        'fixture_pairs': [list(pair) for pair in batch['fixture_pairs']],
        'arm_seed_pairs': [[s['arm'], s['seed']] for s in selected],
        'expected_rows': batch['expected_rows'],
        'row_keys_sha256': batch['row_keys_sha256'],
        'model_sha256_expected_not_retrieved': full['model_sha256_expected_not_retrieved'],
        'runner_sha256_expected_not_retrieved': full['runner_sha256_expected_not_retrieved'],
        'native_executed': False, 'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'redmi_measured': False,
    }


def execute(work, installed_home, batch_id):
    work = Path(work)
    frozen = plan(work, batch_id)
    load_exact(work / 'RUN558_BATCH_PLAN.json', frozen, 'RUN558_BATCH_PLAN_NOT_FROZEN')
    installed_home = Path(installed_home)
    require(installed_home.is_dir() and not installed_home.is_symlink(),
            'INSTALLED_HOME_REQUIRED')
    logs = work / 'run558-raw'
    progress = work / 'RUN558_BATCH_PROGRESS.jsonl'
    result_path = work / 'RUN558_BATCH_RESULT.json'
    preflight_path = work / 'RUN558_INSTALLED_PREFLIGHT.json'
    require(not any(p.exists() or p.is_symlink() for p in
                    (logs, progress, result_path, preflight_path)),
            'REFUSE_BATCH_RERUN_OR_PARTIAL')
    for stage_id in frozen['stage_ids']:
        path = work / ('stage_' + stage_id)
        require(not path.exists() and not path.is_symlink(),
                'REFUSE_EXISTING_STAGE_DIR')
    from run496_heldout10_native_pilot import verify_installed
    installed = verify_installed(installed_home)
    logs.mkdir(parents=True, exist_ok=False)
    stages.write_new(preflight_path, installed)
    receipts = []
    for stage_id in frozen['stage_ids']:
        append_progress(progress, {'stage_id': stage_id, 'state': 'STARTED',
                                   'time_ns': time.time_ns()})
        log_path = logs / (stage_id + '.log')
        command = [sys.executable, str(Path(stages.__file__).resolve()),
                   '--work', str(work), '--installed-home', str(installed_home),
                   '--stage-id', stage_id, '--execute']
        rc = run_child(command, log_path)
        receipt = work / ('stage_' + stage_id) / 'RUN500_STAGE_RESULT.json'
        if rc == 0:
            if not receipt.is_file() or receipt.is_symlink():
                rc = 99
            else:
                try:
                    data = json.loads(receipt.read_text(encoding='utf-8'))
                    require(data['status'] == 'STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY' and
                            data['stage_id'] == stage_id and
                            data['rows_verified'] == 14 and
                            data['native_execution_performed'] is True and
                            data['canonical_gate_pass'] is False and
                            data['step2_exit'] == 'UTILITY_FAIL' and
                            data['b3_l1'] == 'FAIL' and
                            data['body_jepa'] == 'UNAVAILABLE' and
                            data['jepa_weight'] == 0 and
                            data['redmi_measured'] is False,
                            'INVALID_STAGE_RECEIPT')
                except (ValueError, KeyError, TypeError):
                    rc = 98
        sha = digest(receipt.read_bytes()) if receipt.is_file() and not receipt.is_symlink() else None
        append_progress(progress, {'stage_id': stage_id, 'state': 'FINISHED',
                                   'rc': rc, 'receipt_sha256': sha,
                                   'time_ns': time.time_ns()})
        if rc != 0:
            raise RuntimeError(f'RUN558_STOPPED_AT_{stage_id}_RC_{rc}')
        receipts.append({'stage_id': stage_id, 'receipt_sha256': sha,
                         'rows_verified': 14})
    result = {
        'status': 'RUN558_BATCH_STRUCTURALLY_VERIFIED_ONLY',
        'batch_id': batch_id, 'stage_ids': list(frozen['stage_ids']),
        'stage_receipts': receipts, 'rows_verified': frozen['expected_rows'],
        'native_execution_performed': True, 'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'redmi_measured': False,
    }
    stages.write_new(result_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--batch', required=True, choices=ALLOWED)
    parser.add_argument('--installed-home', type=Path)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(args.plan != args.execute, 'EXACTLY_ONE_MODE_REQUIRED')
    if args.plan:
        require(args.installed_home is None, 'PLAN_FORBIDS_INSTALLED_HOME')
        value = plan(args.work, args.batch)
        stages.write_new(args.work / 'RUN558_BATCH_PLAN.json', value)
        print(json.dumps({'status': value['status'], 'batch_id': args.batch,
                          'rows': value['expected_rows'], 'native_executed': False},
                         sort_keys=True))
        return
    require(args.installed_home is not None, 'EXECUTION_NEEDS_INSTALLED_HOME')
    print(json.dumps(execute(args.work, args.installed_home, args.batch), sort_keys=True))


if __name__ == '__main__':
    main()