"""Preregistered World-Model real numeric evidence guard; no native/model calls."""
import unittest
import warnings
import numpy as np

from v13 import world_model as wm


class WorldModelNumericGuardTests(unittest.TestCase):
    def test_complex_numpy_scalar_never_silently_truncated(self):
        for value in (np.complex128(1+2j), np.complex64(1+2j),
                      np.complex128(1+0j), complex(1, 2)):
            with self.subTest(value=repr(value)), warnings.catch_warnings():
                warnings.simplefilter("error")
                self.assertFalse(wm._finite_vector([value, 0., 0., 0.], 4))

    def test_timedelta_and_malformed_real_conversion_fail_closed(self):
        for value in (np.timedelta64(1, "s"), np.timedelta64("NaT")):
            with self.subTest(value=repr(value)):
                self.assertFalse(wm._finite_vector([value, 0., 0., 0.], 4))

    def test_invalid_complex_state_cannot_claim_coverage(self):
        st = {"states": {"simple": [[1., 0., 0., 0.]]}}
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            got = wm.coverage(st, [np.complex128(1+2j), 0., 0., 0.], "simple")
        self.assertTrue(got["invalid"])
        self.assertEqual(got["samples"], 0)
        self.assertIsNone(got["ood_distance"])

    def test_valid_real_numpy_vectors_preserved(self):
        self.assertTrue(wm._finite_vector([np.float64(1.5), np.int64(2), 0., 0.], 4))
        self.assertFalse(wm._finite_vector([np.bool_(True), 0., 0., 0.], 4))
        self.assertFalse(wm._finite_vector([float("nan"), 0., 0., 0.], 4))
        self.assertFalse(wm._finite_vector([float("inf"), 0., 0., 0.], 4))


if __name__ == "__main__":
    unittest.main()
