"""Run51 synthetic-only approved World-JEPA action-outcome SHADOW fit."""
import copy
import unittest
from unittest import mock

import numpy as np

from v13 import world_model
from v13 import world_jepa_action_outcome_adapter as adapter
from v13 import world_jepa_action_outcome_shadow_fit as pipeline
from tests.test_run50_world_jepa_action_outcome_adapter import FakeReadOnlyView


class Run51SyntheticShadowFit(unittest.TestCase):
    def setUp(self):
        view = FakeReadOnlyView(128)
        self.bundle = adapter.build(world_model.transitions(view))

    def fit(self, **kwargs):
        options = {'approved_shadow_fit': True,
                   'source_kind': 'SYNTHETIC_TEST_ONLY',
                   'seed': 11, 'steps': 20, 'ensemble': 2}
        options.update(kwargs)
        return pipeline.run(self.bundle, **options)

    def test_positive_step_action_and_shuffled_control_no_authority(self):
        out = self.fit()
        report = out['report']
        self.assertEqual(report['status'], 'SYNTHETIC_SHADOW_ABLATION_ONLY')
        self.assertEqual(report['steps'], 20)
        self.assertEqual(out['observed_model']._fit_steps, 20)
        self.assertEqual(out['shuffled_model']._fit_steps, 20)
        self.assertFalse(report['learning_gate_pass'])
        self.assertFalse(report['real_world_causality_proven'])
        self.assertFalse(report['source_disjointness_verified'])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(report['jepa_weight'], 0)
        self.assertNotEqual(report['train_rows_sha256'],
                            report['control_train_source_sha256'])
        for key in ('observed_action', 'shuffled_action'):
            self.assertEqual(report[key]['status'], 'SHADOW_OBSERVATION_ONLY')
            self.assertTrue(all(np.isfinite(v) for v in report[key]['metrics'].values()))

    def test_same_seed_same_report_and_unchanged_input_arrays(self):
        before = [tuple(x.copy() for x in self.bundle[side])
                  for side in ('train', 'holdout')]
        first = self.fit()
        second = self.fit()
        self.assertEqual(first['report'], second['report'])
        for side, original in zip(('train', 'holdout'), before):
            for a, b in zip(self.bundle[side], original):
                np.testing.assert_array_equal(a, b)

    def test_unapproved_and_real_source_are_refused_before_fit(self):
        with mock.patch('v13.world_jepa.WorldJEPA.fit', side_effect=AssertionError('must not fit')):
            with self.assertRaises(PermissionError):
                pipeline.run(self.bundle, source_kind='SYNTHETIC_TEST_ONLY')
            with self.assertRaises(PermissionError):
                pipeline.run(self.bundle, approved_shadow_fit=True,
                             source_kind='REAL_STORE')

    def test_declared_synthetic_but_changed_array_bytes_refused_before_fit(self):
        # Preserve X2 state == X state so the tamper reaches the *source
        # digest* gate rather than failing an earlier embedding-shape gate.
        self.bundle['train'][0][0, 0] += 0.001
        self.bundle['train'][2][0, 0] += 0.001
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('must not fit')):
            with self.assertRaisesRegex(PermissionError, 'UNREGISTERED_SYNTHETIC_ARRAYS'):
                self.fit()

    def test_inconsistent_state_embedding_refused_before_digest_or_fit(self):
        # Retain the distinct structural refusal observed in original RED CI.
        self.bundle['train'][0][0, 0] += 0.001
        with mock.patch('v13.world_jepa.WorldJEPA.fit',
                        side_effect=AssertionError('must not fit')):
            with self.assertRaisesRegex(ValueError, 'INVALID_ACTION_OUTCOME_EMBEDDING'):
                self.fit()

    def test_invalid_config_and_manifest_fail_closed(self):
        for options in ({'steps': 0}, {'steps': True}, {'seed': True},
                        {'ensemble': 1}, {'ensemble': 5}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.fit(**options)
        damaged = copy.deepcopy(self.bundle['manifest'])
        damaged['within_supplied_records_id_disjoint'] = False
        self.bundle['manifest'] = damaged
        with self.assertRaisesRegex(ValueError, 'PROVENANCE'):
            self.fit()


if __name__ == '__main__':
    unittest.main()
