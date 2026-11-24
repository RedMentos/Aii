"""Run39 action-balanced full-slot SHADOW: exact row multiplicity and safety."""
import unittest
from unittest.mock import patch

import numpy as np

from v13.world_jepa_action_balanced_fullslot_candidate import (
    BalancedFullSlotWorldJEPA, REVISION, AFFECTED_COPIES,
)
from v13.world_jepa_fullslot_candidate import FullSlotWorldJEPA


class FakeCore:
    fail = False
    def __init__(self, seed, ensemble):
        self.seed, self.ensemble = seed, ensemble
        self.zsd = np.ones(16)
        self.history = [{"step": 0}]
        self.rows = None
    def fit(self, X, A, X2, steps=3000, log_every=500):
        if self.fail:
            raise RuntimeError("synthetic-failure")
        self.rows = (X.copy(), A.copy(), X2.copy(), steps)
        return self


def sample():
    X = np.arange(4 * 60, dtype=float).reshape(4, 60)
    A = np.zeros((4, 12))
    A[0, 2] = 1
    A[0, 6 + 3] = 1  # op2 slot3
    A[1, 1] = 1
    A[1, 6 + 5] = 1  # op1 slot5
    A[2, 5] = 1  # global noop
    # row3 is zero-action control
    return X, A, X + 1


class Run39ActionBalanced(unittest.TestCase):
    def setUp(self):
        FakeCore.fail = False

    def test_exact_all_slot_rows_plus_affected_duplicates(self):
        X, A, X2 = sample()
        originals = (X.copy(), A.copy(), X2.copy())
        with patch("v13.world_jepa_action_balanced_fullslot_candidate.WorldJEPA", FakeCore):
            model = BalancedFullSlotWorldJEPA(seed=501).fit(X, A, X2, steps=9)
        xx, aa, yy, steps = model.core.rows
        self.assertEqual((xx.shape, aa.shape, yy.shape), ((32, 10), (32, 6), (32, 10)))
        self.assertEqual(steps, 9)
        self.assertEqual(AFFECTED_COPIES, 4)
        self.assertTrue(np.all(aa[24:28, 2] == 1))
        self.assertTrue(np.all(aa[28:32, 1] == 1))
        self.assertEqual(int(np.sum(aa[:, 2] == 1)), 5)
        self.assertEqual(int(np.sum(aa[:, 1] == 1)), 5)
        self.assertEqual(int(np.sum(aa[:, 5] == 1)), 16)
        self.assertEqual(int(np.sum(aa.sum(1) == 0)), 6)
        self.assertEqual(int(model._full_counts.sum()), 3)
        self.assertEqual(model._full_counts[2 * 6 + 3], 1)
        self.assertEqual(model._full_counts[1 * 6 + 5], 1)
        self.assertEqual(model._full_counts[30], 1)
        self.assertEqual(model.zsd.shape, (96,))
        for before, after in zip(originals, (X, A, X2)):
            np.testing.assert_array_equal(before, after)
        self.assertTrue(REVISION.startswith("run39-"))

    def test_global_noop_and_zero_controls_are_not_duplicated(self):
        X, A, X2 = sample()
        A[0] = 0
        A[1] = 0
        with patch("v13.world_jepa_action_balanced_fullslot_candidate.WorldJEPA", FakeCore):
            model = BalancedFullSlotWorldJEPA(seed=501).fit(X, A, X2)
        aa = model.core.rows[1]
        self.assertEqual(aa.shape, (24, 6))
        self.assertEqual(int(np.sum(aa[:, 5] == 1)), 6)
        self.assertEqual(int(np.sum(aa.sum(1) == 0)), 18)
        self.assertEqual(int(model._full_counts.sum()), 1)

    def test_original_unweighted_fullslot_unchanged(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_fullslot_candidate.WorldJEPA", FakeCore):
            original = FullSlotWorldJEPA(seed=501).fit(X, A, X2)
        self.assertEqual(original.core.rows[0].shape, (24, 10))
        with patch("v13.world_jepa_action_balanced_fullslot_candidate.WorldJEPA", FakeCore):
            candidate = BalancedFullSlotWorldJEPA(seed=501).fit(X, A, X2)
        self.assertEqual(candidate.core.rows[0].shape, (32, 10))

    def test_failure_is_exception_atomic(self):
        X, A, X2 = sample()
        with patch("v13.world_jepa_action_balanced_fullslot_candidate.WorldJEPA", FakeCore):
            model = BalancedFullSlotWorldJEPA(seed=501).fit(X, A, X2)
            old = model.core
            FakeCore.fail = True
            with self.assertRaisesRegex(RuntimeError, "synthetic-failure"):
                model.fit(X, A, X2)
            self.assertIs(model.core, old)
            fresh = BalancedFullSlotWorldJEPA(seed=502)
            with self.assertRaisesRegex(RuntimeError, "synthetic-failure"):
                fresh.fit(X, A, X2)
            self.assertFalse(hasattr(fresh, "core"))

    def test_invalid_action_and_steps_fail_before_core(self):
        X, A, X2 = sample()
        A[0, 6 + 3] = 0
        model = BalancedFullSlotWorldJEPA(seed=501)
        with self.assertRaisesRegex(ValueError, "RUN28_ACTION_SLOT"):
            model.fit(X, A, X2)
        X, A, X2 = sample()
        for steps in (-1, True, 2.5):
            with self.assertRaisesRegex(ValueError, "RUN39_STEPS"):
                model.fit(X, A, X2, steps=steps)
        self.assertFalse(hasattr(model, "core"))


if __name__ == "__main__":
    unittest.main()
