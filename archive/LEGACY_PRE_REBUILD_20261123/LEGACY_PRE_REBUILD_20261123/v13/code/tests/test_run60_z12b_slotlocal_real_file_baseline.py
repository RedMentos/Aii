"""Run60: fresh real file-action compositional baseline, never JEPA proof."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from scripts import run60_z12b_slotlocal_real_file_baseline as probe
from scripts import z12b_world_jepa as original


class Run60RealFileSlotLocal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = probe.run()

    def test_preregistered_seeds_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['status'], 'REAL_FILE_ACTION_SLOTLOCAL_BASELINE_ONLY')
        self.assertEqual(r['seeds'], [211, 223, 227])
        self.assertEqual(r['n_train_per_seed'], 240)
        self.assertEqual(r['n_holdout_per_seed'], 60)
        self.assertTrue(r['file_actions_executed'])
        self.assertFalse(r['native_model_executed'])
        self.assertFalse(r['model_weights_published'])
        self.assertFalse(r['jepa_training_executed'])
        for key in ('counterfactual_causality_proven',
                    'source_disjointness_verified', 'phone_measured',
                    'learning_gate_pass', 'whole_system_complete'):
            self.assertFalse(r[key])
        self.assertEqual(r['age_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)

    def test_real_heldout_file_outcomes_and_all_comparators(self):
        for row in self.report['reports']:
            self.assertEqual(row['n_train'], 240)
            self.assertEqual(row['n_holdout'], 60)
            self.assertEqual(len(row['heldout_action_indices']), 4)
            self.assertTrue(all(0 <= x < original.NOOP
                                for x in row['heldout_action_indices']))
            self.assertGreater(row['train_changed_count'], 0)
            self.assertGreater(row['test_changed_count'], 0)
            self.assertGreater(row['test_action_count'], 1)
            self.assertGreater(row['train_action_count'], 4)
            self.assertRegex(row['train_rows_sha256'], r'^[0-9a-f]{64}$')
            self.assertRegex(row['test_rows_sha256'], r'^[0-9a-f]{64}$')
            self.assertNotEqual(row['train_rows_sha256'],
                                row['test_rows_sha256'])
            self.assertEqual(set(row['metrics']),
                             {'persistence', 'global_ridge',
                              'slot_local_ridge'})
            for metrics in row['metrics'].values():
                self.assertTrue(np.isfinite(metrics['overall_mse']))
                self.assertTrue(np.isfinite(metrics['target_slot_mse']))
                self.assertGreaterEqual(metrics['overall_mse'], 0)
                self.assertGreaterEqual(metrics['target_slot_mse'], 0)
        for metrics in self.report['aggregate_metrics'].values():
            self.assertTrue(np.isfinite(metrics['overall_mse']))
            self.assertTrue(np.isfinite(metrics['target_slot_mse']))

    def test_preregistered_run_is_deterministic(self):
        self.assertEqual(self.report, probe.run())

    def test_heldout_combinations_never_used_in_train(self):
        seed = 211
        held = tuple(sorted(__import__('random').Random(seed).sample(
            probe.NON_NOOP, 4)))
        train = probe._rows(seed, held, 12, test=False)
        test = probe._rows(seed, held, 12, test=True)
        self.assertTrue(all(a not in held for _, a, _, _ in train))
        self.assertTrue(all(a in held for _, a, _, _ in test))
        self.assertEqual(len(train), 12)
        self.assertEqual(len(test), 12)

    def test_actual_file_action_changes_measured_features(self):
        with tempfile.TemporaryDirectory(prefix='v13-run60-unit-') as td:
            root = Path(td)
            before = original.features(root)
            op, slot = original.ACTIONS[0]
            self.assertTrue(original.do(root, op, slot,
                                        __import__('random').Random(5)))
            after = original.features(root)
            self.assertFalse(np.array_equal(before, after))
            self.assertTrue((root / 'slot0.txt').is_file())

    def test_non_preregistered_config_refused_before_files(self):
        with mock.patch.object(probe, '_rows',
                               side_effect=AssertionError('unexpected files')):
            with self.assertRaises(PermissionError):
                probe.run(seeds=(211,))
            with self.assertRaises(PermissionError):
                probe.run(n_train=10)
            with self.assertRaises(PermissionError):
                probe.run(n_test=10)


if __name__ == '__main__':
    unittest.main()
