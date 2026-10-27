"""Preregistered synthetic World-JEPA support, OOD and calibration audit.

Review-only: does not modify runtime, weights, permissions, or canonical gates.
See docs/proofs/continuation-20261027/world-jepa-support-calibration/PREREG.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
from scripts import world_jepa_heldout_ablation as source
from v13 import world_jepa as wj

SEEN_ACTIONS = (0, 1, 2)
WITHHELD_ACTION = 3
TRAIN_SEEN_N = 761
TEST_SEEN_N = 193
TEST_WITHHELD_N = 47
TRAIN_SEEN_SHA = '8a70c57a6f2b5b4dc10fe033abea3a89335b0fc8023f14cbdeb3ae5f75ea82ee'
TEST_SEEN_SHA = '2d8ebecb798da993df692ad8e38e362b248e9b81cdff0645a05545bc8d69618f'
TEST_WITHHELD_SHA = '95eaaafc88454ff59fbab90f3f7a9daf0d3aec5b455246ab8c316a9f8e303e0b'
MODEL_SEEDS = (3, 7, 11)
STEPS = 1000
ENSEMBLE = 3
OOD_NOISE_OFFSET = 8.
BIN_EDGES = (0., .2, .4, .6, .8, 1.)
NEGATIVE_GATES = dict(source.NEGATIVE_GATES)


def verified_cohorts():
    train = source.make_rows(source.TRAIN_N, source.TRAIN_SEED)
    heldout = source.make_rows(source.TEST_N, source.TEST_SEED)
    source.verify_rows(train, source.TRAIN_N, source.TRAIN_SHA)
    source.verify_rows(heldout, source.TEST_N, source.TEST_SHA)
    train_seen = [r for r in train if r['action'] in SEEN_ACTIONS]
    test_seen = [r for r in heldout if r['action'] in SEEN_ACTIONS]
    test_withheld = [r for r in heldout if r['action'] == WITHHELD_ACTION]
    for rows, size, digest in (
        (train_seen, TRAIN_SEEN_N, TRAIN_SEEN_SHA),
        (test_seen, TEST_SEEN_N, TEST_SEEN_SHA),
        (test_withheld, TEST_WITHHELD_N, TEST_WITHHELD_SHA),
    ):
        source.verify_rows(rows, size, digest)
    if len(train_seen) + sum(r['action'] == WITHHELD_ACTION for r in train) != len(train):
        raise ValueError('Invalid training action partition')
    if len(test_seen) + len(test_withheld) != len(heldout):
        raise ValueError('Invalid heldout action partition')
    canon = lambda rows: {json.dumps(r, sort_keys=True, separators=(',', ':')) for r in rows}
    if canon(train) & canon(heldout):
        raise ValueError('Training and heldout source overlap')
    return train_seen, test_seen, test_withheld


def _rank(x):
    """Average ranks for ties; deterministic and SciPy-independent."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError('Invalid rank inputs')
    order = np.argsort(x, kind='mergesort')
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i + 1
        while j < len(x) and x[order[j]] == x[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + j - 1) / 2.
        i = j
    return ranks


def spearman_confidence_vs_negative_error(conf, error):
    if len(conf) != len(error) or len(conf) < 2:
        raise ValueError('Invalid correlation cohort')
    x, y = _rank(conf), _rank(-np.asarray(error))
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    r = float(np.corrcoef(x, y)[0, 1])
    if not np.isfinite(r):
        raise ValueError('Nonfinite rank correlation')
    return r


def calibration_bins(conf, error, threshold):
    conf = np.asarray(conf, dtype=float)
    error = np.asarray(error, dtype=float)
    if (conf.ndim != 1 or error.shape != conf.shape or len(conf) == 0
            or not np.isfinite(conf).all() or not np.isfinite(error).all()
            or (conf < 0).any() or (conf > 1).any() or (error < 0).any()
            or not np.isfinite(threshold) or threshold < 0):
        raise ValueError('Invalid calibration inputs')
    success = error <= threshold
    bins = np.minimum((conf * 5).astype(int), 4)
    rows, ece = [], 0.
    for i in range(5):
        selected = bins == i
        n = int(selected.sum())
        mean_conf = float(conf[selected].mean()) if n else None
        success_rate = float(success[selected].mean()) if n else None
        if n:
            ece += n / len(conf) * abs(mean_conf - success_rate)
        rows.append({'lo': BIN_EDGES[i], 'hi': BIN_EDGES[i+1],
                     'n': n, 'mean_confidence': mean_conf, 'success_rate': success_rate})
    return {'bins': rows, 'diagnostic_ece_proxy': float(ece),
            'heldout_success_fraction': float(success.mean()),
            'success': success.tolist()}


def _checked_score(model, X, A, X2):
    X = np.asarray(X, dtype=float)
    A = np.asarray(A, dtype=float)
    X2 = np.asarray(X2, dtype=float)
    if (X.ndim != 2 or X.shape[1] != 8 or X2.shape != X.shape
            or A.shape != (len(X), 4) or len(X) == 0
            or not np.isfinite(X).all() or not np.isfinite(A).all()
            or not np.isfinite(X2).all() or not np.all((A == 0) | (A == 1))
            or not np.all(A.sum(1) == 1)):
        raise ValueError('Invalid score cohort')
    mean, spread = model.predict(X, A)
    target = model.latent(X2, target=True)
    scale = np.asarray(model.zsd)
    if (mean.shape != target.shape or mean.shape[0] != len(X)
            or scale.shape != (mean.shape[1],) or spread.shape != (len(X),)
            or not np.isfinite(mean).all() or not np.isfinite(target).all()
            or not np.isfinite(scale).all() or (scale <= 0).any()
            or not np.isfinite(spread).all() or (spread < 0).any()):
        raise ValueError('Invalid prediction/target/scale')
    error = np.mean(((mean-target)/scale)**2, axis=1)
    conf, labels = model.confidence(X, A, counts=None)
    conf = np.asarray(conf)
    if (conf.shape != (len(X),) or not np.isfinite(conf).all()
            or (conf < 0).any() or (conf > 1).any()
            or len(labels) != len(X)
            or any(label not in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN') for label in labels)
            or not np.isfinite(error).all() or (error < 0).any()):
        raise ValueError('Invalid confidence or error evidence')
    return error, conf, labels


def score_seed(model, train_rows, seen_rows, withheld_rows, seed):
    if seed not in MODEL_SEEDS:
        raise ValueError('Unregistered model seed')
    Xt, At, X2t, actt = source.arrays(train_rows)
    Xs, As, X2s, acts = source.arrays(seen_rows)
    Xu, Au, X2u, actu = source.arrays(withheld_rows)
    if (len(Xt) != TRAIN_SEEN_N or len(Xs) != TEST_SEEN_N or len(Xu) != TEST_WITHHELD_N
            or np.any(actt == WITHHELD_ACTION) or np.any(acts == WITHHELD_ACTION)
            or np.any(actu != WITHHELD_ACTION)):
        raise ValueError('Invalid action-support split')
    train_error, _, _ = _checked_score(model, Xt, At, X2t)
    threshold = float(np.quantile(train_error, .75))
    seen_error, seen_conf, seen_labels = _checked_score(model, Xs, As, X2s)
    unseen_error, unseen_conf, unseen_labels = _checked_score(model, Xu, Au, X2u)
    Xood = Xs.copy()
    Xood[:, 4:8] += OOD_NOISE_OFFSET
    ood_conf, ood_labels = model.confidence(Xood, As, counts=None)
    ood_dist = model.ood(Xood)
    ood_conf, ood_dist = np.asarray(ood_conf), np.asarray(ood_dist)
    if (ood_conf.shape != seen_conf.shape or ood_dist.shape != seen_conf.shape
            or not np.isfinite(ood_conf).all() or not np.isfinite(ood_dist).all()
            or (ood_conf < 0).any() or (ood_conf > 1).any() or (ood_dist < 0).any()
            or len(ood_labels) != len(seen_conf)
            or any(x not in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN') for x in ood_labels)):
        raise ValueError('Invalid OOD confidence evidence')
    cal = calibration_bins(seen_conf, seen_error, threshold)
    novel_ok = bool(np.all(unseen_conf == 0) and
                    all(x == 'SIMULATION_UNCERTAIN' for x in unseen_labels))
    median_seen = float(np.median(seen_conf))
    median_ood = float(np.median(ood_conf))
    ood_ok = bool(median_ood <= .5 * median_seen)
    return {
        'seed': seed, 'train_error_q75_threshold': threshold,
        'seen_mse': float(seen_error.mean()), 'withheld_mse': float(unseen_error.mean()),
        'seen_confidence_median': median_seen, 'ood_confidence_median': median_ood,
        'ood_distance_median': float(np.median(ood_dist)),
        'ood_uncertain_fraction': float(sum(x == 'SIMULATION_UNCERTAIN' for x in ood_labels)/len(ood_labels)),
        'withheld_action_zero_confidence': 'PASS' if novel_ok else 'FAIL',
        'state_ood_half_confidence': 'PASS' if ood_ok else 'FAIL',
        'spearman_confidence_vs_negative_error': spearman_confidence_vs_negative_error(seen_conf, seen_error),
        'calibration': {k: v for k, v in cal.items() if k != 'success'},
        'seen_rows': [
            {'error': float(e), 'confidence': float(c), 'label': lab,
             'success': bool(s), 'ood_confidence': float(oc)}
            for e, c, lab, s, oc in zip(seen_error, seen_conf, seen_labels,
                                         cal['success'], ood_conf)],
        'withheld_rows': [
            {'error': float(e), 'confidence': float(c), 'label': lab}
            for e, c, lab in zip(unseen_error, unseen_conf, unseen_labels)]
    }


def summarize(per_seed):
    if [r['seed'] for r in per_seed] != list(MODEL_SEEDS):
        raise ValueError('Incomplete or reordered registered seeds')
    return {
        'withheld_action_gate': 'PASS' if all(
            r['withheld_action_zero_confidence'] == 'PASS' for r in per_seed) else 'FAIL',
        'state_ood_gate': 'PASS' if all(
            r['state_ood_half_confidence'] == 'PASS' for r in per_seed) else 'FAIL',
        'no_runtime_or_age_promotion': True
    }


def run():
    train, seen, withheld = verified_cohorts()
    X, A, X2, _ = source.arrays(train)
    results = []
    for seed in MODEL_SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(X, A, X2, steps=STEPS)
        results.append(score_seed(model, train, seen, withheld, seed))
    return {
        'scope': 'SYNTHETIC_WORLD_JEPA_SUPPORT_CALIBRATION_ONLY',
        'world_revision': wj.REVISION, 'numpy': np.__version__,
        'source': {'train_full_sha256': source.TRAIN_SHA, 'heldout_full_sha256': source.TEST_SHA,
                   'train_seen_sha256': TRAIN_SEEN_SHA, 'test_seen_sha256': TEST_SEEN_SHA,
                   'test_withheld_sha256': TEST_WITHHELD_SHA,
                   'train_seen_n': TRAIN_SEEN_N, 'test_seen_n': TEST_SEEN_N,
                   'test_withheld_n': TEST_WITHHELD_N,
                   'model_seeds': list(MODEL_SEEDS), 'steps': STEPS, 'ensemble': ENSEMBLE,
                   'ood_noise_offset': OOD_NOISE_OFFSET},
        'per_seed': results, **summarize(results),
        'negative_gates_unchanged': NEGATIVE_GATES
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    if not args.run:
        raise ValueError('Explicit --run required')
    report = run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=out.parent,
                                     prefix='.world-support-', delete=False) as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
        name = f.name
    os.replace(name, out)
    dfd = os.open(out.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
    print(json.dumps({'withheld_action_gate': report['withheld_action_gate'],
                      'state_ood_gate': report['state_ood_gate'],
                      'seeds': list(MODEL_SEEDS), 'out': str(out)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
