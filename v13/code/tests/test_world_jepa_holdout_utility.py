"""Fresh real-file-world post-checkpoint World-JEPA utility audit (no training/authority)."""
import contextlib
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import world_jepa_shadow_lifecycle as lifecycle
from scripts.world_jepa_holdout_utility import run_holdout, verify_holdout_export


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WorldJepaHoldoutUtilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.training = cls.root / 'training'
        with contextlib.redirect_stdout(io.StringIO()):
            lifecycle.main(['--seed', '212', '--train', '240', '--steps', '10',
                            '--output-dir', str(cls.training)])
        cls.checkpoint = cls.training / 'slot-shadow-v2.npz'
        cls.before = digest(cls.checkpoint)
        cls.holdout = cls.root / 'heldout'
        with patch('v13.world_jepa_slots.SlotWorldJEPA.fit',
                   side_effect=AssertionError('holdout must never train')):
            with patch('v13.world_jepa_slots.SlotWorldJEPA.calibrate',
                       side_effect=AssertionError('holdout must never calibrate')):
                cls.report = run_holdout(cls.training, cls.holdout, seed=313, rows=160)
        evidence = os.environ.get('V13_HOLDOUT_EVIDENCE_DIR')
        if evidence:
            root = Path(evidence)
            root.mkdir(parents=True, exist_ok=False)
            shutil.copytree(cls.training, root / 'training')
            shutil.copytree(cls.holdout, root / 'heldout')
            print('HOLDOUT_METRICS=' + json.dumps(cls.report['metrics'], sort_keys=True))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_real_linux_holdout_restart_and_controls(self):
        out = self.holdout
        report = self.report
        self.assertEqual(digest(self.checkpoint), self.before)
        self.assertEqual(report['mode'], 'SHADOW_ONLY')
        self.assertEqual(report['authority'], 0)
        self.assertFalse(report['training_performed'])
        self.assertFalse(report['redmi_measured'])
        self.assertEqual(report['holdout_seed'], 313)
        self.assertEqual(report['training_seed'], 212)
        self.assertEqual(report['holdout_rows'], 160)
        self.assertEqual(report['collection'], 'LINUX_TEMP_FILE_WORLD_PROCESS')
        self.assertEqual(report['checkpoint_sha256'], self.before)
        self.assertGreater(report['world_process_log_events'], 0)
        self.assertIn('identity_target_mse', report['metrics'])
        self.assertIn('rotated_action_mse', report['metrics'])
        self.assertIn('action_prediction_mse', report['metrics'])
        self.assertIn('fraction_beats_identity', report['metrics'])
        self.assertIn('fraction_beats_rotated', report['metrics'])
        self.assertIn('uncertain_rows', report['metrics'])
        self.assertEqual(report['metrics']['evaluated_rows'], 160)
        self.assertEqual(report['metrics']['evaluated_slots'], 160 * 6)
        self.assertTrue(all(isinstance(v, (int, float)) for v in report['metrics'].values()))
        self.assertEqual(verify_holdout_export(out, self.training)['verified'], True)
        self.assertEqual(verify_holdout_export(out, self.training)['metrics'], report['metrics'])
        self.assertEqual(digest(self.checkpoint), self.before)

    def test_same_seed_denied_before_any_world_action(self):
        with patch('scripts.world_jepa_holdout_utility.z12b.collect_train',
                   side_effect=AssertionError('world action started')):
            with self.assertRaises(ValueError):
                run_holdout(self.training, self.root / 'same-seed', seed=212, rows=160)
        self.assertFalse((self.root / 'same-seed').exists())

    def test_invalid_row_count_denied_before_any_world_action(self):
        with patch('scripts.world_jepa_holdout_utility.z12b.collect_train',
                   side_effect=AssertionError('world action started')):
            with self.assertRaises(ValueError):
                run_holdout(self.training, self.root / 'too-small', seed=314, rows=119)
        self.assertFalse((self.root / 'too-small').exists())

    def test_unverified_training_denied_before_any_world_action(self):
        bad = self.root / 'unverified-training'
        bad.mkdir(exist_ok=True)
        original = json.loads((self.training / 'manifest.json').read_text())
        original['collection'] = 'CALLER_SUPPLIED_UNVERIFIED'
        (bad / 'manifest.json').write_text(json.dumps(original))
        with patch('scripts.world_jepa_holdout_utility.z12b.collect_train',
                   side_effect=AssertionError('world action started')):
            with self.assertRaises(ValueError):
                run_holdout(bad, self.root / 'unverified-out', seed=315, rows=160)
        self.assertFalse((self.root / 'unverified-out').exists())

    def test_restart_detects_cohort_and_metric_tampering(self):
        out = self.root / 'heldout'
        cohort = out / 'cohort.json'
        original = cohort.read_bytes()
        try:
            cohort.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                verify_holdout_export(out, self.training)
        finally:
            cohort.write_bytes(original)
        manifest = out / 'manifest.json'
        raw = manifest.read_bytes()
        try:
            obj = json.loads(raw)
            obj['metrics']['action_prediction_mse'] += 1.0
            manifest.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                verify_holdout_export(out, self.training)
        finally:
            manifest.write_bytes(raw)
        self.assertTrue(verify_holdout_export(out, self.training)['verified'])
        for field, value in (('redmi_measured', True), ('step2', 'PASS'),
                             ('action_executed_by_model', True)):
            try:
                obj = json.loads(raw)
                obj[field] = value
                manifest.write_text(json.dumps(obj))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_holdout_export(out, self.training)
            finally:
                manifest.write_bytes(raw)

    def test_z_existing_output_refused(self):
        with self.assertRaises(FileExistsError):
            run_holdout(self.training, self.root / 'heldout', seed=316, rows=160)


if __name__ == '__main__':
    unittest.main()
