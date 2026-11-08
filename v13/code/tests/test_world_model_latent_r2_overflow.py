"""T8 latent R2 ratio overflow must not persist FITTED evidence."""
import unittest
from unittest.mock import patch
import numpy as np
from v13 import world_model as wm


class Store:
    def __init__(self):
        self.saved = []
    def set_state(self, key, state):
        self.saved.append((key, state))
    def log(self, *args):
        pass


class TestLatentR2Overflow(unittest.TestCase):
    def test_finite_sums_but_overflowed_ratio_refuses_fitted(self):
        rows = [
            {'s': [i / 12, .2, 0., 1.],
             'a': wm.ACTIONS[i % len(wm.ACTIONS)],
             'y': [0., 0., 0.],
             'latent': [1.]} for i in range(16)
        ]
        real_ridge = wm.ridge
        def latent_large_coefficients(X, Y, lam=wm.RIDGE):
            if lam == 1.:
                return np.full((X.shape[1], len(wm.TARGETS)), 1e150)
            return real_ridge(X, Y, lam)
        store = Store()
        with patch.object(wm, 'transitions', return_value=rows), patch.object(
            wm, 'ridge', side_effect=latent_large_coefficients
        ), self.assertRaisesRegex(ValueError, 'T8_NONFINITE_LATENT_SCORE'):
            wm.fit(store)
        self.assertFalse(any(st.get('status') == 'FITTED' for _, st in store.saved))


if __name__ == '__main__':
    unittest.main()
