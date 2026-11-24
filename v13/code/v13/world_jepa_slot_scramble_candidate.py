"""Run35 SHADOW-only exact-parameter slot-feature locality negative control.

Uses the frozen Run28 slot-shared JEPA unchanged. The fixed bijective feature
permutation deliberately breaks alignment of observed pseudo-slots with physical
action-slot IDs. It is NOT a global-96D capacity-matched model.
"""
from __future__ import annotations

import numpy as np

from .world_jepa_slot_candidate import (
    SlotSharedWorldJEPA, SLOTS, FEATURES, LOCAL_LATENT,
)

REVISION = "run35-slot-alignment-scrambled-shadow-v1"
PERM = np.arange(SLOTS * FEATURES).reshape(SLOTS, FEATURES).T.reshape(-1)
if len(set(PERM.tolist())) != SLOTS * FEATURES:
    raise AssertionError("RUN35_PERM_NOT_BIJECTIVE")


def scramble(X):
    try:
        x = np.asarray(X, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("RUN35_OBS_SHAPE") from exc
    if x.ndim != 2 or x.shape[1] != SLOTS * FEATURES or not np.isfinite(x).all():
        raise ValueError("RUN35_OBS_SHAPE")
    return x[:, PERM]


class ScrambledSlotWorldJEPA:
    """Exactly the Run28 model's trainable core, with wrong feature/slot map."""

    def __init__(self, seed=0, ensemble=5):
        self.seed = seed
        self.ensemble = ensemble

    def fit(self, X, A, X2, steps=3000, log_every=500):
        x, y = scramble(X), scramble(X2)
        core = SlotSharedWorldJEPA(seed=self.seed, ensemble=self.ensemble)
        core.fit(x, A, y, steps=steps, log_every=log_every)
        # Exception-atomic: a failed fit does not publish a partial new core.
        self.core = core
        self.history = core.history
        self.zsd = core.zsd
        return self

    def _ready(self):
        if not hasattr(self, "core"):
            raise ValueError("RUN35_NOT_FITTED")

    def latent(self, X, target=True):
        self._ready()
        return self.core.latent(scramble(X), target=target)

    def predict(self, X, A):
        self._ready()
        return self.core.predict(scramble(X), A)

    def confidence(self, X, A, counts=None):
        self._ready()
        return self.core.confidence(scramble(X), A, counts=counts)

    def collapse_stats(self, X2):
        self._ready()
        return self.core.collapse_stats(scramble(X2))

    def ood(self, X):
        self._ready()
        return self.core.ood(scramble(X))
