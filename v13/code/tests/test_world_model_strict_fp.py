"""Strict NumPy arithmetic errors must not escape as unclassified FITTED evidence."""
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


class TestStrictLatentOverflow(unittest.TestCase):
    def test_overflow_refused_even_under_strict_numpy_settings(self):
        rows = [
            {'s': [i / 12, .2, 0., 1.],
             'a': wm.ACTIONS[i % len(wm.ACTIONS)],
             'y': [0., 0., 0.],
             'latent': [1.]} for i in range(16)
        ]
        original = wm.ridge
        def latent_huge(X, Y, lam=wm.RIDGE):
            if lam == 1.:
                return np.full((X.shape[1], len(wm.TARGETS)), 1e200)
            return original(X, Y, lam)
        store = Store()
        with patch.object(wm, 'transitions', return_value=rows), patch.object(
            wm, 'ridge', side_effect=latent_huge
        ), np.errstate(all='raise'), self.assertRaisesRegex(
            ValueError, 'T8_NONFINITE_LATENT_SCORE'
        ):
            wm.fit(store)
        self.assertFalse(any(s.get('status') == 'FITTED' for _, s in store.saved))


if __name__ == '__main__':
    unittest.main()
