#!/usr/bin/env python3
"""Round-2 action-JEPA candidate: learn only the residual over the mean-delta control.

Identical loss, optimizer, controls and gates as action_jepa_objective.py. The
only change is the starting point: the per-action bias begins at the train
mean delta in the projected space, so the untrained candidate equals the
mean-delta control and every gain must come from learned context dependence.
The number of steps is chosen on the calibration partition only; test and
retention scores of every arm are kept but never used for the choice.
Never activates runtime, learning or receiver authority.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import action_jepa_objective as aj

OBJECTIVE = 'affine-action-jepa-residual-shadow-v1'


def fit(x, y, a, masks, n_actions, cfg):
    p = np.linalg.qr(np.random.default_rng(cfg['seed']).normal(size=(x.shape[1], cfg['dim'])))[0]
    tr = masks['train']
    mean_delta = np.stack([np.mean((y[tr & (a == j)] - x[tr & (a == j)]) @ p, 0) for j in range(n_actions)])
    initial = (p, np.repeat(np.eye(cfg['dim'])[None], n_actions, axis=0), mean_delta.copy(), p.copy())
    err = aj.gradient_check(x[tr], y[tr], a[tr], *initial[:3], initial[3], p)
    candidate, history = aj.optimize(x[tr], y[tr], a[tr], initial, cfg)
    repeat, _ = aj.optimize(x[tr], y[tr], a[tr], initial, cfg)
    no_bias, _ = aj.optimize(x[tr], y[tr], a[tr], initial, cfg, use_bias=False)
    scores = lambda state: {part: aj.evaluate(x[m], y[m], a[m], state, p, mean_delta) for part, m in masks.items() if part != 'train'}
    return {'p': p, 'mean_delta': mean_delta, 'initial': initial, 'candidate': candidate, 'err': err,
            'history': history, 'deterministic': all(np.array_equal(v, w) for v, w in zip(candidate, repeat)),
            'before': scores(initial), 'after': scores(candidate), 'no_bias': scores(no_bias)}


def gates(run, masks, cfg, provenance):
    after, before = run['after'], run['before']
    predictive = all(v['prediction_mse'] < .98 * min(v['copy_mse'], v['mean_delta_mse'], v['shuffled_target_mse'])
                     for part, scores in after.items() if part != 'retention' for v in scores['per_action'].values())
    noncollapse = all(v['target_std_ratio'] >= .75 and v['target_embedding']['effective_rank'] >= min(4, cfg['dim'], int(masks[part].sum()) - 1)
                      for part, v in after.items())
    retention = all(v['prediction_mse'] <= before['retention']['per_action'][j]['prediction_mse'] * (1 + cfg['retention_max_delta']) + 1e-12
                    for j, v in after['retention']['per_action'].items())
    return {'analytic_gradient': run['err'] < 1e-5, 'finite': all(np.isfinite(v).all() for v in run['candidate']),
            'deterministic': run['deterministic'], 'noncollapse': noncollapse,
            'predictive_gain_over_controls': predictive, 'fixed_reference_retention': retention,
            'observed_input_declared': provenance != 'test_fixture'}


def train(dataset, out, base, steps_grid):
    doc, x, y, a, actions, masks = aj.load_dataset(dataset)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    arms = {}
    for steps in steps_grid:
        cfg = dict(base, steps=steps)
        run = fit(x, y, a, masks, len(actions), cfg)
        arms[steps] = (cfg, run)
    # Selection uses calibration only.
    calib = {s: arms[s][1]['after']['calibration']['fixed_target_prediction_mse'] for s in steps_grid}
    chosen = min(steps_grid, key=lambda s: (calib[s], s))
    cfg, run = arms[chosen]
    metadata = {'schema': OBJECTIVE, 'actions': actions, 'dataset_sha256': aj.digest(dataset),
                'objective_source_sha256': aj.digest(aj.__file__), 'candidate_source_sha256': aj.digest(__file__),
                'bindings': doc['bindings'], 'provenance_kind': doc['provenance_kind'], 'config': cfg}
    checkpoint = out / 'candidate.npz'
    c = run['candidate']
    np.savez(checkpoint, projector=c[0], predictor=c[1], bias=c[2], target=c[3], anchor=run['p'],
             metadata=np.asarray(json.dumps(metadata, sort_keys=True)))
    with np.load(checkpoint, allow_pickle=False) as saved:
        reload_ok = all(np.array_equal(v, saved[k]) for v, k in zip(c, ('projector', 'predictor', 'bias', 'target')))
    g = gates(run, masks, cfg, doc['provenance_kind'])
    g['checkpoint_reload'] = reload_ok
    report = metadata | {
        'checkpoint_sha256': aj.digest(checkpoint), 'gates': g, 'candidate_gate_pass': bool(all(g.values())),
        'steps_grid': list(steps_grid), 'calibration_selection_mse': {str(k): v for k, v in calib.items()},
        'chosen_steps': chosen, 'selection_partition': 'calibration',
        'before': run['before'], 'after': run['after'], 'no_bias_ablation': run['no_bias'],
        'unchosen_arms': {str(s): {'gates': gates(r, masks, cf, doc['provenance_kind']), 'after': r['after']}
                          for s, (cf, r) in arms.items() if s != chosen},
        'finite_difference_max_error': run['err'], 'history': run['history'],
        'partition_rows': {part: int(m.sum()) for part, m in masks.items()},
        'native_body_parameters_modified': 0, 'target_stop_gradient': True,
        'receiver_authority': 0, 'learn_authority': 0, 'runtime_integrated': False,
        'semantic_quality_proven': False, 'canonical_architecture_complete': False,
        'claim_limit': 'Adjacent residual candidate only; same gates as action_jepa_objective.py. No native receiver or runtime utility.'}
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
        p, q, b = saved['projector'], saved['predictor'], saved['bias']
        if x.ndim != 2 or x.shape[1] != p.shape[0] or not len(x) or not np.isfinite(x).all():
            raise ValueError('Finite measured-width context states required')
        j = meta['actions'].index(action)
        pred = x @ p @ q[j] + b[j]
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
    ap.add_argument('--steps-grid', default='240,960')
    ap.add_argument('--dim', type=int, default=16)
    ap.add_argument('--lr', type=float, default=.02)
    ap.add_argument('--max-update-norm', type=float, default=.05)
    ap.add_argument('--ema-decay', type=float, default=.99)
    ap.add_argument('--retention-max-delta', type=float, default=0.)
    args = root.parse_args()
    if args.command == 'predict':
        states = json.loads(Path(args.states).read_text())
        print(json.dumps(predict(args.checkpoint, args.metrics, states, args.action), allow_nan=False))
        return
    grid = [int(s) for s in args.steps_grid.split(',')]
    if not grid or any(not 1 <= s <= 5000 for s in grid):
        raise ValueError('Bounded steps grid required')
    base = {'dim': args.dim, 'seed': args.seed, 'lr': args.lr, 'max_update_norm': args.max_update_norm,
            'ema_decay': args.ema_decay, 'retention_max_delta': args.retention_max_delta}
    report = train(args.dataset, args.out, base, grid)
    print(json.dumps({k: report[k] for k in ('chosen_steps', 'gates', 'candidate_gate_pass', 'receiver_authority')}))


if __name__ == '__main__':
    main()
