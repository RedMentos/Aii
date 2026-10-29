"""Regression: original World-Model ablation cannot invent errors after domain rejection.

Registered synthetic world, seeds, cohort size and primary metric are unchanged.
Invalid counterfactuals stay in the denominator and invalidate the primary.
"""
import unittest
from unittest import mock

from scripts import ablation_world_model_confidence as A
from v13 import world_model as WM


class WorldModelAblationInvalidConsumerTests(unittest.TestCase):
    def with_short_queries(self, fn):
        old = A.Q
        A.Q = 20
        try:
            return fn()
        finally:
            A.Q = old

    def test_original_seed_is_accounted_without_crashing(self):
        r = self.with_short_queries(lambda: A.run_seed(13))
        self.assertEqual(r['fit_status'], 'FITTED')
        self.assertEqual(r['query_count'], 20)
        self.assertEqual(r['labels']['supported_n'] +
                         r['labels']['uncertain_n'], 20)
        self.assertGreater(r['invalid_output_n'], 0)
        self.assertEqual(r['status'], 'UNSCORABLE_INVALID_OUTPUT')
        self.assertEqual(r['error_measured_n'] + r['invalid_output_n'], 20)
        self.assertTrue(all(r[a]['primary'] is None for a in A.ARMS))

    def test_all_invalid_predictions_never_create_primary_or_fake_errors(self):
        def invalid(*args, **kwargs):
            return {'prediction': None, 'confidence': 0.,
                    'label': 'SIMULATION_UNCERTAIN',
                    'reason': 'INVALID_NUMERIC_EVIDENCE'}
        with mock.patch.object(WM, 'counterfactual', side_effect=invalid):
            r = self.with_short_queries(lambda: A.run_seed(13))
        self.assertEqual(r['invalid_output_n'], 20)
        self.assertEqual(r['error_measured_n'], 0)
        self.assertEqual(r['labels']['uncertain_n'], 20)
        self.assertIsNone(r['labels']['uncertain_mean_err'])
        self.assertTrue(all(r[a]['primary'] is None for a in A.ARMS))

    def test_all_valid_control_keeps_original_numeric_primary(self):
        def valid(*args, **kwargs):
            return {'prediction': dict(zip(WM.TARGETS, [1., .5, .5])),
                    'confidence': .5, 'label': 'SIMULATION_SUPPORTED',
                    'coverage': {'samples': 10}, 'model_spread': .1}
        with mock.patch.object(WM, 'counterfactual', side_effect=valid):
            r = self.with_short_queries(lambda: A.run_seed(13))
        self.assertEqual(r['status'], 'COMPLETE')
        self.assertEqual(r['invalid_output_n'], 0)
        self.assertEqual(r['error_measured_n'], 20)
        self.assertEqual(r['labels']['supported_n'], 20)
        self.assertTrue(all(isinstance(r[a]['primary'], float)
                            for a in A.ARMS))

    def test_run_all_cannot_promote_invalid_historical_primary(self):
        r = self.with_short_queries(lambda: A.run_all(seeds=(13,)))
        self.assertEqual(r['verdict'], 'UNSCORABLE_INVALID_OUTPUT')
        self.assertIsNone(r['supported_label_lower_error_of_5'])
        self.assertTrue(all(v is None for v in r['wins_of_5'].values()))
        self.assertTrue(all(r['summary'][a]['mean'] is None for a in A.ARMS))

    def test_original_prereg_cohort_is_unchanged(self):
        self.assertEqual(A.N, 300)
        self.assertEqual(A.PREREG['transitions'], 300)
        self.assertEqual(A.PREREG['queries'], 400)
        self.assertEqual(A.PREREG['primary'], 'Spearman(confidence, -error)')
        self.assertEqual(A.ARMS, ('confidence', 'samples_only',
                                  'spread_only', 'random'))


if __name__ == '__main__':
    unittest.main()
