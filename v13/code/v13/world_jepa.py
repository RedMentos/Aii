"""WP-Z12b §29 Nr. 13 / §7.2: small action-grounded World-JEPA in NumPy (phone-capable, SHADOW, not wired into the runtime).

  online encoder   z  = W2 tanh(W1 x + b1) + b2                       (x standardized with training mean/std)
  predictor        z' = z + P2 tanh(P1 [z, a] + c1) + c2              (a = action one-hot; residual)
  target encoder   EMA copy of the online encoder (tau), stop-gradient
  loss             mean (z' - target(x'))^2 + VAR_W * mean relu(1 - std_j(z)) + COV_W * sum offdiag cov(z)^2 / Z
                   + INV_W * inverse-dynamics cross-entropy (action from [z(x), z(x')], §7.2.1): without it the latent
                   kept the slots no action touches and dropped the one an action changed (Z12b dev seed 7)

Only the latent of the next observation is predicted, never the observation itself, so details that no action decides
(random words in a file) can be left out of the latent. Ensemble: extra predictors on bootstrap samples with the encoder
frozen; their spread plus the training count of the action and the state's distance to training states give the
counterfactual confidence (same shape as world_model.py §7.2.2). Below CF_MIN a counterfactual is SIMULATION_UNCERTAIN.
"""
import numpy as np

REVISION = 'z12b-world-jepa-v1'
H = 64; Z = 16; HP = 64
LR = 2e-3; TAU = .99; VAR_W = 1.; COV_W = .04; INV_W = 1.; BATCH = 256
COVER_N = 8.       # BOOT: samples per action for ~63 % of the coverage term (as world_model.py)
SPREAD_REF = .25   # BOOT: ensemble spread (in target-latent std units) that halves confidence
OOD_SUPPORT = 2.   # BOOT: nearest-neighbour distance (median-NN units) still inside the training support
CF_MIN = .5        # BOOT: below this a counterfactual is SIMULATION_UNCERTAIN


class Adam:
    def __init__(self, params, lr):
        self.p = params; self.lr = lr; self.t = 0
        self.m = {k: np.zeros_like(v) for k, v in params.items()}; self.v = {k: np.zeros_like(v) for k, v in params.items()}

    def step(self, grads):
        self.t += 1
        for k, g in grads.items():
            self.m[k] = .9*self.m[k]+.1*g; self.v[k] = .999*self.v[k]+.001*g*g
            mh = self.m[k]/(1-.9**self.t); vh = self.v[k]/(1-.999**self.t)
            self.p[k] -= self.lr*mh/(np.sqrt(vh)+1e-8)


def _init(rng, d, a):
    g = lambda o, i: rng.normal(0, 1/np.sqrt(i), (o, i))
    enc = {'W1': g(H, d), 'b1': np.zeros(H), 'W2': g(Z, H), 'b2': np.zeros(Z)}
    return enc, _init_pred(rng, a)


def _init_pred(rng, a):
    g = lambda o, i: rng.normal(0, 1/np.sqrt(i), (o, i))
    return {'P1': g(HP, Z+a), 'c1': np.zeros(HP), 'P2': g(Z, HP)*.1, 'c2': np.zeros(Z)}


def encode(enc, x):
    h = np.tanh(x@enc['W1'].T+enc['b1']); return h@enc['W2'].T+enc['b2'], h


def predict(pred, z, a):
    u = np.concatenate([z, a], 1); hp = np.tanh(u@pred['P1'].T+pred['c1']); return z+hp@pred['P2'].T+pred['c2'], (u, hp)


def _init_inv(rng, a):
    g = lambda o, i: rng.normal(0, 1/np.sqrt(i), (o, i))
    return {'Q1': g(HP, 2*Z), 'd1': np.zeros(HP), 'Q2': g(a, HP), 'd2': np.zeros(a)}


def loss_grads(enc, pred, x, a, zt, var_w=VAR_W, cov_w=COV_W, train_enc=True, inv=None, x2=None, inv_w=0.):
    """Loss and gradients for one batch; zt = target latents of the next observations (stop-gradient).
    With inv (and x2): inverse-dynamics head, sigmoid cross-entropy of the action vector from [z, online z(x2)] (§7.2.1)."""
    n = len(x); z, h = encode(enc, x); zp, (u, hp) = predict(pred, z, a)
    diff = zp-zt; lp = float((diff**2).mean())
    dzp = 2*diff/diff.size
    gp = {'P2': dzp.T@hp, 'c2': dzp.sum(0)}
    dpre = (dzp@pred['P2'])*(1-hp**2); gp['P1'] = dpre.T@u; gp['c1'] = dpre.sum(0)
    dz = (dpre@pred['P1'])[:, :Z]+dzp
    mu = z.mean(0); zc = z-mu; std = np.sqrt((zc**2).mean(0)+1e-4)
    lv = float(np.maximum(0, 1-std).mean()); C = zc.T@zc/(n-1); off = C-np.diag(np.diag(C)); lc = float((off**2).sum()/Z)
    loss = lp+var_w*lv+cov_w*lc; parts = {'pred': lp, 'var': lv, 'cov': lc}
    if not train_enc: return loss, parts, gp, None
    dzc = -var_w/Z*(std < 1)*zc/(n*std)+cov_w*4/(Z*(n-1))*zc@off
    dz = dz+dzc-dzc.mean(0)
    ge = {'W2': dz.T@h, 'b2': dz.sum(0)}
    dh = (dz@enc['W2'])*(1-h**2); ge['W1'] = dh.T@x; ge['b1'] = dh.sum(0)
    if inv is not None and inv_w > 0:
        z2, h2 = encode(enc, x2); v = np.concatenate([z, z2], 1); hq = np.tanh(v@inv['Q1'].T+inv['d1'])
        lg = hq@inv['Q2'].T+inv['d2']; pr = 1/(1+np.exp(-lg))
        li = float(-(a*np.log(pr+1e-9)+(1-a)*np.log(1-pr+1e-9)).mean()); loss += inv_w*li; parts['inv'] = li
        dl = inv_w*(pr-a)/a.size; gi = {'Q2': dl.T@hq, 'd2': dl.sum(0)}
        dq = (dl@inv['Q2'])*(1-hq**2); gi['Q1'] = dq.T@v; gi['d1'] = dq.sum(0); dv = dq@inv['Q1']
        for zz, hh, xx, dd in ((z, h, x, dv[:, :Z]), (z2, h2, x2, dv[:, Z:])):
            ge['W2'] += dd.T@hh; ge['b2'] += dd.sum(0); dh = (dd@enc['W2'])*(1-hh**2); ge['W1'] += dh.T@xx; ge['b1'] += dh.sum(0)
        return loss, parts, gp, ge, gi
    return loss, parts, gp, ge


def _validate_fit_arrays(X, A, X2, steps, log_every, ensemble):
    """Reject invalid transition evidence before allocating an optimizer."""
    if (type(steps) is not int or steps < 1 or type(log_every) is not int
            or log_every < 1 or type(ensemble) is not int or ensemble < 1):
        raise ValueError('World-JEPA requires positive steps, log interval and ensemble')
    try:
        X = np.asarray(X, dtype=float)
        A = np.asarray(A, dtype=float)
        X2 = np.asarray(X2, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('World-JEPA transitions must be numeric') from exc
    if (X.ndim != 2 or A.ndim != 2 or X2.ndim != 2 or len(X) < 2
            or X.shape != X2.shape or X.shape[1] < 1
            or A.shape[0] != len(X) or A.shape[1] < 1):
        raise ValueError('World-JEPA transition shapes or sample count invalid')
    if not (np.isfinite(X).all() and np.isfinite(A).all() and np.isfinite(X2).all()):
        raise ValueError('World-JEPA requires finite transition observations')
    # Zero rows are retained only for the preregistered no-action control.
    if not np.all((A == 0.) | (A == 1.)) or np.any(A.sum(axis=1) > 1):
        raise ValueError('World-JEPA action must be one-hot or zero control')
    return X, A, X2


class WorldJEPA:
    """fit(X, A, X2) on transitions (obs, action one-hot, next obs); A may be zeroed/shuffled for controls."""

    def __init__(self, seed=0, ensemble=5):
        self.seed = seed; self.ensemble = ensemble

    def fit(self, X, A, X2, steps=3000, log_every=500):
        X, A, X2 = _validate_fit_arrays(X, A, X2, steps, log_every, self.ensemble)
        rng = np.random.default_rng(self.seed)
        self.mu = X.mean(0); self.sd = X.std(0)+1e-3
        x, x2 = (X-self.mu)/self.sd, (X2-self.mu)/self.sd
        enc, pred = _init(rng, x.shape[1], A.shape[1]); inv = _init_inv(rng, A.shape[1]); tgt = {k: v.copy() for k, v in enc.items()}
        opt = Adam({**{'e'+k: v for k, v in enc.items()}, **{'p'+k: v for k, v in pred.items()}, **{'i'+k: v for k, v in inv.items()}}, LR)
        self.history = []
        for s in range(steps):
            b = rng.integers(0, len(x), min(BATCH, len(x)))
            zt = encode(tgt, x2[b])[0]
            out = loss_grads(enc, pred, x[b], A[b], zt, VAR_W, COV_W, inv=inv, x2=x2[b], inv_w=INV_W)
            loss, parts, gp, ge = out[:4]; gi = out[4] if len(out) > 4 else {}
            opt.step({**{'e'+k: v for k, v in ge.items()}, **{'p'+k: v for k, v in gp.items()}, **{'i'+k: v for k, v in gi.items()}})
            for k in enc: tgt[k] = TAU*tgt[k]+(1-TAU)*enc[k]
            if s % log_every == 0 or s == steps-1: self.history.append(dict(step=s, loss=round(loss, 5), **{k: round(v, 5) for k, v in parts.items()}))
        self.enc, self.tgt, self.preds = enc, tgt, [pred]
        zt_all = encode(tgt, x2)[0]; self.zsd = zt_all.std(0)+1e-6
        z_all = encode(enc, x)[0]
        for e in range(1, self.ensemble):  # encoder frozen, bootstrap predictors
            r2 = np.random.default_rng(self.seed*100+e); p = _init_pred(r2, A.shape[1]); o = Adam(p, LR)
            idx = r2.integers(0, len(x), len(x))
            for s in range(steps//2):
                b = idx[r2.integers(0, len(idx), min(BATCH, len(idx)))]
                _, _, gp, _ = loss_grads(enc, p, x[b], A[b], zt_all[b], train_enc=False)
                o.step(gp)
            self.preds.append(p)
        self._ztrain = z_all
        # Only actually observed one-hot training actions count as support.
        # Zero-action controls deliberately confer no action coverage.
        self._action_counts = (A == 1.).sum(axis=0).astype(int)
        sub = z_all[np.random.default_rng(self.seed).choice(len(z_all), min(400, len(z_all)), replace=False)]
        d = np.sqrt(((sub[:, None]-sub[None])**2).sum(-1)); np.fill_diagonal(d, np.inf); self._nn_med = float(np.median(d.min(1)))+1e-9
        return self

    # -- inference -------------------------------------------------------------------------------------------------
    def latent(self, X, target=True):
        return encode(self.tgt if target else self.enc, (X-self.mu)/self.sd)[0]

    def predict(self, X, A):
        """(mean prediction, spread in target-std units) for next latents."""
        z = self.latent(X, target=False)
        ps = np.stack([predict(p, z, A)[0] for p in self.preds])
        return ps.mean(0), (ps.std(0)/self.zsd).mean(1)

    def ood(self, X):
        z = self.latent(X, target=False)
        d = np.sqrt(((z[:, None]-self._ztrain[None])**2).sum(-1)).min(1); return d/self._nn_med

    def confidence(self, X, A, counts):
        """Bound caller counts by actual fit support; invalid evidence is uncertain.

        counts is an optional *lower* per-query coverage report, never authority
        to invent training observations. These scores are not calibrated probabilities.
        """
        try:
            X = np.asarray(X, dtype=float)
            A = np.asarray(A, dtype=float)
            counts = np.asarray(counts, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError('Invalid World-JEPA confidence inputs') from exc
        if (X.ndim != 2 or A.ndim != 2 or counts.ndim != 1
                or len(X) != len(A) or len(X) != len(counts)
                or A.shape[1] < 1):
            raise ValueError('World-JEPA confidence shape mismatch')
        conf = np.zeros(len(X), dtype=float)
        fit_counts = np.asarray(getattr(self, '_action_counts', []))
        if fit_counts.shape != (A.shape[1],):
            return conf, ['SIMULATION_UNCERTAIN'] * len(X)
        action_ok = (np.isfinite(A).all(axis=1)
                     & ((A == 0.) | (A == 1.)).all(axis=1)
                     & (A.sum(axis=1) == 1.))
        count_ok = (np.isfinite(counts) & (counts >= 0)
                    & (counts == np.floor(np.where(np.isfinite(counts), counts, 0.))))
        action_ids = np.argmax(A, axis=1)
        effective = np.minimum(np.where(count_ok, counts, 0.), fit_counts[action_ids])
        valid = (action_ok & count_ok & (effective > 0)
                 & np.isfinite(X).all(axis=1))
        if valid.any():
            _, spread = self.predict(X[valid], A[valid])
            ood = self.ood(X[valid])
            spread = np.asarray(spread, dtype=float)
            ood = np.asarray(ood, dtype=float)
            if spread.shape != (int(valid.sum()),) or ood.shape != spread.shape:
                raise ValueError('World-JEPA uncertainty shape mismatch')
            good = (np.isfinite(spread) & np.isfinite(ood)
                    & (spread >= 0) & (ood >= 0))
            score = np.zeros(len(spread), dtype=float)
            if good.any():
                cover = 1 - np.exp(-effective[valid][good] / COVER_N)
                score[good] = (cover / (1 + spread[good] / SPREAD_REF)
                               * np.minimum(1., OOD_SUPPORT / np.maximum(ood[good], 1e-9)))
            conf[valid] = np.where(np.isfinite(score), np.clip(score, 0., 1.), 0.)
        return conf, ['MODEL_SIMULATION' if c >= CF_MIN else 'SIMULATION_UNCERTAIN' for c in conf]

    def collapse_stats(self, X2):
        zt = self.latent(X2); ev = np.clip(np.linalg.eigvalsh(np.cov(zt.T)), 0, None); p = ev/ev.sum()
        return {'effective_rank': float(np.exp(-(p[p > 0]*np.log(p[p > 0])).sum())), 'min_std': float(zt.std(0).min())}
