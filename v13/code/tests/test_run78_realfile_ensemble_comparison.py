import unittest
from types import SimpleNamespace

import numpy as np

from scripts import run78_realfile_ensemble_comparison as r
from scripts import z12b_world_jepa as world


class TestRun78Integrity(unittest.TestCase):
    def test_action_rows_preserve_exact_slot_and_noop(self):
        x = np.arange(world.SLOTS * 10, dtype=float)
        rows = [
            (x, 0, x + 1, True),
            (x, world.NOOP, x, True),
            (x, len(world.OPS) * world.SLOTS - 1, x, False),
        ]
        X, A, Y = r._action_rows(rows)
        self.assertEqual(X.shape, (3, world.SLOTS * 10))
        self.assertEqual(Y.shape, X.shape)
        self.assertEqual(A.shape, (3, world.SLOTS, len(world.OPS) + 1))
        self.assertTrue((A.sum(2) == 1).all())
        self.assertEqual(A[0, 0, 0], 1)
        self.assertEqual(A[0, 1, -1], 1)
        self.assertTrue((A[1, :, -1] == 1).all())
        self.assertEqual(A[2, world.SLOTS - 1, len(world.OPS) - 1], 1)

    def test_hash_binds_actions_and_outcomes(self):
        x = np.zeros((2, world.SLOTS * 10))
        a = np.zeros((2, world.SLOTS, len(world.OPS) + 1))
        a[:, :, -1] = 1
        d = r._digest(x, a, x)
        a[0, 0, :] = 0
        a[0, 0, 0] = 1
        self.assertNotEqual(d, r._digest(x, a, x))
        y = x.copy()
        y[0, 0] = 1
        self.assertNotEqual(r._digest(x, a, x), r._digest(x, a, y))

    def test_nonregistered_cohorts_refused(self):
        with self.assertRaisesRegex(PermissionError, "RUN78_UNREGISTERED_COHORT"):
            r.run(seeds=(401,))
        with self.assertRaisesRegex(PermissionError, "RUN78_UNREGISTERED_COHORT"):
            r.run(steps=1)

    def test_exact_weight_equality_required(self):
        def model(value):
            return SimpleNamespace(
                enc={"W": np.array([value])},
                tgt={"W": np.array([1.0])},
                preds=[{"W": np.array([1.0])} for _ in range(r.ENSEMBLE)],
                zsd=np.array([1.0]),
            )
        r._equal_fit(model(1.0), model(1.0))
        with self.assertRaisesRegex(AssertionError, "RUN78_TRAINING_WEIGHTS_DIFFER"):
            r._equal_fit(model(1.0), model(2.0))


if __name__ == "__main__":
    unittest.main()
