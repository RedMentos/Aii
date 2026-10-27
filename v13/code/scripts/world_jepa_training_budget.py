#!/usr/bin/env python3
"""Fixed 10/50/200/800-step World-JEPA training-budget ablation on frozen data.

Training happens only in isolated SHADOW candidate objects, never in runtime
models. All original training/heldout bytes are read-only and SHA pinned.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import numpy as np

from scripts import world_jepa_shadow_lifecycle as lifecycle
from scripts.world_jepa_holdout_utility import _training, evaluate_rows, verify_holdout_export
from scripts.world_jepa_ensemble_ablation import (
    CHECKPOINT_SHA256, TRAINING_MANIFEST_SHA256, TRAINING_SOURCE_SHA256, HOLDOUTS, _sha)
from v13.common import atomic_write
from v13.world_jepa_shadow_probe import _json_file
from v13.world_jepa_slots import SlotWorldJEPA

SCHEMA = 'V13_WORLD_JEPA_FROZEN_TRAINING_BUDGET_V1'
STEPS = (10, 50, 200, 800)
CLAIM_LIMIT = ('Fixed exploratory SHADOW training on one already-observed Linux synthetic '
               'file-world cohort; no blinded utility gate, Redmi or runtime authority')


def _frozen(root):
    root = Path(root)
    train = root / 'training'
    if _sha(train / 'manifest.json') != TRAINING_MANIFEST_SHA256:
        raise ValueError('Not the exact frozen training manifest')
    manifest, original = _training(train, holdout_seed=313)
    if (manifest.get('checkpoint_sha256') != CHECKPOINT_SHA256
            or manifest.get('source_sha256') != TRAINING_SOURCE_SHA256
            or _sha(train / 'slot-shadow-v2.npz') != CHECKPOINT_SHA256):
        raise ValueError('Original frozen training checkpoint/source mismatch')
    data = _json_file(train / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES)
    if (lifecycle._digest(lifecycle._checked_rows(data)) != manifest['cohort_sha256']
            or len(data) != 240):
        raise ValueError('Frozen training cohort mismatch')
    split = len(data) - max(20, len(data) // 5)
    fit_rows = data[:split]
    calibration_rows = [r for r in data[split:] if not r['world']]
    if (len(fit_rows) != 192 or len(calibration_rows) != manifest['calibration_rows']
            or len(calibration_rows) != 48):
        raise ValueError('Frozen train/calibration split changed')
    heldouts = {}
    for folder, seed, pinned_manifest in HOLDOUTS:
        out = root / folder
        if _sha(out / 'manifest.json') != pinned_manifest:
            raise ValueError('Frozen heldout manifest changed')
        verified = verify_holdout_export(out, train)
        if verified['rows'] != 160:
            raise ValueError('Frozen heldout row count changed')
        heldouts[seed] = _json_file(out / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES)
    return manifest, original, fit_rows, calibration_rows, heldouts


def _weights_max_difference(a, b):
    differences = []
    for name in ('mu', 'sd', 'zsd', 'op_counts', 'op_err', '_ztrain'):
        x, y = getattr(a, name), getattr(b, name)
        if np.shape(x) != np.shape(y):
            raise ValueError('Reproduction shape differs: ' + name)
        differences.append(float(np.max(np.abs(x - y))))
    differences.append(abs(float(a._nn_med) - float(b._nn_med)))
    for name in ('enc', 'tgt'):
        for key in getattr(a, name):
            differences.append(float(np.max(np.abs(getattr(a, name)[key] - getattr(b, name)[key]))))
    if len(a.preds) != len(b.preds):
        raise ValueError('Reproduction ensemble count differs')
    for i in range(len(a.preds)):
        for key in a.preds[i]:
            differences.append(float(np.max(np.abs(a.preds[i][key] - b.preds[i][key]))))
    return max(differences)


def _candidate_provenance(manifest, steps):
    return {'cohort_sha256': manifest['cohort_sha256'],
            'source_sha256': manifest['source_sha256'],
            'ablation': 'fixed-training-budget-20261027',
            'training_steps': str(steps)}


def _metrics(model, heldouts):
    return {str(seed): evaluate_rows(model, rows, seed) for seed, rows in heldouts.items()}


def run_budget(frozen_root, output_dir):
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError('Refuse to overwrite candidate training evidence')
    training, original, fit_rows, calibration_rows, heldouts = _frozen(frozen_root)
    X, A, X2 = lifecycle._arrays(fit_rows)
    Xv, Av, X2v = lifecycle._arrays(calibration_rows)
    out.mkdir(parents=True, exist_ok=False)
    arms = []
    for steps in STEPS:
        t0 = time.perf_counter()
        try:
            model = SlotWorldJEPA(6, seed=212, ensemble=2).fit(
                X, A, X2, steps=steps, log_every=max(1, steps // 4))
            model.calibrate(Xv, Av, X2v)
            reproduction_difference = (_weights_max_difference(original, model)
                                       if steps == 10 else None)
            if steps == 10 and reproduction_difference > 1e-10:
                raise ValueError('10-step deterministic reproduction differs from original')
            provenance = _candidate_provenance(training, steps)
            saved = model.save(out / ('candidate-%d.npz' % steps), provenance=provenance)
            restarted = SlotWorldJEPA.load(
                out / ('candidate-%d.npz' % steps),
                expected_provenance=provenance, expected_sha256=saved['sha256'])
            if _weights_max_difference(model, restarted) > 1e-12:
                raise ValueError('Candidate checkpoint restart differs')
            metrics = _metrics(restarted, heldouts)
            row = {'steps': steps, 'status': 'SHADOW_CANDIDATE_RESTART_VERIFIED',
                   'checkpoint_sha256': saved['sha256'],
                   'checkpoint_bytes': saved['bytes'],
                   'provenance': provenance,
                   'reproduction_max_abs_difference': reproduction_difference,
                   'metrics': metrics,
                   'training_seconds_linux': time.perf_counter() - t0,
                   'process_peak_rss_kib_after_arm': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        except Exception as exc:
            row = {'steps': steps, 'status': 'FAILED_PRESERVED',
                   'error_type': type(exc).__name__,
                   'error': str(exc)[:500],
                   'training_seconds_linux': time.perf_counter() - t0}
        arms.append(row)
        atomic_write(out / ('arm-%d.json' % steps), lifecycle._canonical(row) + b'\n')
    report = {
        'schema': SCHEMA,
        'mode': 'SHADOW_ONLY',
        'authority': 0,
        'candidate_training_performed': True,
        'runtime_learning_performed': False,
        'native_body_training': False,
        'training_seed': 212,
        'fit_rows': len(fit_rows),
        'calibration_rows': len(calibration_rows),
        'frozen_training_cohort_sha256': training['cohort_sha256'],
        'frozen_training_source_sha256': training['source_sha256'],
        'frozen_original_checkpoint_sha256': CHECKPOINT_SHA256,
        'holdout_seeds': list(heldouts),
        'steps': list(STEPS),
        'arms': arms,
        'redmi_measured': False,
        'step2': 'UTILITY_FAIL',
        'b3': 'L1_FAIL',
        'body_jepa': 'UNAVAILABLE',
        'jepa_weight': 0,
        'canonical_architecture_complete': False,
        'user_full_scope_complete': False,
        'claim_limit': CLAIM_LIMIT,
    }
    atomic_write(out / 'manifest.json', lifecycle._canonical(report) + b'\n')
    verify_budget(frozen_root, out)
    return report


def verify_budget(frozen_root, output_dir):
    """Restart every successful candidate and recompute all frozen heldout scores."""
    training, _, _, _, heldouts = _frozen(frozen_root)
    out = Path(output_dir)
    report = _json_file(out / 'manifest.json', 1024 * 1024)
    if (report.get('schema') != SCHEMA or report.get('mode') != 'SHADOW_ONLY'
            or type(report.get('authority')) is not int or report['authority'] != 0
            or report.get('runtime_learning_performed') is not False
            or report.get('redmi_measured') is not False
            or report.get('native_body_training') is not False
            or report.get('step2') != 'UTILITY_FAIL'
            or report.get('b3') != 'L1_FAIL'
            or report.get('body_jepa') != 'UNAVAILABLE'
            or report.get('jepa_weight') != 0
            or report.get('claim_limit') != CLAIM_LIMIT
            or report.get('steps') != list(STEPS)
            or report.get('frozen_original_checkpoint_sha256') != CHECKPOINT_SHA256
            or report.get('frozen_training_cohort_sha256') != training['cohort_sha256']
            or report.get('frozen_training_source_sha256') != training['source_sha256']):
        raise ValueError('Invalid candidate report or negative gates')
    if type(report.get('arms')) is not list or len(report['arms']) != len(STEPS):
        raise ValueError('Candidate arm count mismatch')
    checked = 0
    for steps, arm in zip(STEPS, report['arms']):
        raw = (out / ('arm-%d.json' % steps)).read_bytes()
        if json.loads(raw) != arm or arm.get('steps') != steps:
            raise ValueError('Candidate raw arm manifest mismatch')
        if arm.get('status') == 'FAILED_PRESERVED':
            if 'error_type' not in arm or 'error' not in arm:
                raise ValueError('Malformed preserved failure')
            continue
        if arm.get('status') != 'SHADOW_CANDIDATE_RESTART_VERIFIED':
            raise ValueError('Unknown candidate status')
        provenance = _candidate_provenance(training, steps)
        if arm.get('provenance') != provenance:
            raise ValueError('Candidate step-specific provenance mismatch')
        model = SlotWorldJEPA.load(
            out / ('candidate-%d.npz' % steps),
            expected_provenance=provenance, expected_sha256=arm.get('checkpoint_sha256'))
        if _metrics(model, heldouts) != arm.get('metrics'):
            raise ValueError('Candidate restart heldout metrics mismatch')
        checked += 1
    return {'verified': True, 'successful_arms': checked, 'total_arms': len(STEPS),
            'original_checkpoint_sha256': CHECKPOINT_SHA256}


def main(argv=None):
    p = argparse.ArgumentParser(description='Frozen SHADOW World-JEPA training budget')
    subs = p.add_subparsers(dest='command', required=True)
    for name in ('run', 'verify'):
        q = subs.add_parser(name)
        q.add_argument('--frozen-root', required=True)
        q.add_argument('--output-dir', required=True)
    args = p.parse_args(argv)
    result = (run_budget(args.frozen_root, args.output_dir) if args.command == 'run'
              else verify_budget(args.frozen_root, args.output_dir))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
