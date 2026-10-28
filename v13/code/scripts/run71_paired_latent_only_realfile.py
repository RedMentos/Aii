"""Run71: preregistered paired real-file *latent-only* action sensitivity.

Isolated Linux temporary-file SHADOW experiment. No supervised observation
readout, no Runtime/Store, no model publication, no permission promotion.
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
from scripts import run64_realfile_jepa_factorized_readout as prior
from scripts import run67_delta_jepa_realfile as delta
from scripts import z12b_world_jepa as original
from v13 import world_jepa as frozen

SCHEMA = 'v13.z12b.paired_latent_only_realfile_shadow.v1'
SEEDS = (311, 313, 317)
N_TRAIN = 240
N_STATES = 24
STEPS = 200
TIE_TOL = 1e-12
TARGET_DISTINCT_TOL = 1e-12


def _paired_states(seed, held):
    if (type(seed) is not int or seed not in SEEDS
            or type(held) is not tuple or len(held) != 4
            or held != tuple(sorted(held))
            or any(type(a) is not int or a not in parent.NON_NOOP for a in held)
            or len(set(held)) != 4):
        raise PermissionError('RUN71_UNREGISTERED_PAIRED_SOURCE')
    allowed = tuple(a for a in parent.NON_NOOP if a not in held)
    rng = random.Random(seed+30000)
    choices = random.Random(seed+30001)
    states = []
    with tempfile.TemporaryDirectory(prefix='v13-run71-file-') as td:
        root = Path(td)
        live = root/'live'
        live.mkdir()
        for _ in range(16):
            op, slot = original.ACTIONS[choices.choice(allowed)]
            original.do(live, op, slot, rng)
        for state_idx in range(N_STATES):
            for _ in range(1+choices.randrange(3)):
                op, slot = original.ACTIONS[choices.choice(allowed)]
                original.do(live, op, slot, rng)
            x = np.asarray(original.features(live), dtype=np.float64)
            candidates = []
            for a in held:
                cp = root/'trial'
                shutil.copytree(live, cp)
                op, slot = original.ACTIONS[a]
                payload = random.Random(900000+seed*100000+state_idx*100+a)
                ok = bool(original.do(cp, op, slot, payload))
                x2 = np.asarray(original.features(cp), dtype=np.float64)
                shutil.rmtree(cp)
                if (x.shape != (parent.FEATURES,) or x2.shape != x.shape
                        or not np.isfinite(x).all() or not np.isfinite(x2).all()):
                    raise ValueError('RUN71_INVALID_REAL_FILE_FEATURES')
                candidates.append((a, x2.copy(), ok,
                                   not np.array_equal(x, x2)))
            states.append({'x': x.copy(), 'candidates': candidates})
    return states


def _digest(states):
    h = hashlib.sha256()
    for row in states:
        h.update(np.ascontiguousarray(row['x'], dtype='<f8').tobytes())
        for a, x2, ok, changed in row['candidates']:
            h.update(int(a).to_bytes(4, 'little'))
            h.update(np.ascontiguousarray(x2, dtype='<f8').tobytes())
            h.update(b'1' if ok else b'0')
            h.update(b'1' if changed else b'0')
    return h.hexdigest()


def _target(model, x2):
    if isinstance(model, frozen.WorldJEPA):
        z = model.latent(x2, target=True)
    else:
        z = frozen.encode(model.tgt, (x2-model.mu)/model.sd)[0]
    if z.shape != (len(x2), frozen.Z) or not np.isfinite(z).all():
        raise ValueError('RUN71_INVALID_TARGET_LATENTS')
    return z


def _predict(model, x, actions):
    z, _ = model.predict(x, actions)
    if z.shape != (len(x), frozen.Z) or not np.isfinite(z).all():
        raise ValueError('RUN71_INVALID_PREDICTED_LATENTS')
    return z


def _train(model_type, seed, x, actions, x2):
    model = (model_type(seed=seed, ensemble=1)
             if model_type is frozen.WorldJEPA else model_type(seed=seed))
    model.fit(x, actions, x2, steps=STEPS, log_every=STEPS)
    zt = _target(model, x2)
    std = zt.std(0)+1e-6
    eig = np.clip(np.linalg.eigvalsh(np.cov(zt.T)), 0., None)
    p = eig/eig.sum() if eig.sum() > 0 else np.zeros_like(eig)
    stats = {'effective_rank': float(np.exp(
                 -(p[p > 0]*np.log(p[p > 0])).sum())) if eig.sum() > 0 else 0.,
             'min_std': float(zt.std(0).min())}
    if not np.isfinite(std).all() or not all(np.isfinite(v) for v in stats.values()):
        raise ValueError('RUN71_INVALID_TRAIN_NORMALIZATION')
    return model, std, stats


def _score(pred, target, observed, train_std):
    pred, target, observed = (np.asarray(v, dtype=np.float64)
                              for v in (pred, target, observed))
    std = np.asarray(train_std, dtype=np.float64)
    if (pred.shape != target.shape
            or pred.shape != (N_STATES, 4, frozen.Z)
            or observed.shape != (N_STATES, 4, parent.FEATURES)
            or std.shape != (frozen.Z,) or np.any(std <= 0)
            or not all(np.isfinite(v).all()
                       for v in (pred, target, observed, std))):
        raise ValueError('RUN71_INVALID_LATENT_PAIR_SCORE')
    p = pred/std
    y = target/std
    correct = wrong = tied = observed_same = target_same = 0
    for ps, ys, obs in zip(p, y, observed):
        for i, j in itertools.combinations(range(4), 2):
            if np.array_equal(obs[i], obs[j]):
                observed_same += 1
                continue
            if float(np.mean((ys[i]-ys[j])**2)) <= TARGET_DISTINCT_TOL:
                target_same += 1
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
    n = correct+wrong+tied
    return {
        'normalized_latent_mse': float(np.mean((p-y)**2)),
        'informative_pairs': n, 'observed_identical_pairs': observed_same,
        'target_collapsed_pairs': target_same,
        'correct': correct, 'wrong': wrong, 'tied': tied,
        'strict_pair_accuracy': float(correct/n) if n else 0.,
        'pair_tie_fraction': float(tied/n) if n else 0.,
    }


def _evaluate_model(model, std, stats, xt, actions, truth, *, include_zero_train=False):
    target = _target(model, truth)
    shape = (N_STATES, 4, frozen.Z)
    target = target.reshape(shape)
    obs = truth.reshape(N_STATES, 4, parent.FEATURES)
    base = _predict(model, xt, actions).reshape(shape)
    zero = _predict(model, xt, np.zeros_like(actions)).reshape(shape)
    perm = np.roll(actions.reshape(N_STATES, 4, -1), 1, axis=1).reshape(actions.shape)
    permuted = _predict(model, xt, perm).reshape(shape)
    scores = {
        'observed': _score(base, target, obs, std),
        'zero_at_eval': _score(zero, target, obs, std),
        'permuted_at_eval': _score(permuted, target, obs, std),
        'oracle_diagnostic': _score(target, target, obs, std),
        'blind_diagnostic': _score(zero, target, obs, std),
    }
    if include_zero_train:
        scores = {'zero_trained': scores['zero_at_eval'],
                  'oracle_diagnostic': scores['oracle_diagnostic'],
                  'blind_diagnostic': scores['blind_diagnostic']}
    oracle = scores['oracle_diagnostic']
    blind = scores['blind_diagnostic']
    if (oracle['informative_pairs'] <= 0 or oracle['wrong'] or oracle['tied']
            or blind['correct'] or blind['wrong']
            or blind['tied'] != blind['informative_pairs']):
        raise AssertionError('RUN71_LATENT_DIAGNOSTIC_CONTROL_FAILURE')
    return {'train_target_collapse': stats, 'scores': scores}


def _seed(seed):
    held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
    train = parent._rows(seed, held, N_TRAIN, test=False)
    if len(train) != N_TRAIN or any(a in held for _, a, _, _ in train):
        raise ValueError('RUN71_TRAIN_HELDOUT_CONTAMINATION')
    states = _paired_states(seed, held)
    if (len(states) != N_STATES
            or any(tuple(c[0] for c in s['candidates']) != held for s in states)):
        raise ValueError('RUN71_PAIRED_SOURCE_DRIFT')
    x = np.stack([r[0] for r in train])
    x2 = np.stack([r[2] for r in train])
    a = prior._factor_actions(train)
    xt = np.stack([s['x'] for s in states for _ in s['candidates']])
    truth = np.stack([c[1] for s in states for c in s['candidates']])
    actions = np.stack([
        prior._factor_actions([(s['x'], c[0], c[1], c[2])])[0]
        for s in states for c in s['candidates']
    ])
    if (xt.shape != (N_STATES*4, parent.FEATURES)
            or truth.shape != xt.shape
            or actions.shape != (len(xt), len(original.OPS)+original.SLOTS)
            or not np.all(actions.sum(1) == 2)):
        raise ValueError('RUN71_INVALID_TEST_MATRIX')
    m0, sd0, stat0 = _train(frozen.WorldJEPA, seed, x, a, x2)
    m1, sd1, stat1 = _train(delta.DeltaWorldJEPA, seed, x, a, x2)
    mz, sdz, statz = _train(delta.DeltaWorldJEPA, seed, x, np.zeros_like(a), x2)
    reports = {
        'original': _evaluate_model(m0, sd0, stat0, xt, actions, truth),
        'delta': _evaluate_model(m1, sd1, stat1, xt, actions, truth),
        'delta_zero_train': _evaluate_model(
            mz, sdz, statz, xt, actions, truth, include_zero_train=True),
    }
    return {
        'seed': seed, 'heldout_action_indices': list(held),
        'train_rows_sha256': parent._digest(train),
        'paired_rows_sha256': _digest(states),
        'n_train': len(train), 'paired_source_states': len(states),
        'candidate_file_actions': len(truth),
        'candidate_successes': sum(c[2] for s in states for c in s['candidates']),
        'candidate_observed_changes': sum(c[3] for s in states for c in s['candidates']),
        'models': reports,
    }


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_states=N_STATES, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_states) is not int or n_states != N_STATES
            or type(steps) is not int or steps != STEPS):
        raise PermissionError('RUN71_ONLY_PREREGISTERED_COHORT')
    reports = [_seed(seed) for seed in seeds]
    aggregate = {}
    for model in ('original', 'delta', 'delta_zero_train'):
        aggregate[model] = {}
        names = reports[0]['models'][model]['scores']
        for name in names:
            rows = [r['models'][model]['scores'][name] for r in reports]
            n = sum(v['informative_pairs'] for v in rows)
            aggregate[model][name] = {
                'normalized_latent_mse': float(np.mean(
                    [v['normalized_latent_mse'] for v in rows])),
                'informative_pairs': n,
                'observed_identical_pairs': sum(v['observed_identical_pairs'] for v in rows),
                'target_collapsed_pairs': sum(v['target_collapsed_pairs'] for v in rows),
                'correct': sum(v['correct'] for v in rows),
                'wrong': sum(v['wrong'] for v in rows),
                'tied': sum(v['tied'] for v in rows),
                'strict_pair_accuracy':
                    float(sum(v['correct'] for v in rows)/n) if n else 0.,
            }
    return {
        'schema': SCHEMA, 'status': 'PAIRED_LATENT_ONLY_REALFILE_SHADOW',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'train_rows_per_seed': n_train,
        'paired_source_states_per_seed': n_states,
        'candidate_actions_per_state': 4, 'steps': steps,
        'tie_tolerance': TIE_TOL, 'target_distinct_tolerance': TARGET_DISTINCT_TOL,
        'reports': reports, 'aggregate': aggregate,
        'file_actions_executed': True, 'jepa_training_executed': True,
        'supervised_observation_readout_used': False,
        'jepa_only_grounded_utility_proven': False,
        'counterfactual_causality_proven': False,
        'source_disjointness_verified': False, 'confidence_measured': False,
        'native_model_executed': False, 'phone_measured': False,
        'model_weights_published': False, 'learning_gate_pass': False,
        'age_authority': 0, 'jepa_weight': 0,
        'whole_system_complete': False,
    }


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
