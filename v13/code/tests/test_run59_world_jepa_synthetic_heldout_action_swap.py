"""Run59: synthetic heldout action-swap readout; no causal or utility gate."""
import copy
import unittest
from unittest import mock

import numpy as np

from v13 import world_model, world_jepa
from v13 import world_jepa_action_outcome_adapter as adapter
from v13 import world_jepa_synthetic_heldout_action_swap as probe
from tests.test_run50_world_jepa_action_outcome_adapter import FakeReadOnlyView


class Run59HeldoutActionSwap(unittest.TestCase):
    def setUp(self):
        self.bundle = adapter.build(world_model.transitions(FakeReadOnlyView(128)))

    def readout(self, **kwargs):
        args = dict(approved_shadow_fit=True,
                    source_kind='SYNTHETIC_TEST_ONLY',
                    seed=11, steps=20, ensemble=2)
        args.update(kwargs)
        return probe.run(self.bundle, **args)

    def test_grounded_train_only_readout_and_negative_gates(self):
        result = self.readout()
        self.assertEqual(result['status'],
                         'SYNTHETIC_HELDOUT_ACTION_SWAP_DIAGNOSTIC_ONLY')
        self.assertEqual((result['n_train'], result['n_holdout']), (89, 39))
        self.assertEqual(result['swapped_action_rows'], 39)
        self.assertEqual(set(result['readout_metrics']),
                         {'observed_action', 'shuffled_train_action'})
        for arm in result['readout_metrics'].values():
            self.assertTrue(np.isfinite(arm['wrong_minus_correct_overall_mse']))
            self.assertFalse(arm['readout_weights_published'])
            for name in ('correct_action', 'swapped_holdout_action'):
                self.assertTrue(np.isfinite(arm[name]['overall_mse']))
                self.assertEqual(set(arm[name]['per_target_mse']),
                                 set(world_model.TARGETS))
        self.assertFalse(result['counterfactual_outcome_observed'])
        self.assertTrue(result['readout_supervised_on_synthetic_outcomes'])
        for key in ('causality_proven', 'outcome_utility_proven',
                    'source_disjointness_verified', 'native_executed',
                    'phone_measured', 'learning_gate_pass',
                    'whole_system_complete'):
            self.assertFalse(result[key])
        self.assertEqual(result['age_authority'], 0)
        self.assertEqual(result['jepa_weight'], 0)

    def test_actual_heldout_actions_changed_for_every_row(self):
        original_predict = world_jepa.WorldJEPA.predict
        calls = []
        def spy(model, x, a):
            calls.append((np.asarray(x).copy(), np.asarray(a).copy()))
            return original_predict(model, x, a)
        with mock.patch.object(world_jepa.WorldJEPA, 'predict', spy):
            self.readout()
        train_a = self.bundle['train'][1]
        holdout_a = self.bundle['holdout'][1]
        swapped = np.roll(holdout_a, 1, axis=1)
        self.assertTrue(np.all(np.any(swapped != holdout_a, axis=1)))
        self.assertTrue(np.all(swapped.sum(axis=1) == 1))
        # Final six calls: observed train/correct/wrong, control train/correct/wrong.
        self.assertGreaterEqual(len(calls), 6)
        np.testing.assert_array_equal(calls[-6][1], train_a)
        np.testing.assert_array_equal(calls[-5][1], holdout_a)
        np.testing.assert_array_equal(calls[-4][1], swapped)
        np.testing.assert_array_equal(calls[-2][1], holdout_a)
        np.testing.assert_array_equal(calls[-1][1], swapped)

    def test_repeatable_and_caller_unchanged(self):
        before = copy.deepcopy(self.bundle)
        self.assertEqual(self.readout(), self.readout())
        for side in ('train', 'holdout'):
            for old, current in zip(before[side], self.bundle[side]):
                np.testing.assert_array_equal(old, current)

    def test_unapproved_and_real_refused_before_fit(self):
        with mock.patch.object(world_jepa.WorldJEPA, 'fit',
                               side_effect=AssertionError('unauthorized fit')):
            with self.assertRaises(PermissionError):
                probe.run(self.bundle, source_kind='SYNTHETIC_TEST_ONLY')
            with self.assertRaises(PermissionError):
                probe.run(self.bundle, approved_shadow_fit=True,
                          source_kind='REAL_STORE')

    def test_tampered_fixture_refused(self):
        self.bundle['train'][2][0, 4] += .001
        with mock.patch.object(world_jepa.WorldJEPA, 'fit',
                               side_effect=AssertionError('tampered fit')):
            with self.assertRaisesRegex(PermissionError,
                                        'UNREGISTERED_SYNTHETIC_ARRAYS'):
                self.readout()

    def test_oversized_fixture_refused_before_fit(self):
        self.bundle['holdout'] = (np.empty((4096, 7)),
                                  self.bundle['holdout'][1],
                                  self.bundle['holdout'][2])
        with mock.patch.object(world_jepa.WorldJEPA, 'fit',
                               side_effect=AssertionError('oversized fit')):
            with self.assertRaisesRegex(ValueError, 'UNBOUNDED_ADAPTER_INPUT'):
                self.readout()


if __name__ == '__main__':
    unittest.main()
