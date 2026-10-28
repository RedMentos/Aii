"""Run54 pinned synthetic-only digital outcome baselines; no authority."""
import copy
import unittest
from unittest import mock

import numpy as np

from v13 import world_model
from v13 import world_jepa_action_outcome_adapter as adapter
from v13 import world_jepa_synthetic_outcome_baselines as baseline
from tests.test_run50_world_jepa_action_outcome_adapter import FakeReadOnlyView


class Run54SyntheticOutcomeBaselines(unittest.TestCase):
    def setUp(self):
        self.bundle = adapter.build(world_model.transitions(FakeReadOnlyView(128)))

    def evaluate(self, **kwargs):
        options = {'approved_shadow_fit': True,
                   'source_kind': 'SYNTHETIC_TEST_ONLY',
                   'seed': 11, 'steps': 20, 'ensemble': 2}
        options.update(kwargs)
        return baseline.run(self.bundle, **options)

    def test_synthetic_action_signal_and_per_target_linear_controls(self):
        report = self.evaluate()
        self.assertEqual(report['status'], 'SYNTHETIC_OUTCOME_BASELINES_ONLY')
        self.assertEqual(report['n_train'], 89)
        self.assertEqual(report['n_holdout'], 39)
        metrics = report['baseline_metrics']
        self.assertEqual(set(metrics), {'intercept_only', 'state_only',
                                        'state_plus_action',
                                        'shuffled_train_action'})
        for item in metrics.values():
            self.assertTrue(np.isfinite(item['overall_mse']))
            self.assertEqual(set(item['per_target_mse']), set(world_model.TARGETS))
            self.assertTrue(all(np.isfinite(v) for v in
                                item['per_target_mse'].values()))
        # The fixture explicitly injects a route-dependent duration. This
        # proves the *synthetic task* has an action signal, not JEPA utility.
        target = 'log_duration'
        self.assertLess(metrics['state_plus_action']['per_target_mse'][target],
                        metrics['shuffled_train_action']['per_target_mse'][target])
        self.assertLess(metrics['state_plus_action']['per_target_mse'][target],
                        metrics['state_only']['per_target_mse'][target])
        self.assertEqual(report['world_jepa_observed_latent_diagnostic']['status'],
                         'SHADOW_OBSERVATION_ONLY')
        self.assertEqual(report['world_jepa_shuffled_latent_diagnostic']['status'],
                         'SHADOW_OBSERVATION_ONLY')
        for flag in ('outcome_utility_proven', 'causality_proven',
                     'source_disjointness_verified', 'native_executed',
                     'phone_measured', 'learning_gate_pass',
                     'whole_system_complete'):
            self.assertFalse(report[flag])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(report['jepa_weight'], 0)

    def test_repeat_is_deterministic_and_does_not_mutate_input(self):
        before = copy.deepcopy(self.bundle)
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertEqual(before['manifest'], self.bundle['manifest'])
        for side in ('train', 'holdout'):
            for a, b in zip(before[side], self.bundle[side]):
                np.testing.assert_array_equal(a, b)

    def test_approval_and_real_source_refused_before_any_fit(self):
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('unauthorized fit')):
            with self.assertRaises(PermissionError):
                baseline.run(self.bundle, source_kind='SYNTHETIC_TEST_ONLY')
            with self.assertRaises(PermissionError):
                baseline.run(self.bundle, approved_shadow_fit=True,
                             source_kind='REAL_STORE')

    def test_changed_synthetic_arrays_refused_before_fit(self):
        self.bundle['train'][0][0, 0] += .001
        self.bundle['train'][2][0, 0] += .001
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('tampered fit')):
            with self.assertRaisesRegex(PermissionError,
                                        'UNREGISTERED_SYNTHETIC_ARRAYS'):
                self.evaluate()

    def test_missing_bundle_refused(self):
        with self.assertRaisesRegex(ValueError, 'ADAPTER_BUNDLE_REQUIRED'):
            baseline.run(None, approved_shadow_fit=True,
                         source_kind='SYNTHETIC_TEST_ONLY')


if __name__ == '__main__':
    unittest.main()
