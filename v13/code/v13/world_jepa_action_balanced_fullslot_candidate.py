"""Run39 isolated action-balanced six-slot World-JEPA SHADOW research candidate.

One copy of all six slots, plus four extra affected-slot rows per ordinary
action: five action rows vs five noop rows, same shared WorldJEPA core.
No production wiring, model swap, Store, tools or Age authority.
"""
from __future__ import annotations

import numpy as np

from .world_jepa import WorldJEPA
from .world_jepa_fullslot_candidate import FullSlotWorldJEPA
from .world_jepa_slot_candidate import (
    SLOTS, FEATURES, OPS, LOCAL_ACTIONS, FULL_ACTIONS, _local_actions,
)

REVISION = "run39-world-jepa-action-balanced-fullslot-shadow-v1"
AFFECTED_COPIES = SLOTS - 2  # four extra + one base = five action rows


class BalancedFullSlotWorldJEPA(FullSlotWorldJEPA):
    """Same parameters, action/zero controls and 96D inference as Run38."""

    def fit(self, X, A, X2, steps=3000, log_every=500):
        X, A, X2, ids = self._validate(X, A, X2)
        if type(steps) is not int or steps < 0:
            raise ValueError("RUN39_STEPS")
        n = len(X)
        obs = X.reshape(n, SLOTS, FEATURES)
        nxt = X2.reshape(n, SLOTS, FEATURES)
        local = _local_actions(ids)
        if local.shape != (n, SLOTS, LOCAL_ACTIONS):
            raise ValueError("RUN39_LOCAL_ACTION_SHAPE")
        affected = np.flatnonzero((ids >= 0) & (ids < OPS * SLOTS))
        slots = ids[affected] % SLOTS
        extra_x = np.repeat(obs[affected, slots], AFFECTED_COPIES, axis=0)
        extra_a = np.repeat(local[affected, slots], AFFECTED_COPIES, axis=0)
        extra_y = np.repeat(nxt[affected, slots], AFFECTED_COPIES, axis=0)
        xx = np.concatenate((obs.reshape(n * SLOTS, FEATURES), extra_x), axis=0)
        aa = np.concatenate((local.reshape(n * SLOTS, LOCAL_ACTIONS), extra_a), axis=0)
        yy = np.concatenate((nxt.reshape(n * SLOTS, FEATURES), extra_y), axis=0)
        if len(xx) != n * SLOTS + len(affected) * AFFECTED_COPIES:
            raise ValueError("RUN39_TRAINING_ROWS")
        core = WorldJEPA(seed=self.seed, ensemble=self.ensemble)
        core.fit(xx, aa, yy, steps=steps, log_every=log_every)
        counts = np.bincount(ids[ids >= 0], minlength=FULL_ACTIONS)
        if counts.shape != (FULL_ACTIONS,):
            raise ValueError("RUN39_ACTION_SUPPORT_SHAPE")
        # Publish only after all training and validation succeed.
        self.core = core
        self._full_counts = counts
        self.zsd = np.tile(core.zsd, SLOTS)
        self.history = core.history
        return self
