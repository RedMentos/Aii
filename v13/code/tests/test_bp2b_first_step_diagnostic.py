"""BP2b first-step diagnostic SOFTWARE_FAKE_TEST controls; no public master loaded."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import bp2b_first_step_diagnostic as D
from v13 import body_jepa_checkpoint as checkpoint


def preflight(*args):
    return {'status': 'FULL_FILE_HASH_PASS',
            'master_sha256_verified_locally': True,
            'master_expected_sha256': D.MASTER_SHA}


class FakeTrainer:
    last_cfg = None

    def __init__(self, master, work, *, master_sha256, anchors, cfg, arch):
        self.__class__.last_cfg = cfg
        assert master_sha256 == D.MASTER_SHA
        assert arch == 'lfm2'
        assert anchors

    def fit(self, items, generation):
        assert generation == 'bp2b-first-step-diagnostic'
        assert items and all('answer_keys' in row for row in items)
        checkpoint.save('synthetic')


class NoCheckpoint(FakeTrainer):
    def fit(self, items, generation):
        return {'artifact': 'NOT_A_CHECKPOINT'}


class FirstStepDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_plan_is_new_one_step_cohort_without_changing_frozen_reference(self):
        p = D.diagnostic_plan()
        self.assertEqual(p['reference']['seed'], 41)
        self.assertEqual(p['reference']['arm'], 'legacy')
        self.assertEqual(p['reference']['config']['max_steps'], 30)
        self.assertEqual(p['reference']['config']['min_steps'], 30)
        self.assertEqual(p['diagnostic_config']['max_steps'], 1)
        self.assertEqual(p['diagnostic_config']['min_steps'], 1)
        self.assertTrue(p['diagnostic_config']['checkpoint_resume'])
        self.assertEqual(p['diagnostic_config']['jepa_weight'], 0)
        self.assertEqual(p['age_authority'], 0)

    def test_first_step_receipt_and_raw_rss_are_persisted_in_isolated_attempt(self):
        expected_sha = 'a' * 64
        result = D.run_probe('fake-master', self.root, 'test-01',
                             preflight=preflight, trainer_factory=FakeTrainer,
                             save_fn=lambda *a, **k: {'step': 1, 'sha256': expected_sha})
        self.assertEqual(result['status'], 'FIRST_STEP_COMMITTED')
        self.assertEqual(result['checkpoint_sha256'], expected_sha)
        self.assertEqual(result['evidence_class'], 'SOFTWARE_FAKE_TEST')
        self.assertEqual(result['age_authority'], 0)
        self.assertTrue(FakeTrainer.last_cfg['checkpoint_resume'])
        folder = self.root / 'attempt-test-01'
        self.assertEqual(json.loads((folder / 'RESULT.json').read_text()), result)
        self.assertTrue((folder / 'RSS.jsonl').read_text().strip())
        self.assertFalse((folder / 'FAILED.json').exists())
        with self.assertRaises(FileExistsError):
            D.run_probe('fake-master', self.root, 'test-01', preflight=preflight,
                        trainer_factory=FakeTrainer, save_fn=lambda *a, **k: {'step': 1, 'sha256': expected_sha})

    def test_return_without_first_step_fails_and_retains_failed_receipt(self):
        with self.assertRaisesRegex(ValueError, 'without a completed first-step'):
            D.run_probe('fake-master', self.root, 'test-02',
                        preflight=preflight, trainer_factory=NoCheckpoint)
        failure = json.loads((self.root / 'attempt-test-02' / 'FAILED.json').read_text())
        self.assertEqual(failure['status'], 'FAILED')
        self.assertEqual(failure['error_class'], 'ValueError')
        self.assertFalse((self.root / 'attempt-test-02' / 'RESULT.json').exists())

    def test_unverified_master_refused_before_attempt_directory(self):
        def unverified(*args):
            return dict(preflight(), master_sha256_verified_locally=False)
        with self.assertRaisesRegex(ValueError, 'full master preflight'):
            D.run_probe('fake-master', self.root, 'test-03',
                        preflight=unverified, trainer_factory=FakeTrainer)
        self.assertFalse((self.root / 'attempt-test-03').exists())

    def test_bad_checkpoint_receipt_cannot_claim_first_step(self):
        with self.assertRaisesRegex(ValueError, 'verified first-step checkpoint'):
            D.run_probe('fake-master', self.root, 'test-04',
                        preflight=preflight, trainer_factory=FakeTrainer,
                        save_fn=lambda *a, **k: {'step': 2, 'sha256': 'not-a-sha'})
        self.assertTrue((self.root / 'attempt-test-04' / 'FAILED.json').exists())

    def test_invalid_attempt_and_cli_require_explicit_execution(self):
        for bad in ('', '../bad', 'a.b', 'x'*33):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    D.run_probe('fake-master', self.root, bad,
                                preflight=preflight, trainer_factory=FakeTrainer)
        with self.assertRaises(ValueError):
            D.main([])
        self.assertEqual(D.main(['--dry-run']), 0)


if __name__ == '__main__':
    unittest.main()
