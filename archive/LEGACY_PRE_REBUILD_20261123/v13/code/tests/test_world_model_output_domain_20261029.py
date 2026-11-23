"""Preregistered World-Model nonphysical output-domain counterexamples.

Deterministic synthetic FITTED states; no native model, private Store or
registered training-cohort mutation. Only tests the read-only prediction API.
"""
import unittest
import numpy as np

from v13 import world_model as WM


class WorldModelOutputDomainTests(unittest.TestCase):
    def state(self, log_duration=.4, success=.7, log_chars=.6):
        s = [.5, 0., 0., 1.]
        points = [[.5 + .0001*i, 0., 0., 1.] for i in range(16)]
        weights = np.zeros((WM.ENSEMBLE,
                            1 + 4 + len(WM.ACTIONS), len(WM.TARGETS)))
        weights[:, 0, :] = [log_duration, success, log_chars]
        st = {
            'revision': WM.REVISION,
            'status': 'FITTED',
            'support_scope': 'TRAIN_SPLIT_ONLY_HELDOUT_EXCLUDED',
            'states': {'simple': points},
            'support_counts': {'simple': len(points)},
            'forward': weights.tolist(),
        }
        return s, st

    def assert_invalid(self, **kwargs):
        s, st = self.state(**kwargs)
        out = WM.counterfactual(None, s, 'simple', st=st)
        self.assertEqual(out['label'], 'SIMULATION_UNCERTAIN')
        self.assertEqual(out['confidence'], 0.)
        self.assertEqual(out['reason'], 'INVALID_NUMERIC_EVIDENCE')
        self.assertIsNone(out['prediction'])
        self.assertEqual(out['authority'], 'HYPOTHESIS')

    def test_negative_log_duration_is_not_a_supported_negative_seconds(self):
        self.assert_invalid(log_duration=-.5)

    def test_negative_log_output_chars_is_not_supported(self):
        self.assert_invalid(log_chars=-.1)

    def test_out_of_range_success_probability_is_not_supported(self):
        for probability in (-.01, 1.01):
            with self.subTest(probability=probability):
                self.assert_invalid(success=probability)

    def test_valid_in_support_forecast_remains_supported(self):
        s, st = self.state()
        out = WM.counterfactual(None, s, 'simple', st=st)
        self.assertEqual(out['label'], 'SIMULATION_SUPPORTED')
        self.assertGreaterEqual(out['confidence'], WM.CF_MIN)
        self.assertGreater(out['prediction']['duration_s'], 0.)
        self.assertAlmostEqual(out['prediction']['success'], .7)
        self.assertEqual(out['authority'], 'HYPOTHESIS')

    def test_valid_exact_zero_duration_and_chars_remain_allowed(self):
        s, st = self.state(log_duration=0., log_chars=0., success=0.)
        out = WM.counterfactual(None, s, 'simple', st=st)
        self.assertEqual(out['label'], 'SIMULATION_SUPPORTED')
        self.assertEqual(out['prediction']['duration_s'], 0.)


if __name__ == '__main__':
    unittest.main()
