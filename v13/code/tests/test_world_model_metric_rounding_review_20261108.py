"""T8 metric rounding must not turn finite evidence into infinity."""
import json
import math
import unittest
from unittest.mock import patch

import numpy as np

from v13 import world_model as wm


class Store:
    def __init__(self):
        self.saved = []

    def set_state(self, key, value):
        self.saved.append((key, value))

    def log(self, *args):
        pass


def observations(latent):
    return [
        {'s': [i / 12, .2, 0., 1.], 'a': wm.ACTIONS[i % len(wm.ACTIONS)],
         'y': [0., 0., 0.], 'latent': latent} for i in range(16)
    ]


class TestMetricRounding(unittest.TestCase):
    def test_regular_rounding_keeps_numpy_behavior(self):
        values = np.array([-1.23456, -0.00005, 0., 0.34567, 1.23456])
        self.assertEqual(wm._round_finite_metrics(values), np.round(values, 4).tolist())

    def test_nonfinite_values_are_rejected(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'T8_NONFINITE_ROUNDED_METRIC'):
                wm._round_finite_metrics([value])

    def test_route_finite_large_error_stays_finite_even_with_strict_numpy(self):
        rows = [{'a': 'simple', 'y': [0., 0., 0.]},
                {'a': 'simple', 'y': [0., 0., 0.]}]
        with np.errstate(over='raise', invalid='raise'):
            result = wm.heldout_route_errors(
                rows, [0], [1], [[1e305, 0., 0.]], [[0., 0., 0.]])
        self.assertTrue(math.isfinite(result['simple']['mae']['log_duration']))
        self.assertEqual(result['simple']['mae']['log_duration'], 1e305)

    def test_latent_score_stays_json_finite_after_rounding(self):
        original = wm.ridge

        def large_latent(X, Y, lam=wm.RIDGE):
            if lam == 1.:
                return np.full((X.shape[1], len(wm.TARGETS)), 1e146)
            return original(X, Y, lam)

        for mode in ('ignore', 'raise'):
            with self.subTest(mode=mode):
                store = Store()
                with patch.object(wm, 'transitions', return_value=observations([1.])), \
                        patch.object(wm, 'ridge', side_effect=large_latent), \
                        np.errstate(over=mode, invalid=mode):
                    result = wm.fit(store)
                self.assertEqual(result['status'], 'FITTED')
                self.assertTrue(all(math.isfinite(x) for x in result['metrics']['state_align']['r2'].values()))
                json.dumps(store.saved[-1][1], allow_nan=False)

    def test_pooled_fit_metrics_stay_json_finite_after_rounding(self):
        original = wm.ridge

        def large_forward(X, Y, lam=wm.RIDGE):
            if Y.shape[1] == len(wm.TARGETS):
                return np.full((X.shape[1], len(wm.TARGETS)), 1e305)
            return original(X, Y, lam)

        store = Store()
        with patch.object(wm, 'transitions', return_value=observations(None)), \
                patch.object(wm, 'ridge', side_effect=large_forward), \
                np.errstate(over='ignore', invalid='ignore'):
            result = wm.fit(store)
        self.assertEqual(result['status'], 'FITTED')
        self.assertTrue(all(math.isfinite(x) for x in result['metrics']['forward_mae'].values()))
        json.dumps(store.saved[-1][1], allow_nan=False)


if __name__ == '__main__':
    unittest.main()
