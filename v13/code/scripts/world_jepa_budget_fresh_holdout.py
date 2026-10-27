#!/usr/bin/env python3
"""Fresh independent Linux file-world holdouts for a frozen 200-step SHADOW World-JEPA.

No model training/calibration, no live tool authority, no runtime default change.
All original model/cohort/provenance and timing evidence is verified before any
new temporary file-world actions. The selected arm is post-selection exploratory.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile

from scripts import z12b_world_jepa as z12b
from scripts import world_jepa_shadow_lifecycle as lifecycle
from scripts.world_jepa_budget_ablation import (
    SCHEMA as BUDGET_SCHEMA, CHECKPOINT_SHA256 as ORIGINAL_CHECKPOINT_SHA256,
    TRAINING_SOURCE_SHA256, verify_budget_export, _provenance,
)
from scripts.world_jepa_holdout_utility import evaluate_rows
from v13.common import atomic_write
from v13.world_jepa_shadow_probe import _json_file
from v13.world_jepa_slots import SlotWorldJEPA

SCHEMA = 'V13_WORLD_JEPA_BUDGET_FRESH_HOLDOUT_V1'
SEEDS = (401, 402, 403)
ROWS = 160
STEPS = 200
SELECTED_CHECKPOINT_SHA256 = '7cb6158b3f39de2d9fa589906c5ed24ce92869709ce18fc09a70f3804e8b20c0'
BUDGET_ZIP_SHA256 = '8413b6abcdd2651c0e3346f348f0372b13dc4a407199e29a7e24cb9c1f23979a'
ORIGINAL_ZIP_SHA256 = 'f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8'
CLAIM_LIMIT = ('Fresh real Linux synthetic-content file-world after posthoc selection of '
               '200-step candidate; predictive latent MSE only, no causal/semantic '
               'utility, Redmi, native Body-JEPA or decision authority')


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, cap):
    return lifecycle._bounded_bytes(path, cap)


def _frozen(original_root, budget_root):
    """Verify frozen original + all four budget arms before new world actions."""
    original_root, budget_root = Path(original_root), Path(budget_root)
    verified = verify_budget_export(original_root, budget_root)
    if verified != {'verified': True, 'arms': [10, 50, 200, 800],
                    'rows': 480, 'authority': 0, 'redmi_measured': False}:
        raise ValueError('Frozen budget verification failed')
    report = _json_file(budget_root / 'report.json', 1024 * 1024)
    if (report.get('schema') != BUDGET_SCHEMA
            or report.get('training_seed') != 212
            or report.get('training_source_sha256') != TRAINING_SOURCE_SHA256
            or report.get('frozen_checkpoint_sha256') != ORIGINAL_CHECKPOINT_SHA256
            or report.get('budgets') != [10, 50, 200, 800]):
        raise ValueError('Wrong frozen budget lineage')
    arm = next((x for x in report['arms'] if x.get('steps') == STEPS), None)
    if arm is None or arm.get('checkpoint_sha256') != SELECTED_CHECKPOINT_SHA256:
        raise ValueError('Wrong frozen 200-step checkpoint')
    arm_dir = budget_root / ('steps-%04d' % STEPS)
    arm_meta = _json_file(arm_dir / 'arm.json', 1024 * 1024)
    checkpoint = arm_dir / 'slot-shadow-v2.npz'
    if (arm_meta.get('checkpoint_sha256') != SELECTED_CHECKPOINT_SHA256
            or _sha(_read(checkpoint, 32 * 1024 * 1024)) != SELECTED_CHECKPOINT_SHA256
            or arm_meta.get('provenance') != _provenance(
                {'cohort_sha256': report['training_cohort_sha256']}, STEPS)):
        raise ValueError('Selected checkpoint or provenance mismatch')
    model = SlotWorldJEPA.load(
        checkpoint, expected_provenance=arm_meta['provenance'],
        expected_sha256=SELECTED_CHECKPOINT_SHA256)
    if model.S != z12b.SLOTS or len(model.preds) != 2:
        raise ValueError('Selected model dimensions mismatch')
    return model, report


def _validate_metrics(recorded, replay):
    if type(recorded) is not dict or set(recorded) != set(replay):
        raise ValueError('New holdout metric keys mismatch')
    for key, value in replay.items():
        prior = recorded[key]
        if type(value) is float:
            if (type(prior) is not float or not math.isfinite(prior)
                    or not math.isclose(value, prior, rel_tol=0., abs_tol=1e-10)):
                raise ValueError('New holdout metric replay mismatch: ' + key)
        elif type(prior) is not type(value) or prior != value:
            raise ValueError('New holdout count/label mismatch: ' + key)


def _one(model, seed, output_dir):
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError('Never overwrite existing fresh holdout')
    with tempfile.TemporaryDirectory(prefix='v13-world-budget-fresh-') as td:
        work = Path(td)
        raw_rows = z12b.collect_train(work, seed, ROWS, held=set())
        log_raw = _read(work / ('world-%d.log' % seed),
                        lifecycle.MAX_TIMING_AUDIT_BYTES)
        schedule_raw = _read(work / ('world-%d.json' % seed),
                             lifecycle.MAX_TIMING_AUDIT_BYTES)
        intervals = lifecycle.validate_timing_rows(raw_rows, log_raw, schedule_raw, seed)
        rows = lifecycle._checked_rows(raw_rows)
        if len(rows) != ROWS or len(intervals) != ROWS:
            raise ValueError('Unexpected fresh world cohort size')
        metrics = evaluate_rows(model, rows, seed)
        cohort_raw = lifecycle._canonical(rows)
        intervals_raw = lifecycle._canonical(intervals)
        source = lifecycle.source_manifest()
        auditor_sha = _sha(Path(__file__).read_bytes())
        manifest = {
            'schema': SCHEMA, 'mode': 'SHADOW_ONLY', 'authority': 0,
            'collection': 'LINUX_TEMP_FILE_WORLD_PROCESS',
            'holdout_seed': seed, 'holdout_rows': ROWS,
            'training_performed': False, 'calibration_performed': False,
            'action_executed_by_model': False,
            'selected_after_prior_holdout_inspection': True,
            'budget_steps': STEPS, 'budget_zip_sha256': BUDGET_ZIP_SHA256,
            'original_zip_sha256': ORIGINAL_ZIP_SHA256,
            'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256,
            'training_source_sha256': TRAINING_SOURCE_SHA256,
            'source_sha256': source['sha256'], 'auditor_sha256': auditor_sha,
            'cohort_sha256': _sha(cohort_raw),
            'row_intervals_sha256': _sha(intervals_raw),
            'world_process_log_sha256': _sha(log_raw),
            'world_process_schedule_sha256': _sha(schedule_raw),
            'world_process_log_events': sum(bool(x.strip()) for x in log_raw.splitlines()),
            'metrics': metrics, 'redmi_measured': False,
            'native_body_training': False, 'runtime_authority': False,
            'step2': 'UTILITY_FAIL', 'b3': 'L1_FAIL',
            'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
            'canonical_architecture_complete': False,
            'user_full_scope_complete': False, 'claim_limit': CLAIM_LIMIT,
        }
        out.mkdir(parents=True, exist_ok=False)
        for name, raw in (
                ('cohort.json', cohort_raw), ('row_intervals.json', intervals_raw),
                ('world-%d.log' % seed, log_raw),
                ('world-%d.json' % seed, schedule_raw),
                ('manifest.json', _canonical(manifest) + b'\n')):
            atomic_write(out / name, raw)
    return manifest


def _verify_one(model, seed, out):
    out = Path(out)
    manifest = _json_file(out / 'manifest.json', 1024 * 1024)
    if (type(manifest) is not dict or manifest.get('schema') != SCHEMA
            or manifest.get('mode') != 'SHADOW_ONLY'
            or manifest.get('authority') != 0
            or manifest.get('collection') != 'LINUX_TEMP_FILE_WORLD_PROCESS'
            or manifest.get('holdout_seed') != seed or manifest.get('holdout_rows') != ROWS
            or manifest.get('training_performed') is not False
            or manifest.get('calibration_performed') is not False
            or manifest.get('action_executed_by_model') is not False
            or manifest.get('selected_after_prior_holdout_inspection') is not True
            or manifest.get('budget_steps') != STEPS
            or manifest.get('budget_zip_sha256') != BUDGET_ZIP_SHA256
            or manifest.get('original_zip_sha256') != ORIGINAL_ZIP_SHA256
            or manifest.get('checkpoint_sha256') != SELECTED_CHECKPOINT_SHA256
            or manifest.get('training_source_sha256') != TRAINING_SOURCE_SHA256
            or manifest.get('source_sha256') != lifecycle.source_manifest()['sha256']
            or manifest.get('auditor_sha256') != _sha(Path(__file__).read_bytes())
            or manifest.get('redmi_measured') is not False
            or manifest.get('native_body_training') is not False
            or manifest.get('runtime_authority') is not False
            or manifest.get('step2') != 'UTILITY_FAIL'
            or manifest.get('b3') != 'L1_FAIL'
            or manifest.get('body_jepa') != 'UNAVAILABLE'
            or type(manifest.get('jepa_weight')) is not int
            or manifest.get('jepa_weight') != 0
            or manifest.get('canonical_architecture_complete') is not False
            or manifest.get('user_full_scope_complete') is not False
            or manifest.get('claim_limit') != CLAIM_LIMIT):
        raise ValueError('Malformed/unauthorized fresh holdout manifest')
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
            raise ValueError('Fresh raw SHA mismatch: ' + name)
    rows = lifecycle._checked_rows(json.loads(raw['cohort.json']))
    intervals = json.loads(raw['row_intervals.json'])
    if len(rows) != ROWS or type(intervals) is not list or len(intervals) != ROWS:
        raise ValueError('Fresh rows/intervals count mismatch')
    joined = []
    for i, (row, receipt) in enumerate(zip(rows, intervals)):
        if (type(receipt) is not dict
                or set(receipt) != {'index', 'a', 'a0', 'a1', 'world', 'world_changed'}
                or type(receipt['index']) is not int or receipt['index'] != i
                or any(receipt[k] != row.get(k) for k in ('a', 'world', 'world_changed'))):
            raise ValueError('Fresh row/receipt binding mismatch')
        joined.append({**row, 'a0': receipt['a0'], 'a1': receipt['a1']})
    recomputed = lifecycle.validate_timing_rows(
        joined, raw['world-%d.log' % seed], raw['world-%d.json' % seed], seed)
    if recomputed != intervals:
        raise ValueError('Fresh world overlap timing mismatch')
    if sum(bool(x.strip()) for x in raw['world-%d.log' % seed].splitlines()) != manifest.get('world_process_log_events'):
        raise ValueError('Fresh world event count mismatch')
    metrics = evaluate_rows(model, rows, seed)
    _validate_metrics(manifest.get('metrics'), metrics)
    return {'seed': seed, 'rows': ROWS,
            'manifest_sha256': _sha(_read(out / 'manifest.json', 1024 * 1024)),
            'cohort_sha256': manifest['cohort_sha256'], 'metrics': metrics}


def _summary(per_seed):
    if [x['seed'] for x in per_seed] != list(SEEDS):
        raise ValueError('Fresh seed set mismatch')
    n = sum(x['rows'] for x in per_seed)
    def weighted(key):
        return sum(x['rows'] * x['metrics'][key] for x in per_seed) / n
    action, identity, rotated = (weighted(k) for k in (
        'action_prediction_mse', 'identity_target_mse', 'rotated_action_mse'))
    return {
        'schema': SCHEMA + '_SUMMARY', 'mode': 'SHADOW_ONLY',
        'authority': 0, 'training_performed': False,
        'selected_after_prior_holdout_inspection': True,
        'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256,
        'budget_steps': STEPS, 'budget_zip_sha256': BUDGET_ZIP_SHA256,
        'original_zip_sha256': ORIGINAL_ZIP_SHA256,
        'seeds': list(SEEDS), 'rows': n, 'per_seed': per_seed,
        'weighted_action_mse': action, 'weighted_identity_mse': identity,
        'weighted_rotated_mse': rotated,
        'weighted_action_over_identity': action / identity,
        'weighted_action_over_rotated': action / rotated,
        'beats_identity_seeds': sum(x['metrics']['action_prediction_mse'] <
                                    x['metrics']['identity_target_mse'] for x in per_seed),
        'beats_rotated_seeds': sum(x['metrics']['action_prediction_mse'] <
                                   x['metrics']['rotated_action_mse'] for x in per_seed),
        'exploratory_signal': all(x['metrics']['action_prediction_mse'] <
                                  min(x['metrics']['identity_target_mse'],
                                      x['metrics']['rotated_action_mse']) for x in per_seed),
        'uncertain_rows': sum(x['metrics']['uncertain_rows'] for x in per_seed),
        'redmi_measured': False, 'step2': 'UTILITY_FAIL',
        'b3': 'L1_FAIL', 'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'canonical_architecture_complete': False,
        'user_full_scope_complete': False, 'claim_limit': CLAIM_LIMIT,
    }


def run(original_root, budget_root, output_dir):
    original_root, budget_root, out = map(Path, (original_root, budget_root, output_dir))
    if (out.exists() or out.resolve().is_relative_to(original_root.resolve())
            or out.resolve().is_relative_to(budget_root.resolve())):
        raise FileExistsError('Fresh output must be new and outside frozen input')
    model, _ = _frozen(original_root, budget_root)
    out.mkdir(parents=True, exist_ok=False)
    per_seed = []
    for seed in SEEDS:
        _one(model, seed, out / ('seed-%d' % seed))
        per_seed.append(_verify_one(model, seed, out / ('seed-%d' % seed)))
        atomic_write(out / 'summary.partial.json', _canonical(_summary(per_seed))
                     if len(per_seed) == len(SEEDS) else _canonical({
                         'status': 'PARTIAL_NOT_A_PASS', 'seeds_finished': [x['seed'] for x in per_seed],
                         'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256}) + b'\n')
    result = _summary(per_seed)
    atomic_write(out / 'summary.json', _canonical(result) + b'\n')
    verify(original_root, budget_root, out)
    return result


def verify(original_root, budget_root, output_dir):
    model, _ = _frozen(original_root, budget_root)
    out = Path(output_dir)
    per_seed = [_verify_one(model, seed, out / ('seed-%d' % seed)) for seed in SEEDS]
    expected = _summary(per_seed)
    saved = _json_file(out / 'summary.json', 1024 * 1024)
    if saved != expected:
        raise ValueError('Fresh summary differs from persisted raw re-evaluation')
    return {'verified': True, 'seeds': list(SEEDS), 'rows': 480,
            'authority': 0, 'redmi_measured': False}


def main(argv=None):
    p = argparse.ArgumentParser(description='Frozen 200-step World-JEPA fresh Linux holdouts')
    p.add_argument('--original-root', required=True)
    p.add_argument('--budget-root', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--verify-only', action='store_true')
    args = p.parse_args(argv)
    result = (verify(args.original_root, args.budget_root, args.output_dir)
              if args.verify_only else run(args.original_root, args.budget_root, args.output_dir))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
