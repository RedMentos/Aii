#!/usr/bin/env python3
"""Research-only A->B->A ablation using V13's existing NumPy WorldJEPA.

See the preregistered design in docs/research. This module consumes only
synthetic generated arrays and never touches a Runtime, store or model file.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from v13.world_jepa import WorldJEPA

SEEDS = (13, 21, 34)
TRAIN_N = 32
HELDOUT_N = 64
STEPS = 20
STORED_PER_PHASE = 16


def generate(seed: int, split: int, n: int, domain: str):
    """Independent synthetic transitions; domain A/B share inputs but differ in dynamics."""
    if type(seed) is not int or seed < 0 or type(split) is not int or split < 0:
        raise ValueError('seed and split must be nonnegative integers')
    if type(n) is not int or n < 2 or n % 2 or domain not in ('A', 'B'):
        raise ValueError('invalid synthetic split')
    rng = np.random.default_rng(np.random.SeedSequence([seed, split, 20261110]))
    x = rng.normal(size=(n, 4))
    labels = np.repeat([0, 1], n // 2)
    rng.shuffle(labels)
    action = np.eye(2)[labels]
    # Same observable state and action distributions but conflicting dynamics.
    # Without a context variable, simultaneous perfect A/B prediction is impossible.
    direction = 1. if domain == 'A' else -1.
    signed = 2 * labels - 1
    shift = np.column_stack((.7 * signed, -.4 * signed,
                             .25 * signed, np.zeros(n)))
    target = .8 * x + direction * shift
    ids = tuple(f'{seed}:{split}:{i}' for i in range(n))
    return {'x': x, 'a': action, 'y': target, 'ids': ids, 'domain': domain}


def verify_disjoint(train, heldout):
    """Fail closed on malformed cohorts and shared observations, not just split IDs.

    Input/state-action equality is disallowed across train and evaluation even
    when caller-controlled IDs or targets differ. No data is normalized or
    silently dropped; NaN, Inf and shape mismatches invalidate the cohort.
    """
    def keys(groups):
        ids, rows = [], []
        for part in groups:
            x = np.asarray(part['x'])
            a = np.asarray(part['a'])
            y = np.asarray(part['y'])
            identities = part['ids']
            n = len(identities)
            if (n == 0 or x.shape != (n, 4) or a.shape != (n, 2)
                    or y.shape != (n, 4)):
                raise ValueError('invalid cohort shape')
            if not all(np.issubdtype(v.dtype, np.number) for v in (x, a, y)):
                raise ValueError('non-numeric cohort')
            if not all(np.all(np.isfinite(v)) for v in (x, a, y)):
                raise ValueError('nonfinite cohort')
            if (any(type(identity) is not str or not identity for identity in identities)
                    or len(set(identities)) != n):
                raise ValueError('invalid or duplicate cohort identity')
            ids.extend(identities)
            for state, action in zip(x, a):
                row = np.concatenate((state, action)).astype('<f8')
                # Canonicalize signed zeros, which represent identical inputs.
                row[row == 0] = 0.0
                rows.append(hashlib.sha256(row.tobytes()).hexdigest())
        if len(set(ids)) != len(ids) or len(set(rows)) != len(rows):
            raise ValueError('duplicate cohort observation')
        return set(ids), set(rows)

    train_ids, train_rows = keys(train)
    held_ids, held_rows = keys(heldout)
    if train_ids & held_ids or train_rows & held_rows:
        raise ValueError('train/holdout overlap')


def arrays(part):
    return part['x'], part['a'], part['y']


def source_hash(parts):
    h = hashlib.sha256()
    for part in parts:
        h.update(part['domain'].encode('ascii'))
        for identity in part['ids']:
            h.update(identity.encode('ascii') + b'\n')
        for value in arrays(part):
            h.update(np.asarray(value, dtype='<f8').tobytes())
    return h.hexdigest()


def fit_readout(model, part):
    """Fit a fixed linear decoder on initial train targets, never on heldouts."""
    z = model.latent(part['y'], target=True)
    design = np.column_stack((z, np.ones(len(z))))
    reg = 1e-3 * np.eye(design.shape[1])
    reg[-1, -1] = 0.
    return np.linalg.solve(design.T @ design + reg, design.T @ part['y'])


def score(model, part, readout):
    x, action, y = arrays(part)
    pred = model.predict(x, action)[0]
    wrong_action_pred = model.predict(x, action[:, ::-1])[0]
    def output_mse(latent):
        decoded = np.column_stack((latent, np.ones(len(latent)))) @ readout
        return float(np.mean((decoded - y) ** 2))
    collapse = model.collapse_stats(y)
    result = {
        'observable_mse': output_mse(pred),
        'flipped_action_mse': output_mse(wrong_action_pred),
        'native_target_latent_mse': model.prediction_loss(x, action, y),
        'target_effective_rank': collapse['effective_rank'],
        'target_collapsed': collapse['collapsed'],
    }
    if not all(np.isfinite(v) for k, v in result.items() if k != 'target_collapsed'):
        raise ValueError('nonfinite experiment result')
    return result


def mixed(current, prior):
    """32 rows: 16 current and 16 from capped, equally sampled prior phases."""
    if not prior or len(prior) > 2:
        raise ValueError('expected one or two prior phases')
    rows = [tuple(v[:16] for v in arrays(current))]
    base, extra = divmod(16, len(prior))
    for i, phase in enumerate(prior):
        n = base + (1 if i < extra else 0)
        rows.append(tuple(v[:n] for v in arrays(phase)))
    return tuple(np.concatenate([row[i] for row in rows]) for i in range(3))


def run_seed(seed: int, steps: int = STEPS):
    if type(steps) is not int or not 1 <= steps <= 200:
        raise ValueError('invalid per-phase update budget')
    train = [generate(seed, 1, TRAIN_N, 'A'), generate(seed, 2, TRAIN_N, 'B'),
             generate(seed, 3, TRAIN_N, 'A')]
    heldout = [generate(seed, 101, HELDOUT_N, 'A'), generate(seed, 102, HELDOUT_N, 'B')]
    verify_disjoint(train, heldout)
    init = WorldJEPA(seed=seed, ensemble=1)
    init.fit(*arrays(train[0]), steps=steps, log_every=steps)
    readout = fit_readout(init, train[0])
    models = {name: copy.deepcopy(init) for name in ('frozen', 'current', 'replay')}
    out = {'seed': seed, 'source_sha256': source_hash(train + heldout),
           'arms': {k: [] for k in models}}

    def measure(phase, stored):
        memory = sum(sum(v[:STORED_PER_PHASE].nbytes for v in arrays(p)) for p in stored)
        for name, model in models.items():
            out['arms'][name].append({'after': phase, 'fit_steps': model._fit_steps,
                'old_A': score(model, heldout[0], readout),
                'new_B': score(model, heldout[1], readout),
                'stored_rows': len(stored) * STORED_PER_PHASE if name == 'replay' else 0,
                'nominal_stored_array_bytes': memory if name == 'replay' else 0})

    measure('initial_A', [])
    for i, phase in ((1, 'after_B'), (2, 'after_return_A')):
        models['current'].partial_fit(*arrays(train[i]), steps=steps, log_every=steps)
        models['replay'].partial_fit(*mixed(train[i], train[:i]), steps=steps, log_every=steps)
        measure(phase, train[:i])
    return out


def run(seeds=SEEDS, steps=STEPS):
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('seeds must be nonempty and unique')
    return {
        'schema': 'v13-research-jepa-bounded-replay-ablation-v1',
        'scope': 'SYNTHETIC_CPU_NO_RUNTIME_PROMOTION_NOT_JEPA_TTT_REPRODUCTION',
        'configuration': {'seeds': list(seeds), 'train_per_phase': TRAIN_N,
            'holdout_per_domain': HELDOUT_N, 'steps_per_phase': steps,
            'ensemble': 1, 'replay_rows_per_prior_phase': STORED_PER_PHASE,
            'mixed_current_rows': 16, 'mixed_replay_rows': 16,
            'prior_phases_maximum': 2, 'observable_readout': 'fixed_initial_A_train_ridge',
            'domains': 'opposing_dynamics_without_domain_observation'},
        'results': [run_seed(seed, steps) for seed in seeds],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='explicit result JSON path (never a V13 model checkpoint)')
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(f'wrote {args.output} ({len(result["results"])} seeds, synthetic only)')


if __name__ == '__main__':
    main()
