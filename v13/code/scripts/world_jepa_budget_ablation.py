#!/usr/bin/env python3
"""Preregistered, isolated World-JEPA training-budget experiment on exact closed Linux rows.

Four from-scratch SHADOW models, never the frozen original checkpoint or runtime.
Heldouts are SHA/timing verified BEFORE fitting and never used for calibration.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from scripts import world_jepa_shadow_lifecycle as lifecycle
from scripts.world_jepa_ensemble_ablation import (
    CHECKPOINT_SHA256, TRAINING_MANIFEST_SHA256, TRAINING_SOURCE_SHA256, HOLDOUTS, _sha,
)
from scripts.world_jepa_holdout_utility import _training, evaluate_rows, verify_holdout_export
from v13.common import atomic_write
from v13.world_jepa_shadow_probe import _json_file
from v13.world_jepa_slots import SlotWorldJEPA

SCHEMA = 'V13_WORLD_JEPA_FIXED_BUDGET_ABLATION_V1'
BUDGETS = (10, 50, 200, 800)
TRAINING_SEED = 212
TRAINING_ROWS = 240
HOLDOUT_ROWS = 160
CLAIM_LIMIT = ('Preregistered isolated Linux synthetic-content file-world budget comparison; '
               'not causal/semantic utility, Redmi, native Body-JEPA or decision authority')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')



def _verify_original_holdout(path, train, expected_manifest_sha):
    """Require exact original integrity; permit only <=1e-10 float replay drift.

    The original verifier checks all raw SHA/timing/seed/source/auditor gates
    before its last exact-float equality check. Only that exact final mismatch
    is eligible for this pinned-manifest, independently recomputed fallback.
    """
    if _sha(path / 'manifest.json') != expected_manifest_sha:
        raise ValueError('Wrong frozen holdout manifest')
    try:
        return verify_holdout_export(path, train), 0.
    except ValueError as exc:
        if str(exc) != 'Heldout utility metrics differ after restart':
            raise
    manifest = _json_file(path / 'manifest.json', 1024 * 1024)
    seed = manifest['holdout_seed']
    _, frozen = _training(train, holdout_seed=seed)
    data = lifecycle._checked_rows(_json_file(
        path / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES))
    replay = evaluate_rows(frozen, data, seed)
    recorded = manifest['metrics']
    if type(recorded) is not dict or set(recorded) != set(replay):
        raise ValueError('Frozen metric keys changed')
    delta = 0.
    for key, value in replay.items():
        prior = recorded[key]
        if type(value) is float:
            if type(prior) is not float or not math.isfinite(prior):
                raise ValueError('Nonfinite or invalid frozen metric')
            delta = max(delta, abs(value - prior))
            if not math.isclose(value, prior, rel_tol=0., abs_tol=1e-10):
                raise ValueError('Frozen metric differs beyond replay tolerance')
        elif type(value) is not type(prior) or value != prior:
            raise ValueError('Frozen integer/count metric differs')
    return {'verified': True, 'rows': len(data), 'metrics': replay,
            'cohort_sha256': manifest['cohort_sha256']}, delta


def _original(root):
    """Validate ALL original immutable inputs before any fit or output creation."""
    root = Path(root)
    train = root / 'training'
    if _sha(train / 'manifest.json') != TRAINING_MANIFEST_SHA256:
        raise ValueError('Wrong frozen training manifest')
    manifest, frozen = _training(train, holdout_seed=313)
    if (manifest.get('seed') != TRAINING_SEED
            or manifest.get('steps') != 10
            or manifest.get('total_rows') != TRAINING_ROWS
            or manifest.get('checkpoint_sha256') != CHECKPOINT_SHA256
            or _sha(train / 'slot-shadow-v2.npz') != CHECKPOINT_SHA256
            or manifest.get('source_sha256') != TRAINING_SOURCE_SHA256
            or lifecycle.source_manifest()['sha256'] != TRAINING_SOURCE_SHA256):
        raise ValueError('Frozen training checkpoint/seed/source mismatch')
    raw = lifecycle._bounded_bytes(train / 'cohort.json',
                                   lifecycle.MAX_COHORT_AUDIT_BYTES)
    rows = lifecycle._checked_rows(json.loads(raw))
    if (len(rows) != TRAINING_ROWS
            or hashlib.sha256(_canonical(rows)).hexdigest() != manifest['cohort_sha256']):
        raise ValueError('Frozen training cohort mismatch')
    split = len(rows) - max(20, len(rows) // 5)
    training, calibration = rows[:split], [r for r in rows[split:] if not r['world']]
    if (split != 192 or len(calibration) != manifest['calibration_rows']
            or len(calibration) < 12 or manifest['train_rows'] != split):
        raise ValueError('Frozen chronological training/calibration split mismatch')
    X, A, X2 = lifecycle._arrays(training)
    Xv, Av, X2v = lifecycle._arrays(calibration)
    if any(np.any(np.bincount(a.argmax(axis=2).ravel(), minlength=6) == 0)
           for a in (A, Av)):
        raise ValueError('Original training or calibration lacks operation coverage')
    heldouts = []
    replay_deltas = {}
    for folder, seed, expected in HOLDOUTS:
        path = root / folder
        if _sha(path / 'manifest.json') != expected:
            raise ValueError('Wrong frozen holdout manifest: ' + folder)
        verified, replay_delta = _verify_original_holdout(path, train, expected)
        replay_deltas[str(seed)] = replay_delta
        man = _json_file(path / 'manifest.json', 1024 * 1024)
        if (man.get('holdout_seed') != seed or verified['rows'] != HOLDOUT_ROWS
                or man.get('checkpoint_sha256') != CHECKPOINT_SHA256):
            raise ValueError('Frozen holdout identity mismatch')
        cohort = lifecycle._checked_rows(_json_file(
            path / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES))
        if len(cohort) != HOLDOUT_ROWS:
            raise ValueError('Frozen holdout cohort length mismatch')
        heldouts.append((seed, expected, verified['cohort_sha256'], cohort))
    return manifest, frozen, (X, A, X2), (Xv, Av, X2v), heldouts, replay_deltas


def _metrics(model, heldouts):
    per_seed = []
    for seed, manifest_sha, cohort_sha, rows in heldouts:
        m = evaluate_rows(model, rows, seed)
        action = m['action_prediction_mse']
        identity = m['identity_target_mse']
        rotated = m['rotated_action_mse']
        if identity <= 0 or rotated <= 0:
            raise ValueError('Zero baseline invalidates preregistered ratios')
        per_seed.append({
            'seed': seed, 'rows': len(rows), 'manifest_sha256': manifest_sha,
            'cohort_sha256': cohort_sha, **m,
            'action_over_identity': action / identity,
            'action_over_rotated': action / rotated,
        })
    n = sum(x['rows'] for x in per_seed)
    def weighted(key):
        return sum(x['rows'] * x[key] for x in per_seed) / n
    summary = {
        'rows': n, 'seeds': [x['seed'] for x in per_seed], 'per_seed': per_seed,
        'weighted_action_mse': weighted('action_prediction_mse'),
        'weighted_identity_mse': weighted('identity_target_mse'),
        'weighted_rotated_mse': weighted('rotated_action_mse'),
        'weighted_action_over_identity': weighted('action_prediction_mse') / weighted('identity_target_mse'),
        'weighted_action_over_rotated': weighted('action_prediction_mse') / weighted('rotated_action_mse'),
        'beats_identity_seeds': sum(x['action_over_identity'] < 1 for x in per_seed),
        'beats_rotated_seeds': sum(x['action_over_rotated'] < 1 for x in per_seed),
        'exploratory_signal': all(x['action_over_identity'] < 1 and x['action_over_rotated'] < 1
                                  for x in per_seed),
        'total_uncertain_rows': sum(x['uncertain_rows'] for x in per_seed),
    }
    if n != 480 or any(not math.isfinite(v) for x in per_seed
                       for v in x.values() if type(v) is float):
        raise ValueError('Invalid frozen heldout score')
    return summary


def _provenance(manifest, steps):
    return {'cohort_sha256': manifest['cohort_sha256'],
            'source_sha256': TRAINING_SOURCE_SHA256,
            'budget_steps': str(steps),
            'frozen_checkpoint_sha256': CHECKPOINT_SHA256,
            'experiment_revision': SCHEMA}


def ablate(root, output_dir):
    """Run fixed arms in order, persist each checkpoint, independently restart verify."""
    root, out = Path(root), Path(output_dir)
    if out.exists() or out.resolve().is_relative_to(root.resolve()):
        raise FileExistsError('New output must be outside frozen input and not already exist')
    manifest, frozen, train, val, heldouts, replay_deltas = _original(root)
    # Original frozen checkpoint is a reference only, never refitted.
    frozen_metrics = _metrics(frozen, heldouts)
    out.mkdir(parents=True, exist_ok=False)
    report = {
        'schema': SCHEMA, 'mode': 'SHADOW_ONLY', 'authority': 0,
        'training_performed': True, 'original_checkpoint_modified': False,
        'training_seed': TRAINING_SEED, 'training_rows': manifest['train_rows'],
        'calibration_rows': manifest['calibration_rows'],
        'training_cohort_sha256': manifest['cohort_sha256'],
        'training_manifest_sha256': TRAINING_MANIFEST_SHA256,
        'training_source_sha256': TRAINING_SOURCE_SHA256,
        'frozen_checkpoint_sha256': CHECKPOINT_SHA256,
        'heldout_manifest_sha256': {str(s): m for s, m, _, _ in heldouts},
        'frozen_reference': frozen_metrics, 'budgets': list(BUDGETS),
        'original_numeric_replay_delta_by_seed': replay_deltas,
        'arms': [], 'redmi_measured': False, 'native_body_training': False,
        'runtime_authority': False, 'step2': 'UTILITY_FAIL', 'b3': 'L1_FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'canonical_architecture_complete': False, 'user_full_scope_complete': False,
        'claim_limit': CLAIM_LIMIT,
    }
    for steps in BUDGETS:
        model = SlotWorldJEPA(6, seed=TRAINING_SEED, ensemble=2).fit(
            *train, steps=steps, log_every=max(1, steps // 4))
        model.calibrate(*val)
        arm_dir = out / ('steps-%04d' % steps)
        arm_dir.mkdir(exist_ok=False)
        provenance = _provenance(manifest, steps)
        checkpoint = arm_dir / 'slot-shadow-v2.npz'
        saved = model.save(checkpoint, provenance=provenance)
        # Verify persistence and evaluate only the restarted, SHA-bound weights.
        loaded = SlotWorldJEPA.load(checkpoint, expected_provenance=provenance,
                                    expected_sha256=saved['sha256'])
        scores = _metrics(loaded, heldouts)
        arm = {'steps': steps, 'checkpoint_sha256': saved['sha256'],
               'checkpoint_bytes': saved['bytes'], 'provenance': provenance,
               'metrics': scores, 'training_history': model.history,
               'calibration_complete': True, 'authority': 0}
        atomic_write(arm_dir / 'arm.json', _canonical(arm) + b'\n')
        report['arms'].append({'steps': steps,
                              'checkpoint_sha256': saved['sha256'],
                              'arm_json_sha256': _sha(arm_dir / 'arm.json'),
                              'metrics': scores})
        # A partial failure remains a visible, non-successful artifact.
        atomic_write(out / 'report.partial.json', _canonical(report) + b'\n')
    atomic_write(out / 'report.json', _canonical(report) + b'\n')
    verify_budget_export(root, out)
    return report


def verify_budget_export(root, output_dir):
    """Read-only verification of all four saved arms against exact original rows."""
    root, out = Path(root), Path(output_dir)
    manifest, frozen, _, _, heldouts, replay_deltas = _original(root)
    report = _json_file(out / 'report.json', 1024 * 1024)
    if (type(report) is not dict or report.get('schema') != SCHEMA
            or report.get('mode') != 'SHADOW_ONLY' or report.get('authority') != 0
            or report.get('training_performed') is not True
            or report.get('original_checkpoint_modified') is not False
            or report.get('training_seed') != TRAINING_SEED
            or report.get('training_rows') != manifest['train_rows']
            or report.get('calibration_rows') != manifest['calibration_rows']
            or report.get('training_cohort_sha256') != manifest['cohort_sha256']
            or report.get('training_manifest_sha256') != TRAINING_MANIFEST_SHA256
            or report.get('training_source_sha256') != TRAINING_SOURCE_SHA256
            or report.get('frozen_checkpoint_sha256') != CHECKPOINT_SHA256
            or report.get('heldout_manifest_sha256') != {str(s): m for s, m, _, _ in heldouts}
            or report.get('original_numeric_replay_delta_by_seed') != replay_deltas
            or report.get('frozen_reference') != _metrics(frozen, heldouts)
            or report.get('budgets') != list(BUDGETS)
            or type(report.get('arms')) is not list or len(report['arms']) != len(BUDGETS)
            or report.get('redmi_measured') is not False
            or report.get('native_body_training') is not False
            or report.get('runtime_authority') is not False
            or report.get('step2') != 'UTILITY_FAIL' or report.get('b3') != 'L1_FAIL'
            or report.get('body_jepa') != 'UNAVAILABLE'
            or type(report.get('jepa_weight')) is not int or report['jepa_weight'] != 0
            or report.get('canonical_architecture_complete') is not False
            or report.get('user_full_scope_complete') is not False
            or report.get('claim_limit') != CLAIM_LIMIT):
        raise ValueError('Budget report identity or negative-gate mismatch')
    for steps, entry in zip(BUDGETS, report['arms']):
        arm_dir = out / ('steps-%04d' % steps)
        arm = _json_file(arm_dir / 'arm.json', 1024 * 1024)
        if (entry.get('steps') != steps or arm.get('steps') != steps
                or entry.get('arm_json_sha256') != _sha(arm_dir / 'arm.json')
                or entry.get('checkpoint_sha256') != arm.get('checkpoint_sha256')
                or arm.get('provenance') != _provenance(manifest, steps)
                or arm.get('calibration_complete') is not True
                or arm.get('authority') != 0):
            raise ValueError('Budget arm identity or provenance mismatch')
        checkpoint = arm_dir / 'slot-shadow-v2.npz'
        if _sha(checkpoint) != arm['checkpoint_sha256']:
            raise ValueError('Budget arm checkpoint digest mismatch')
        model = SlotWorldJEPA.load(checkpoint,
                                   expected_provenance=arm['provenance'],
                                   expected_sha256=arm['checkpoint_sha256'])
        if _metrics(model, heldouts) != arm.get('metrics') or entry.get('metrics') != arm['metrics']:
            raise ValueError('Budget arm metrics differ after restart')
    return {'verified': True, 'arms': list(BUDGETS), 'rows': 480,
            'authority': 0, 'redmi_measured': False}


def main(argv=None):
    p = argparse.ArgumentParser(description='Frozen Linux World-JEPA training-budget ablation')
    p.add_argument('--frozen-root', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--verify-only', action='store_true')
    args = p.parse_args(argv)
    result = (verify_budget_export(args.frozen_root, args.output_dir) if args.verify_only
              else ablate(args.frozen_root, args.output_dir))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
