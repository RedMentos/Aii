"""Run38 isolated six-slot training ablation for slot-shared World-JEPA.

The original Run28 two-slot source, WorldJEPA, collectors and gates are frozen.
No runtime authority, Store, tools or model swap; research SHADOW only.
"""
from __future__ import annotations

import numpy as np

from .world_jepa import WorldJEPA
from .world_jepa_slot_candidate import (
    SlotSharedWorldJEPA, SLOTS, FEATURES, LOCAL_ACTIONS,
    FULL_ACTIONS, _local_actions,
)

REVISION = "run38-world-jepa-full-six-slot-training-shadow-v1"


class FullSlotWorldJEPA(SlotSharedWorldJEPA):
    """Same shared core and parameter count; all six slots per transition.

    One affected local operation + five noop slots. Global noop = six noop
    slots. Zero-action ablation = six all-zero local action vectors.
    The full physical operation-slot support remains independently gated.
    """

    def fit(self, X, A, X2, steps=3000, log_every=500):
        X, A, X2, ids = self._validate(X, A, X2)
        if type(steps) is not int or steps < 0:
            raise ValueError("RUN38_STEPS")
        n = len(X)
        local = _local_actions(ids)
        if local.shape != (n, SLOTS, LOCAL_ACTIONS):
            raise ValueError("RUN38_LOCAL_ACTION_SHAPE")
        xx = X.reshape(n * SLOTS, FEATURES)
        aa = local.reshape(n * SLOTS, LOCAL_ACTIONS)
        yy = X2.reshape(n * SLOTS, FEATURES)
        core = WorldJEPA(seed=self.seed, ensemble=self.ensemble)
        core.fit(xx, aa, yy, steps=steps, log_every=log_every)
        counts = np.bincount(ids[ids >= 0], minlength=FULL_ACTIONS)
        if counts.shape != (FULL_ACTIONS,):
            raise ValueError("RUN38_ACTION_SUPPORT_SHAPE")
        # Exception atomic: no new published core if fit fails.
        self.core = core
        self._full_counts = counts
        self.zsd = np.tile(core.zsd, SLOTS)
        self.history = core.history
        return self
