import inspect
import unittest

import numpy as np

from scripts import run79_realfile_grounded_readout as r


class TestRun79GroundedReadout(unittest.TestCase):
    def test_registered_cohort_is_immutable(self):
        with self.assertRaisesRegex(PermissionError, "RUN79_UNREGISTERED_COHORT"):
            r.run(seeds=(431,))
        with self.assertRaisesRegex(PermissionError, "RUN79_UNREGISTERED_COHORT"):
            r.run(n_train=4)

    def test_supervised_readout_only_accepts_train_arrays(self):
        self.assertEqual(tuple(inspect.signature(r._fit_readout).parameters),
                         ("predicted_train", "train_targets"))
        z = np.arange(12, dtype=float).reshape(4, 3)
        y = np.zeros((4, 60), dtype=float)
        y[:, 0] = np.arange(4)
        w = r._fit_readout(z, y)
        decoded = r._decode(z, w)
        self.assertEqual(decoded.shape, (4, 60))
        self.assertTrue(np.isfinite(decoded).all())
        with self.assertRaisesRegex(ValueError, "RUN79_BAD_READOUT_TRAIN"):
            r._fit_readout(z[:3], y)

    def test_target_slot_error_does_not_average_untouched_slots(self):
        actual = np.zeros((2, 60))
        expected = actual.copy()
        expected[0, 0:10] = 2
        expected[1, 10:20] = 3
        m = r._metrics(actual, expected, np.array([0, 1]))
        self.assertAlmostEqual(m["target_slot_mse"], 6.5)
        self.assertAlmostEqual(m["overall_mse"], 65 / 60)

    def test_nonfinite_and_bad_shapes_are_rejected(self):
        a = np.zeros((2, 60))
        b = a.copy()
        b[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "RUN79_INVALID_OUTCOMES"):
            r._metrics(a, b, np.array([0, 1]))
        with self.assertRaisesRegex(ValueError, "RUN79_BAD_READOUT_SHAPE"):
            r._decode(np.zeros((2, 3)), np.zeros((3, 60)))


if __name__ == "__main__":
    unittest.main()
