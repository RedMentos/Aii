"""Run55 synthetic predicted-latent outcome readout, not a utility gate."""
import copy
import unittest
from unittest import mock

import numpy as np

from v13 import world_model
from v13 import world_jepa_action_outcome_adapter as adapter
from v13 import world_jepa_synthetic_predicted_latent_readout as probe
from tests.test_run50_world_jepa_action_outcome_adapter import FakeReadOnlyView


class Run55GroundedReadout(unittest.TestCase):
    def setUp(self):
        self.bundle = adapter.build(world_model.transitions(FakeReadOnlyView(128)))

    def readout(self, **kwargs):
        options = {'approved_shadow_fit': True,
                   'source_kind': 'SYNTHETIC_TEST_ONLY',
                   'seed': 11, 'steps': 20, 'ensemble': 2}
        options.update(kwargs)
        return probe.run(self.bundle, **options)

    def test_predicted_latent_readout_and_direct_baselines_both_reported(self):
        result = self.readout()
        self.assertEqual(result['status'],
                         'SYNTHETIC_PREDICTED_LATENT_READOUT_ONLY')
        self.assertTrue(result['readout_supervised_on_synthetic_outcomes'])
        self.assertEqual(result['n_train'], 89)
        self.assertEqual(result['n_holdout'], 39)
        self.assertEqual(set(result['predicted_latent_outcome_metrics']),
                         {'observed_action', 'shuffled_train_action'})
        self.assertEqual(set(result['direct_linear_outcome_metrics']),
                         {'intercept_only', 'state_only', 'state_plus_action',
                          'shuffled_train_action'})
        for value in result['predicted_latent_outcome_metrics'].values():
            self.assertTrue(np.isfinite(value['overall_mse']))
            self.assertEqual(set(value['per_target_mse']), set(world_model.TARGETS))
            self.assertTrue(all(np.isfinite(v) for v in
                                value['per_target_mse'].values()))
        self.assertEqual(result['world_jepa_latent_diagnostics']
                         ['observed_action']['status'], 'SHADOW_OBSERVATION_ONLY')
        for name in ('outcome_utility_proven', 'causality_proven',
                     'source_disjointness_verified', 'native_executed',
                     'phone_measured', 'learning_gate_pass',
                     'whole_system_complete'):
            self.assertFalse(result[name])
        self.assertEqual(result['age_authority'], 0)
        self.assertEqual(result['jepa_weight'], 0)

    def test_deterministic_and_caller_arrays_unchanged(self):
        before = copy.deepcopy(self.bundle)
        self.assertEqual(self.readout(), self.readout())
        for side in ('train', 'holdout'):
            for original, current in zip(before[side], self.bundle[side]):
                np.testing.assert_array_equal(original, current)

    def test_real_or_unapproved_refused_before_fit(self):
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('unauthorized fit')):
            with self.assertRaises(PermissionError):
                probe.run(self.bundle, source_kind='SYNTHETIC_TEST_ONLY')
            with self.assertRaises(PermissionError):
                probe.run(self.bundle, approved_shadow_fit=True,
                          source_kind='REAL_STORE')

    def test_tampered_array_refused_before_fit(self):
        self.bundle['holdout'][2][0, 4] += .001
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('tampered fit')):
            with self.assertRaisesRegex(PermissionError,
                                        'UNREGISTERED_SYNTHETIC_ARRAYS'):
                self.readout()

    def test_unbounded_array_refused(self):
        self.bundle['train'] = (np.empty((2049, 7)), self.bundle['train'][1],
                                self.bundle['train'][2])
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('unbounded fit')):
            with self.assertRaisesRegex(ValueError, 'UNBOUNDED_ADAPTER_INPUT'):
                self.readout()


if __name__ == '__main__':
    unittest.main()
