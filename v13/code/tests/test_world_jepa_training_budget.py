"""Frozen Linux file-world fixed training-budget experiment, no runtime authority."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.world_jepa_training_budget import run_budget, verify_budget, STEPS, CHECKPOINT_SHA256


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WorldJepaTrainingBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('V13_FROZEN_WORLD_ROOT')
        if not root or not Path(root).is_dir():
            raise unittest.SkipTest('Exact SHA-bound original Actions artifact not mounted')
        cls.root = Path(root)
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name) / 'candidates'
        cls.original_sha = sha(cls.root / 'training' / 'slot-shadow-v2.npz')
        cls.report = run_budget(cls.root, cls.out)
        dest = os.environ.get('V13_TRAIN_BUDGET_EVIDENCE_DIR')
        if dest:
            shutil.copytree(cls.out, dest)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_original_model_unchanged_and_ten_step_reproduced(self):
        self.assertEqual(self.original_sha, CHECKPOINT_SHA256)
        self.assertEqual(sha(self.root / 'training' / 'slot-shadow-v2.npz'), CHECKPOINT_SHA256)
        self.assertEqual(self.report['steps'], list(STEPS))
        arm10 = self.report['arms'][0]
        self.assertEqual(arm10['status'], 'SHADOW_CANDIDATE_RESTART_VERIFIED')
        self.assertLessEqual(arm10['reproduction_max_abs_difference'], 1e-10)

    def test_all_fixed_arms_saved_and_restart_verified(self):
        self.assertEqual([a['steps'] for a in self.report['arms']], list(STEPS))
        self.assertTrue(all(a['status'] == 'SHADOW_CANDIDATE_RESTART_VERIFIED'
                            for a in self.report['arms']))
        for arm in self.report['arms']:
            path = self.out / ('candidate-%d.npz' % arm['steps'])
            self.assertEqual(sha(path), arm['checkpoint_sha256'])
            self.assertEqual(set(arm['metrics']), {'313', '314', '315'})
            for metrics in arm['metrics'].values():
                self.assertEqual(metrics['evaluated_rows'], 160)
                self.assertEqual(metrics['evaluated_slots'], 960)
        check = verify_budget(self.root, self.out)
        self.assertTrue(check['verified'])
        self.assertEqual(check['successful_arms'], 4)

    def test_explicit_shadow_negative_gates(self):
        m = self.report
        self.assertEqual(m['mode'], 'SHADOW_ONLY')
        self.assertEqual(m['authority'], 0)
        self.assertTrue(m['candidate_training_performed'])
        self.assertFalse(m['runtime_learning_performed'])
        self.assertFalse(m['native_body_training'])
        self.assertFalse(m['redmi_measured'])
        self.assertEqual(m['step2'], 'UTILITY_FAIL')
        self.assertEqual(m['b3'], 'L1_FAIL')
        self.assertEqual(m['body_jepa'], 'UNAVAILABLE')
        self.assertEqual(m['jepa_weight'], 0)
        self.assertFalse(m['user_full_scope_complete'])

    def test_tampered_candidate_checkpoint_denied(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / 'copy'
            shutil.copytree(self.out, copy)
            p = copy / 'candidate-50.npz'
            p.write_bytes(p.read_bytes() + b'\x00')
            with self.assertRaises(ValueError):
                verify_budget(self.root, copy)

    def test_forged_gate_denied(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / 'copy'
            shutil.copytree(self.out, copy)
            p = copy / 'manifest.json'
            obj = json.loads(p.read_text())
            obj['jepa_weight'] = 1
            p.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                verify_budget(self.root, copy)

    def test_existing_output_refused(self):
        with self.assertRaises(FileExistsError):
            run_budget(self.root, self.out)


if __name__ == '__main__':
    unittest.main()
