#!/usr/bin/env python3
"""Action-JEPA round 6: changed objective, mean delta as fixed base plus a ridge residual.

Rounds 1-5 trained the affine objective of action_jepa_objective.py (moving
projector, EMA target, variance floor). On near-constant action deltas it lost
to the per-action mean-delta control and even unlearned it. Here the mean delta
is a fixed, not trainable base and only a context-dependent remainder is fitted
in closed form:

    pred = x @ p + mean_delta[a] + (x - mu_a) @ W_a        (arm "full", x = native tap)
    pred = x @ p + mean_delta[a] + (z - nu_a) @ W_a        (arm "proj", z = x @ p)

p is the seeded fixed projection that rounds 1-5 used as evaluation anchor; it
is also the target space, so there is no EMA target and no variance floor.
W_a is the ridge solution on train rows only; lambda per action comes from a
preregistered grid that includes lambda = inf (W_a = 0, i.e. the pure
mean-delta control) and is chosen on the calibration partition only. Scores,
controls and gates are the ones of action_jepa_objective.py; the analytic
gradient gate becomes a check of the ridge normal equations. Never activates
runtime, learning or receiver authority.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import action_jepa_objective as aj
from v13.predictor_worker import collapse_telemetry

OBJECTIVE = 'mean-delta-ridge-residual-shadow-v1'
SCALES = (.01, .1, 1., 10., 100., 1000.)  # lambda = scale * trace(K) / n; plus inf


def projection(width, cfg):
    return np.linalg.qr(np.random.default_rng(cfg['seed']).normal(size=(width, cfg['dim'])))[0]


def features(x, p, arm):
    return x if arm == 'full' else x @ p


def ridge(f, r, lam):
    """Dual ridge W = F^T (F F^T + lam I)^-1 R; returns W and the normal-equation residual."""
    if not np.isfinite(lam):
        return np.zeros((f.shape[1], r.shape[1])), 0.
    k = f @ f.T
    w = f.T @ np.linalg.solve(k + lam * np.eye(len(f)), r)
    # Normal equations of the primal problem: (F^T F + lam I) W = F^T R.
    lhs = f.T @ (f @ w) + lam * w
    rhs = f.T @ r
    return w, float(np.max(np.abs(lhs - rhs)) / max(float(np.max(np.abs(rhs))), 1e-12))


def predict_state(x, a, state):
    p, mean_delta, centre, weight, arm = state['p'], state['mean_delta'], state['centre'], state['weight'], state['arm']
    f = features(x, p, arm)
    pred = x @ p + mean_delta[a]
    for j in range(len(mean_delta)):
        m = a == j
        pred[m] += (f[m] - centre[j]) @ weight[j]
    return pred


def score(x, y, a, pred, p, mean_delta, n_actions):
    """Same quantities and formulas as action_jepa_objective.evaluate, for any prediction."""
    reference = y @ p
    mse = lambda v: float(np.mean((v - reference) ** 2))
    shuffled = np.empty_like(reference)
    for j in range(n_actions):
        m = a == j
        shuffled[m] = np.roll(reference[m], 1, axis=0)
    std0 = float(np.std(reference, axis=0).mean())
    per_action = {}
    for j in range(n_actions):
        m = a == j
        per_action[str(j)] = {
            'prediction_mse': float(np.mean((pred[m] - reference[m]) ** 2)),
            'copy_mse': float(np.mean((x[m] @ p - reference[m]) ** 2)),
            'mean_delta_mse': float(np.mean((x[m] @ p + mean_delta[j] - reference[m]) ** 2)),
            'shuffled_target_mse': float(np.mean((pred[m] - shuffled[m]) ** 2))}
    # The target space is the fixed projection, so the training-space metric equals the fixed one.
    return {'fixed_target_prediction_mse': mse(pred), 'copy_mse': mse(x @ p),
            'mean_delta_mse': mse(x @ p + mean_delta[a]),
            'shuffled_target_mse': float(np.mean((pred - shuffled) ** 2)),
            'ema_training_space_mse': mse(pred),
            'target_std_ratio': float(np.std(reference, axis=0).mean() / max(std0, 1e-12)),
            'target_embedding': collapse_telemetry(reference), 'per_action': per_action}


def fit(x, y, a, masks, n_actions, cfg):
    p = projection(x.shape[1], cfg)
    tr, cal = masks['train'], masks['calibration']
    f = features(x, p, cfg['arm'])
    mean_delta = np.stack([np.mean((y[tr & (a == j)] - x[tr & (a == j)]) @ p, 0) for j in range(n_actions)])
    centre = np.stack([f[tr & (a == j)].mean(0) for j in range(n_actions)])
    weight = np.zeros((n_actions, f.shape[1], cfg['dim']))
    chosen, grid_mse, check = {}, {}, 0.
    for j in range(n_actions):
        mt, mc = tr & (a == j), cal & (a == j)
        ft = f[mt] - centre[j]
        r = (y[mt] - x[mt]) @ p - mean_delta[j]
        unit = float(np.trace(ft @ ft.T)) / len(ft)
        best = None
        grid_mse[str(j)] = {}
        for scale in (*cfg['scales'], float('inf')):
            w, err = ridge(ft, r, scale * unit)
            check = max(check, err)
            pc = (y[mc] - x[mc]) @ p - mean_delta[j] - (f[mc] - centre[j]) @ w
            value = float(np.mean(pc * pc))
            grid_mse[str(j)][str(scale)] = value
            # Ties go to the stronger regularization, inf (the control) last in order wins ties.
            if best is None or value <= best[0]:
                best = (value, scale, w)
        chosen[str(j)] = best[1] if np.isfinite(best[1]) else 'inf'
        weight[j] = best[2]
    base = {'p': p, 'mean_delta': mean_delta, 'centre': centre, 'arm': cfg['arm']}
    return base | {'weight': weight}, base | {'weight': np.zeros_like(weight)}, chosen, grid_mse, check


def train(dataset, out, cfg):
    doc, x, y, a, actions, masks = aj.load_dataset(dataset)
    if cfg['arm'] not in ('full', 'proj') or not 2 <= cfg['dim'] <= x.shape[1] or cfg['retention_max_delta'] != 0:
        raise ValueError('Preregistered arm/dim/retention configuration required')
    n = len(actions)
    state, control, chosen, grid_mse, check = fit(x, y, a, masks, n, cfg)
    repeat = fit(x, y, a, masks, n, cfg)[0]
    parts = [part for part in masks if part != 'train']
    scores = lambda s: {part: score(x[masks[part]], y[masks[part]], a[masks[part]],
                                    predict_state(x[masks[part]], a[masks[part]], s), s['p'], s['mean_delta'], n)
                        for part in parts}
    before, after = scores(control), scores(state)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    metadata = {'schema': OBJECTIVE, 'actions': actions, 'dataset_sha256': aj.digest(dataset),
                'objective_source_sha256': aj.digest(aj.__file__), 'candidate_source_sha256': aj.digest(__file__),
                'bindings': doc['bindings'], 'provenance_kind': doc['provenance_kind'],
                'config': dict(cfg, scales=list(cfg['scales']))}
    checkpoint = out / 'candidate.npz'
    np.savez(checkpoint, projector=state['p'], mean_delta=state['mean_delta'], centre=state['centre'],
             weight=state['weight'], metadata=np.asarray(json.dumps(metadata, sort_keys=True)))
    with np.load(checkpoint, allow_pickle=False) as saved:
        reload_ok = all(np.array_equal(state[k], saved[s]) for k, s in
                        (('p', 'projector'), ('mean_delta', 'mean_delta'), ('centre', 'centre'), ('weight', 'weight')))
    predictive = all(v['prediction_mse'] < .98 * min(v['copy_mse'], v['mean_delta_mse'], v['shuffled_target_mse'])
                     for part, s in after.items() if part != 'retention' for v in s['per_action'].values())
    noncollapse = all(v['target_std_ratio'] >= .75 and v['target_embedding']['effective_rank'] >= min(4, cfg['dim'], int(masks[part].sum()) - 1)
                      for part, v in after.items())
    retention = all(v['prediction_mse'] <= before['retention']['per_action'][j]['prediction_mse'] * (1 + cfg['retention_max_delta']) + 1e-12
                    for j, v in after['retention']['per_action'].items())
    gates = {'normal_equations': check < 1e-8,
             'finite': all(np.isfinite(state[k]).all() for k in ('p', 'mean_delta', 'centre', 'weight')),
             'deterministic': all(np.array_equal(state[k], repeat[k]) for k in ('p', 'mean_delta', 'centre', 'weight')),
             'checkpoint_reload': reload_ok, 'noncollapse': noncollapse,
             'predictive_gain_over_controls': predictive, 'fixed_reference_retention': retention,
             'observed_input_declared': doc['provenance_kind'] != 'test_fixture'}
    report = metadata | {
        'checkpoint_sha256': aj.digest(checkpoint), 'gates': gates, 'candidate_gate_pass': bool(all(gates.values())),
        'chosen_lambda_scale': {actions[int(j)]: v for j, v in chosen.items()},
        'calibration_grid_mse': {actions[int(j)]: v for j, v in grid_mse.items()}, 'selection_partition': 'calibration',
        'normal_equation_max_relative_error': check, 'before_is_mean_delta_control': True,
        'before': before, 'after': after,
        'trainable_parameter_count': int(state['weight'].size),
        'partition_rows': {part: int(m.sum()) for part, m in masks.items()},
        'variance_floor': False, 'ema_target': False, 'noncollapse_note': 'Target is the fixed projection; the noncollapse gate cannot fail by construction.',
        'native_body_parameters_modified': 0, 'target_stop_gradient': True,
        'receiver_authority': 0, 'learn_authority': 0, 'runtime_integrated': False,
        'semantic_quality_proven': False, 'canonical_architecture_complete': False,
        'claim_limit': 'Adjacent closed-form residual candidate only; same scores, controls and gates as action_jepa_objective.py. No native receiver or runtime utility.'}
    (out / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def predict(checkpoint, metrics, states, action):
    """External consumer of the measured checkpoint; output is a hypothesis only."""
    report = json.loads(Path(metrics).read_text())
    if report['checkpoint_sha256'] != aj.digest(checkpoint):
        raise ValueError('Candidate bytes differ from measured checkpoint')
    with np.load(checkpoint, allow_pickle=False) as saved:
        meta = json.loads(str(saved['metadata']))
        if meta['schema'] != OBJECTIVE or action not in meta['actions']:
            raise ValueError('Unknown objective/action')
        x = np.asarray(states, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != saved['projector'].shape[0] or not len(x) or not np.isfinite(x).all():
            raise ValueError('Finite measured-width context states required')
        state = {'p': saved['projector'], 'mean_delta': saved['mean_delta'], 'centre': saved['centre'],
                 'weight': saved['weight'], 'arm': meta['config']['arm']}
        pred = predict_state(x, np.full(len(x), meta['actions'].index(action)), state)
    return {'predicted_future_latents': pred.tolist(), 'action': action,
            'authority': 'LOCAL_PREDICTION_HYPOTHESIS', 'future_observed': False,
            'receiver_injection': False, 'candidate_gate_pass': report['candidate_gate_pass']}


def main():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest='command', required=True)
    use = sub.add_parser('predict')
    for name in ('--checkpoint', '--metrics', '--states', '--action'):
        use.add_argument(name, required=True)
    ap = sub.add_parser('train')
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--arm', choices=('full', 'proj'), required=True)
    ap.add_argument('--dim', type=int, default=16)
    args = root.parse_args()
    if args.command == 'predict':
        states = json.loads(Path(args.states).read_text())
        print(json.dumps(predict(args.checkpoint, args.metrics, states, args.action), allow_nan=False))
        return
    cfg = {'dim': args.dim, 'seed': args.seed, 'arm': args.arm, 'scales': SCALES, 'retention_max_delta': 0.}
    report = train(args.dataset, args.out, cfg)
    print(json.dumps({k: report[k] for k in ('chosen_lambda_scale', 'gates', 'candidate_gate_pass', 'receiver_authority')}))


if __name__ == '__main__':
    main()
