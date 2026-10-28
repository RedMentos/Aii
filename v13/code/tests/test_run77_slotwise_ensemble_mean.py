"""Run77 deterministic regression: true ensemble mean, frozen Run76 untouched."""
import unittest
from unittest.mock import patch

import numpy as np

from v13.world_jepa_slots_isolated import SlotWorldJEPA
from v13.world_jepa_slots_mean_candidate import EnsembleMeanSlotWorldJEPA, REVISION


def _member(offset):
    return {
        "P1": np.zeros((1, 3), dtype=float),
        "c1": np.zeros(1, dtype=float),
        "P2": np.zeros((1, 1), dtype=float),
        "c2": np.array([offset], dtype=float),
    }


def _model(cls, offsets):
    m = cls(slots=1, ensemble=len(offsets), k=1)
    m.preds = [_member(v) for v in offsets]
    m.zsd = np.ones(1, dtype=float)
    return m


def _latent(X, target=True):
    return np.full((len(X), 1, 1), 1.0 if target else 0.0)


class TestRun77EnsembleMean(unittest.TestCase):
    def setUp(self):
        self.x = np.zeros((2, 1), dtype=float)
        self.a = np.array([[[1.0, 0.0]], [[1.0, 0.0]]])

    def test_mean_spread_and_original_discrepancy(self):
        old = _model(SlotWorldJEPA, [0.0, 2.0])
        new = _model(EnsembleMeanSlotWorldJEPA, [0.0, 2.0])
        with patch.object(old, "latent", side_effect=_latent), patch.object(new, "latent", side_effect=_latent):
            legacy, old_spread = old.predict(self.x, self.a)
            actual_mean, new_spread = new.predict(self.x, self.a)
        np.testing.assert_allclose(legacy, 0.0)
        np.testing.assert_allclose(actual_mean, 1.0)
        np.testing.assert_allclose(old_spread, 1.0)
        np.testing.assert_allclose(new_spread, old_spread)
        self.assertEqual(actual_mean.shape, (2, 1, 1))
        self.assertEqual(new_spread.shape, (2, 1))

    def test_mean_is_order_invariant_legacy_is_not(self):
        values = []
        for offsets in ([0.0, 2.0], [2.0, 0.0]):
            old = _model(SlotWorldJEPA, offsets)
            new = _model(EnsembleMeanSlotWorldJEPA, offsets)
            with patch.object(old, "latent", side_effect=_latent), patch.object(new, "latent", side_effect=_latent):
                values.append((old.predict(self.x, self.a)[0], new.predict(self.x, self.a)[0]))
        self.assertFalse(np.array_equal(values[0][0], values[1][0]))
        np.testing.assert_array_equal(values[0][1], values[1][1])

    def test_one_member_matches_frozen_implementation(self):
        old = _model(SlotWorldJEPA, [2.0])
        new = _model(EnsembleMeanSlotWorldJEPA, [2.0])
        with patch.object(old, "latent", side_effect=_latent), patch.object(new, "latent", side_effect=_latent):
            for actual, expected in zip(new.predict(self.x, self.a), old.predict(self.x, self.a)):
                np.testing.assert_array_equal(actual, expected)

    def test_slot_errors_use_corrected_point_estimate(self):
        old = _model(SlotWorldJEPA, [0.0, 2.0])
        new = _model(EnsembleMeanSlotWorldJEPA, [0.0, 2.0])
        with patch.object(old, "latent", side_effect=_latent), patch.object(new, "latent", side_effect=_latent):
            np.testing.assert_allclose(old.slot_errors(self.x, self.a, self.x), 1.0)
            np.testing.assert_allclose(new.slot_errors(self.x, self.a, self.x), 0.0)

    def test_original_method_and_revision_remain_unchanged(self):
        self.assertIsNot(SlotWorldJEPA.predict, EnsembleMeanSlotWorldJEPA.predict)
        self.assertEqual(REVISION, "run77-slotwise-ensemble-mean-candidate-v1")
        self.assertEqual(SlotWorldJEPA.__module__, "v13.world_jepa_slots_isolated")


if __name__ == "__main__":
    unittest.main()
