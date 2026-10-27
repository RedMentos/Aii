#!/usr/bin/env python3
"""Opt-in, post-checkpoint real Linux file-world utility audit for World-JEPA.

No fitting, calibration, model/tool actions, fact writes, or Age/approval changes.
All real file actions are confined to a new TemporaryDirectory; the output is
an explicit, immutable review artifact. This is not a semantic utility gate.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile

import numpy as np

from scripts import z12b_world_jepa as z12b
from scripts import world_jepa_shadow_lifecycle as lifecycle
from v13.common import atomic_write
from v13.world_jepa_shadow_probe import _json_file
from v13.world_jepa_slots import SlotWorldJEPA

SCHEMA = 'V13_WORLD_JEPA_FRESH_HOLDOUT_AUDIT_V1'
MAX_REPORT_BYTES = 1024 * 1024
MAX_ROWS = 20000
CLAIM_LIMIT = ('Fresh Linux synthetic-content file-world; exploratory latent MSE controls only, '
               'not semantic/causal utility, Redmi or decision authority')
AUDITOR_PATH = Path(__file__).resolve()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, cap):
    return lifecycle._bounded_bytes(path, cap)


def _training(training_dir, holdout_seed):
    """Verify existing real-world export BEFORE any new file-world action."""
    root = Path(training_dir)
    manifest = _json_file(root / 'manifest.json', MAX_REPORT_BYTES)
    if (type(manifest) is not dict
            or manifest.get('collection') != 'LINUX_TEMP_FILE_WORLD_PROCESS'
            or manifest.get('world_overlap_recomputed') is not True
            or type(manifest.get('seed')) is not int
            or manifest['seed'] == holdout_seed
            or manifest.get('source_sha256') != lifecycle.source_manifest()['sha256']):
        raise ValueError('Requires different-seed, current-source verified real-file-world training')
    lifecycle.verify_timing_export(root)
    provenance = _json_file(root / 'provenance.json', 8192)
    if provenance != {'cohort_sha256': manifest.get('cohort_sha256'),
                      'source_sha256': manifest.get('source_sha256')}:
        raise ValueError('Training checkpoint provenance differs from training manifest')
    model = SlotWorldJEPA.load(
        root / 'slot-shadow-v2.npz',
        expected_provenance=provenance,
        expected_sha256=manifest.get('checkpoint_sha256'))
    if (model.S != z12b.SLOTS or len(model.mu) != 10
            or len(model.op_counts) != len(z12b.OPS) + 1):
        raise ValueError('Checkpoint dimensions do not match the independent file world')
    return manifest, model


def evaluate_rows(model, rows, seed):
    """Frozen metrics on a separate cohort; never updates model/calibration.

    Action-rotated control retains the exact observed states and outcomes, but
    feeds a different row's action. Identity control is the target-encoder
    latent of the BEFORE state, avoiding a cross-encoder baseline penalty.
    """
    if type(seed) is not int or seed < 0:
        raise ValueError('Invalid evaluation seed')
    data = lifecycle._checked_rows(rows)
    X, A, X2 = lifecycle._arrays(data)
    if (model.S != z12b.SLOTS or len(model.mu) != 10
            or len(model.op_counts) != A.shape[2]):
        raise ValueError('Model and holdout dimensions disagree')
    rotated = np.roll(A, 1, axis=0)
    if not np.any(rotated != A):
        raise ValueError('Action-rotation control has no distinct actions')
    predicted, spread = model.predict(X, A)
    predicted_rotated, _ = model.predict(X, rotated)
    target = model.latent(X2, target=True)
    identity = model.latent(X, target=True)
    confidence, labels = model.confidence(X, A)
    scale = model.zsd.reshape(1, 1, -1)
    action_error = np.mean(((predicted - target) / scale) ** 2, axis=2)
    identity_error = np.mean(((identity - target) / scale) ** 2, axis=2)
    rotated_error = np.mean(((predicted_rotated - target) / scale) ** 2, axis=2)
    arrays = (action_error, identity_error, rotated_error, spread, confidence)
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError('Nonfinite heldout metrics; no utility claim')
    if (np.any(action_error < 0) or np.any(identity_error < 0)
            or np.any(rotated_error < 0)
            or np.any(confidence < 0) or np.any(confidence > 1)
            or np.any(spread < 0)):
        raise ValueError('Invalid heldout inference/calibration')
    if any(label not in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN') for label in labels):
        raise ValueError('Unknown SHADOW confidence label')
    a_row, i_row, r_row = (x.mean(axis=1) for x in
                           (action_error, identity_error, rotated_error))
    metrics = {
        'evaluated_rows': len(data),
        'evaluated_slots': len(data) * model.S,
        'world_overlapping_rows': sum(r['world'] for r in data),
        'world_changed_rows': sum(r['world_changed'] for r in data),
        'action_rotation_changed_rows': int(np.count_nonzero(np.any(rotated != A, axis=(1, 2)))),
        'action_prediction_mse': float(action_error.mean()),
        'identity_target_mse': float(identity_error.mean()),
        'rotated_action_mse': float(rotated_error.mean()),
        'fraction_beats_identity': float(np.mean(a_row < i_row)),
        'fraction_beats_rotated': float(np.mean(a_row < r_row)),
        'mean_confidence': float(confidence.mean()),
        'mean_slot_spread': float(spread.mean()),
        'uncertain_rows': sum(x == 'SIMULATION_UNCERTAIN' for x in labels),
    }
    if any(type(v) is float and not math.isfinite(v) for v in metrics.values()):
        raise ValueError('Nonfinite heldout summary')
    return metrics


def run_holdout(training_dir, output_dir, seed, rows):
    """Collect a new, non-training cohort and save closed, restartable evidence."""
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError('Refuse to overwrite an existing holdout audit')
    if (type(seed) is not int or seed < 0 or type(rows) is not int
            or not 120 <= rows <= MAX_ROWS):
        raise ValueError('Requires nonnegative seed and 120..20000 heldout rows')
    training, model = _training(training_dir, seed)
    with tempfile.TemporaryDirectory(prefix='v13-world-holdout-') as td:
        work = Path(td)
        raw_rows = z12b.collect_train(work, seed, rows, held=set())
        log_raw = _read(work / ('world-%d.log' % seed), lifecycle.MAX_TIMING_AUDIT_BYTES)
        schedule_raw = _read(work / ('world-%d.json' % seed), lifecycle.MAX_TIMING_AUDIT_BYTES)
        intervals = lifecycle.validate_timing_rows(raw_rows, log_raw, schedule_raw, seed)
        data = lifecycle._checked_rows(raw_rows)
        if len(data) != rows or len(intervals) != rows:
            raise ValueError('Independent world returned wrong heldout row count')
        metrics = evaluate_rows(model, data, seed)
        cohort_raw = lifecycle._canonical(data)
        interval_raw = lifecycle._canonical(intervals)
        source = lifecycle.source_manifest()
        manifest = {
            'schema': SCHEMA,
            'mode': 'SHADOW_ONLY',
            'authority': 0,
            'training_performed': False,
            'calibration_performed': False,
            'action_executed_by_model': False,
            'collection': 'LINUX_TEMP_FILE_WORLD_PROCESS',
            'training_seed': training['seed'],
            'holdout_seed': seed,
            'holdout_rows': rows,
            'training_cohort_sha256': training['cohort_sha256'],
            'checkpoint_sha256': training['checkpoint_sha256'],
            'source_sha256': source['sha256'],
            'auditor_sha256': _sha(AUDITOR_PATH.read_bytes()),
            'cohort_sha256': _sha(cohort_raw),
            'row_intervals_sha256': _sha(interval_raw),
            'world_process_log_sha256': _sha(log_raw),
            'world_process_schedule_sha256': _sha(schedule_raw),
            'world_process_log_events': sum(bool(line.strip()) for line in log_raw.splitlines()),
            'metrics': metrics,
            'redmi_measured': False,
            'native_body_training': False,
            'step2': 'UTILITY_FAIL',
            'b3': 'L1_FAIL',
            'body_jepa': 'UNAVAILABLE',
            'jepa_weight': 0,
            'canonical_architecture_complete': False,
            'user_full_scope_complete': False,
            'claim_limit': CLAIM_LIMIT,
        }
        out.mkdir(parents=True, exist_ok=False)
        for name, raw in (
                ('cohort.json', cohort_raw),
                ('row_intervals.json', interval_raw),
                ('world-%d.log' % seed, log_raw),
                ('world-%d.json' % seed, schedule_raw),
                ('manifest.json', lifecycle._canonical(manifest) + b'\n')):
            atomic_write(out / name, raw)
        verify_holdout_export(out, training_dir)
    return manifest


def verify_holdout_export(output_dir, training_dir):
    """Read-only restart verification, including recomputed heldout metrics."""
    out = Path(output_dir)
    manifest = _json_file(out / 'manifest.json', MAX_REPORT_BYTES)
    if (type(manifest) is not dict or manifest.get('schema') != SCHEMA
            or manifest.get('mode') != 'SHADOW_ONLY'
            or manifest.get('authority') != 0
            or manifest.get('training_performed') is not False
            or manifest.get('calibration_performed') is not False
            or manifest.get('action_executed_by_model') is not False
            or manifest.get('redmi_measured') is not False
            or manifest.get('native_body_training') is not False
            or manifest.get('canonical_architecture_complete') is not False
            or manifest.get('user_full_scope_complete') is not False
            or manifest.get('step2') != 'UTILITY_FAIL'
            or manifest.get('b3') != 'L1_FAIL'
            or manifest.get('body_jepa') != 'UNAVAILABLE'
            or type(manifest.get('jepa_weight')) is not int
            or manifest.get('jepa_weight') != 0
            or manifest.get('claim_limit') != CLAIM_LIMIT
            or manifest.get('collection') != 'LINUX_TEMP_FILE_WORLD_PROCESS'
            or type(manifest.get('holdout_seed')) is not int
            or type(manifest.get('holdout_rows')) is not int
            or not 120 <= manifest['holdout_rows'] <= MAX_ROWS):
        raise ValueError('Malformed or unauthorized holdout manifest')
    training, model = _training(training_dir, manifest['holdout_seed'])
    if (manifest.get('training_seed') != training['seed']
            or manifest.get('training_cohort_sha256') != training['cohort_sha256']
            or manifest.get('checkpoint_sha256') != training['checkpoint_sha256']
            or manifest.get('source_sha256') != lifecycle.source_manifest()['sha256']
            or manifest.get('auditor_sha256') != _sha(AUDITOR_PATH.read_bytes())):
        raise ValueError('Holdout source/checkpoint/provenance mismatch')
    seed = manifest['holdout_seed']
    names = {
        'cohort.json': ('cohort_sha256', lifecycle.MAX_COHORT_AUDIT_BYTES),
        'row_intervals.json': ('row_intervals_sha256', lifecycle.MAX_TIMING_AUDIT_BYTES),
        'world-%d.log' % seed: ('world_process_log_sha256', lifecycle.MAX_TIMING_AUDIT_BYTES),
        'world-%d.json' % seed: ('world_process_schedule_sha256', lifecycle.MAX_TIMING_AUDIT_BYTES),
    }
    raw = {}
    for name, (key, cap) in names.items():
        raw[name] = _read(out / name, cap)
        if _sha(raw[name]) != manifest.get(key):
            raise ValueError('Holdout raw SHA256 mismatch: ' + name)
    data = json.loads(raw['cohort.json'])
    intervals = json.loads(raw['row_intervals.json'])
    if (type(data) is not list or type(intervals) is not list
            or len(data) != manifest['holdout_rows'] or len(intervals) != len(data)):
        raise ValueError('Holdout row/interval count mismatch')
    joined = []
    for i, (row, receipt) in enumerate(zip(data, intervals)):
        if (type(row) is not dict or type(receipt) is not dict
                or set(receipt) != {'index', 'a', 'a0', 'a1', 'world', 'world_changed'}
                or type(receipt['index']) is not int or receipt['index'] != i
                or any(receipt[k] != row.get(k) for k in ('a', 'world', 'world_changed'))):
            raise ValueError('Holdout row/receipt identity mismatch')
        joined.append({**row, 'a0': receipt['a0'], 'a1': receipt['a1']})
    log_name, schedule_name = 'world-%d.log' % seed, 'world-%d.json' % seed
    recomputed = lifecycle.validate_timing_rows(
        joined, raw[log_name], raw[schedule_name], seed)
    if recomputed != intervals:
        raise ValueError('Holdout intervals differ from independent recomputation')
    if sum(bool(line.strip()) for line in raw[log_name].splitlines()) != manifest.get('world_process_log_events'):
        raise ValueError('Holdout independent process event count mismatch')
    metrics = evaluate_rows(model, data, seed)
    if metrics != manifest.get('metrics'):
        raise ValueError('Heldout utility metrics differ after restart')
    return {'verified': True, 'rows': len(data), 'metrics': metrics,
            'cohort_sha256': manifest['cohort_sha256']}


def main(argv=None):
    parser = argparse.ArgumentParser(description='V13 independent real-file-world SHADOW holdout')
    subs = parser.add_subparsers(dest='command', required=True)
    run = subs.add_parser('run', help='new sandbox actions + read-only checkpoint evaluation')
    run.add_argument('--training-export', required=True)
    run.add_argument('--output-dir', required=True)
    run.add_argument('--seed', type=int, required=True)
    run.add_argument('--rows', type=int, default=240)
    check = subs.add_parser('verify', help='read-only persisted restart verification')
    check.add_argument('--training-export', required=True)
    check.add_argument('--output-dir', required=True)
    args = parser.parse_args(argv)
    if args.command == 'run':
        result = run_holdout(args.training_export, args.output_dir, args.seed, args.rows)
    else:
        result = verify_holdout_export(args.output_dir, args.training_export)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
