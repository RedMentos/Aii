"""WP-Z12c §29 Nr. 13 / §7.2: slot-wise (object-centric) World-JEPA in NumPy (phone-capable, SHADOW, not wired in).

Z12b (world_jepa.py) encoded the whole folder into one latent and fed the action as one (op, slot) one-hot: it could not
compose an operation it knew with a slot it had never seen that operation on (.27 retrieval), and its noop output drifted.
Here every slot is encoded by the same encoder and predicted by the same predictor; the action reaches a slot only as
"which operation happens to this slot" (op one-hot, or the UNTOUCHED class). So
  - what `append` does is learned once from every slot it was taken on, and applies to any slot (slot equivariance);
  - every slot an action does not touch, and every slot under noop, share one input: lots of data for "stays as it is";
  - prediction errors are per slot, so attribution can ask "did the touched slot do what my action does, and did every
    other slot stay put" instead of comparing one pooled distance with a per-operation threshold.
No interactions between slots are modelled (no message passing): that is the claim limit of this module.

  slot encoder     z_s = W2 tanh(W1 x_s + b1) + b2                    (x_s standardized with training mean/std over slots)
  slot predictor   z_s' = z_s + P2 tanh(P1 [z_s, a_s] + c1) + c2       (a_s = op one-hot of slot s, last column UNTOUCHED)
  target encoder   EMA copy of the slot encoder (tau), stop-gradient
  loss             world_jepa.loss_grads on the (batch x slots) rows: MSE to the target latent, variance/covariance guard,
                   inverse dynamics (a_s from [z_s, z_s'])
Confidence = coverage of the operation (count over all slots) x 1/(1 + (ensemble spread + typical error of that operation
on held-out transitions) / ERR_REF) x state-OOD term (worst slot). The typical-error term is the model's own record of
how predictable an operation is (random content makes `write_long` less predictable than `remove`).
"""
import numpy as np
from v13.world_jepa_slots_kernels import Adam, encode, predict, loss_grads, collapse_stats, _init, _init_inv, _init_pred

REVISION = 'run76-z12c-slot-world-jepa-isolated-v1'
H = 32; K = 8; HP = 48
LR = 2e-3; TAU = .99; VAR_W = 1.; COV_W = .04; INV_W = 1.; BATCH = 128   # BATCH counts states (x slots rows)
COVER_N = 8.       # BOOT: samples per operation for ~63 % of the coverage term (as world_model.py)
ERR_REF = 1.       # BOOT: spread + typical error (target-latent std units) that halves confidence (dev seed 7: .5 called 80 % uncertain)
OOD_SUPPORT = 2.   # BOOT: nearest-neighbour distance (median-NN units) still inside the training support
CF_MIN = .5        # BOOT: below this a counterfactual is SIMULATION_UNCERTAIN


class SlotWorldJEPA:
    """fit(X, A, X2): X, X2 (n, slots*d) observations, A (n, slots, ops+1) per-slot action vectors (last = UNTOUCHED).
    A may be replaced by all-UNTOUCHED or shuffled rows for controls."""

    def __init__(self, slots, seed=0, ensemble=5, k=K, h=H, hp=HP):
        self.S = slots; self.seed = seed; self.ensemble = ensemble; self.k, self.h, self.hp = k, h, hp

    def _rows(self, X):
        n = len(X); return ((X.reshape(n, self.S, -1)-self.mu)/self.sd).reshape(n*self.S, -1)

    def fit(self, X, A, X2, steps=3000, log_every=500):
        rng = np.random.default_rng(self.seed); n = len(X); S = self.S
        xs = X.reshape(n*S, -1); self.mu = xs.mean(0); self.sd = xs.std(0)+1e-3
        x, x2 = self._rows(X).reshape(n, S, -1), self._rows(X2).reshape(n, S, -1); a = A
        na = A.shape[2]; d = x.shape[2]
        enc, pred = _init(rng, d, na, self.h, self.k, self.hp); inv = _init_inv(rng, na, self.k, self.hp)
        tgt = {kk: v.copy() for kk, v in enc.items()}
        opt = Adam({**{'e'+kk: v for kk, v in enc.items()}, **{'p'+kk: v for kk, v in pred.items()}, **{'i'+kk: v for kk, v in inv.items()}}, LR)
        self.history = []
        for s in range(steps):
            b = rng.integers(0, n, min(BATCH, n))
            xb, x2b, ab = x[b].reshape(-1, d), x2[b].reshape(-1, d), a[b].reshape(-1, na)
            zt = encode(tgt, x2b)[0]
            loss, parts, gp, ge, gi = loss_grads(enc, pred, xb, ab, zt, VAR_W, COV_W, inv=inv, x2=x2b, inv_w=INV_W)
            opt.step({**{'e'+kk: v for kk, v in ge.items()}, **{'p'+kk: v for kk, v in gp.items()}, **{'i'+kk: v for kk, v in gi.items()}})
            for kk in enc: tgt[kk] = TAU*tgt[kk]+(1-TAU)*enc[kk]
            if s % log_every == 0 or s == steps-1: self.history.append(dict(step=s, loss=round(loss, 5), **{kk: round(v, 5) for kk, v in parts.items()}))
        self.enc, self.tgt, self.preds = enc, tgt, [pred]
        xf, x2f, af = x.reshape(-1, d), x2.reshape(-1, d), a.reshape(-1, na)
        zt_all = encode(tgt, x2f)[0]; self.zsd = zt_all.std(0)+1e-6; z_all = encode(enc, xf)[0]
        for e in range(1, self.ensemble):  # encoder frozen, bootstrap predictors over states
            r2 = np.random.default_rng(self.seed*100+e); p = _init_pred(r2, na, self.k, self.hp); o = Adam(p, LR)
            idx = r2.integers(0, n, n)
            for s in range(steps//2):
                b = idx[r2.integers(0, n, min(BATCH, n))]
                rows = (b[:, None]*S+np.arange(S)).ravel()
                _, _, gp, _ = loss_grads(enc, p, xf[rows], af[rows], zt_all[rows], train_enc=False)
                o.step(gp)
            self.preds.append(p)
        self.op_counts = af.sum(0)
        self._ztrain = z_all[np.random.default_rng(self.seed).choice(len(z_all), min(2000, len(z_all)), replace=False)]
        sub = self._ztrain[:400]
        dd = np.sqrt(((sub[:, None]-sub[None])**2).sum(-1)); np.fill_diagonal(dd, np.inf)
        self._nn_med = float(np.median(dd[np.isfinite(dd.min(1))].min(1))) if np.isfinite(dd.min(1)).any() else 1.
        self._nn_med = max(self._nn_med, 1e-3)
        self.op_err = np.zeros(na)
        return self

    def calibrate(self, X, A, X2):
        """Typical squared error per operation (on the slot it touches; UNTOUCHED on all others) from held-out transitions."""
        e = self.slot_errors(X, A, X2); cls = A.argmax(2)
        self.op_err = np.array([float(e[cls == c].mean()) if (cls == c).any() else 0. for c in range(A.shape[2])])
        return self

    # -- inference -------------------------------------------------------------------------------------------------
    def latent(self, X, target=True):
        n = len(X); return encode(self.tgt if target else self.enc, self._rows(X))[0].reshape(n, self.S, -1)

    def predict(self, X, A):
        """(mean prediction (n, S, k), spread per slot (n, S) in target-std units)."""
        n = len(X); z = self.latent(X, target=False).reshape(n*self.S, -1); a = A.reshape(n*self.S, -1)
        ps = np.stack([predict(p, z, a)[0] for p in self.preds])
        return ps[0].reshape(n, self.S, -1), (ps.std(0)/self.zsd).mean(1).reshape(n, self.S)

    def slot_errors(self, X, A, X2):
        """Normalized squared prediction error per slot (n, S)."""
        p, _ = self.predict(X, A); return (((p-self.latent(X2))/self.zsd)**2).mean(-1)

    def ood(self, X):
        n = len(X); z = self.latent(X, target=False).reshape(n*self.S, -1)
        d = np.sqrt(((z[:, None]-self._ztrain[None])**2).sum(-1)).min(1)/self._nn_med
        return d.reshape(n, self.S).max(1)

    def confidence(self, X, A):
        """Per query: worst slot of coverage x 1/(1 + (spread + sqrt(typical error)) / ERR_REF), times the OOD term."""
        _, spread = self.predict(X, A); cls = A.argmax(2)
        cover = 1-np.exp(-self.op_counts[cls]/COVER_N)
        per = cover/(1+(spread+np.sqrt(self.op_err[cls]))/ERR_REF)
        conf = per.min(1)*np.minimum(1., OOD_SUPPORT/np.maximum(self.ood(X), 1e-9))
        return conf, ['MODEL_SIMULATION' if c >= CF_MIN else 'SIMULATION_UNCERTAIN' for c in conf]

    def collapse_stats(self, X2):
        return collapse_stats(self.latent(X2).reshape(-1, self.k))
