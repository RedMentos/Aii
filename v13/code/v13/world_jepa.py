"""WP-Z12b §29 Nr. 13 / §7.2: small action-grounded World-JEPA in NumPy (phone-capable SHADOW, wired to the postcommit Store consumer; no native body-weight update).

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

REVISION = 'z12b-world-jepa-v1'
H = 64; Z = 16; HP = 64
LR = 2e-3; TAU = .99; VAR_W = 1.; COV_W = .04; INV_W = 1.; BATCH = 256
MAX_REPLAY_CONSTRAINTS = 8
MAX_REPLAY_REFERENCE_ROWS = 64
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


def _project_halfspace_intersection(raw, reference_vectors):
    """Exact active-set projection onto <=8 GEM half-spaces in parameter space.

    Dykstra's cyclic projection can need thousands of sweeps for nearly
    opposing session gradients. With at most eight cohorts, enumerating the
    KKT active set is bounded (256 tiny systems) and avoids a false learner
    ERROR after an arbitrary sweep cap.
    """
    vectors = [np.asarray(item, dtype=float) for item in reference_vectors]
    norms_sq = [float(np.dot(item, item)) for item in vectors]
    active = [index for index, value in enumerate(norms_sq) if value > 1e-20]
    if not active:
        return raw.copy(), 0, 0.0, 0.0, 0, "NO_ACTIVE_REFERENCE"

    vectors = [vectors[index] for index in active]
    gram = np.asarray([
        [float(np.dot(left, right)) for right in vectors]
        for left in vectors
    ], dtype=float)
    before = np.asarray([float(np.dot(item, raw)) for item in vectors], dtype=float)
    direction_norm = float(np.linalg.norm(raw))
    tolerance = max(
        1e-10 * max(1.0, float(np.sqrt(float(np.dot(item, item)))) * direction_norm)
        for item in vectors
    )
    if float(np.min(before)) >= -tolerance:
        return raw.copy(), 0, tolerance, max(0.0, -float(np.min(before))), 0, "ALREADY_FEASIBLE"

    count = len(vectors)
    best = None
    candidates = 1 << count
    for mask in range(candidates):
        selected = [index for index in range(count) if mask & (1 << index)]
        multipliers = np.zeros(count, dtype=float)
        if selected:
            submatrix = gram[np.ix_(selected, selected)]
            rhs = -before[selected]
            try:
                solution = np.linalg.solve(submatrix, rhs)
            except np.linalg.LinAlgError:
                solution = np.linalg.lstsq(submatrix, rhs, rcond=1e-14)[0]
            if not np.isfinite(solution).all():
                continue
            multiplier_scale = max(1.0, float(np.max(np.abs(solution))))
            if np.any(solution < -1e-10 * multiplier_scale):
                continue
            multipliers[selected] = np.maximum(solution, 0.0)

        projected = raw.copy()
        for index, multiplier in enumerate(multipliers):
            if multiplier:
                projected += multiplier * vectors[index]
        after = before + gram @ multipliers
        projected_norm = float(np.linalg.norm(projected))
        tolerance = max(
            1e-10 * max(1.0, float(np.sqrt(float(gram[index, index]))) * projected_norm)
            for index in range(count)
        )
        violation = max(0.0, -float(np.min(after)))
        multiplier_scale = max(1.0, float(np.max(np.abs(multipliers))))
        complementarity = float(np.max(np.abs(multipliers * after)))
        if (violation > tolerance
                or complementarity > 10.0 * tolerance * multiplier_scale):
            continue
        delta = projected - raw
        distance_sq = float(np.dot(delta, delta))
        score = (violation, complementarity, distance_sq)
        if best is None or score < best[0]:
            best = (score, projected, after, tolerance, multipliers)

    if best is None:
        raise ValueError("WorldJEPA active-set GEM projection did not converge")
    _, projected, after, tolerance, multipliers = best
    violation = max(0.0, -float(np.min(after)))
    kkt_active = int(np.count_nonzero(multipliers > 1e-12))
    return projected, 1, tolerance, violation, kkt_active, "ACTIVE_SET_ENUMERATION"


class Adam:
    def __init__(self, params, lr):
        self.p = params; self.lr = lr; self.t = 0
        self.steps = {k: 0 for k in params}
        self.m = {k: np.zeros_like(v) for k, v in params.items()}; self.v = {k: np.zeros_like(v) for k, v in params.items()}

    def step(self, grads, *, constraint_gradients=None, update_scale=1.0):
        if (type(update_scale) not in (int, float) or not np.isfinite(update_scale)
                or not 0.0 < float(update_scale) <= 1.0):
            raise ValueError("WorldJEPA update scale must be finite and in (0,1]")
        update_scale = float(update_scale)
        if type(grads) is not dict or not grads or any(k not in self.p for k in grads):
            raise ValueError("WorldJEPA Adam received an unknown parameter")
        references = None
        if constraint_gradients is not None:
            if type(constraint_gradients) is dict:
                references = (constraint_gradients,)
            elif (type(constraint_gradients) in (list, tuple)
                    and 1 <= len(constraint_gradients) <= MAX_REPLAY_CONSTRAINTS):
                references = tuple(constraint_gradients)
            else:
                raise ValueError("WorldJEPA replay constraints must be one to eight cohort gradients")
            for reference in references:
                if type(reference) is not dict or set(reference) != set(grads):
                    raise ValueError("WorldJEPA replay constraint does not match trainable parameters")
                for key, value in reference.items():
                    ref = np.asarray(value, dtype=float)
                    if ref.shape != self.p[key].shape or not np.isfinite(ref).all():
                        raise ValueError("WorldJEPA Adam received an invalid replay constraint")
        self.t += 1
        directions = {}
        for key, gradient in grads.items():
            value = np.asarray(gradient, dtype=float)
            if value.shape != self.p[key].shape or not np.isfinite(value).all():
                raise ValueError("WorldJEPA Adam received an invalid gradient")
            self.steps[key] += 1
            self.m[key] = .9*self.m[key]+.1*value
            self.v[key] = .999*self.v[key]+.001*value*value
            step = self.steps[key]
            mh = self.m[key]/(1-.9**step)
            vh = self.v[key]/(1-.999**step)
            directions[key] = mh/(np.sqrt(vh)+1e-8)
        report = {
            "enabled": references is not None, "projected": False,
            "reference_zero": False, "constraint_dot_before": None,
            "constraint_dot_after": None, "constraint_norm_sq": 0.0,
            "direction_norm_sq": float(sum(
                np.sum(value*value, dtype=np.float64) for value in directions.values()
            )),
            "projection_norm": 0.0, "constraint_tolerance": 0.0,
            "constraint_count": 0 if references is None else len(references),
            "active_constraint_count": 0, "projection_sweeps": 0,
            "max_constraint_violation": 0.0,
        }
        if references is not None:
            keys = tuple(sorted(directions))
            raw = np.concatenate([directions[key].reshape(-1) for key in keys])
            reference_vectors = [
                np.concatenate([
                    np.asarray(reference[key], dtype=float).reshape(-1)
                    for key in keys
                ])
                for reference in references
            ]
            reference_norms = [
                float(np.dot(reference, reference)) for reference in reference_vectors
            ]
            if not all(np.isfinite(value) for value in reference_norms):
                raise ValueError("WorldJEPA replay constraint norm is nonfinite")
            before_dots = [
                float(np.dot(reference, raw)) for reference in reference_vectors
            ]
            active = [
                (reference, norm_sq)
                for reference, norm_sq in zip(reference_vectors, reference_norms)
                if norm_sq > 1e-20
            ]
            projected, sweeps, tolerance, max_violation, kkt_active, projection_method = (
                _project_halfspace_intersection(raw, reference_vectors)
            )
            after_dots = [
                float(np.dot(reference, projected)) for reference in reference_vectors
            ]
            projection_delta = projected - raw
            projection_norm = float(np.sqrt(np.dot(projection_delta, projection_delta)))
            offset = 0
            for key in keys:
                size = self.p[key].size
                directions[key] = projected[offset:offset + size].reshape(self.p[key].shape)
                offset += size
            report.update({
                "projected": projection_norm > 1e-12,
                "reference_zero": not active,
                "constraint_dot_before": min(before_dots),
                "constraint_dot_after": min(after_dots),
                "constraint_norm_sq": float(sum(reference_norms)),
                "direction_norm_sq": float(np.dot(projected, projected)),
                "projection_norm": projection_norm,
                "constraint_tolerance": tolerance,
                "active_constraint_count": len(active),
                "kkt_active_constraint_count": kkt_active,
                "projection_sweeps": sweeps,
                "projection_method": projection_method,
                "projection_candidates_examined": (
                    (1 << len(active))
                    if active and projection_method == "ACTIVE_SET_ENUMERATION" else 0
                ),
                "max_constraint_violation": max_violation,
            })
        for key, direction in directions.items():
            self.p[key] -= self.lr*update_scale*direction
        return report


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


class WorldJEPA:
    """fit(X, A, X2) on transitions (obs, action one-hot, next obs); A may be zeroed/shuffled for controls."""

    def __init__(self, seed=0, ensemble=5):
        self.seed = seed; self.ensemble = ensemble

    def fit(self, X, A, X2, steps=3000, log_every=500, warm_start=False, cancel_check=None,
            allow_optimizer_bootstrap=False, train_encoder=True, drift_control=None,
            replay_start=None, update_scale=1.0, replay_cohort_ranges=None, replay_reference_batches=None):
        # Invalid transitions cannot establish learned SHADOW inference evidence.
        # The covariance objective divides by n-1; never fit a single row.
        from . import world_jepa_training_state as training_state
        from . import world_jepa_drift as drift
        if (type(self.seed) is not int or not 0 <= self.seed <= 2**63-1
                or type(self.ensemble) is not int or not 1 <= self.ensemble <= 16
                or type(steps) is not int or steps < 0
                or type(log_every) is not int or log_every < 1
                or type(warm_start) is not bool
                or type(allow_optimizer_bootstrap) is not bool
                or type(train_encoder) is not bool
                or (replay_start is not None and type(replay_start) is not int)
                or (replay_cohort_ranges is not None and replay_start is None)
                or (replay_reference_batches is not None and replay_start is None)
                or (cancel_check is not None and not callable(cancel_check))):
            raise ValueError('Invalid WorldJEPA fit configuration')
        if (type(update_scale) not in (int, float) or not np.isfinite(update_scale)
                or not 0.0 < float(update_scale) <= 1.0):
            raise ValueError('WorldJEPA update scale must be finite and in (0,1]')
        drift_config = drift.normalize_config(drift_control)
        if cancel_check is not None and cancel_check():
            raise InterruptedError('WorldJEPA fit cancelled')
        if not train_encoder and not warm_start:
            raise ValueError('Predictor-only adaptation requires an existing encoder checkpoint')
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
        if replay_start is not None and (
                not warm_start or replay_start < 2 or len(X)-replay_start < 2):
            raise ValueError('Replay projection requires a warm-start split with at least two new and two replay rows')
        replay_ranges = ()
        if replay_start is not None:
            if replay_cohort_ranges is None:
                replay_ranges = ((replay_start, len(X)),)
            else:
                if (type(replay_cohort_ranges) not in (list, tuple)
                        or not 1 <= len(replay_cohort_ranges) <= MAX_REPLAY_CONSTRAINTS):
                    raise ValueError('Replay projection cohort count exceeds its bounded capacity')
                expected_start = replay_start
                validated_ranges = []
                for pair in replay_cohort_ranges:
                    if type(pair) not in (list, tuple) or len(pair) != 2:
                        raise ValueError('Invalid replay cohort range')
                    start, end = pair
                    if (type(start) is not int or type(end) is not int
                            or start != expected_start or end - start < 2 or end > len(X)):
                        raise ValueError('Replay cohort ranges must be contiguous and contain at least two rows')
                    validated_ranges.append((start, end))
                    expected_start = end
                if expected_start != len(X):
                    raise ValueError('Replay cohort ranges must cover the complete replay fold')
                replay_ranges = tuple(validated_ranges)
        validated_replay_reference_batches = None
        if replay_reference_batches is not None:
            if (type(replay_reference_batches) not in (list, tuple)
                    or len(replay_reference_batches) != len(replay_ranges)):
                raise ValueError('Replay reference batches must match the selected session constraints')
            validated = []
            for reference in replay_reference_batches:
                if type(reference) not in (list, tuple) or len(reference) != 3:
                    raise ValueError('Invalid replay reference batch')
                try:
                    ref_x = np.asarray(reference[0], dtype=float)
                    ref_a = np.asarray(reference[1], dtype=float)
                    ref_x2 = np.asarray(reference[2], dtype=float)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError('Invalid replay reference arrays') from exc
                if (ref_x.ndim != 2 or not 2 <= len(ref_x) <= MAX_REPLAY_REFERENCE_ROWS
                        or ref_x.shape[1] != X.shape[1]
                        or ref_a.shape != (len(ref_x), A.shape[1])
                        or ref_x2.shape != ref_x.shape
                        or not all(np.isfinite(value).all() for value in (ref_x, ref_a, ref_x2))):
                    raise ValueError('Replay reference batch shape, size or values are invalid')
                validated.append((ref_x, ref_a, ref_x2))
            validated_replay_reference_batches = tuple(validated)
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
        with _WORLD_JEPA_IO_LOCK:
            existing = (hasattr(self,'enc') and hasattr(self,'preds') and
                        len(self.mu)==X.shape[1] and
                        self.preds[0]['P1'].shape[1]==Z+A.shape[1])
            if warm_start and not existing:
                raise ValueError('Warm-start requires a compatible fitted JEPA')
            if warm_start:
                if hasattr(self, '_training_state'):
                    saved_training = training_state.from_model(self)
                elif allow_optimizer_bootstrap:
                    saved_training = training_state.bootstrap_from_inference(self)
                else:
                    raise ValueError('World-JEPA training state missing; explicit optimizer bootstrap permission required')
            else:
                saved_training = None
            prior = ({'mu':self.mu.copy(),'sd':self.sd.copy(),
                      'enc':{k:v.copy() for k,v in self.enc.items()},
                      'tgt':{k:v.copy() for k,v in self.tgt.items()},
                      'pred':{k:v.copy() for k,v in self.preds[0].items()},
                      'ensemble':[{k:v.copy() for k,v in p.items()} for p in self.preds]}
                     if warm_start else None)
        # Keep a frozen prior-EMA target for replay constraints. The live tgt
        # below is updated by EMA each step and must not move this reference.
        replay_target_anchor = (
            {k: v.copy() for k, v in prior['tgt'].items()} if prior else None
        )
        mu = prior['mu'] if prior else X.mean(0)
        sd = prior['sd'] if prior else X.std(0)+1e-3
        x, x2 = (X-mu)/sd, (X2-mu)/sd
        enc, pred = _init(rng, x.shape[1], A.shape[1]); inv = _init_inv(rng, A.shape[1]); tgt = {k: v.copy() for k, v in enc.items()}
        if prior:
            enc=prior['enc'];pred=prior['pred'];tgt=prior['tgt']
            inv=saved_training['inverse']
            rng.bit_generator.state=saved_training['rng']
        opt = Adam({**{'e'+k: v for k, v in enc.items()}, **{'p'+k: v for k, v in pred.items()}, **{'i'+k: v for k, v in inv.items()}}, LR)
        if saved_training is not None:
            training_state.restore_adam(opt,saved_training['main'])
        drift_state = saved_training.get('drift') if saved_training is not None else drift.default_state()
        # Drift control covers the primary optimizer's encoder/predictor/inverse groups.
        # Bootstrap ensemble predictors remain a separately trained uncertainty lane.
        params_by_group = {
            'encoder': {'e'+k: v for k, v in enc.items()} if train_encoder else {},
            'predictor': {'p'+k: v for k, v in pred.items()},
            'inverse': {'i'+k: v for k, v in inv.items()} if train_encoder else {},
        }
        prior_steps = int(getattr(self, '_fit_steps', 0)) if warm_start else 0
        drift_prepared = drift.prepare_task(
            drift_state, drift_config, params_by_group,
            has_prior_training=bool(warm_start and prior_steps > 0),
        )
        previous_step_params = {
            name: {key: np.array(value, copy=True) for key, value in params.items()}
            for name, params in params_by_group.items() if params
        } if drift_config['enabled'] else {}
        update_norms = {name: [] for name in previous_step_params}
        projection_stats = {"enabled": replay_start is not None,
                            "replay_target_anchor": "prior_ema_snapshot" if replay_start is not None else None,
                            "steps": 0, "projected_steps": 0, "reference_zero_steps": 0,
                            "post_constraint_violation_steps": 0,
                            "constraint_dot_before_sum": 0.0, "constraint_dot_after_sum": 0.0,
                            "min_constraint_dot_before": None, "max_constraint_dot_after": None,
                            "projection_norm_sum": 0.0,
                            "constraint_count": len(replay_ranges),
                            "constraint_source": (
                                "prior_guard" if validated_replay_reference_batches is not None
                                else "fit_replay" if replay_start is not None else None
                            ),
                            "reference_batch_count": (
                                0 if validated_replay_reference_batches is None
                                else len(validated_replay_reference_batches)
                            ),
                            "reference_rows_total": (
                                0 if validated_replay_reference_batches is None
                                else sum(len(item[0]) for item in validated_replay_reference_batches)
                            ),
                            "active_constraint_count": 0, "projection_sweeps_total": 0,
                            "max_constraint_violation": 0.0}
        def pack_gradients(out):
            _, _, gp, ge = out[:4]
            gi = out[4] if len(out) > 4 else {}
            return {
                **({'e'+key: value for key, value in ge.items()} if ge is not None else {}),
                **{'p'+key: value for key, value in gp.items()},
                **{'i'+key: value for key, value in gi.items()},
            }
        history = []
        for s in range(steps):
            if cancel_check is not None and cancel_check():
                raise InterruptedError('WorldJEPA fit cancelled')
            constraint_gradients = None
            if replay_start is None:
                batch = rng.integers(0, len(x), min(BATCH, len(x)))
                target = encode(tgt, x2[batch])[0]
                out = loss_grads(
                    enc, pred, x[batch], A[batch], target, VAR_W, COV_W,
                    train_enc=train_encoder, inv=inv if train_encoder else None,
                    x2=x2[batch] if train_encoder else None, inv_w=INV_W if train_encoder else 0.,
                )
                loss, parts = out[0], out[1]
                gradients = pack_gradients(out)
            else:
                # The selected fit-fold rows identify bounded prior sessions.
                # Prefer source-disjoint prior-guard microbatches for the GEM
                # constraints; legacy callers without them retain fit-fold GEM.
                new_count = replay_start
                new_size = min(BATCH//2, new_count)
                replay_capacity = BATCH - new_size
                if replay_capacity < 2 * len(replay_ranges):
                    raise ValueError('Replay batch cannot cover every selected session with two rows')
                replay_sizes = [
                    min(end - start, max(2, replay_capacity // len(replay_ranges)))
                    for start, end in replay_ranges
                ]
                used = sum(replay_sizes)
                while used < replay_capacity:
                    progressed = False
                    for index, (start, end) in enumerate(replay_ranges):
                        if replay_sizes[index] < end - start:
                            replay_sizes[index] += 1
                            used += 1
                            progressed = True
                            if used == replay_capacity:
                                break
                    if not progressed:
                        break
                new_batch = rng.integers(0, new_count, new_size)
                new_target = encode(tgt, x2[new_batch])[0]
                new_out = loss_grads(
                    enc, pred, x[new_batch], A[new_batch], new_target, VAR_W, COV_W,
                    train_enc=train_encoder, inv=inv if train_encoder else None,
                    x2=x2[new_batch] if train_encoder else None, inv_w=INV_W if train_encoder else 0.,
                )
                loss, parts = new_out[0], new_out[1]
                gradients = pack_gradients(new_out)
                constraint_gradients = []
                if validated_replay_reference_batches is not None:
                    for ref_x, ref_a, ref_x2 in validated_replay_reference_batches:
                        ref_size = min(16, len(ref_x))
                        ref_batch = rng.choice(len(ref_x), ref_size, replace=False)
                        guard_x = (ref_x[ref_batch] - mu) / sd
                        guard_x2 = (ref_x2[ref_batch] - mu) / sd
                        guard_target = encode(replay_target_anchor, guard_x2)[0]
                        guard_out = loss_grads(
                            enc, pred, guard_x, ref_a[ref_batch], guard_target,
                            VAR_W, COV_W, train_enc=train_encoder,
                            inv=inv if train_encoder else None,
                            x2=guard_x2 if train_encoder else None,
                            inv_w=INV_W if train_encoder else 0.,
                        )
                        constraint_gradients.append(pack_gradients(guard_out))
                else:
                    for (start, end), replay_size in zip(replay_ranges, replay_sizes):
                        replay_batch = rng.integers(start, end, replay_size)
                        replay_target = encode(replay_target_anchor, x2[replay_batch])[0]
                        replay_out = loss_grads(
                            enc, pred, x[replay_batch], A[replay_batch], replay_target,
                            VAR_W, COV_W, train_enc=train_encoder,
                            inv=inv if train_encoder else None,
                            x2=x2[replay_batch] if train_encoder else None,
                            inv_w=INV_W if train_encoder else 0.,
                        )
                        constraint_gradients.append(pack_gradients(replay_out))
            if drift_prepared['active']:
                gradients = drift.apply_pullback(params_by_group, gradients, drift_prepared)
            step_report = opt.step(gradients, constraint_gradients=constraint_gradients,
                                   update_scale=update_scale)
            if replay_start is not None:
                projection_stats["steps"] += 1
                if step_report.get("projected") is True: projection_stats["projected_steps"] += 1
                if step_report.get("reference_zero") is True: projection_stats["reference_zero_steps"] += 1
                dot_before = float(step_report["constraint_dot_before"])
                dot_after = float(step_report["constraint_dot_after"])
                projection_stats["constraint_dot_before_sum"] += dot_before
                projection_stats["constraint_dot_after_sum"] += dot_after
                projection_stats["projection_norm_sum"] += float(step_report["projection_norm"])
                projection_stats["projection_sweeps_total"] += int(step_report.get("projection_sweeps", 0))
                projection_stats["active_constraint_count"] = max(
                    projection_stats["active_constraint_count"],
                    int(step_report.get("active_constraint_count", 0)),
                )
                projection_stats["max_constraint_violation"] = max(
                    projection_stats["max_constraint_violation"],
                    float(step_report.get("max_constraint_violation", 0.0)),
                )
                prior_min = projection_stats["min_constraint_dot_before"]
                projection_stats["min_constraint_dot_before"] = dot_before if prior_min is None else min(prior_min, dot_before)
                prior_max = projection_stats["max_constraint_dot_after"]
                projection_stats["max_constraint_dot_after"] = dot_after if prior_max is None else max(prior_max, dot_after)
                if float(step_report.get("max_constraint_violation", 0.0)) > float(step_report["constraint_tolerance"]):
                    projection_stats["post_constraint_violation_steps"] += 1
            if drift_config['enabled']:
                for name, params in params_by_group.items():
                    if not params: continue
                    delta_sq = sum(float(np.sum((params[key] - previous_step_params[name][key]) ** 2)) for key in params)
                    update_norms[name].append(delta_sq)
                    previous_step_params[name] = {key: np.array(value, copy=True) for key, value in params.items()}
            if drift_prepared['active']:
                drift.update_dual(drift_prepared, params_by_group)
            if train_encoder:
                for k in enc: tgt[k] = TAU*tgt[k]+(1-TAU)*enc[k]
            if s % log_every == 0 or s == steps-1: history.append(dict(step=s, loss=round(loss, 5), **{k: round(v, 5) for k, v in parts.items()}))
        if projection_stats["steps"]:
            projection_stats["mean_constraint_dot_before"] = projection_stats["constraint_dot_before_sum"]/projection_stats["steps"]
            projection_stats["mean_constraint_dot_after"] = projection_stats["constraint_dot_after_sum"]/projection_stats["steps"]
            projection_stats["mean_projection_norm"] = projection_stats["projection_norm_sum"]/projection_stats["steps"]
        else:
            projection_stats["mean_constraint_dot_before"] = None
            projection_stats["mean_constraint_dot_after"] = None
            projection_stats["mean_projection_norm"] = 0.0
        preds = [pred]
        bootstrap_training=[]
        zt_all = encode(tgt, x2)[0]; zsd = zt_all.std(0)+1e-6
        z_all = encode(enc, x)[0]
        for e in range(1, self.ensemble):  # encoder frozen, bootstrap predictors
            if cancel_check is not None and cancel_check():
                raise InterruptedError('WorldJEPA fit cancelled')
            if saved_training is not None:
                r2 = np.random.default_rng()
                r2.bit_generator.state=saved_training['bootstrap'][e-1]['rng']
                p = {k:v.copy() for k,v in prior['ensemble'][e].items()}
                o = Adam(p, LR)
                training_state.restore_adam(o,saved_training['bootstrap'][e-1]['adam'])
            else:
                r2 = np.random.default_rng(self.seed*100+e)
                p = _init_pred(r2, A.shape[1])
                o = Adam(p, LR)
            idx = r2.integers(0, len(x), len(x))
            for s in range(steps//2):
                if cancel_check is not None and cancel_check():
                    raise InterruptedError('WorldJEPA fit cancelled')
                b = idx[r2.integers(0, len(idx), min(BATCH, len(idx)))]
                _, _, gp, _ = loss_grads(enc, p, x[b], A[b], zt_all[b], train_enc=False)
                o.step(gp, update_scale=update_scale)
            preds.append(p)
            bootstrap_training.append({'adam':training_state.snapshot(o),'rng':r2.bit_generator.state})
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
        if cancel_check is not None and cancel_check():
            raise InterruptedError('WorldJEPA fit cancelled')
        total_steps=(getattr(self,'_fit_steps',0)+steps) if warm_start else steps
        origin = saved_training['origin'] if saved_training is not None else 'FRESH'
        next_drift = drift.finish_task(
            drift_prepared, params_by_group, steps=steps, update_norms=update_norms
        )
        next_training=training_state.capture(opt,inv,rng,bootstrap_training,X.shape[1],A.shape[1],
                                            self.seed,self.ensemble,total_steps,origin=origin,
                                            drift_state=next_drift)
        with _WORLD_JEPA_IO_LOCK:
            if _WORLD_JEPA_FIT_TICKETS.get(self) != fit_ticket:
                raise RuntimeError('Superseded WorldJEPA fit cannot publish stale state')
            self.__dict__.update(_training_state=next_training, _fit_steps=total_steps, _action_counts=action_counts, mu=mu, sd=sd,
                                 history=history, enc=enc, tgt=tgt, preds=preds,
                                 zsd=zsd, _ztrain=ztrain, _nn_med=nn_med,
                                 _last_gradient_projection=projection_stats)
        return self

    def partial_fit(self,X,A,X2,steps=100,log_every=50,cancel_check=None,allow_optimizer_bootstrap=False,
                    train_encoder=True, drift_control=None, replay_start=None, update_scale=1.0,
                    replay_cohort_ranges=None, replay_reference_batches=None):
        """Continue JEPA weights and EMA target instead of reinitializing.

        Callers should mix replay transitions with new ones to reduce forgetting.
        This experimental path does not itself establish durable retention.
        """
        return self.fit(X,A,X2,steps=steps,log_every=log_every,warm_start=True,cancel_check=cancel_check,
                        allow_optimizer_bootstrap=allow_optimizer_bootstrap,train_encoder=train_encoder,
                        drift_control=drift_control,replay_start=replay_start,update_scale=update_scale,
                         replay_cohort_ranges=replay_cohort_ranges,
                        replay_reference_batches=replay_reference_batches)

    # -- inference -------------------------------------------------------------------------------------------------
    @_read_locked
    def prediction_loss(self,X,A,X2,*,target_snapshot=None):
        """Read-only transition error, optionally in a fixed pre-update EMA space.

        Retention comparisons must use the same target coordinates before and
        after an online update. Otherwise EMA movement is mistaken for task
        forgetting. The snapshot is evaluation-only and never used for gradients.
        """
        X=np.asarray(X,dtype=float);A=np.asarray(A,dtype=float);X2=np.asarray(X2,dtype=float)
        if (not hasattr(self,'mu') or X.ndim!=2 or X2.shape!=X.shape
                or X.shape[1]!=len(self.mu) or A.shape!=(len(X),self.preds[0]['P1'].shape[1]-Z)
                or not len(X) or not all(np.isfinite(v).all() for v in (X,A,X2))):
            raise ValueError('Invalid JEPA retention probe')
        target_params=self.tgt if target_snapshot is None else target_snapshot
        if type(target_params) is not dict or set(target_params)!=set(self.tgt):
            raise ValueError('Invalid JEPA retention target snapshot')
        for key,value in target_params.items():
            arr=np.asarray(value)
            if (arr.shape!=self.tgt[key].shape or arr.dtype.kind not in 'fiub'
                    or not np.isfinite(arr).all()):
                raise ValueError('Invalid JEPA retention target snapshot')
        x=(X-self.mu)/self.sd;x2=(X2-self.mu)/self.sd
        z=encode(self.enc,x)[0]
        target=encode(target_params,x2)[0]
        pred=predict(self.preds[0],z,A)[0]
        return float(np.mean((pred-target)**2))

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
