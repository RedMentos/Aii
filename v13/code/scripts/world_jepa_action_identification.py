#!/usr/bin/env python3
"""Frozen World-JEPA action identification on new real Linux file-world outcomes.

Task: infer the true action from before/after observations by ranking all 31
hypothetical action-conditioned latent predictions. No training or runtime use.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from scripts import z12b_world_jepa as z12b
from scripts import z12c_slot_world_jepa as z12c
from scripts import world_jepa_shadow_lifecycle as lifecycle
from scripts.world_jepa_budget_fresh_holdout import (
    _frozen, _one, _verify_one, _canonical, _read, _sha,
    SELECTED_CHECKPOINT_SHA256, BUDGET_ZIP_SHA256, ORIGINAL_ZIP_SHA256,
)
from v13.common import atomic_write
from v13.world_jepa_shadow_probe import _json_file

SCHEMA = 'V13_WORLD_JEPA_ACTION_IDENTIFICATION_V1'
SEEDS = (501, 502, 503)
ROWS = 160
CLAIM_LIMIT = ('Post-selected 200-step frozen model, fresh real Linux synthetic-content '
               'file-world action identification from observed outcomes; not planning, '
               'causal/semantic utility, Redmi, native Body-JEPA or decision authority')


def _prior(original_root):
    """Fixed most-common action from verified original seed212 training prefix."""
    rows = lifecycle._checked_rows(_json_file(
        Path(original_root) / 'training' / 'cohort.json',
        lifecycle.MAX_COHORT_AUDIT_BYTES))
    if len(rows) != 240:
        raise ValueError('Wrong frozen original cohort size')
    counts = Counter(r['a'] for r in rows[:192])
    return min(range(len(z12b.ACTIONS)), key=lambda a: (-counts[a], a))


def rank_rows(model, rows, prior):
    """Return per-row task receipts; true label is used ONLY after predictions."""
    data = lifecycle._checked_rows(rows)
    if len(data) != ROWS or type(prior) is not int or not 0 <= prior < len(z12b.ACTIONS):
        raise ValueError('Invalid preregistered task input')
    actions = np.stack([z12c.slot_action(i) for i in range(len(z12b.ACTIONS))])
    if actions.shape != (31, 6, 6):
        raise ValueError('Unexpected action vocabulary')
    records = []
    for row in data:
        before = np.asarray(row['x'], dtype=np.float64).reshape(6, 10)
        after = np.asarray(row['x2'], dtype=np.float64).reshape(6, 10)
        # True action row['a'] is NOT used to generate/rank candidates.
        X = np.repeat(before.reshape(1, -1), len(actions), axis=0)
        predicted, _ = model.predict(X, actions)
        target = model.latent(after.reshape(1, -1), target=True)[0]
        scores = np.mean(((predicted - target[None]) /
                          model.zsd.reshape(1, 1, -1)) ** 2, axis=(1, 2))
        if scores.shape != (31,) or not np.isfinite(scores).all():
            raise ValueError('Invalid candidate consequence scores')
        order = np.argsort(scores, kind='stable')
        guess = int(order[0])
        true = row['a']
        rank = int(np.where(order == true)[0][0]) + 1
        delta = np.sqrt(((after - before) ** 2).sum(axis=1))
        slot_guess = (z12b.NOOP if float(delta.max()) <= 1e-12
                      else int(np.argmax(delta)))  # fixed write_short on changed slot
        rotated_guess = (guess + 1) % len(z12b.ACTIONS)
        records.append({
            'true_action': true, 'predicted_action': guess,
            'true_rank': rank, 'top5': rank <= 5,
            'prior_guess': prior, 'slot_heuristic_guess': slot_guess,
            'rotated_guess': rotated_guess,
            'world_overlap': row['world'], 'world_changed': row['world_changed'],
            'true_action_score': float(scores[true]),
            'best_action_score': float(scores[guess]),
        })
    return records


def _metrics(records):
    if len(records) != ROWS:
        raise ValueError('Wrong action identification cohort')
    rate = lambda predicate: sum(bool(predicate(r)) for r in records) / len(records)
    clean = [r for r in records if not r['world_overlap']]
    if not clean:
        raise ValueError('No clean action identification rows')
    return {
        'rows': len(records),
        'world_overlap_rows': len(records) - len(clean),
        'world_changed_rows': sum(r['world_changed'] for r in records),
        'model_top1': rate(lambda r: r['predicted_action'] == r['true_action']),
        'model_top5': rate(lambda r: r['top5']),
        'model_mean_true_rank': sum(r['true_rank'] for r in records) / len(records),
        'prior_top1': rate(lambda r: r['prior_guess'] == r['true_action']),
        'slot_heuristic_top1': rate(lambda r: r['slot_heuristic_guess'] == r['true_action']),
        'rotated_label_top1': rate(lambda r: r['rotated_guess'] == r['true_action']),
        'clean_rows': len(clean),
        'clean_model_top1': sum(r['predicted_action'] == r['true_action'] for r in clean) / len(clean),
        'clean_slot_heuristic_top1': sum(r['slot_heuristic_guess'] == r['true_action'] for r in clean) / len(clean),
    }


def _verify_task_one(model, seed, directory, prior):
    out = Path(directory)
    _verify_one(model, seed, out)
    task_manifest = _json_file(out / 'task_manifest.json', 1024 * 1024)
    if (type(task_manifest) is not dict or task_manifest.get('schema') != SCHEMA
            or task_manifest.get('mode') != 'SHADOW_ONLY'
            or task_manifest.get('authority') != 0
            or task_manifest.get('seed') != seed
            or task_manifest.get('rows') != ROWS
            or task_manifest.get('prior_action') != prior
            or task_manifest.get('checkpoint_sha256') != SELECTED_CHECKPOINT_SHA256
            or task_manifest.get('budget_zip_sha256') != BUDGET_ZIP_SHA256
            or task_manifest.get('original_zip_sha256') != ORIGINAL_ZIP_SHA256
            or task_manifest.get('auditor_sha256') != _sha(Path(__file__).read_bytes())
            or task_manifest.get('training_performed') is not False
            or task_manifest.get('redmi_measured') is not False
            or task_manifest.get('step2') != 'UTILITY_FAIL'
            or task_manifest.get('b3') != 'L1_FAIL'
            or task_manifest.get('body_jepa') != 'UNAVAILABLE'
            or type(task_manifest.get('jepa_weight')) is not int
            or task_manifest.get('jepa_weight') != 0
            or task_manifest.get('canonical_architecture_complete') is not False
            or task_manifest.get('user_full_scope_complete') is not False
            or task_manifest.get('claim_limit') != CLAIM_LIMIT):
        raise ValueError('Malformed task receipt or gate promotion')
    raw = _read(out / 'task_rows.json', 8 * 1024 * 1024)
    if _sha(raw) != task_manifest.get('task_rows_sha256'):
        raise ValueError('Action identification task receipt SHA mismatch')
    records = json.loads(raw)
    data = _json_file(out / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES)
    replay = rank_rows(model, data, prior)
    if type(records) is not list or len(records) != len(replay):
        raise ValueError('Action identification row count mismatch')
    for old, new in zip(records, replay):
        if type(old) is not dict or set(old) != set(new):
            raise ValueError('Action identification row schema mismatch')
        for key, value in new.items():
            recorded = old[key]
            if type(value) is float:
                if (type(recorded) is not float or not math.isfinite(recorded)
                        or not math.isclose(value, recorded, rel_tol=0., abs_tol=1e-10)):
                    raise ValueError('Action identification float replay mismatch')
            elif type(recorded) is not type(value) or recorded != value:
                raise ValueError('Action identification rank/label replay mismatch')
    metrics = _metrics(replay)
    saved_metrics = task_manifest.get('metrics')
    if type(saved_metrics) is not dict or set(saved_metrics) != set(metrics):
        raise ValueError('Task metric keys mismatch')
    for key, value in metrics.items():
        prior_value = saved_metrics[key]
        if type(value) is float:
            if (type(prior_value) is not float or not math.isclose(
                    value, prior_value, rel_tol=0., abs_tol=1e-10)):
                raise ValueError('Task metric replay mismatch')
        elif type(prior_value) is not type(value) or prior_value != value:
            raise ValueError('Task count replay mismatch')
    return {'seed': seed, 'rows': ROWS,
            'task_manifest_sha256': _sha(_read(out / 'task_manifest.json', 1024 * 1024)),
            'task_rows_sha256': task_manifest['task_rows_sha256'], 'metrics': metrics}


def _summary(per_seed, prior):
    if [x['seed'] for x in per_seed] != list(SEEDS):
        raise ValueError('Wrong preregistered action task seeds')
    keys = ('model_top1', 'model_top5', 'model_mean_true_rank',
            'prior_top1', 'slot_heuristic_top1', 'rotated_label_top1')
    weighted = {k: sum(x['rows'] * x['metrics'][k] for x in per_seed) /
                sum(x['rows'] for x in per_seed) for k in keys}
    wins = sum(x['metrics']['model_top1'] >
               max(x['metrics'][k] for k in (
                   'prior_top1', 'slot_heuristic_top1', 'rotated_label_top1'))
               and x['metrics']['model_top5'] > 5 / 31 for x in per_seed)
    return {
        'schema': SCHEMA + '_SUMMARY', 'mode': 'SHADOW_ONLY', 'authority': 0,
        'seeds': list(SEEDS), 'rows': sum(x['rows'] for x in per_seed),
        'prior_action': prior, 'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256,
        'per_seed': per_seed, 'weighted': weighted,
        'positive_seeds': wins, 'exploratory_signal': wins == len(SEEDS),
        'chance_top1_reference': 1 / 31, 'chance_top5_reference': 5 / 31,
        'training_performed': False, 'redmi_measured': False,
        'step2': 'UTILITY_FAIL', 'b3': 'L1_FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'canonical_architecture_complete': False,
        'user_full_scope_complete': False, 'claim_limit': CLAIM_LIMIT,
    }


def run(original_root, budget_root, output_dir):
    original_root, budget_root, out = map(Path, (original_root, budget_root, output_dir))
    if (out.exists() or out.resolve().is_relative_to(original_root.resolve())
            or out.resolve().is_relative_to(budget_root.resolve())):
        raise FileExistsError('Task output must be new and outside frozen inputs')
    model, _ = _frozen(original_root, budget_root)
    prior = _prior(original_root)
    out.mkdir(parents=True, exist_ok=False)
    per_seed = []
    for seed in SEEDS:
        folder = out / ('seed-%d' % seed)
        _one(model, seed, folder)  # new Linux temporary world, raw receipts
        data = _json_file(folder / 'cohort.json', lifecycle.MAX_COHORT_AUDIT_BYTES)
        records = rank_rows(model, data, prior)
        raw = _canonical(records)
        metrics = _metrics(records)
        task_manifest = {
            'schema': SCHEMA, 'mode': 'SHADOW_ONLY', 'authority': 0,
            'seed': seed, 'rows': ROWS, 'prior_action': prior,
            'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256,
            'budget_zip_sha256': BUDGET_ZIP_SHA256,
            'original_zip_sha256': ORIGINAL_ZIP_SHA256,
            'auditor_sha256': _sha(Path(__file__).read_bytes()),
            'task_rows_sha256': _sha(raw), 'metrics': metrics,
            'training_performed': False, 'redmi_measured': False,
            'step2': 'UTILITY_FAIL', 'b3': 'L1_FAIL',
            'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
            'canonical_architecture_complete': False,
            'user_full_scope_complete': False, 'claim_limit': CLAIM_LIMIT,
        }
        atomic_write(folder / 'task_rows.json', raw)
        atomic_write(folder / 'task_manifest.json', _canonical(task_manifest) + b'\n')
        per_seed.append(_verify_task_one(model, seed, folder, prior))
        atomic_write(out / 'summary.partial.json', _canonical({
            'status': 'PARTIAL_NOT_A_PASS', 'seeds_finished': [x['seed'] for x in per_seed],
            'checkpoint_sha256': SELECTED_CHECKPOINT_SHA256}) + b'\n')
    result = _summary(per_seed, prior)
    atomic_write(out / 'summary.json', _canonical(result) + b'\n')
    verify(original_root, budget_root, out)
    return result


def verify(original_root, budget_root, output_dir):
    model, _ = _frozen(original_root, budget_root)
    prior = _prior(original_root)
    out = Path(output_dir)
    per_seed = [_verify_task_one(model, seed, out / ('seed-%d' % seed), prior)
                for seed in SEEDS]
    result = _summary(per_seed, prior)
    saved = _json_file(out / 'summary.json', 1024 * 1024)
    if saved != result:
        raise ValueError('Task summary differs from persisted independent restart')
    return {'verified': True, 'seeds': list(SEEDS), 'rows': 480,
            'authority': 0, 'redmi_measured': False}


def main(argv=None):
    p = argparse.ArgumentParser(description='Frozen World-JEPA action consequence identification')
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
