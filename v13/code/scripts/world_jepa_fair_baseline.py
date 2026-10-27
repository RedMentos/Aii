"""Research-only fair direct-vs-World-JEPA readout with train-only scaling.

No runtime hook, private data, weight persistence, Age authority or utility claim.
The original incremental probe and its registered cohorts remain untouched.
"""
import numpy as np

from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_incremental_probe as original
from v13 import world_jepa as wj

SEEDS = original.SEEDS
STEPS = original.STEPS
ENSEMBLE = original.ENSEMBLE
LAMBDA = original.LAMBDA
PROJECTION_SEED = original.PROJECTION_SEED


def _scaled_direct(train, heldout):
    """Keep the intercept fixed at 1; fit all other scaling on TRAIN only."""
    train = np.asarray(train, dtype=np.float64)
    heldout = np.asarray(heldout, dtype=np.float64)
    if (train.ndim != 2 or heldout.ndim != 2 or train.shape[1] != heldout.shape[1]
            or train.shape[1] < 2 or len(train) < 2
            or not np.isfinite(train).all() or not np.isfinite(heldout).all()
            or not np.all(train[:, 0] == 1.) or not np.all(heldout[:, 0] == 1.)):
        raise ValueError('Invalid direct readout features')
    center = train[:, 1:].mean(0)
    scale = train[:, 1:].std(0) + 1e-3
    if not np.isfinite(center).all() or not np.isfinite(scale).all():
        raise ValueError('Nonfinite train-only direct scaler')
    dtr = np.c_[np.ones(len(train)), (train[:, 1:] - center) / scale]
    dte = np.c_[np.ones(len(heldout)), (heldout[:, 1:] - center) / scale]
    if not np.isfinite(dtr).all() or not np.isfinite(dte).all():
        raise ValueError('Nonfinite scaled direct features')
    return dtr, dte


def _score(dtr, dte, ztr, zte, ytr, yte):
    ztr, zte = original._standardize_train_only(ztr, zte)
    w = bridge._ridge(np.c_[dtr, ztr], ytr, LAMBDA)
    return bridge._mae(np.c_[dte, zte] @ w, yte)


def run_rows(rows, steps=STEPS):
    if type(steps) is not int or not 0 <= steps <= STEPS:
        raise ValueError('Invalid preregistered step count')
    data = bridge.make_dataset(rows)
    tr, te = data['train'], data['heldout']
    X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
    direct = np.c_[np.ones(len(X)), X[:, :4], A]
    dtr, dte = _scaled_direct(direct[tr], direct[te])
    direct_w = bridge._ridge(dtr, Y[tr], LAMBDA)
    direct_mae = bridge._mae(dte @ direct_w, Y[te])
    arms = []
    for seed in SEEDS:
        model = wj.WorldJEPA(seed=seed, ensemble=ENSEMBLE).fit(
            X[tr], A[tr], X2[tr], steps=steps)
        ztr, _ = model.predict(X[tr], A[tr])
        zte, _ = model.predict(X[te], A[te])
        augmented = _score(dtr, dte, ztr, zte, Y[tr], Y[te])
        wrong = np.roll(A, 1, axis=1)
        zwtr, _ = model.predict(X[tr], wrong[tr])
        zwte, _ = model.predict(X[te], wrong[te])
        wrong_mae = _score(dtr, dte, zwtr, zwte, Y[tr], Y[te])
        rng = np.random.default_rng(PROJECTION_SEED + seed)
        projection = rng.normal(size=(dtr.shape[1], wj.Z)) / np.sqrt(dtr.shape[1])
        random_mae = _score(dtr, dte, dtr @ projection, dte @ projection, Y[tr], Y[te])
        arms.append({
            'seed': seed,
            'augmented_mae': augmented,
            'wrong_action_augmented_mae': wrong_mae,
            'direct_projection_augmented_mae': random_mae,
            'gain_vs_scaled_direct': float(direct_mae['pooled'] - augmented['pooled']),
            'gain_vs_wrong_action': float(wrong_mae['pooled'] - augmented['pooled']),
            'gain_vs_projection': float(random_mae['pooled'] - augmented['pooled']),
        })
    return {
        'scope': 'WORLD_JEPA_FAIR_SCALED_DIRECT_RESEARCH_ONLY',
        'evidence_level': 'SYNTHETIC_DIGITAL_OUTCOME_NOT_REAL_WORLD_UTILITY',
        'source_sha256': data['source_sha256'],
        'train_ids_sha256': data['train_ids_sha256'],
        'heldout_ids_sha256': data['heldout_ids_sha256'],
        'n': len(rows), 'train_n': len(tr), 'heldout_n': len(te),
        'model_revision': wj.REVISION, 'seeds': list(SEEDS),
        'steps': steps, 'ensemble': ENSEMBLE, 'ridge_lambda': LAMBDA,
        'scaled_direct_ridge_mae': direct_mae, 'per_seed': arms,
        'runtime_wired': False, 'model_weights_persisted': False,
        'utility_proven': False, 'age_authority': 0,
        'negative_gates_unchanged': bridge.NEGATIVE_GATES,
    }
