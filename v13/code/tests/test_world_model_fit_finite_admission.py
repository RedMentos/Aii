"""T8 coefficient and score admission: never persist a FITTED state on corrupt matrices."""
import unittest
from unittest.mock import patch
import numpy as np
from v13 import world_model as wm


class Store:
    def __init__(self):
        self.saved = []
        self.logs = []
    def set_state(self, key, state):
        self.saved.append((key, state))
    def log(self, *args):
        self.logs.append(args)


def observations():
    return [
        {'s': [i / 12, .2, 0., 1.], 'a': wm.ACTIONS[i % 4],
         'y': [float(i % 3), float(i % 2), float(i % 5) / 8],
         'latent': None} for i in range(16)
    ]


class TestFitFiniteAdmission(unittest.TestCase):
    def test_matrix_rejects_nan_inf_wrong_shape(self):
        for bad in (np.full((9, 3), np.nan), np.full((9, 3), np.inf),
                    np.zeros((8, 3)), [[1 + 1j] * 3] * 9):
            with self.subTest(shape=np.shape(bad)), self.assertRaises(ValueError):
                wm._require_finite_fit_matrix(bad, (9, 3), 'FORWARD')

    def test_finite_matrix_accepted(self):
        np.testing.assert_array_equal(
            wm._require_finite_fit_matrix(np.ones((9, 3)), (9, 3), 'FORWARD'),
            np.ones((9, 3)))

    def test_corrupt_forward_coefficients_never_persist_fitted(self):
        store = Store()
        with patch.object(wm, 'transitions', return_value=observations()), patch.object(
            wm, 'ridge', return_value=np.full((9, 3), np.nan)
        ), self.assertRaisesRegex(ValueError, 'T8_INVALID_FIT_FORWARD'):
            wm.fit(store)
        self.assertFalse(any(s.get('status') == 'FITTED' for _, s in store.saved))

    def test_corrupt_inverse_coefficients_never_persist_fitted(self):
        store = Store()
        original = wm.ridge
        def corrupt_inverse(X, Y, lam=wm.RIDGE):
            if Y.shape[1] == len(wm.ACTIONS):
                return np.full((X.shape[1], len(wm.ACTIONS)), np.inf)
            return original(X, Y, lam)
        with patch.object(wm, 'transitions', return_value=observations()), patch.object(
            wm, 'ridge', side_effect=corrupt_inverse
        ), self.assertRaisesRegex(ValueError, 'T8_INVALID_FIT_INVERSE'):
            wm.fit(store)
        self.assertFalse(any(s.get('status') == 'FITTED' for _, s in store.saved))

    def test_normal_fit_still_persists(self):
        store = Store()
        with patch.object(wm, 'transitions', return_value=observations()):
            result = wm.fit(store)
        self.assertEqual(result['status'], 'FITTED')
        self.assertEqual(store.saved[-1][1]['status'], 'FITTED')


if __name__ == '__main__':
    unittest.main()
