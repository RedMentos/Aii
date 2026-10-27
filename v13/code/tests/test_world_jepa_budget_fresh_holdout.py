"""Fresh independent Linux file-world holdouts on frozen 200-step World-JEPA."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.world_jepa_budget_fresh_holdout import (
    SEEDS, ROWS, SELECTED_CHECKPOINT_SHA256, run, verify,
)


def snapshot(root):
    return sorted((str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest())
                  for p in Path(root).rglob('*') if p.is_file())


class FrozenWorldBudgetFreshHoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = os.environ.get('V13_FROZEN_WORLD_ROOT')
        budget = os.environ.get('V13_FROZEN_BUDGET_ROOT')
        if not original or not budget or not Path(original).is_dir() or not Path(budget).is_dir():
            raise unittest.SkipTest('Exact original+budget Actions artifacts not mounted')
        cls.original, cls.budget = Path(original), Path(budget)
        cls.original_before, cls.budget_before = snapshot(cls.original), snapshot(cls.budget)
        durable = os.environ.get('V13_FRESH_OUTPUT_ROOT')
        cls.temp = None if durable else tempfile.TemporaryDirectory()
        cls.output = Path(durable) if durable else Path(cls.temp.name) / 'fresh'
        cls.result = run(cls.original, cls.budget, cls.output)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'temp', None) is not None:
            cls.temp.cleanup()

    def test_preregistered_new_seeds_and_negative_gates(self):
        result = self.result
        self.assertEqual(result['seeds'], list(SEEDS))
        self.assertEqual(result['rows'], 480)
        self.assertEqual(result['checkpoint_sha256'], SELECTED_CHECKPOINT_SHA256)
        self.assertEqual(result['budget_steps'], 200)
        self.assertTrue(result['selected_after_prior_holdout_inspection'])
        self.assertEqual(result['authority'], 0)
        self.assertFalse(result['training_performed'])
        self.assertFalse(result['redmi_measured'])
        self.assertEqual(result['step2'], 'UTILITY_FAIL')
        self.assertEqual(result['b3'], 'L1_FAIL')
        self.assertEqual(result['body_jepa'], 'UNAVAILABLE')
        self.assertEqual(result['jepa_weight'], 0)
        self.assertFalse(result['canonical_architecture_complete'])
        self.assertFalse(result['user_full_scope_complete'])
        self.assertEqual(len(result['per_seed']), 3)
        for seed, item in zip(SEEDS, result['per_seed']):
            self.assertEqual(item['seed'], seed)
            self.assertEqual(item['rows'], ROWS)
            self.assertIn('action_prediction_mse', item['metrics'])
            self.assertIn('identity_target_mse', item['metrics'])
            self.assertIn('rotated_action_mse', item['metrics'])

    def test_original_training_and_budget_checkpoint_bytes_unchanged(self):
        self.assertEqual(snapshot(self.original), self.original_before)
        self.assertEqual(snapshot(self.budget), self.budget_before)

    def test_independent_restart_verify(self):
        self.assertEqual(verify(self.original, self.budget, self.output),
                         {'verified': True, 'seeds': [401, 402, 403], 'rows': 480,
                          'authority': 0, 'redmi_measured': False})

    def test_modified_new_world_log_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'fresh'
            shutil.copytree(self.output, dest)
            p = dest / 'seed-402' / 'world-402.log'
            p.write_bytes(p.read_bytes() + b'X')
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, dest)

    def test_forged_metric_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'fresh'
            shutil.copytree(self.output, dest)
            p = dest / 'seed-401' / 'manifest.json'
            man = json.loads(p.read_text())
            man['metrics']['action_prediction_mse'] += 0.2
            p.write_text(json.dumps(man))
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, dest)

    def test_swapped_cohort_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'fresh'
            shutil.copytree(self.output, dest)
            (dest / 'seed-403' / 'cohort.json').write_bytes(
                (dest / 'seed-401' / 'cohort.json').read_bytes())
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, dest)

    def test_frozen_selected_checkpoint_tamper_denied(self):
        with tempfile.TemporaryDirectory() as td:
            budget = Path(td) / 'budget'
            shutil.copytree(self.budget, budget)
            p = budget / 'steps-0200' / 'slot-shadow-v2.npz'
            p.write_bytes(p.read_bytes() + b'X')
            with self.assertRaises(ValueError):
                verify(self.original, budget, self.output)

    def test_no_overwrite_or_input_alias(self):
        with self.assertRaises(FileExistsError):
            run(self.original, self.budget, self.output)
        with self.assertRaises(FileExistsError):
            run(self.original, self.budget, self.original / 'training' / 'forbidden')


if __name__ == '__main__':
    unittest.main()
