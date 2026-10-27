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
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
from v13.common import atomic_write
from v13.world_jepa import Adam, encode, predict, loss_grads, collapse_stats, _init, _init_inv, _init_pred

REVISION = 'z12c-slot-world-jepa-v1'
CHECKPOINT_REVISION = 'z12c-slot-world-jepa-inference-npz-v1'
MAX_CHECKPOINT_BYTES = 32 * 1024 * 1024  # small phone inference-only checkpoint, no optimizer state
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

    @staticmethod
    def _provenance(provenance):
        if (type(provenance) is not dict or not provenance
                or any(type(k) is not str or not k or len(k)>80
                       or type(v) is not str or not v or len(v)>256
                       for k, v in provenance.items())):
            raise ValueError('Checkpoint requires nonempty explicit string provenance')
        return dict(provenance)

    def save(self, path, provenance):
        """Atomically persist a bound, pickle-free inference-only SHADOW model.

        This does not store the optimizer or authorize runtime activation,
        fact writes, age changes or training continuation.
        """
        self._provenance(provenance)
        if not all(hasattr(self, k) for k in ('enc','tgt','preds','mu','sd','zsd',
                                              'op_counts','op_err','_ztrain','_nn_med')):
            raise ValueError('Slot World-JEPA must be fitted before checkpointing')
        if not 1<=self.S<=128 or not 1<=len(self.preds)<=16:
            raise ValueError('Invalid slot/ensemble count')
        dims = {'slots': int(self.S), 'seed': int(self.seed),
                'ensemble': len(self.preds), 'k': int(self.k),
                'h': int(self.h), 'hp': int(self.hp),
                'input_dim': int(len(self.mu)), 'op_dim': int(len(self.op_counts))}
        if not (1<=dims['input_dim']<=4096 and 2<=dims['op_dim']<=128
                and 1<=dims['k']<=256 and 1<=dims['h']<=1024 and 1<=dims['hp']<=1024):
            raise ValueError('Checkpoint dimensions out of bounds')
        arrays = {'mu': self.mu, 'sd': self.sd, 'zsd': self.zsd,
                  'op_counts': self.op_counts, 'op_err': self.op_err,
                  'ztrain': self._ztrain, 'nn_med': np.array([self._nn_med])}
        for prefix, weights in (('enc', self.enc), ('tgt', self.tgt)):
            for name in ('W1','b1','W2','b2'): arrays[prefix+'_'+name] = weights[name]
        for i, weights in enumerate(self.preds):
            for name in ('P1','c1','P2','c2'): arrays[f'pred{i}_'+name] = weights[name]
        for key, value in list(arrays.items()):
            a = np.asarray(value)
            if a.dtype != np.dtype('float64') or not np.isfinite(a).all():
                raise ValueError('Nonfinite or non-float64 checkpoint array: '+key)
            arrays[key] = a
        meta = {'checkpoint_revision': CHECKPOINT_REVISION, 'model_revision': REVISION,
                'inference_only': True, 'provenance': dict(provenance), **dims}
        encoded = json.dumps(meta, sort_keys=True, separators=(',', ':')).encode('utf-8')
        if len(encoded)>8192: raise ValueError('Checkpoint metadata too large')
        buf = io.BytesIO()
        np.savez_compressed(buf, meta=np.frombuffer(encoded, dtype=np.uint8), **arrays)
        data = buf.getvalue()
        if len(data)>MAX_CHECKPOINT_BYTES: raise ValueError('Checkpoint exceeds size cap')
        atomic_write(path, data)
        return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                'checkpoint_revision': CHECKPOINT_REVISION, 'inference_only': True}

    @classmethod
    def load(cls, path, expected_provenance=None, expected_sha256=None):
        """Require exact whole-file digest and provenance before loading SHADOW weights."""
        cls._provenance(expected_provenance)
        if (type(expected_sha256) is not str or len(expected_sha256)!=64
                or any(c not in '0123456789abcdef' for c in expected_sha256)):
            raise ValueError('Checkpoint requires pinned lowercase SHA256')
        raw = Path(path).read_bytes()
        if not 100<=len(raw)<=MAX_CHECKPOINT_BYTES:
            raise ValueError('Checkpoint file size out of bounds')
        if hashlib.sha256(raw).hexdigest()!=expected_sha256:
            raise ValueError('Checkpoint whole-file SHA256 mismatch')
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos = archive.infolist()
                names = [x.filename for x in infos]
                if (len(names)!=len(set(names))
                        or sum(x.file_size for x in infos)>MAX_CHECKPOINT_BYTES
                        or any(x.file_size>MAX_CHECKPOINT_BYTES or
                               not x.filename.endswith('.npy') or
                               '/' in x.filename or '\\' in x.filename
                               for x in infos)):
                    raise ValueError('Unsafe checkpoint archive')
            with np.load(io.BytesIO(raw), allow_pickle=False) as z:
                if 'meta' not in z.files: raise ValueError('Missing metadata')
                mb = z['meta']
                if mb.dtype != np.dtype('uint8') or mb.ndim!=1 or len(mb)>8192:
                    raise ValueError('Invalid checkpoint metadata')
                meta = json.loads(mb.tobytes().decode('utf-8'))
                if (type(meta) is not dict or meta.get('checkpoint_revision')!=CHECKPOINT_REVISION
                        or meta.get('model_revision')!=REVISION
                        or meta.get('inference_only') is not True
                        or meta.get('provenance')!=expected_provenance):
                    raise ValueError('Checkpoint revision/provenance mismatch')
                dims = {k: meta.get(k) for k in
                        ('slots','seed','ensemble','k','h','hp','input_dim','op_dim')}
                if any(type(v) is not int for v in dims.values()):
                    raise ValueError('Invalid checkpoint dimensions')
                S, n, k, h, hp, d, na = (dims[q] for q in
                    ('slots','ensemble','k','h','hp','input_dim','op_dim'))
                if not (1<=S<=128 and 1<=n<=16 and 1<=k<=256 and
                        1<=h<=1024 and 1<=hp<=1024 and 1<=d<=4096 and 2<=na<=128):
                    raise ValueError('Checkpoint dimensions out of bounds')
                shapes = {'mu':(d,), 'sd':(d,), 'zsd':(k,),
                          'op_counts':(na,), 'op_err':(na,),
                          'nn_med':(1,)}
                for prefix in ('enc','tgt'):
                    shapes.update({prefix+'_W1':(h,d), prefix+'_b1':(h,),
                                   prefix+'_W2':(k,h), prefix+'_b2':(k,)})
                for i in range(n):
                    shapes.update({f'pred{i}_P1':(hp,k+na), f'pred{i}_c1':(hp,),
                                   f'pred{i}_P2':(k,hp), f'pred{i}_c2':(k,)})
                if set(z.files)!=set(shapes)|{'meta','ztrain'}:
                    raise ValueError('Unexpected or missing checkpoint array')
                arrays = {}
                for name in shapes:
                    a = z[name]
                    if a.dtype!=np.dtype('float64') or a.shape!=shapes[name] or not np.isfinite(a).all():
                        raise ValueError('Invalid checkpoint array: '+name)
                    arrays[name] = np.array(a, copy=True)
                ztrain = z['ztrain']
                if (ztrain.dtype!=np.dtype('float64') or ztrain.ndim!=2 or
                        ztrain.shape[1]!=k or not 1<=len(ztrain)<=2000 or
                        not np.isfinite(ztrain).all()):
                    raise ValueError('Invalid checkpoint training support')
                arrays['ztrain'] = np.array(ztrain, copy=True)
        except (zipfile.BadZipFile, KeyError, UnicodeError, TypeError, OSError, EOFError) as exc:
            raise ValueError('Invalid slot World-JEPA checkpoint') from exc
        if (np.any(arrays['sd']<=0) or np.any(arrays['zsd']<=0)
                or np.any(arrays['op_counts']<0) or np.any(arrays['op_err']<0)
                or arrays['nn_med'][0]<=0):
            raise ValueError('Invalid checkpoint calibration')
        model = cls(S, seed=dims['seed'], ensemble=n, k=k, h=h, hp=hp)
        model.mu, model.sd, model.zsd = arrays['mu'], arrays['sd'], arrays['zsd']
        model.op_counts, model.op_err = arrays['op_counts'], arrays['op_err']
        model._ztrain, model._nn_med = arrays['ztrain'], float(arrays['nn_med'][0])
        model.enc = {q: arrays['enc_'+q] for q in ('W1','b1','W2','b2')}
        model.tgt = {q: arrays['tgt_'+q] for q in ('W1','b1','W2','b2')}
        model.preds = [{q: arrays[f'pred{i}_'+q] for q in ('P1','c1','P2','c2')}
                       for i in range(n)]
        model.history = []  # inference-only; no training-resume claim
        return model
