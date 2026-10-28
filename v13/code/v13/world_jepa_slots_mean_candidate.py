"""Run77 opt-in candidate: true ensemble mean for isolated slot-wise World-JEPA.

The Run76 source intentionally stays frozen. This subclass corrects the
documented return contract without changing training, bootstrap members,
confidence thresholds, permissions, or the existing default implementation.
Software-only; not wired into the runtime or used for gate promotion.
"""
import numpy as np

from v13.world_jepa_slots_isolated import SlotWorldJEPA
from v13.world_jepa_slots_kernels import predict as _predict_kernel

REVISION = "run77-slotwise-ensemble-mean-candidate-v1"


class EnsembleMeanSlotWorldJEPA(SlotWorldJEPA):
    """Use all fitted ensemble members for the point estimate and spread."""

    def predict(self, X, A):
        """Return (ensemble mean (n, slots, k), spread (n, slots)).

        The spread is the unchanged per-dimension ensemble standard deviation
        normalized by target-latent std, averaged across latent dimensions.
        """
        n = len(X)
        z = self.latent(X, target=False).reshape(n * self.S, -1)
        a = A.reshape(n * self.S, -1)
        predictions = np.stack([_predict_kernel(p, z, a)[0] for p in self.preds])
        return (
            predictions.mean(axis=0).reshape(n, self.S, -1),
            (predictions.std(axis=0) / self.zsd).mean(axis=1).reshape(n, self.S),
        )
