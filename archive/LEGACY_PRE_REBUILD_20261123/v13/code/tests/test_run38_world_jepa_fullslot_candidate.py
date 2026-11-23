"""Run38 six-slot World-JEPA SHADOW candidate: exact action and source controls."""
import unittest
from unittest.mock import patch

import numpy as np

from v13.world_jepa_fullslot_candidate import FullSlotWorldJEPA, REVISION
from v13.world_jepa_slot_candidate import SlotSharedWorldJEPA


class FakeCore:
    instances = []
    fail = False

    def __init__(self, seed, ensemble):
        self.seed, self.ensemble = seed, ensemble
        self.zsd = np.ones(16)
        self.history = [{"step": 0, "loss": .5}]
        self.data = None
        self.instances.append(self)

    def fit(self, X, A, X2, steps=3000, log_every=500):
        if self.fail:
            raise RuntimeError("synthetic-fit-failure")
        self.data = (X.copy(), A.copy(), X2.copy(), steps, log_every)
        return self


def sample():
    X = np.arange(3 * 60, dtype=float).reshape(3, 60)
    X2 = X + 1
    A = np.zeros((3, 12))
    A[0, 2] = 1
    A[0, 6 + 3] = 1  # write_digits on physical slot 3
    A[1, 5] = 1  # global noop
    # row 2 = zero-action ablation, not noop
    return X, A, X2


class Run38FullSlot(unittest.TestCase):
    def setUp(self):
        FakeCore.instances.clear()
        FakeCore.fail = False

    def test_six_slots_and_exact_local_action_mapping(self):
        X, A, X2 = sample()
        frozen = (X.copy(), A.copy(), X2.copy())
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            model = FullSlotWorldJEPA(seed=401, ensemble=5).fit(X, A, X2, steps=7)
        x, a, y, steps, _ = model.core.data
        self.assertEqual(x.shape, (18, 10))
        self.assertEqual(a.shape, (18, 6))
        self.assertEqual(y.shape, (18, 10))
        self.assertEqual(steps, 7)
        self.assertEqual(a.reshape(3, 6, 6)[0, 3].tolist(), [0, 0, 1, 0, 0, 0])
        for slot in (0, 1, 2, 4, 5):
            self.assertEqual(a.reshape(3, 6, 6)[0, slot].tolist(),
                             [0, 0, 0, 0, 0, 1])
        self.assertTrue(np.all(a.reshape(3, 6, 6)[1, :, 5] == 1))
        self.assertTrue(np.all(a.reshape(3, 6, 6)[2] == 0))
        for before, after in zip(frozen, (X, A, X2)):
            np.testing.assert_array_equal(before, after)
        self.assertEqual(model.zsd.shape, (96,))
        self.assertTrue(REVISION.startswith("run38-"))

    def test_full_action_support_exact_and_zero_control_excluded(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            model = FullSlotWorldJEPA(seed=401).fit(X, A, X2)
        self.assertEqual(model._full_counts.shape, (31,))
        self.assertEqual(model._full_counts[2 * 6 + 3], 1)
        self.assertEqual(model._full_counts[30], 1)
        self.assertEqual(int(model._full_counts.sum()), 2)
        self.assertEqual(model._full_counts[2 * 6 + 4], 0)

    def test_original_two_slot_source_behavior_is_not_modified(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_slot_candidate.WorldJEPA", FakeCore):
            original = SlotSharedWorldJEPA(seed=401).fit(X, A, X2, steps=7)
        self.assertEqual(original.core.data[0].shape, (6, 10))
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            candidate = FullSlotWorldJEPA(seed=401).fit(X, A, X2, steps=7)
        self.assertEqual(candidate.core.data[0].shape, (18, 10))

    def test_invalid_action_fails_closed_before_fit(self):
        X, A, X2 = sample()
        A[0, 6 + 3] = 0
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            model = FullSlotWorldJEPA(seed=401)
            with self.assertRaisesRegex(ValueError, "RUN28_ACTION_SLOT"):
                model.fit(X, A, X2)
            self.assertFalse(hasattr(model, "core"))

    def test_fit_failure_does_not_publish_partial_core(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            model = FullSlotWorldJEPA(seed=401).fit(X, A, X2)
            old = model.core
            FakeCore.fail = True
            with self.assertRaisesRegex(RuntimeError, "synthetic-fit-failure"):
                model.fit(X, A, X2)
            self.assertIs(model.core, old)
            empty = FullSlotWorldJEPA(seed=402)
            with self.assertRaisesRegex(RuntimeError, "synthetic-fit-failure"):
                empty.fit(X, A, X2)
            self.assertFalse(hasattr(empty, "core"))

    def test_steps_validation(self):
        X, A, X2 = sample()
        model = FullSlotWorldJEPA(seed=401)
        for steps in (-1, 2.5, True):
            with self.assertRaisesRegex(ValueError, "RUN38_STEPS"):
                model.fit(X, A, X2, steps=steps)
        self.assertFalse(hasattr(model, "core"))


if __name__ == "__main__":
    unittest.main()
