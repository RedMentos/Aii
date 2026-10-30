"""Run28 isolated slot-shared World-JEPA candidate; SHADOW, no live authority.

Six independent file slots each have 10 observed features. A single WorldJEPA
(EMA encoder + action predictor + inverse-dynamics head) learns local transitions
and is reused across slots. Held-out operation/slot support remains zero even
when the operation has been seen on another slot. This is a research candidate,
not a modification of the original registered Z12b model or experiment.
"""
from __future__ import annotations

import numpy as np

from .world_jepa import WorldJEPA, CF_MIN, COVER_N

SLOTS = 6
FEATURES = 10
OPS = 5
LOCAL_ACTIONS = OPS + 1
FULL_ACTIONS = OPS * SLOTS + 1
LOCAL_LATENT = 16
REVISION = "run28-slot-shared-world-jepa-candidate-v1"


def _array(value, cols, label):
    try:
        x = np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("RUN28_" + label + "_SHAPE") from exc
    if x.ndim != 2 or x.shape[1] != cols or not np.isfinite(x).all():
        raise ValueError("RUN28_" + label + "_SHAPE")
    return x


def _decode(A):
    """Return exact full action IDs 0..30, or -1 for zero-action controls."""
    A = _array(A, LOCAL_ACTIONS + SLOTS, "ACTION")
    ids = np.empty(len(A), dtype=int)
    for i, row in enumerate(A):
        if np.all(row == 0):
            ids[i] = -1
            continue
        op, slot = row[:LOCAL_ACTIONS], row[LOCAL_ACTIONS:]
        if (not np.all((row == 0) | (row == 1))
                or op.sum() != 1):
            raise ValueError("RUN28_ACTION_ONEHOT")
        k = int(np.argmax(op))
        if k == OPS:
            if slot.sum() != 0:
                raise ValueError("RUN28_NOOP_SLOT")
            ids[i] = OPS * SLOTS
        else:
            if slot.sum() != 1:
                raise ValueError("RUN28_ACTION_SLOT")
            ids[i] = k * SLOTS + int(np.argmax(slot))
    return ids


def _local_actions(ids):
    """N full actions -> N x 6 slots x 6 local action one-hots."""
    local = np.zeros((len(ids), SLOTS, LOCAL_ACTIONS), dtype=float)
    for i, action in enumerate(ids):
        if action == -1:
            continue  # original zeroed-action control remains exactly zero
        local[i, :, OPS] = 1.
        if action < OPS * SLOTS:
            op, slot = divmod(int(action), SLOTS)
            local[i, slot, OPS] = 0.
            local[i, slot, op] = 1.
    return local


class SlotSharedWorldJEPA:
    """Shared local JEPA with exact full operation-slot support gating.

    Uses one affected slot and one deterministic unaffected slot per training
    transition; noop/zero controls use two deterministic slots. Prediction
    applies the learned local dynamics to all six slots, concatenating 96
    latent coordinates. No memory, tools, state authority or deployment.
    """

    def __init__(self, seed=0, ensemble=5):
        if type(seed) is not int or seed < 0 or type(ensemble) is not int or not 1 <= ensemble <= 16:
            raise ValueError("RUN28_INVALID_CONFIGURATION")
        self.seed = seed
        self.ensemble = ensemble

    def _validate(self, X, A, X2=None):
        X = _array(X, SLOTS * FEATURES, "OBS")
        A = _array(A, LOCAL_ACTIONS + SLOTS, "ACTION")
        if len(X) != len(A):
            raise ValueError("RUN28_TRANSITION_LENGTH")
        ids = _decode(A)
        if X2 is None:
            return X, A, ids
        X2 = _array(X2, SLOTS * FEATURES, "NEXT_OBS")
        if X2.shape != X.shape or len(X) < 2 or len(X) > 100000:
            raise ValueError("RUN28_TRANSITION_SHAPE")
        return X, A, X2, ids

    def fit(self, X, A, X2, steps=3000, log_every=500):
        X, A, X2, ids = self._validate(X, A, X2)
        if type(steps) is not int or steps < 0:
            raise ValueError("RUN28_STEPS")
        rng = np.random.default_rng(self.seed)
        slots = np.empty((len(ids), 2), dtype=int)
        for i, action in enumerate(ids):
            if 0 <= action < OPS * SLOTS:
                target = int(action % SLOTS)
                other = int(rng.choice([s for s in range(SLOTS) if s != target]))
                slots[i] = (target, other)
            else:
                slots[i] = rng.choice(SLOTS, size=2, replace=False)
        rows = np.arange(len(ids))[:, None]
        obs = X.reshape(len(X), SLOTS, FEATURES)
        next_obs = X2.reshape(len(X), SLOTS, FEATURES)
        local = _local_actions(ids)
        xx = obs[rows, slots].reshape(-1, FEATURES)
        aa = local[rows, slots].reshape(-1, LOCAL_ACTIONS)
        yy = next_obs[rows, slots].reshape(-1, FEATURES)
        core = WorldJEPA(seed=self.seed, ensemble=self.ensemble)
        core.fit(xx, aa, yy, steps=steps, log_every=log_every)
        counts = np.bincount(ids[ids >= 0], minlength=FULL_ACTIONS)
        if len(counts) != FULL_ACTIONS:
            raise ValueError("RUN28_ACTION_SUPPORT_SHAPE")
        # Exception-atomic candidate publication: no partial core on failure.
        self.core = core
        self._full_counts = counts
        self.zsd = np.tile(core.zsd, SLOTS)
        self.history = core.history
        return self

    def _ready(self):
        if not hasattr(self, "core"):
            raise ValueError("RUN28_NOT_FITTED")

    def latent(self, X, target=True):
        self._ready()
        X = _array(X, SLOTS * FEATURES, "OBS")
        z = self.core.latent(X.reshape(-1, FEATURES), target=target)
        return z.reshape(len(X), SLOTS * LOCAL_LATENT)

    def predict(self, X, A):
        self._ready()
        X, A, ids = self._validate(X, A)
        local = _local_actions(ids)
        z, spread = self.core.predict(
            X.reshape(-1, FEATURES), local.reshape(-1, LOCAL_ACTIONS))
        return (z.reshape(len(X), SLOTS * LOCAL_LATENT),
                spread.reshape(len(X), SLOTS).max(axis=1))

    def confidence(self, X, A, counts=None):
        self._ready()
        X, A, ids = self._validate(X, A)
        n = len(X)
        local = _local_actions(ids)
        c, _ = self.core.confidence(
            X.reshape(-1, FEATURES), local.reshape(-1, LOCAL_ACTIONS))
        c = np.asarray(c, dtype=float).reshape(n, SLOTS).min(axis=1)
        if counts is not None:
            requested = np.asarray(counts, dtype=object)
            if requested.shape != (n,):
                raise ValueError("RUN28_SUPPORT_SHAPE")
        else:
            requested = [None] * n
        out = np.zeros(n, dtype=float)
        for i, action in enumerate(ids):
            if action < 0:
                continue
            count = int(self._full_counts[action])
            if requested[i] is not None:
                v = requested[i]
                if (isinstance(v, (bool, np.bool_))
                        or not isinstance(v, (int, float, np.integer, np.floating))):
                    continue
                value = float(v)
                if not np.isfinite(value) or value < 0 or not value.is_integer():
                    continue
                count = min(count, int(value))
            if count <= 0:
                continue
            support = -np.expm1(-count / COVER_N)
            out[i] = np.clip(c[i] * support, 0., 1.)
        if self.ensemble < 2:
            out[:] = 0.
        return out, ["MODEL_SIMULATION" if v >= CF_MIN else "SIMULATION_UNCERTAIN"
                     for v in out]

    def collapse_stats(self, X2):
        self._ready()
        X2 = _array(X2, SLOTS * FEATURES, "NEXT_OBS")
        # Reports shared local latent rank, not the rank of concatenated 96D
        # states. The capacity mismatch to original 16D is explicit.
        return self.core.collapse_stats(X2.reshape(-1, FEATURES))

    def ood(self, X):
        self._ready()
        X = _array(X, SLOTS * FEATURES, "OBS")
        return self.core.ood(X.reshape(-1, FEATURES)).reshape(len(X), SLOTS).max(axis=1)
