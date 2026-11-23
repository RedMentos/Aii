"""Run64 fresh real-file factorized WorldJEPA readout: no utility promotion."""
import random
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as factor
from scripts import run64_realfile_jepa_factorized_readout as probe
from scripts import z12b_world_jepa as original


class Run64RealFileJEPATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_fresh_preregistered_cohort_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['schema'], probe.SCHEMA)
        self.assertEqual(r['seeds'], [251, 257, 263])
        self.assertEqual(r['n_train_per_seed'], 240)
        self.assertEqual(r['n_holdout_per_seed'], 60)
        self.assertEqual(r['jepa_steps'], 200)
        self.assertEqual(r['jepa_ensemble'], 1)
        self.assertEqual(r['ridge_lambda'], .01)
        self.assertTrue(r['file_actions_executed'])
        self.assertTrue(r['jepa_training_executed'])
        self.assertFalse(r['jepa_confidence_supported_for_factorized_actions'])
        for key in ('native_model_executed', 'model_weights_published',
                    'jepa_only_utility_proven', 'counterfactual_causality_proven',
                    'source_disjointness_verified', 'phone_measured',
                    'learning_gate_pass', 'whole_system_complete'):
            self.assertFalse(r[key])
        self.assertEqual(r['age_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)

    def test_real_action_rows_and_all_arms(self):
        for row in self.report['reports']:
            self.assertEqual(row['n_train'], 240)
            self.assertEqual(row['n_holdout'], 60)
            self.assertEqual(len(row['heldout_action_indices']), 4)
            self.assertGreater(row['train_changed_count'], 0)
            self.assertGreater(row['test_changed_count'], 0)
            self.assertEqual(row['test_action_count'], 4)
            self.assertGreater(row['train_action_count'], 4)
            for name in ('train_rows_sha256', 'test_rows_sha256',
                         'shuffled_train_permutation_sha256'):
                self.assertRegex(row[name], r'^[0-9a-f]{64}$')
            self.assertNotEqual(row['train_rows_sha256'],
                                row['test_rows_sha256'])
            self.assertEqual(set(row['jepa_readout_metrics']),
                             set(probe.ARM_NAMES))
            self.assertEqual(set(row['supervised_baseline_metrics']),
                             set(factor.MODEL_NAMES))
            for section in ('jepa_readout_metrics',
                            'supervised_baseline_metrics'):
                for metrics in row[section].values():
                    self.assertTrue(np.isfinite(metrics['overall_mse']))
                    self.assertTrue(np.isfinite(metrics['target_slot_mse']))
                    self.assertGreaterEqual(metrics['overall_mse'], 0.)
                    self.assertGreaterEqual(metrics['target_slot_mse'], 0.)

    def test_deterministic_original_cohort(self):
        self.assertEqual(self.report, probe.run())

    def test_factorized_twohot_and_zero_action_control(self):
        seed = 251
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        train = parent._rows(seed, held, 15, test=False)
        a = probe._factor_actions(train)
        self.assertEqual(a.shape, (15, len(original.OPS)+original.SLOTS))
        self.assertTrue(np.all((a == 0) | (a == 1)))
        self.assertTrue(all(a[i].sum() == (0 if row[1] == original.NOOP else 2)
                            for i, row in enumerate(train)))
        self.assertTrue(all(row[1] not in held for row in train))

    def test_train_only_fit_receives_no_heldout_outcomes(self):
        seen = []
        def fake_fit(x, train_actions, x2, xt, at, *, seed):
            self.assertEqual(x.shape, x2.shape)
            self.assertEqual(x.shape[0], 240)
            self.assertEqual(xt.shape[0], 60)
            self.assertEqual(train_actions.shape, (240, 11))
            self.assertEqual(at.shape, (60, 11))
            seen.append((train_actions.copy(), at.copy()))
            return xt.copy()
        with mock.patch.object(probe, '_fit_readout', side_effect=fake_fit):
            row = probe._seed(257)
        self.assertEqual(len(seen), 3)
        self.assertTrue(np.array_equal(seen[1][0], np.zeros((240, 11))))
        self.assertTrue(np.array_equal(seen[1][1], np.zeros((60, 11))))
        self.assertFalse(np.array_equal(seen[0][0], seen[2][0]))
        self.assertEqual(row['n_holdout'], 60)

    def test_heldout_target_is_not_fit_argument(self):
        x = np.zeros((2, 60))
        a = np.zeros((2, 11))
        xt = np.zeros((1, 60))
        with self.assertRaises(ValueError):
            probe._fit_readout(x, a[:, :10], x, xt, a[:1], seed=1)
        with self.assertRaises(ValueError):
            probe._fit_readout(x, a, x, xt, a[:0], seed=1)

    def test_invalid_config_refused_before_files(self):
        with mock.patch.object(parent, '_rows',
                               side_effect=AssertionError('unexpected files')):
            for kwargs in ({'seeds': (251,)}, {'seeds': [251, 257, 263]},
                           {'n_train': 12}, {'n_test': 12},
                           {'steps': 199}):
                with self.assertRaises(PermissionError):
                    probe.run(**kwargs)


if __name__ == '__main__':
    unittest.main()
