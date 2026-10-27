"""Preregistered exact-cohort World-JEPA budget ablation; all arms stay SHADOW."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.world_jepa_budget_ablation import (
    BUDGETS, CHECKPOINT_SHA256, ablate, verify_budget_export,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FrozenWorldBudgetAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('V13_FROZEN_WORLD_ROOT')
        if not root or not Path(root).is_dir():
            raise unittest.SkipTest('Original SHA-bound Actions artifact not mounted')
        cls.root = Path(root)
        durable = os.environ.get('V13_BUDGET_OUTPUT_ROOT')
        cls.temp = None if durable else tempfile.TemporaryDirectory()
        cls.output = Path(durable) if durable else Path(cls.temp.name) / 'budget'
        cls.before = sorted((str(p.relative_to(cls.root)), sha(p))
                            for p in cls.root.rglob('*') if p.is_file())
        cls.report = ablate(cls.root, cls.output)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'temp', None) is not None:
            cls.temp.cleanup()

    def test_all_four_exact_budgets_and_negative_gates(self):
        report = self.report
        self.assertEqual(report['budgets'], [10, 50, 200, 800])
        self.assertEqual([x['steps'] for x in report['arms']], list(BUDGETS))
        self.assertEqual(len({x['checkpoint_sha256'] for x in report['arms']}), 4)
        self.assertEqual(report['frozen_checkpoint_sha256'], CHECKPOINT_SHA256)
        self.assertEqual(report['mode'], 'SHADOW_ONLY')
        self.assertEqual(report['authority'], 0)
        self.assertFalse(report['redmi_measured'])
        self.assertFalse(report['runtime_authority'])
        self.assertEqual(report['step2'], 'UTILITY_FAIL')
        self.assertEqual(report['b3'], 'L1_FAIL')
        self.assertEqual(report['body_jepa'], 'UNAVAILABLE')
        self.assertEqual(report['jepa_weight'], 0)
        self.assertFalse(report['canonical_architecture_complete'])
        self.assertFalse(report['user_full_scope_complete'])
        for arm in report['arms']:
            scores = arm['metrics']
            self.assertEqual(scores['rows'], 480)
            self.assertEqual(scores['seeds'], [313, 314, 315])
            self.assertEqual(len(scores['per_seed']), 3)
            self.assertTrue(all('action_over_identity' in x and 'action_over_rotated' in x
                                for x in scores['per_seed']))

    def test_original_bytes_never_modified(self):
        after = sorted((str(p.relative_to(self.root)), sha(p))
                       for p in self.root.rglob('*') if p.is_file())
        self.assertEqual(self.before, after)

    def test_frozen_ten_step_reference_and_restart(self):
        self.assertAlmostEqual(self.report['frozen_reference']['weighted_action_mse'],
                               0.31348980990632647, places=9)
        self.assertAlmostEqual(self.report['frozen_reference']['weighted_identity_mse'],
                               0.27064646738716414, places=9)
        self.assertEqual(verify_budget_export(self.root, self.output),
                         {'verified': True, 'arms': [10, 50, 200, 800],
                          'rows': 480, 'authority': 0, 'redmi_measured': False})
        # Same training data, seed, source and 10 steps should reproduce the
        # frozen reference; this is a diagnostic, not a promotion gate.
        self.assertAlmostEqual(self.report['arms'][0]['metrics']['weighted_action_mse'],
                               self.report['frozen_reference']['weighted_action_mse'],
                               places=8)

    def test_checkpoint_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'budget'
            shutil.copytree(self.output, copy)
            p = copy / 'steps-0200' / 'slot-shadow-v2.npz'
            p.write_bytes(p.read_bytes() + b'X')
            with self.assertRaises(ValueError):
                verify_budget_export(self.root, copy)

    def test_report_gate_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'budget'
            shutil.copytree(self.output, copy)
            p = copy / 'report.json'
            report = json.loads(p.read_text())
            report['step2'] = 'UTILITY_PASS'
            p.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                verify_budget_export(self.root, copy)

    def test_wrong_budget_arm_or_seed_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'budget'
            shutil.copytree(self.output, copy)
            p = copy / 'steps-0050' / 'arm.json'
            arm = json.loads(p.read_text())
            arm['provenance']['budget_steps'] = '800'
            p.write_text(json.dumps(arm))
            with self.assertRaises(ValueError):
                verify_budget_export(self.root, copy)

    def test_existing_or_inside_original_output_refused(self):
        with self.assertRaises(FileExistsError):
            ablate(self.root, self.output)
        with self.assertRaises(FileExistsError):
            ablate(self.root, self.root / 'training' / 'forbidden')


if __name__ == '__main__':
    unittest.main()
