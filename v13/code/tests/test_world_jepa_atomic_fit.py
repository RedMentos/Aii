"""Exception-atomic World-JEPA SHADOW fit; no native model or learning authority."""
import copy
import unittest
from unittest.mock import patch

import numpy as np

from v13 import world_jepa as wj


class WorldJEPAAtomicFit(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[0., 1.], [1., 0.], [0.4, 0.6], [0.6, 0.4]])
        self.A = np.array([[1., 0.], [0., 1.], [1., 0.], [0., 1.]])
        self.X2 = self.X[:, ::-1].copy()

    def fitted(self):
        return wj.WorldJEPA(seed=7, ensemble=2).fit(
            self.X, self.A, self.X2, steps=0
        )

    def snapshot(self, m):
        return copy.deepcopy(m.__dict__)

    def assert_unchanged(self, m, old):
        self.assertEqual(set(m.__dict__), set(old))
        for key, value in old.items():
            current = m.__dict__[key]
            if isinstance(value, np.ndarray):
                np.testing.assert_array_equal(current, value, err_msg=key)
            elif isinstance(value, list) and key == "preds":
                self.assertEqual(len(current), len(value))
                for a, b in zip(current, value):
                    for k in b:
                        np.testing.assert_array_equal(a[k], b[k], err_msg=k)
            elif isinstance(value, dict) and key in ("enc", "tgt"):
                for k in value:
                    np.testing.assert_array_equal(current[k], value[k], err_msg=k)
            else:
                self.assertEqual(current, value, key)

    def test_failed_main_training_preserves_complete_previous_fit(self):
        m = self.fitted()
        old = self.snapshot(m)
        before = m.confidence(self.X, self.A)
        with patch.object(wj, "loss_grads", side_effect=RuntimeError("injected main failure")):
            with self.assertRaisesRegex(RuntimeError, "injected main failure"):
                m.fit(self.X + 2, self.A, self.X2 + 2, steps=1)
        self.assert_unchanged(m, old)
        after = m.confidence(self.X, self.A)
        np.testing.assert_array_equal(before[0], after[0])
        self.assertEqual(before[1], after[1])

    def test_failed_ensemble_training_preserves_complete_previous_fit(self):
        m = self.fitted()
        old = self.snapshot(m)
        original = wj._init_pred
        calls = [0]

        def flaky(*args):
            calls[0] += 1
            if calls[0] == 2:  # second predictor belongs to ensemble
                raise RuntimeError("injected ensemble failure")
            return original(*args)

        with patch.object(wj, "_init_pred", side_effect=flaky):
            with self.assertRaisesRegex(RuntimeError, "injected ensemble failure"):
                m.fit(self.X + 1, self.A, self.X2 + 1, steps=0)
        self.assert_unchanged(m, old)

    def test_first_fit_failure_exposes_no_partial_state(self):
        m = wj.WorldJEPA(seed=7, ensemble=2)
        before = dict(m.__dict__)
        with patch.object(wj, "_init_pred", side_effect=RuntimeError("init failure")):
            with self.assertRaisesRegex(RuntimeError, "init failure"):
                m.fit(self.X, self.A, self.X2, steps=0)
        self.assertEqual(m.__dict__, before)
        self.assertFalse(hasattr(m, "enc"))

    def test_nonfinite_learned_latents_rejected_without_clobbering_fit(self):
        m = self.fitted()
        old = self.snapshot(m)

        def nonfinite_encode(enc, x):
            return np.full((len(x), wj.Z), np.nan), np.zeros((len(x), wj.H))

        with patch.object(wj, "encode", side_effect=nonfinite_encode):
            with np.errstate(all="ignore"):
                with self.assertRaisesRegex(ValueError, "nonfinite learned state"):
                    m.fit(self.X, self.A, self.X2, steps=0)
        self.assert_unchanged(m, old)

    def test_successful_refit_publishes_new_state_and_deterministic_seed(self):
        m = self.fitted()
        old_mu = m.mu.copy()
        shifted = self.X + 3
        m.fit(shifted, self.A, self.X2 + 3, steps=2, log_every=1)
        self.assertFalse(np.array_equal(m.mu, old_mu))
        np.testing.assert_array_equal(m.mu, shifted.mean(0))
        self.assertEqual(len(m.history), 2)
        self.assertEqual(len(m.preds), 2)
        control = wj.WorldJEPA(seed=7, ensemble=2).fit(
            shifted, self.A, self.X2 + 3, steps=2, log_every=1
        )
        for key in m.enc:
            np.testing.assert_array_equal(m.enc[key], control.enc[key])
        np.testing.assert_array_equal(m._ztrain, control._ztrain)


if __name__ == "__main__":
    unittest.main()
