"""Frozen World-JEPA action identification on new Linux file-world seeds."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.world_jepa_action_identification import (
    SEEDS, SELECTED_CHECKPOINT_SHA256, run, verify,
)


def snapshot(root):
    return sorted((str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest())
                  for p in Path(root).rglob('*') if p.is_file())


class WorldActionIdentificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = os.environ.get('V13_FROZEN_WORLD_ROOT')
        budget = os.environ.get('V13_FROZEN_BUDGET_ROOT')
        if not original or not budget or not Path(original).is_dir() or not Path(budget).is_dir():
            raise unittest.SkipTest('Original and budget SHA-bound artifacts not mounted')
        cls.original, cls.budget = Path(original), Path(budget)
        cls.before_original, cls.before_budget = snapshot(cls.original), snapshot(cls.budget)
        durable = os.environ.get('V13_TASK_OUTPUT_ROOT')
        cls.temp = None if durable else tempfile.TemporaryDirectory()
        cls.output = Path(durable) if durable else Path(cls.temp.name) / 'task'
        cls.report = run(cls.original, cls.budget, cls.output)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'temp', None) is not None:
            cls.temp.cleanup()

    def test_fixed_new_seeds_controls_and_negative_gates(self):
        r = self.report
        self.assertEqual(r['seeds'], [501, 502, 503])
        self.assertEqual(r['rows'], 480)
        self.assertEqual(r['checkpoint_sha256'], SELECTED_CHECKPOINT_SHA256)
        self.assertEqual(r['authority'], 0)
        self.assertFalse(r['training_performed'])
        self.assertFalse(r['redmi_measured'])
        self.assertEqual(r['step2'], 'UTILITY_FAIL')
        self.assertEqual(r['b3'], 'L1_FAIL')
        self.assertEqual(r['body_jepa'], 'UNAVAILABLE')
        self.assertEqual(r['jepa_weight'], 0)
        self.assertFalse(r['canonical_architecture_complete'])
        self.assertFalse(r['user_full_scope_complete'])
        self.assertEqual(len(r['per_seed']), 3)
        for row in r['per_seed']:
            self.assertEqual(row['rows'], 160)
            m = row['metrics']
            self.assertTrue(0 <= m['model_top1'] <= 1)
            self.assertTrue(0 <= m['model_top5'] <= 1)
            self.assertTrue(0 <= m['slot_heuristic_top1'] <= 1)
            self.assertTrue(1 <= m['model_mean_true_rank'] <= 31)

    def test_original_and_frozen_budget_bytes_unchanged(self):
        self.assertEqual(snapshot(self.original), self.before_original)
        self.assertEqual(snapshot(self.budget), self.before_budget)

    def test_independent_persisted_restart(self):
        self.assertEqual(verify(self.original, self.budget, self.output),
                         {'verified': True, 'seeds': [501, 502, 503], 'rows': 480,
                          'authority': 0, 'redmi_measured': False})

    def test_task_row_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'task'
            shutil.copytree(self.output, copy)
            p = copy / 'seed-501' / 'task_rows.json'
            p.write_bytes(p.read_bytes() + b'X')
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, copy)

    def test_forged_task_metric_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'task'
            shutil.copytree(self.output, copy)
            p = copy / 'seed-502' / 'task_manifest.json'
            m = json.loads(p.read_text())
            m['metrics']['model_top1'] = 1.
            p.write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, copy)

    def test_swapped_raw_cohort_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'task'
            shutil.copytree(self.output, copy)
            (copy / 'seed-503' / 'cohort.json').write_bytes(
                (copy / 'seed-501' / 'cohort.json').read_bytes())
            with self.assertRaises(ValueError):
                verify(self.original, self.budget, copy)

    def test_frozen_checkpoint_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            budget = Path(td) / 'budget'
            shutil.copytree(self.budget, budget)
            p = budget / 'steps-0200' / 'slot-shadow-v2.npz'
            p.write_bytes(p.read_bytes() + b'X')
            with self.assertRaises(ValueError):
                verify(self.original, budget, self.output)

    def test_existing_and_input_alias_rejected(self):
        with self.assertRaises(FileExistsError):
            run(self.original, self.budget, self.output)
        with self.assertRaises(FileExistsError):
            run(self.original, self.budget, self.budget / 'forbidden')


if __name__ == '__main__':
    unittest.main()
