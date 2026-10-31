"""W7D isolated research fork: latent-displacement inverse head.

Derived solely from the repo's frozen world_jepa.py Git blob
99a686a131a1bdc89efe0d0cf9610ec54cbd853b. Same model parameter
shapes/counts; only inverse input and gradient routing differ. No runtime,
learning or promotion authority. See WORLD_JEPA_DELTA_INVERSE_PREREG_20261031.
"""
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
import threading
import weakref
from functools import wraps

import numpy as np

REVISION = 'w7d-world-jepa-delta-inverse-shadow-v1'
H = 64; Z = 16; HP = 64
LR = 2e-3; TAU = .99; VAR_W = 1.; COV_W = .04; INV_W = 1.; BATCH = 256
COVER_N = 8.       # BOOT: samples per action for ~63 % of the coverage term (as world_model.py)
SPREAD_REF = .25   # BOOT: ensemble spread (in target-latent std units) that halves confidence
OOD_SUPPORT = 2.   # BOOT: nearest-neighbour distance (median-NN units) still inside the training support
CF_MIN = .5        # BOOT: below this a counterfactual is SIMULATION_UNCERTAIN

# Protect complete inference/checkpoint reads from a refit publication in this
# Python process. Keep the lock outside model.__dict__: fitted model snapshots
# and existing tests serialize/deepcopy those attributes. Training runs unlocked.
_WORLD_JEPA_IO_LOCK = threading.RLock()
# Per-instance tickets live outside model.__dict__: checkpoint/deepcopy and
# failed-fit exception-atomicity must not observe in-flight fit metadata.
_WORLD_JEPA_FIT_TICKETS = weakref.WeakKeyDictionary()


def _read_locked(fn):
    @wraps(fn)
    def read(*args, **kwargs):
        with _WORLD_JEPA_IO_LOCK:
            return fn(*args, **kwargs)
    return read


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
        z2, h2 = encode(enc, x2); delta = z2-z
        v = np.concatenate([delta, delta], 1); hq = np.tanh(v@inv['Q1'].T+inv['d1'])
        lg = hq@inv['Q2'].T+inv['d2']; pr = 1/(1+np.exp(-lg))
        li = float(-(a*np.log(pr+1e-9)+(1-a)*np.log(1-pr+1e-9)).mean()); loss += inv_w*li; parts['inv'] = li
        dl = inv_w*(pr-a)/a.size; gi = {'Q2': dl.T@hq, 'd2': dl.sum(0)}
        dq = (dl@inv['Q2'])*(1-hq**2); gi['Q1'] = dq.T@v; gi['d1'] = dq.sum(0); dv = dq@inv['Q1']
        d_delta = dv[:, :Z] + dv[:, Z:]
        for zz, hh, xx, dd in ((z, h, x, -d_delta), (z2, h2, x2, d_delta)):
            ge['W2'] += dd.T@hh; ge['b2'] += dd.sum(0); dh = (dd@enc['W2'])*(1-hh**2); ge['W1'] += dh.T@xx; ge['b1'] += dh.sum(0)
        return loss, parts, gp, ge, gi
    return loss, parts, gp, ge


class DeltaWorldJEPA:
    """fit(X, A, X2) on transitions (obs, action one-hot, next obs); A may be zeroed/shuffled for controls."""

    def __init__(self, seed=0, ensemble=5):
        self.seed = seed; self.ensemble = ensemble

    def fit(self, X, A, X2, steps=3000, log_every=500):
        # Invalid transitions cannot establish learned SHADOW inference evidence.
        # The covariance objective divides by n-1; never fit a single row.
        if (type(self.seed) is not int or not 0 <= self.seed <= 2**63-1
                or type(self.ensemble) is not int or not 1 <= self.ensemble <= 16
                or type(steps) is not int or steps < 0
                or type(log_every) is not int or log_every < 1):
            raise ValueError('Invalid WorldJEPA fit configuration')
        try:
            X, A, X2 = np.asarray(X), np.asarray(A), np.asarray(X2)
        except (TypeError, ValueError) as exc:
            raise ValueError('Invalid WorldJEPA transition arrays') from exc
        if (X.ndim != 2 or A.ndim != 2 or X2.ndim != 2
                or not 2 <= len(X) <= 100000
                or not 1 <= X.shape[1] <= 4096
                or not 1 <= A.shape[1] <= 64
                or A.shape[0] != len(X) or X2.shape != X.shape
                or any(v.dtype.kind not in 'fiub' for v in (X, A, X2))
                or not all(np.isfinite(v).all() for v in (X, A, X2))):
            raise ValueError('Invalid WorldJEPA transition shape or nonfinite values')
        # Training stays concurrent, but a late older fit must never replace
        # a newer fit's complete publication. Invalid inputs above do not
        # supersede an in-flight valid fit. A failed newer valid fit leaves the
        # previous committed model intact and vetoes older in-flight results.
        with _WORLD_JEPA_IO_LOCK:
            fit_ticket = _WORLD_JEPA_FIT_TICKETS.get(self, 0) + 1
            _WORLD_JEPA_FIT_TICKETS[self] = fit_ticket
        rng = np.random.default_rng(self.seed)
        # Confidence may use only actions actually present in fit's training rows.
        # Zeroed/shuffled-action controls do not gain fabricated one-hot support.
        valid_a = np.isfinite(A).all(1) & np.all((A == 0) | (A == 1), axis=1) & (A.sum(1) == 1)
        action_counts = np.bincount(np.argmax(A[valid_a], axis=1), minlength=A.shape[1])
        mu = X.mean(0); sd = X.std(0)+1e-3
        x, x2 = (X-mu)/sd, (X2-mu)/sd
        enc, pred = _init(rng, x.shape[1], A.shape[1]); inv = _init_inv(rng, A.shape[1]); tgt = {k: v.copy() for k, v in enc.items()}
        opt = Adam({**{'e'+k: v for k, v in enc.items()}, **{'p'+k: v for k, v in pred.items()}, **{'i'+k: v for k, v in inv.items()}}, LR)
        history = []
        for s in range(steps):
            b = rng.integers(0, len(x), min(BATCH, len(x)))
            zt = encode(tgt, x2[b])[0]
            out = loss_grads(enc, pred, x[b], A[b], zt, VAR_W, COV_W, inv=inv, x2=x2[b], inv_w=INV_W)
            loss, parts, gp, ge = out[:4]; gi = out[4] if len(out) > 4 else {}
            opt.step({**{'e'+k: v for k, v in ge.items()}, **{'p'+k: v for k, v in gp.items()}, **{'i'+k: v for k, v in gi.items()}})
            for k in enc: tgt[k] = TAU*tgt[k]+(1-TAU)*enc[k]
            if s % log_every == 0 or s == steps-1: history.append(dict(step=s, loss=round(loss, 5), **{k: round(v, 5) for k, v in parts.items()}))
        preds = [pred]
        zt_all = encode(tgt, x2)[0]; zsd = zt_all.std(0)+1e-6
        z_all = encode(enc, x)[0]
        for e in range(1, self.ensemble):  # encoder frozen, bootstrap predictors
            r2 = np.random.default_rng(self.seed*100+e); p = _init_pred(r2, A.shape[1]); o = Adam(p, LR)
            idx = r2.integers(0, len(x), len(x))
            for s in range(steps//2):
                b = idx[r2.integers(0, len(idx), min(BATCH, len(idx)))]
                _, _, gp, _ = loss_grads(enc, p, x[b], A[b], zt_all[b], train_enc=False)
                o.step(gp)
            preds.append(p)
        ztrain = z_all
        sub = z_all[np.random.default_rng(self.seed).choice(len(z_all), min(400, len(z_all)), replace=False)]
        d = np.sqrt(((sub[:, None]-sub[None])**2).sum(-1)); np.fill_diagonal(d, np.inf); nn_med = float(np.median(d.min(1)))+1e-9
        # Exception-atomic SHADOW refit: publish only after every stage and
        # ensemble member has completed with finite learned state. The old fit
        # remains usable if any training, calibration or validation step fails.
        arrays = [mu, sd, zsd, ztrain, *enc.values(), *tgt.values(),
                  *(v for p in preds for v in p.values())]
        if (not all(np.isfinite(v).all() for v in arrays)
                or not np.isfinite(nn_med) or nn_med <= 0
                or not all(np.isfinite(v) for row in history
                           for key, v in row.items() if key != 'step')):
            raise ValueError('WorldJEPA fit produced nonfinite learned state')
        with _WORLD_JEPA_IO_LOCK:
            if _WORLD_JEPA_FIT_TICKETS.get(self) != fit_ticket:
                raise RuntimeError('Superseded WorldJEPA fit cannot publish stale state')
            self.__dict__.update(_fit_steps=steps, _action_counts=action_counts, mu=mu, sd=sd,
                                 history=history, enc=enc, tgt=tgt, preds=preds,
                                 zsd=zsd, _ztrain=ztrain, _nn_med=nn_med)
        return self

    # -- inference -------------------------------------------------------------------------------------------------
    @_read_locked
    def latent(self, X, target=True):
        return encode(self.tgt if target else self.enc, (X-self.mu)/self.sd)[0]

    @_read_locked
    def predict(self, X, A):
        """(mean prediction, spread in target-std units) for next latents."""
        z = self.latent(X, target=False)
        ps = np.stack([predict(p, z, A)[0] for p in self.preds])
        return ps.mean(0), (ps.std(0)/self.zsd).mean(1)

    @_read_locked
    def ood(self, X):
        z = self.latent(X, target=False)
        d = np.sqrt(((z[:, None]-self._ztrain[None])**2).sum(-1)).min(1); return d/self._nn_med

    @_read_locked
    def confidence(self, X, A, counts=None):
        """Train-bound per-action support, never caller-asserted evidence.

        Optional counts can restrict the training support but cannot increase it.
        Invalid rows remain finite zero-confidence uncertain simulations.
        """
        if not hasattr(self, '_action_counts'):
            raise ValueError('WorldJEPA must be fitted before confidence')
        X = np.asarray(X, dtype=float); A = np.asarray(A, dtype=float)
        if (X.ndim != 2 or X.shape[1] != len(self.mu) or A.ndim != 2
                or A.shape != (len(X), len(self._action_counts))):
            raise ValueError('WorldJEPA confidence input shape mismatch')
        n = len(X); conf = np.zeros(n, dtype=float)
        onehot = (np.isfinite(A).all(1) & np.all((A == 0) | (A == 1), axis=1)
                  & (A.sum(1) == 1))
        # Argmax is only consumed for valid one-hot rows; NaNs cannot create support.
        action_index = np.argmax(np.where(np.isfinite(A), A, -np.inf), axis=1)
        if counts is None:
            requested = np.asarray([int(self._action_counts[i]) for i in action_index], dtype=object)
        else:
            requested = np.asarray(counts, dtype=object)
            if requested.shape != (n,):
                raise ValueError('WorldJEPA confidence counts shape mismatch')
        # Synthetic zero-step controls carry input/action coverage but no
        # learned predictor evidence. Legacy checkpoints with unknown step
        # provenance must also stay uncertain, regardless of ensemble spread.
        if type(getattr(self, '_fit_steps', None)) is not int or self._fit_steps <= 0:
            return conf, ['SIMULATION_UNCERTAIN'] * n
        count_valid = []
        for v in requested:
            try:
                if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
                    count_valid.append(False)
                else:
                    f = float(v)
                    count_valid.append(bool(np.isfinite(f) and f >= 0 and f.is_integer()))
            except (TypeError, ValueError, OverflowError):
                count_valid.append(False)
        eligible = onehot & np.isfinite(X).all(1) & np.asarray(count_valid)
        support = np.zeros(n, dtype=float)
        for i in np.flatnonzero(eligible):
            support[i] = min(float(requested[i]), float(self._action_counts[action_index[i]]))
        selected = np.flatnonzero(eligible & (support > 0))
        if len(selected):
            _, spread = self.predict(X[selected], A[selected])
            ood = self.ood(X[selected])
            spread = np.asarray(spread, dtype=float); ood = np.asarray(ood, dtype=float)
            if spread.shape != (len(selected),) or ood.shape != (len(selected),):
                raise ValueError('WorldJEPA confidence evidence shape mismatch')
            finite = np.isfinite(spread) & (spread >= 0) & np.isfinite(ood) & (ood >= 0)
            valid = selected[finite]
            cover = -np.expm1(-support[valid]/COVER_N)
            conf[valid] = np.clip(
                cover/(1+spread[finite]/SPREAD_REF)
                * np.minimum(1., OOD_SUPPORT/np.maximum(ood[finite], 1e-9)), 0., 1.)
        # One predictor has zero ensemble spread by construction, not
        # measured certainty. Keep the read/calibration path above intact so
        # confidence and concurrent refit still share a consistent snapshot.
        if self.ensemble < 2 or len(self.preds) < 2:
            return np.zeros_like(conf), ['SIMULATION_UNCERTAIN'] * len(conf)
        return conf, ['MODEL_SIMULATION' if c >= CF_MIN else 'SIMULATION_UNCERTAIN' for c in conf]

    @_read_locked
    def collapse_stats(self, X2):
        """Finite diagnostic only: zero covariance has no measurable effective rank.

        This is not a learning/utility gate. A degenerate or invalid probe
        cannot silently become rank one through a 0/0 probability vector.
        """
        if not hasattr(self, 'mu'):
            raise ValueError('WorldJEPA must be fitted before collapse stats')
        try:
            X2 = np.asarray(X2, dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError('Invalid WorldJEPA collapse probe') from exc
        if (X2.ndim != 2 or len(X2) < 2 or X2.shape[1] != len(self.mu)
                or not np.isfinite(X2).all()):
            raise ValueError('Invalid WorldJEPA collapse probe')
        zt = self.latent(X2)
        if zt.ndim != 2 or len(zt) != len(X2) or not np.isfinite(zt).all():
            raise ValueError('Invalid WorldJEPA target latents')
        # Exact constant rows can produce tiny positive covariance from
        # floating mean rounding (e.g. 3 or 7 identical nonzero latents).
        # Detect the actual zero-information condition before eigendecomp.
        min_std = float(zt.std(0).min())
        if not np.isfinite(min_std):
            raise ValueError('Nonfinite WorldJEPA collapse evidence')
        # A 64-wide float64 encoder can produce a few ULPs of row-wise
        # variation for mathematically identical latents on different BLAS
        # kernels. Below the conservative floating-point resolution floor,
        # effective rank is not measurable: do not invent positive rank.
        # A real resolvable change remains visible to the eigenvalue path.
        span = np.ptp(zt, axis=0)
        roundoff = (64. * np.finfo(np.float64).eps
                    * np.maximum(1., np.max(np.abs(zt), axis=0)))
        if np.all(span <= roundoff):
            return {'effective_rank': 0., 'min_std': 0., 'collapsed': True}
        ev = np.clip(np.linalg.eigvalsh(np.cov(zt.T)), 0, None)
        total = float(ev.sum())
        if not np.isfinite(total):
            raise ValueError('Nonfinite WorldJEPA collapse evidence')
        if total == 0.:
            return {'effective_rank': 0., 'min_std': min_std, 'collapsed': True}
        p = ev[ev > 0]/total
        return {'effective_rank': float(np.exp(-(p*np.log(p)).sum())),
                'min_std': min_std, 'collapsed': False}
