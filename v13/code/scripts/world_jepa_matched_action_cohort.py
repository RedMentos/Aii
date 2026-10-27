"""Preregistered matched-state heldout-action World-JEPA synthetic cohort.

Different from frozen n64 SQLite cohort: 48 states x 4 actions, one unseen
state-action pair per state. Research only, no real observed data or authority.
"""
import json
import math
import sys

import numpy as np

from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_fair_baseline as fair
from v13 import world_jepa as wj
from v13 import world_model as wm

STATES = 48
SHUFFLE_SEEDS = (11, 23, 37)
STEPS = 400
MODEL_SEEDS = (3, 7)
ENSEMBLE = 3
RIDGE_LAMBDA = 0.01


def fixture():
    """Fixed state-major rows; no randomness or private data."""
    rows = []
    for i in range(STATES):
        x = i / 47
        state = [0.25 + 1.25*x, (i % 3)/2,
                 math.sin(2*math.pi*(i+0.5)/48),
                 math.cos(2*math.pi*(i+0.5)/48)]
        for a, route in enumerate(wm.ACTIONS):
            outcome = [
                0.2 + 0.15*x + 0.12*a + 0.2*x*(a/3) + 0.05*(state[2]+1),
                float((i+2*a) % 7 != 0),
                0.3 + 0.08*(a+1) + 0.25*(x-0.5)**2*((a+1)/4)
                + 0.02*(state[3]+1),
            ]
            rows.append({'action_id': f'matched-s{i:02d}-a{a}',
                         's': list(state), 'a': route, 'y': outcome})
    return rows


def split():
    """One unseen action per seen state; exactly 12 heldout per action."""
    train, heldout = [], []
    for i in range(STATES):
        held_action = (3*i + 1) % 4
        for a in range(4):
            (heldout if a == held_action else train).append(4*i+a)
    return np.asarray(train, dtype=np.int64), np.asarray(heldout, dtype=np.int64)


def permute_actions(A, train, heldout, seed):
    """Independent split-local row permutations, no target inspection."""
    if type(seed) is not int or seed not in SHUFFLE_SEEDS:
        raise ValueError('Unregistered action permutation seed')
    train, heldout = np.asarray(train), np.asarray(heldout)
    A = np.asarray(A, dtype=np.float64)
    if (A.shape != (STATES*4, 4)
            or not np.all((A == 0.) | (A == 1.))
            or not np.all(A.sum(1) == 1.)
            or len(train) != 144 or len(heldout) != 48
            or len(np.unique(train)) != 144 or len(np.unique(heldout)) != 48
            or np.intersect1d(train, heldout).size):
        raise ValueError('Invalid matched-action cohort')
    rng = np.random.default_rng(seed)
    shifted_train = A[train][rng.permutation(len(train))]
    shifted_heldout = A[heldout][rng.permutation(len(heldout))]
    if (not np.array_equal(shifted_train.sum(0), A[train].sum(0))
            or not np.array_equal(shifted_heldout.sum(0), A[heldout].sum(0))):
        raise ValueError('Permutation changed action marginal')
    return shifted_train, shifted_heldout


def run(steps=STEPS):
    if type(steps) is not int or not 0 <= steps <= STEPS:
        raise ValueError('Invalid preregistered step count')
    rows = fixture()
    data = bridge.make_dataset(rows)
    tr, te = split()
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    if (len(rows) != 192 or len(tr) != 144 or len(te) != 48
            or not np.array_equal(np.bincount(np.argmax(A[te], axis=1), minlength=4),
                                  np.full(4, 12))):
        raise ValueError('Matched-action split violated preregistration')

    ids = [r['action_id'] for r in rows]
    train_hash = bridge._digest([ids[int(i)] for i in tr])
    heldout_hash = bridge._digest([ids[int(i)] for i in te])
    direct = np.c_[np.ones(len(X)), X[:, :4], A]
    dtr, dte = fair._scaled_direct(direct[tr], direct[te])
    direct_w = bridge._ridge(dtr, Y[tr], RIDGE_LAMBDA)
    direct_mae = bridge._mae(dte @ direct_w, Y[te])

    state = np.c_[np.ones(len(X)), X[:, :4]]
    str_, ste = fair._scaled_direct(state[tr], state[te])
    state_w = bridge._ridge(str_, Y[tr], RIDGE_LAMBDA)
    state_mae = bridge._mae(ste @ state_w, Y[te])

    shuffles = {seed: permute_actions(A, tr, te, seed)
                for seed in SHUFFLE_SEEDS}
    arms = []
    for model_seed in MODEL_SEEDS:
        model = wj.WorldJEPA(seed=model_seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=steps)
        ztr, _ = model.predict(X[tr], A[tr])
        zte, _ = model.predict(X[te], A[te])
        correct = fair._score(dtr, dte, ztr, zte, Y[tr], Y[te])
        controls = []
        for shuffle_seed, (atr, ate) in shuffles.items():
            z_wrong_train, _ = model.predict(X[tr], atr)
            z_wrong_heldout, _ = model.predict(X[te], ate)
            score = fair._score(
                dtr, dte, z_wrong_train, z_wrong_heldout, Y[tr], Y[te])
            controls.append({
                'shuffle_seed': shuffle_seed,
                'row_permuted_mae': score,
                'train_changed_fraction': float(
                    np.mean(np.any(atr != A[tr], axis=1))),
                'heldout_changed_fraction': float(
                    np.mean(np.any(ate != A[te], axis=1))),
                'correct_gain_vs_shuffled': float(
                    score['pooled'] - correct['pooled']),
            })
        arms.append({
            'model_seed': model_seed,
            'correct_latent_mae': correct,
            'correct_gain_vs_state_only': float(
                state_mae['pooled'] - correct['pooled']),
            'correct_gain_vs_direct': float(
                direct_mae['pooled'] - correct['pooled']),
            'row_shuffle_controls': controls,
        })
    return {
        'scope': 'WORLD_JEPA_MATCHED_ACTION_SYNTHETIC_RESEARCH_ONLY',
        'evidence_level': 'SYNTHETIC_MATCHED_STATES_NO_REAL_CAUSALITY',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': train_hash,
        'heldout_ids_sha256': heldout_hash,
        'n': len(rows), 'distinct_states': STATES,
        'train_n': len(tr), 'heldout_n': len(te),
        'heldout_action_counts': [12, 12, 12, 12],
        'train_state_overlap_intentional': True,
        'heldout_state_action_pairs_seen_in_train': 0,
        'model_revision': wj.REVISION,
        'model_seeds': list(MODEL_SEEDS),
        'shuffle_seeds': list(SHUFFLE_SEEDS),
        'steps': steps, 'ensemble': ENSEMBLE,
        'ridge_lambda': RIDGE_LAMBDA,
        'scaled_state_only_mae': state_mae,
        'scaled_state_action_direct_mae': direct_mae,
        'per_model_seed': arms,
        'runtime_wired': False, 'model_weights_persisted': False,
        'utility_proven': False, 'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic-smoke', action='store_true')
    args = parser.parse_args(argv)
    if not args.synthetic_smoke:
        raise ValueError('Explicit synthetic-only mode required')
    result = run()
    sys.stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
