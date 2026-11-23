"""Run69: same-state real-file heldout action pairs, source-only SHADOW.

Never reads user files or Runtime/Store; trains only isolated NumPy research
models and never publishes weights. Frozen Run60/63/64/67 and WorldJEPA intact.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import shutil
import tempfile
from pathlib import Path

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as factor
from scripts import run64_realfile_jepa_factorized_readout as prior
from scripts import run67_delta_jepa_realfile as delta
from scripts import z12b_world_jepa as original
from v13 import world_jepa as frozen

SCHEMA = 'v13.z12b.paired_realfile_counterfactual_shadow.v1'
SEEDS = (283, 293, 307)
N_TRAIN = 240
N_STATES = 24
STEPS = 200
MODEL_NAMES = ('delta_observed', 'delta_zero', 'original_observed',
               'original_permuted_at_eval', 'slot_aware_local_ridge',
               'factorized_global_delta_ridge', 'persistence_blind',
               'oracle_diagnostic')
TIE_TOL = 1e-12


def _digest_paired(states):
    h = hashlib.sha256()
    for row in states:
        h.update(np.ascontiguousarray(row['x'], dtype='<f8').tobytes())
        for a, x2, ok, changed in row['candidates']:
            h.update(int(a).to_bytes(4, 'little'))
            h.update(np.ascontiguousarray(x2, dtype='<f8').tobytes())
            h.update(b'1' if ok else b'0')
            h.update(b'1' if changed else b'0')
    return h.hexdigest()


def _paired_states(seed, held, count=N_STATES):
    """Each candidate runs on an independent copy of one actual source folder."""
    if (type(seed) is not int or seed not in SEEDS
            or type(held) is not tuple or len(held) != 4
            or held != tuple(sorted(held))
            or any(type(a) is not int or a not in parent.NON_NOOP for a in held)
            or type(count) is not int or count != N_STATES):
        raise PermissionError('RUN69_UNREGISTERED_PAIRED_COHORT')
    allowed = tuple(a for a in parent.NON_NOOP if a not in held)
    state_rng = random.Random(seed + 25000)
    action_choices = random.Random(seed + 25001)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v13-run69-file-') as td:
        root = Path(td)
        live = root / 'live'
        live.mkdir()
        for _ in range(16):
            op, slot = original.ACTIONS[action_choices.choice(allowed)]
            original.do(live, op, slot, state_rng)
        for state_idx in range(count):
            for _ in range(1 + action_choices.randrange(3)):
                op, slot = original.ACTIONS[action_choices.choice(allowed)]
                original.do(live, op, slot, state_rng)
            x = np.asarray(original.features(live), dtype=np.float64)
            candidates = []
            for a in held:
                trial = root / 'trial'
                shutil.copytree(live, trial)
                op, slot = original.ACTIONS[a]
                # Separate deterministic action-payload stream per candidate.
                payload_rng = random.Random(seed*100000 + state_idx*100 + a)
                ok = bool(original.do(trial, op, slot, payload_rng))
                x2 = np.asarray(original.features(trial), dtype=np.float64)
                shutil.rmtree(trial)
                if (x.shape != (parent.FEATURES,) or x2.shape != x.shape
                        or not np.isfinite(x).all() or not np.isfinite(x2).all()):
                    raise ValueError('RUN69_INVALID_REAL_FILE_FEATURES')
                candidates.append((a, x2.copy(), ok,
                                   not np.array_equal(x, x2)))
            rows.append({'x': x.copy(), 'candidates': candidates})
    return rows


def _score(pred, truth):
    """Strict direct-vs-swapped assignment: action-blind output must tie."""
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=np.float64)
    if (pred.ndim != 3 or pred.shape != truth.shape
            or pred.shape[1:] != (4, parent.FEATURES)
            or len(pred) != N_STATES
            or not np.isfinite(pred).all() or not np.isfinite(truth).all()):
        raise ValueError('RUN69_INVALID_PAIRED_SCORE')
    correct = wrong = tied = indistinct = 0
    for ps, ys in zip(pred, truth):
        for i, j in itertools.combinations(range(4), 2):
            if np.array_equal(ys[i], ys[j]):
                indistinct += 1
                continue
            direct = float(np.mean((ps[i]-ys[i])**2 + (ps[j]-ys[j])**2))
            swapped = float(np.mean((ps[i]-ys[j])**2 + (ps[j]-ys[i])**2))
            margin = swapped-direct
            if margin > TIE_TOL:
                correct += 1
            elif margin < -TIE_TOL:
                wrong += 1
            else:
                tied += 1
    informative = correct + wrong + tied
    return {
        'overall_mse': float(np.mean((pred-truth)**2)),
        'informative_pairs': informative,
        'indistinguishable_pairs': indistinct,
        'correct': correct, 'wrong': wrong, 'tied': tied,
        'strict_pair_accuracy': float(correct/informative) if informative else 0.,
        'pair_tie_fraction': float(tied/informative) if informative else 0.,
    }


def _fit_latent(ctor, seed, x, a, x2):
    """Train only on the supplied training transitions; no holdout targets."""
    model = (ctor(seed=seed, ensemble=1) if ctor is frozen.WorldJEPA
             else ctor(seed=seed))
    model.fit(x, a, x2, steps=STEPS, log_every=STEPS)
    z, _ = model.predict(x, a)
    if z.shape != (len(x), frozen.Z) or not np.isfinite(z).all():
        raise ValueError('RUN69_INVALID_TRAIN_LATENTS')
    w = parent._ridge(np.c_[np.ones(len(x)), z], x2)
    return model, w


def _latent_predict(model, w, x, a):
    z, _ = model.predict(x, a)
    if z.shape != (len(x), frozen.Z) or not np.isfinite(z).all():
        raise ValueError('RUN69_INVALID_TEST_LATENTS')
    result = np.c_[np.ones(len(x)), z] @ w
    if result.shape != x.shape or not np.isfinite(result).all():
        raise ValueError('RUN69_INVALID_OUTCOME_PREDICTION')
    return result


def _seed(seed):
    held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
    train = parent._rows(seed, held, N_TRAIN, test=False)
    if (len(train) != N_TRAIN
            or any(a in held for _, a, _, _ in train)):
        raise ValueError('RUN69_TRAIN_HELDOUT_CONTAMINATION')
    states = _paired_states(seed, held)
    if (len(states) != N_STATES
            or any(tuple(a for a, _, _, _ in s['candidates']) != held
                   for s in states)):
        raise ValueError('RUN69_INVALID_PAIRED_ACTIONS')
    x = np.stack([r[0] for r in train])
    x2 = np.stack([r[2] for r in train])
    a = prior._factor_actions(train)
    xt = np.stack([s['x'] for s in states for _ in s['candidates']])
    truth = np.stack([c[1] for s in states for c in s['candidates']])
    actions = np.stack([
        factor._factorized_global_features(s['x'], c[0])[1+parent.FEATURES:]
        for s in states for c in s['candidates']
    ])
    if (xt.shape != (N_STATES*4, parent.FEATURES)
            or truth.shape != xt.shape
            or actions.shape != (len(xt), len(original.OPS)+original.SLOTS)
            or not np.all(actions.sum(1) == 2)):
        raise ValueError('RUN69_INVALID_HELDOUT_MATRIX')
    original_model, original_w = _fit_latent(
        frozen.WorldJEPA, seed, x, a, x2)
    delta_model, delta_w = _fit_latent(
        delta.DeltaWorldJEPA, seed, x, a, x2)
    zero_model, zero_w = _fit_latent(
        delta.DeltaWorldJEPA, seed, x, np.zeros_like(a), x2)
    # Rotate heldout candidate actions *within each same-state group*.
    permuted = np.roll(actions.reshape(N_STATES, 4, -1), 1, axis=1).reshape(
        actions.shape)
    baseline_w = factor._fit(train)
    base_predictions = [
        factor._predict(s['x'], c[0], baseline_w)
        for s in states for c in s['candidates']
    ]
    predicted = {
        'delta_observed': _latent_predict(delta_model, delta_w, xt, actions),
        'delta_zero': _latent_predict(
            zero_model, zero_w, xt, np.zeros_like(actions)),
        'original_observed': _latent_predict(
            original_model, original_w, xt, actions),
        'original_permuted_at_eval': _latent_predict(
            original_model, original_w, xt, permuted),
        'slot_aware_local_ridge': np.stack(
            [p['slot_aware_local_ridge'] for p in base_predictions]),
        'factorized_global_delta_ridge': np.stack(
            [p['factorized_global_delta_ridge'] for p in base_predictions]),
        'persistence_blind': xt.copy(),
        'oracle_diagnostic': truth.copy(),
    }
    if set(predicted) != set(MODEL_NAMES):
        raise AssertionError('RUN69_MODEL_SET_DRIFT')
    metrics = {
        name: _score(value.reshape(N_STATES, 4, parent.FEATURES),
                     truth.reshape(N_STATES, 4, parent.FEATURES))
        for name, value in predicted.items()
    }
    if (metrics['oracle_diagnostic']['wrong']
            or metrics['oracle_diagnostic']['tied']
            or metrics['persistence_blind']['correct']
            or metrics['persistence_blind']['wrong']
            or metrics['delta_zero']['correct']
            or metrics['delta_zero']['wrong']):
        raise AssertionError('RUN69_DIAGNOSTIC_CONTROL_FAILURE')
    if metrics['oracle_diagnostic']['informative_pairs'] <= 0:
        raise ValueError('RUN69_NO_DISTINGUISHABLE_PAIRS')
    return {
        'seed': seed, 'heldout_action_indices': list(held),
        'train_rows_sha256': parent._digest(train),
        'paired_rows_sha256': _digest_paired(states),
        'train_rows': len(train), 'paired_source_states': len(states),
        'real_candidate_file_actions': len(xt),
        'real_candidate_successes': sum(c[2] for s in states
                                        for c in s['candidates']),
        'observably_changed_candidates': sum(c[3] for s in states
                                              for c in s['candidates']),
        'metrics': metrics,
    }


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_states=N_STATES, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_states) is not int or n_states != N_STATES
            or type(steps) is not int or steps != STEPS):
        raise PermissionError('RUN69_ONLY_PREREGISTERED_COHORT')
    reports = [_seed(seed) for seed in seeds]
    aggregate = {}
    for name in MODEL_NAMES:
        rows = [r['metrics'][name] for r in reports]
        n = sum(r['informative_pairs'] for r in rows)
        aggregate[name] = {
            'overall_mse': float(np.mean([r['overall_mse'] for r in rows])),
            'informative_pairs': n,
            'correct': sum(r['correct'] for r in rows),
            'wrong': sum(r['wrong'] for r in rows),
            'tied': sum(r['tied'] for r in rows),
            'indistinguishable_pairs':
                sum(r['indistinguishable_pairs'] for r in rows),
            'strict_pair_accuracy':
                float(sum(r['correct'] for r in rows)/n) if n else 0.,
        }
    return {
        'schema': SCHEMA,
        'status': 'PAIRED_REALFILE_COUNTERFACTUAL_SHADOW_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'train_rows_per_seed': n_train,
        'paired_source_states_per_seed': n_states,
        'candidate_actions_per_state': 4, 'steps': steps,
        'tie_tolerance': TIE_TOL, 'reports': reports,
        'aggregate': aggregate, 'file_actions_executed': True,
        'jepa_training_executed': True,
        'oracle_uses_heldout_targets_diagnostic_only': True,
        'native_model_executed': False, 'model_weights_published': False,
        'counterfactual_causality_proven': False,
        'jepa_only_utility_proven': False, 'confidence_measured': False,
        'source_disjointness_verified': False, 'phone_measured': False,
        'learning_gate_pass': False, 'age_authority': 0,
        'jepa_weight': 0, 'whole_system_complete': False,
    }


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
