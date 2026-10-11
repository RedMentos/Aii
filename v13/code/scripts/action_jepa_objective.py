#!/usr/bin/env python3
"""Adjacent WP-T17 affine action-JEPA candidate; never activates runtime rights.

Fits only a projector, per-action predictor and per-action bias. Native body
weights are not opened. Evaluation uses the frozen initial target coordinate
system, so a shrinking/moving EMA target cannot manufacture predictive gain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13.predictor_worker import collapse_telemetry

PARTITIONS = ('train', 'calibration', 'test', 'retention')
SCHEMA = 'v13-action-jepa-dataset-v1'
OBJECTIVE = 'affine-action-jepa-shadow-v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dataset(path):
    """Require immutable source/encoder files and source-disjoint partitions.

    Provenance type is supplied by the exporter: checked bytes bind the dataset
    but do not prove that a native tap or a physical outcome actually happened.
    """
    path = Path(path).resolve()
    doc = json.loads(path.read_text())
    if doc.get('schema') != SCHEMA:
        raise ValueError('Dataset schema mismatch')
    if doc.get('provenance_kind') not in ('native_dense_tap', 'digital_transition', 'test_fixture'):
        raise ValueError('Explicit supported provenance kind required')
    bindings = doc['bindings']
    if not bindings or 'encoder' not in bindings:
        raise ValueError('Encoder and immutable source bindings required')
    for value in bindings.values():
        bound = path.parent / value['path']
        if len(value['sha256']) != 64 or digest(bound) != value['sha256']:
            raise ValueError('Immutable file binding mismatch')
    rows = doc['rows']
    if not rows:
        raise ValueError('No observed pairs')
    seen_ids = set()
    owners = {}
    for row in rows:
        part = row['partition']
        if part not in PARTITIONS or not row['episode_id'] or not row['source_ids']:
            raise ValueError('Named partition, episode and source IDs required')
        if row['row_id'] in seen_ids:
            raise ValueError('Duplicate observed pair')
        seen_ids.add(row['row_id'])
        for source in row['source_ids']:
            if source == 'encoder' or source not in bindings:
                raise ValueError('Observed source file missing')
        # Transitive source reuse is prohibited even through different episode IDs.
        identities = [('episode', row['episode_id'])] + [('source_bytes', bindings[s]['sha256']) for s in row['source_ids']]
        for identity in identities:
            if owners.setdefault(identity, part) != part:
                raise ValueError('Source/episode overlap across partitions')
    x = np.asarray([r['context_state'] for r in rows], dtype=np.float64)
    y = np.asarray([r['future_state'] for r in rows], dtype=np.float64)
    if x.ndim != 2 or x.shape != y.shape or x.shape[1] < 2 or not all(np.isfinite(v).all() for v in (x, y)):
        raise ValueError('Finite same-width observed state pairs required')
    actions = sorted({r['action'] for r in rows})
    if len(actions) < 2 or any(not isinstance(a, str) or not a for a in actions):
        raise ValueError('At least two named actions required')
    a = np.asarray([actions.index(r['action']) for r in rows])
    masks = {p: np.asarray([r['partition'] == p for r in rows]) for p in PARTITIONS}
    for mask in masks.values():
        if any(np.sum(mask & (a == j)) < 2 for j in range(len(actions))):
            raise ValueError('Each action needs two pairs in every partition')
    return doc, x, y, a, actions, masks


def loss_gradient(x, y, a, p, q, bias, target, anchor):
    """Global per-pair mean loss; targets/anchor have no gradient or mutation."""
    z = x @ p
    pred = np.einsum('ni,nij->nj', z, q[a]) + bias[a]
    delta = pred - y @ target
    dpred = 2 * delta / delta.size
    gq = np.zeros_like(q)
    gb = np.zeros_like(bias)
    for j in range(len(q)):
        m = a == j
        gq[j] = z[m].T @ dpred[m]
        gb[j] = dpred[m].sum(0)
    dz = np.einsum('nj,nij->ni', dpred, q[a])
    centred = z - z.mean(0)
    std = np.sqrt(np.mean(centred * centred, 0) + 1e-4)
    short = np.maximum(.25 - std, 0)
    dz += .1 * (-2 * short / std / z.size) * centred
    gp = x.T @ dz + .02 * (p - anchor) / p.size
    loss = np.mean(delta * delta) + .1 * np.mean(short * short) + .01 * np.mean((p - anchor) ** 2)
    return float(loss), gp, gq, gb


def gradient_check(x, y, a, p, q, bias, target, anchor):
    _, gp, gq, gb = loss_gradient(x, y, a, p, q, bias, target, anchor)
    params = (p, q, bias)
    errors = []
    for j, (param, grad) in enumerate(zip(params, (gp, gq, gb))):
        for flat in np.argsort(np.abs(grad).ravel())[-8:]:
            index = np.unravel_index(flat, param.shape)
            plus = param.copy()
            minus = param.copy()
            plus[index] += 1e-5
            minus[index] -= 1e-5
            left, right = list(params), list(params)
            left[j], right[j] = plus, minus
            hi = loss_gradient(x, y, a, *left, target, anchor)[0]
            lo = loss_gradient(x, y, a, *right, target, anchor)[0]
            errors.append(abs((hi - lo) / 2e-5 - grad[index]))
    return float(max(errors))


def optimize(x, y, a, initial, cfg, use_bias=True):
    p, q, bias, target = [v.copy() for v in initial]
    anchor = initial[0]
    history = []
    for step in range(cfg['steps']):
        loss, gp, gq, gb = loss_gradient(x, y, a, p, q, bias, target, anchor)
        if not use_bias:
            gb[:] = 0
        updates = [-cfg['lr'] * g for g in (gp, gq, gb)]
        norm = np.sqrt(sum(np.sum(u * u) for u in updates))
        scale = min(1., cfg['max_update_norm'] / max(float(norm), 1e-12))
        p += updates[0] * scale
        q += updates[1] * scale
        bias += updates[2] * scale
        target = cfg['ema_decay'] * target + (1 - cfg['ema_decay']) * p
        if step % 32 == 0 or step == cfg['steps'] - 1:
            history.append({'step': step, 'loss': loss, 'applied_norm': float(norm * scale)})
    return (p, q, bias, target), history


def evaluate(x, y, a, state, anchor, mean_delta):
    p, q, bias, target = state
    pred = np.einsum('ni,nij->nj', x @ p, q[a]) + bias[a]
    reference = y @ anchor
    # Every arm scores in one fixed space; training's EMA MSE is diagnostic only.
    mse = lambda v: float(np.mean((v - reference) ** 2))
    shuffled = np.empty_like(reference)
    for j in range(len(q)):
        m = a == j
        shuffled[m] = np.roll(reference[m], 1, axis=0)
    std0 = float(np.std(reference, axis=0).mean())
    per_action = {}
    for j in range(len(q)):
        m = a == j
        per_action[str(j)] = {
            'prediction_mse': float(np.mean((pred[m] - reference[m]) ** 2)),
            'copy_mse': float(np.mean((x[m] @ anchor - reference[m]) ** 2)),
            'mean_delta_mse': float(np.mean((x[m] @ anchor + mean_delta[j] - reference[m]) ** 2)),
            'shuffled_target_mse': float(np.mean((pred[m] - shuffled[m]) ** 2))}
    return {'fixed_target_prediction_mse': mse(pred),
            'copy_mse': mse(x @ anchor),
            'mean_delta_mse': mse(x @ anchor + mean_delta[a]),
            'shuffled_target_mse': float(np.mean((pred - shuffled) ** 2)),
            'ema_training_space_mse': float(np.mean((pred - y @ target) ** 2)),
            'target_std_ratio': float(np.std(y @ target, axis=0).mean() / max(std0, 1e-12)),
            'target_embedding': collapse_telemetry(y @ target), 'per_action': per_action}


def train(dataset, out, cfg):
    doc, x, y, a, actions, masks = load_dataset(dataset)
    if (type(cfg['steps']) is not int or not 1 <= cfg['steps'] <= 5000 or
            not 0 < cfg['lr'] <= 1 or not 0 < cfg['max_update_norm'] <= 1 or
            not 0 <= cfg['ema_decay'] < 1 or not 2 <= cfg['dim'] <= x.shape[1] or
            not 0 <= cfg['retention_max_delta'] <= .1):
        raise ValueError('Bounded optimizer/EMA/retention configuration required')
    p = np.linalg.qr(np.random.default_rng(cfg['seed']).normal(size=(x.shape[1], cfg['dim'])))[0]
    initial = (p, np.repeat(np.eye(cfg['dim'])[None], len(actions), axis=0),
               np.zeros((len(actions), cfg['dim'])), p.copy())
    tr = masks['train']
    mean_delta = np.stack([np.mean((y[tr & (a == j)] - x[tr & (a == j)]) @ p, 0) for j in range(len(actions))])
    err = gradient_check(x[tr], y[tr], a[tr], *initial[:3], initial[3], p)
    candidate, history = optimize(x[tr], y[tr], a[tr], initial, cfg)
    repeat, _ = optimize(x[tr], y[tr], a[tr], initial, cfg)
    no_bias, _ = optimize(x[tr], y[tr], a[tr], initial, cfg, use_bias=False)
    finite = all(np.isfinite(v).all() for v in candidate)
    deterministic = all(np.array_equal(v, w) for v, w in zip(candidate, repeat))
    before = {part: evaluate(x[m], y[m], a[m], initial, p, mean_delta) for part, m in masks.items() if part != 'train'}
    after = {part: evaluate(x[m], y[m], a[m], candidate, p, mean_delta) for part, m in masks.items() if part != 'train'}
    ablation = {part: evaluate(x[m], y[m], a[m], no_bias, p, mean_delta) for part, m in masks.items() if part != 'train'}
    predictive = all(v['prediction_mse'] < .98 * min(v['copy_mse'], v['mean_delta_mse'], v['shuffled_target_mse'])
                     for part, scores in after.items() if part != 'retention' for v in scores['per_action'].values())
    noncollapse = all(v['target_std_ratio'] >= .75 and v['target_embedding']['effective_rank'] >= min(4, cfg['dim'], int(masks[part].sum()) - 1) for part, v in after.items())
    retention = all(v['prediction_mse'] <= before['retention']['per_action'][j]['prediction_mse'] * (1 + cfg['retention_max_delta']) + 1e-12
                    for j, v in after['retention']['per_action'].items())
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    metadata = {'schema': OBJECTIVE, 'actions': actions, 'dataset_sha256': digest(dataset),
                'objective_source_sha256': digest(__file__), 'bindings': doc['bindings'],
                'provenance_kind': doc['provenance_kind'], 'config': cfg}
    checkpoint = out / 'candidate.npz'
    np.savez(checkpoint, projector=candidate[0], predictor=candidate[1], bias=candidate[2],
             target=candidate[3], anchor=p, metadata=np.asarray(json.dumps(metadata, sort_keys=True)))
    with np.load(checkpoint, allow_pickle=False) as saved:
        reload_ok = all(np.array_equal(v, saved[name]) for v, name in zip(candidate, ('projector', 'predictor', 'bias', 'target')))
    gates = {'analytic_gradient': err < 1e-5, 'finite': finite, 'deterministic': deterministic,
             'checkpoint_reload': reload_ok, 'noncollapse': noncollapse,
             'predictive_gain_over_controls': predictive, 'fixed_reference_retention': retention,
             'observed_input_declared': doc['provenance_kind'] != 'test_fixture'}
    report = metadata | {'checkpoint_sha256': digest(checkpoint), 'gates': gates,
                         'candidate_gate_pass': bool(all(gates.values())), 'before': before, 'after': after,
                         'no_bias_ablation': ablation, 'finite_difference_max_error': err, 'history': history,
                         'trainable_parameter_count': int(sum(v.size for v in candidate[:3])),
                         'partition_rows': {part: int(m.sum()) for part, m in masks.items()},
                         'native_body_parameters_modified': 0, 'target_stop_gradient': True,
                         'receiver_authority': 0, 'learn_authority': 0, 'runtime_integrated': False,
                         'semantic_quality_proven': False, 'canonical_architecture_complete': False,
                         'claim_limit': 'Adjacent affine candidate only. File hashes verify supplied bytes; provenance remains exporter-declared. Fixed digital/native cohort gates do not prove general semantic/world dynamics or native receiver utility.'}
    (out / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def predict(checkpoint, metrics, states, action):
    """Actual external candidate consumer; output is a prediction hypothesis."""
    report = json.loads(Path(metrics).read_text())
    if report['checkpoint_sha256'] != digest(checkpoint):
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
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    fit = sub.add_parser('train')
    fit.add_argument('--dataset', required=True)
    fit.add_argument('--out', required=True)
    fit.add_argument('--steps', type=int, default=240)
    fit.add_argument('--dim', type=int, default=16)
    fit.add_argument('--seed', type=int, default=13)
    fit.add_argument('--lr', type=float, default=.02)
    fit.add_argument('--max-update-norm', type=float, default=.05)
    fit.add_argument('--ema-decay', type=float, default=.99)
    fit.add_argument('--retention-max-delta', type=float, default=0.)
    use = sub.add_parser('predict')
    use.add_argument('--checkpoint', required=True)
    use.add_argument('--metrics', required=True)
    use.add_argument('--states', required=True, help='JSON file containing a 2D array')
    use.add_argument('--action', required=True)
    args = ap.parse_args()
    if args.command == 'train':
        cfg = {k: getattr(args, k) for k in ('steps', 'dim', 'seed', 'lr', 'max_update_norm', 'ema_decay', 'retention_max_delta')}
        report = train(args.dataset, args.out, cfg)
        print(json.dumps({k: report[k] for k in ('gates', 'candidate_gate_pass', 'receiver_authority')}))
    else:
        print(json.dumps(predict(args.checkpoint, args.metrics, json.loads(Path(args.states).read_text()), args.action), allow_nan=False))


if __name__ == '__main__':
    main()
