"""Run67: isolated latent-difference inverse WorldJEPA candidate on real file actions.

Research-only. Frozen v13.world_jepa is never modified, monkeypatched,
registered with Runtime, or granted authority. No model weights persisted.
"""
from __future__ import annotations

import random

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as factor
from scripts import run64_realfile_jepa_factorized_readout as prior
from scripts import z12b_world_jepa as original
from v13 import world_jepa as frozen

SCHEMA = 'v13.z12b.delta_inverse_real_file_jepa.v1'
SEEDS = (271, 277, 281)
N_TRAIN = 240
N_TEST = 60
STEPS = 200
ARM_NAMES = ('original_observed', 'original_zero', 'delta_observed',
             'delta_zero', 'delta_shuffled_train')


def _init_delta_inv(rng, action_dim):
    g = lambda o, i: rng.normal(0, 1/np.sqrt(i), (o, i))
    return {'Q1': g(frozen.HP, frozen.Z),
            'd1': np.zeros(frozen.HP),
            'Q2': g(action_dim, frozen.HP),
            'd2': np.zeros(action_dim)}


def delta_inverse_loss_grads(enc, inv, x, x2, action, *, inv_w=1.):
    """BCE inverse action reconstruction from z(x2)-z(x), with analytic grads."""
    z, h = frozen.encode(enc, x)
    z2, h2 = frozen.encode(enc, x2)
    dz = z2-z
    q = np.tanh(dz @ inv['Q1'].T + inv['d1'])
    logits = q @ inv['Q2'].T + inv['d2']
    # logaddexp is stable; derivative of mean BCE is sigmoid(logits)-target.
    loss = float(inv_w * np.mean(np.logaddexp(0., logits)-action*logits))
    sigmoid = 1/(1+np.exp(-np.clip(logits, -50., 50.)))
    dl = inv_w*(sigmoid-action)/action.size
    gi = {'Q2': dl.T@q, 'd2': dl.sum(0)}
    dq = (dl @ inv['Q2'])*(1-q*q)
    gi['Q1'] = dq.T@dz
    gi['d1'] = dq.sum(0)
    ddz = dq @ inv['Q1']
    d2h = (ddz @ enc['W2'])*(1-h2*h2)
    d1h = (-ddz @ enc['W2'])*(1-h*h)
    ge = {'W2': ddz.T@h2-ddz.T@h,
          'b2': np.zeros(frozen.Z, dtype=float),
          'W1': d2h.T@x2+d1h.T@x,
          'b1': d2h.sum(0)+d1h.sum(0)}
    if not np.isfinite(loss) or not all(np.isfinite(v).all()
                                       for v in (*gi.values(), *ge.values())):
        raise ValueError('RUN67_NONFINITE_DELTA_INVERSE')
    return loss, ge, gi


def _delta_loss_grads(enc, pred, inv, x, a, x2, zt):
    loss, parts, gp, ge = frozen.loss_grads(
        enc, pred, x, a, zt, frozen.VAR_W, frozen.COV_W)
    inv_loss, inv_ge, gi = delta_inverse_loss_grads(
        enc, inv, x, x2, a, inv_w=frozen.INV_W)
    for key in ge:
        ge[key] = ge[key]+inv_ge[key]
    parts['inv'] = inv_loss
    return loss+inv_loss, parts, gp, ge, gi


class DeltaWorldJEPA:
    """Isolated research candidate, not a subclass of production WorldJEPA."""

    def __init__(self, seed):
        if type(seed) is not int or seed < 0:
            raise ValueError('RUN67_INVALID_SEED')
        self.seed = seed

    def fit(self, X, A, X2, *, steps=STEPS, log_every=STEPS):
        if (type(steps) is not int or steps != STEPS
                or type(log_every) is not int or log_every != STEPS):
            raise PermissionError('RUN67_ONLY_PREREGISTERED_TRAINING')
        X, A, X2 = [np.asarray(v, dtype=float) for v in (X, A, X2)]
        if (X.ndim != 2 or X.shape != X2.shape or len(X) < 2
                or X.shape[1] != parent.FEATURES
                or A.shape != (len(X), len(original.OPS)+original.SLOTS)
                or not all(np.isfinite(v).all() for v in (X, A, X2))):
            raise ValueError('RUN67_INVALID_TRANSITIONS')
        rng = np.random.default_rng(self.seed)
        mu, sd = X.mean(0), X.std(0)+1e-3
        x, x2 = (X-mu)/sd, (X2-mu)/sd
        enc, pred = frozen._init(rng, x.shape[1], A.shape[1])
        inv = _init_delta_inv(rng, A.shape[1])
        tgt = {k: v.copy() for k, v in enc.items()}
        params = {**{'e'+k: v for k, v in enc.items()},
                  **{'p'+k: v for k, v in pred.items()},
                  **{'i'+k: v for k, v in inv.items()}}
        opt = frozen.Adam(params, frozen.LR)
        history = []
        for step in range(steps):
            b = rng.integers(0, len(x), min(frozen.BATCH, len(x)))
            zt = frozen.encode(tgt, x2[b])[0]
            loss, parts, gp, ge, gi = _delta_loss_grads(
                enc, pred, inv, x[b], A[b], x2[b], zt)
            opt.step({**{'e'+k: v for k, v in ge.items()},
                      **{'p'+k: v for k, v in gp.items()},
                      **{'i'+k: v for k, v in gi.items()}})
            for k in enc:
                tgt[k] = frozen.TAU*tgt[k]+(1-frozen.TAU)*enc[k]
            if step == 0 or step == steps-1:
                history.append({'step': step, 'loss': float(loss),
                                **{k: float(v) for k, v in parts.items()}})
        if not all(np.isfinite(v).all()
                   for v in (mu, sd, *enc.values(), *pred.values(),
                             *inv.values(), *tgt.values())):
            raise ValueError('RUN67_NONFINITE_TRAINED_STATE')
        self.__dict__.update(mu=mu, sd=sd, enc=enc, pred=pred, inv=inv,
                             tgt=tgt, history=history, _fit_steps=steps)
        return self

    def predict(self, X, A):
        if not hasattr(self, '_fit_steps'):
            raise ValueError('RUN67_UNFITTED')
        X, A = np.asarray(X, dtype=float), np.asarray(A, dtype=float)
        if (X.ndim != 2 or X.shape[1] != len(self.mu)
                or A.shape != (len(X), self.pred['P1'].shape[1]-frozen.Z)
                or not np.isfinite(X).all() or not np.isfinite(A).all()):
            raise ValueError('RUN67_INVALID_INFERENCE')
        z = frozen.encode(self.enc, (X-self.mu)/self.sd)[0]
        zp = frozen.predict(self.pred, z, A)[0]
        return zp, np.zeros(len(X), dtype=float)

    def collapse_stats(self, X2):
        X2 = np.asarray(X2, dtype=float)
        z = frozen.encode(self.tgt, (X2-self.mu)/self.sd)[0]
        eig = np.clip(np.linalg.eigvalsh(np.cov(z.T)), 0., None)
        if eig.sum() <= 0:
            return {'effective_rank': 0., 'min_std': 0.}
        p = eig/eig.sum()
        return {'effective_rank': float(np.exp(-(p[p>0]*np.log(p[p>0])).sum())),
                'min_std': float(z.std(0).min())}


def _fit_readout(model, x, a, x2, xt, at, *, seed):
    model = (model(seed=seed, ensemble=1) if model is frozen.WorldJEPA
             else model(seed=seed))
    model.fit(x, a, x2, steps=STEPS, log_every=STEPS)
    z, _ = model.predict(x, a)
    zt, _ = model.predict(xt, at)
    if (z.shape != (len(x), frozen.Z)
            or zt.shape != (len(xt), frozen.Z)
            or not np.isfinite(z).all() or not np.isfinite(zt).all()):
        raise ValueError('RUN67_INVALID_LATENT_READOUT')
    w = parent._ridge(np.c_[np.ones(len(x)), z], x2)
    predicted = np.c_[np.ones(len(xt)), zt] @ w
    if predicted.shape != xt.shape or not np.isfinite(predicted).all():
        raise ValueError('RUN67_INVALID_OUTCOME')
    return predicted, (model.collapse_stats(x2)
                       if isinstance(model, DeltaWorldJEPA) else None)


def _seed(seed):
    held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
    train = parent._rows(seed, held, N_TRAIN, test=False)
    test = parent._rows(seed, held, N_TEST, test=True)
    if (len(train) != N_TRAIN or len(test) != N_TEST
            or any(a in held for _, a, _, _ in train)
            or any(a not in held for _, a, _, _ in test)
            or len(set(a for _, a, _, _ in test)) < 2):
        raise ValueError('RUN67_SPLIT_CONTAMINATION')
    x = np.stack([r[0] for r in train])
    x2 = np.stack([r[2] for r in train])
    xt = np.stack([r[0] for r in test])
    a, at = prior._factor_actions(train), prior._factor_actions(test)
    perm = np.random.default_rng(seed+500).permutation(len(train))
    arms = {
        'original_observed': (frozen.WorldJEPA, a, at),
        'original_zero': (frozen.WorldJEPA, np.zeros_like(a), np.zeros_like(at)),
        'delta_observed': (DeltaWorldJEPA, a, at),
        'delta_zero': (DeltaWorldJEPA, np.zeros_like(a), np.zeros_like(at)),
        'delta_shuffled_train': (DeltaWorldJEPA, a[perm], at),
    }
    scores, collapse = {}, {}
    for name in ARM_NAMES:
        model, aa, ah = arms[name]
        pred, stats = _fit_readout(model, x, aa, x2, xt, ah, seed=seed)
        scores[name] = prior._metrics(pred, test)
        if stats is not None:
            collapse[name] = stats
    return {
        'seed': seed, 'heldout_action_indices': list(held),
        'n_train': len(train), 'n_holdout': len(test),
        'train_rows_sha256': parent._digest(train),
        'test_rows_sha256': parent._digest(test),
        'shuffled_train_permutation_sha256': prior._perm_sha256(perm),
        'test_action_succeeded_count': sum(bool(r[3]) for r in test),
        'test_action_count': len(set(r[1] for r in test)),
        'metrics': scores, 'delta_train_collapse_stats': collapse,
        'supervised_baseline_metrics': factor._evaluate(train, test),
    }


def run(*, seeds=SEEDS, n_train=N_TRAIN, n_test=N_TEST, steps=STEPS):
    if (type(seeds) is not tuple or seeds != SEEDS
            or type(n_train) is not int or n_train != N_TRAIN
            or type(n_test) is not int or n_test != N_TEST
            or type(steps) is not int or steps != STEPS):
        raise PermissionError('RUN67_ONLY_PREREGISTERED_COHORT')
    reports = [_seed(seed) for seed in seeds]
    def aggregate(key, names):
        return {name: {field: float(np.mean([r[key][name][field] for r in reports]))
                       for field in ('overall_mse', 'target_slot_mse')}
                for name in names}
    return {
        'schema': SCHEMA, 'status': 'DELTA_INVERSE_REAL_FILE_SHADOW_ONLY',
        'source_kind': 'ISOLATED_LINUX_TEMP_FILE_ACTIONS',
        'seeds': list(seeds), 'n_train_per_seed': n_train,
        'n_holdout_per_seed': n_test, 'steps': steps,
        'ridge_lambda': parent.RIDGE, 'action_encoding': 'TWO_HOT_OP_SLOT',
        'reports': reports,
        'aggregate_jepa_readout_metrics': aggregate('metrics', ARM_NAMES),
        'aggregate_supervised_baseline_metrics':
            aggregate('supervised_baseline_metrics', factor.MODEL_NAMES),
        'file_actions_executed': True, 'jepa_training_executed': True,
        'jepa_only_utility_proven': False,
        'native_model_executed': False, 'model_weights_published': False,
        'counterfactual_causality_proven': False,
        'confidence_measured': False, 'source_disjointness_verified': False,
        'phone_measured': False, 'age_authority': 0,
        'learning_gate_pass': False, 'jepa_weight': 0,
        'whole_system_complete': False,
    }
