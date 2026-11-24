"""Run63 independent factorized action comparator, software-only proof."""
import random
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as parent
from scripts import run63_z12b_factorized_real_file_baselines as probe
from scripts import z12b_world_jepa as original


class Run63FactorizedRealFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_fixed_fresh_cohort_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['schema'], probe.SCHEMA)
        self.assertEqual(r['status'], 'REAL_FILE_FACTORIZED_BASELINES_ONLY')
        self.assertEqual(r['seeds'], [233, 239, 241])
        self.assertEqual(r['n_train_per_seed'], 240)
        self.assertEqual(r['n_holdout_per_seed'], 60)
        self.assertEqual(r['ridge_lambda'], .01)
        self.assertTrue(r['file_actions_executed'])
        for key in ('native_model_executed', 'model_weights_published',
                    'jepa_training_executed', 'counterfactual_causality_proven',
                    'source_disjointness_verified', 'phone_measured',
                    'learning_gate_pass', 'whole_system_complete'):
            self.assertFalse(r[key])
        self.assertEqual(r['age_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)

    def test_all_five_metrics_and_real_actions(self):
        for row in self.report['reports']:
            self.assertEqual(row['n_train'], 240)
            self.assertEqual(row['n_holdout'], 60)
            self.assertEqual(len(row['heldout_action_indices']), 4)
            self.assertGreater(row['train_changed_count'], 0)
            self.assertGreater(row['test_changed_count'], 0)
            self.assertEqual(row['test_action_count'], 4)
            self.assertGreater(row['train_action_count'], 4)
            self.assertRegex(row['train_rows_sha256'], r'^[a-f0-9]{64}$')
            self.assertRegex(row['test_rows_sha256'], r'^[a-f0-9]{64}$')
            self.assertNotEqual(row['train_rows_sha256'], row['test_rows_sha256'])
            self.assertEqual(set(row['metrics']), set(probe.MODEL_NAMES))
            for value in row['metrics'].values():
                self.assertTrue(np.isfinite(value['overall_mse']))
                self.assertTrue(np.isfinite(value['target_slot_mse']))
                self.assertGreaterEqual(value['overall_mse'], 0.)
                self.assertGreaterEqual(value['target_slot_mse'], 0.)
        self.assertEqual(set(self.report['aggregate_metrics']), set(probe.MODEL_NAMES))

    def test_reproducible_registered_real_file_cohort(self):
        self.assertEqual(self.report, probe.run())

    def test_heldout_combinations_excluded_from_train(self):
        seed = 233
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        train = parent._rows(seed, held, 12, test=False)
        test = parent._rows(seed, held, 12, test=True)
        self.assertTrue(all(a not in held for _, a, _, _ in train))
        self.assertTrue(all(a in held for _, a, _, _ in test))

    def test_factorized_features_separate_operation_and_slot(self):
        x = np.arange(parent.FEATURES, dtype=np.float64)
        a = 0  # first op, first slot
        b = 1  # same op, next slot
        c = original.SLOTS  # next op, first slot
        f0, f1, f2 = [probe._factorized_global_features(x, i)
                      for i in (a, b, c)]
        self.assertEqual(f0.shape, (1 + parent.FEATURES
                                   + len(original.OPS) + original.SLOTS,))
        self.assertTrue(np.array_equal(f0[:1+parent.FEATURES],
                                       f1[:1+parent.FEATURES]))
        self.assertTrue(np.array_equal(
            f0[1+parent.FEATURES:1+parent.FEATURES+len(original.OPS)],
            f1[1+parent.FEATURES:1+parent.FEATURES+len(original.OPS)]))
        self.assertFalse(np.array_equal(f0, f1))
        self.assertFalse(np.array_equal(f0, f2))
        self.assertEqual(probe._slot_aware_features(x, a).shape,
                         (1 + parent.SLOT_FEATURES
                          + len(original.OPS) + original.SLOTS,))
        with self.assertRaises(ValueError):
            probe._slot_aware_features(x, original.NOOP)

    def test_fits_only_training_labels_not_heldout_outcomes(self):
        seed = 239
        held = tuple(sorted(random.Random(seed).sample(parent.NON_NOOP, 4)))
        train = parent._rows(seed, held, 30, test=False)
        test = parent._rows(seed, held, 6, test=True)
        weights = probe._fit(train)
        x, a, x2, ok = test[0]
        p1 = probe._predict(x, a, weights)
        mutated = list(test)
        mutated[0] = (x, a, x2 + 100., ok)
        p2 = probe._predict(mutated[0][0], mutated[0][1], weights)
        for key in probe.MODEL_NAMES:
            self.assertTrue(np.array_equal(p1[key], p2[key]))
        # Altering only the heldout target must change scoring, not fit.
        original_scores = probe._evaluate(train, test)
        modified_scores = probe._evaluate(train, mutated)
        self.assertNotEqual(original_scores, modified_scores)

    def test_invalid_cohort_refused_before_file_operations(self):
        with mock.patch.object(parent, '_rows',
                               side_effect=AssertionError('files should not run')):
            for kwargs in ({'seeds': (233,)}, {'n_train': 30},
                           {'n_test': 30}, {'seeds': [233, 239, 241]}):
                with self.assertRaises(PermissionError):
                    probe.run(**kwargs)


if __name__ == '__main__':
    unittest.main()
