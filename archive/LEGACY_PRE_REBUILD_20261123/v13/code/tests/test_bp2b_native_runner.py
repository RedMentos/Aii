"""BP2b one-arm runner: synthetic software orchestration, no model execution."""
import fcntl
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import bp2b_native_runner as nr


class FakeTrainer:
    def __init__(self, master, out, **kwargs):
        self.kwargs = kwargs
        self.out = Path(out)
    def fit(self, items, kind):
        if len(items) != 16 or kind != 'bp2b-transfer':
            raise ValueError('unexpected training source')
        self.out.mkdir(parents=True, exist_ok=True)
        artifact = self.out / 'fake-adapter.gguf'
        data = b'SOFTWARE_FAKE_TEST_NOT_A_REAL_GGUF\n'
        artifact.write_bytes(data)
        return {'artifact': str(artifact), 'hash': hashlib.sha256(data).hexdigest(),
                'method': 'SOFTWARE_FAKE_TEST', 'metrics': {'steps': 30}}


def fake_preflight(master, pin, metadata_only):
    assert metadata_only is False
    return {'status': 'FULL_FILE_HASH_PASS', 'master_sha256_verified_locally': True,
            'master_expected_sha256': nr.MASTER_SHA, 'pin_sha256': '1'*64}


def fake_predict(tr, facing):
    return [{'case_id': row['case_id'], 'text': 'No matching information.'} for row in facing]


def fake_eval(tr, facts):
    return {'software_only': True, 'facts': len(facts)}


class NativeRunnerSoftwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_fake(self, arm='bp2b', attempt='test001', **kwargs):
        return nr.run_arm('/fake/master', self.root, 41, arm, attempt,
                          trainer_factory=kwargs.get('trainer_factory', FakeTrainer),
                          predictor=kwargs.get('predictor', fake_predict),
                          preflight=kwargs.get('preflight', fake_preflight),
                          evaluate_fn=fake_eval)

    def test_twelve_preregistered_plans_and_frozen_controls(self):
        for seed in nr.SEEDS:
            for arm in nr.ARMS:
                p = nr.plan(seed, arm)
                self.assertEqual(p['heldout_count'], 32)
                self.assertEqual(p['config']['max_steps'], 30)
                self.assertEqual(p['config']['min_steps'], 30)
                self.assertEqual(p['config']['jepa_weight'], 0)
                self.assertEqual(p['master_expected_sha256'], nr.MASTER_SHA)
                self.assertEqual(p['age_authority'], 0)
                if arm.startswith('bp2b'):
                    self.assertEqual(p['config']['locality_policy'], 'bp2b')
                else:
                    self.assertNotIn('locality_policy', p['config'])
                if arm == 'bp2b_minor':
                    self.assertEqual(p['config']['lora_subspace'], 'minor')
                else:
                    self.assertNotIn('lora_subspace', p['config'])
        self.assertEqual(nr.plan(41, 'manual_ref')['anchor_count_explicit'],
                         nr.plan(41, 'legacy')['anchor_count_explicit'] + 32)

    def test_invalid_arm_seed_attempt_rejected(self):
        for seed, arm in ((1, 'bp2b'), (41, 'wrong'), (True, 'bp2b')):
            with self.assertRaises(ValueError):
                nr.plan(seed, arm)
        with self.assertRaises(ValueError):
            self.run_fake(attempt='../escape')

    def test_preflight_fail_closed_before_attempt_directory(self):
        def no_weights(*args):
            return {'status': 'METADATA_ONLY_PASS', 'master_sha256_verified_locally': False}
        with self.assertRaises(ValueError):
            self.run_fake(preflight=no_weights)
        self.assertFalse((self.root/'seed-41'/'bp2b'/'attempt-test001').exists())

    def test_fake_end_to_end_preserves_blinded_boundary_and_receipts(self):
        result = self.run_fake()
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['evidence_class'], 'SOFTWARE_FAKE_TEST')
        self.assertEqual(result['heldout_score']['heldout_count'], 32)
        self.assertEqual(result['heldout_score']['leak_hits'], 0)
        self.assertFalse(result['heldout_score']['native_proof'])
        self.assertEqual(result['age_authority'], 0)
        folder = self.root/'seed-41'/'bp2b'/'attempt-test001'
        self.assertTrue((folder/'ATTEMPT.json').exists())
        self.assertTrue((folder/'RESULT.json').exists())
        self.assertTrue((folder/'SCORE.json').exists())
        rows = [json.loads(x) for x in (folder/'predictions.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(set(x) == {'case_id', 'text'} for x in rows))
        self.assertNotIn('answer_keys', (folder/'predictions.jsonl').read_text())
        self.assertEqual(json.loads((folder/'SCORE.json').read_text())['evidence_class'],
                         'UNATTESTED_SUPPLIED_PREDICTIONS')

    def test_unique_attempt_directory_never_overwritten(self):
        self.run_fake()
        with self.assertRaises(FileExistsError):
            self.run_fake()

    def test_failed_trainer_preserves_failed_receipt(self):
        class FailTrainer(FakeTrainer):
            def fit(self, items, kind):
                raise RuntimeError('synthetic failure')
        with self.assertRaises(RuntimeError):
            self.run_fake(trainer_factory=FailTrainer, attempt='fail001')
        p = self.root/'seed-41'/'bp2b'/'attempt-fail001'/'FAILED.json'
        self.assertEqual(json.loads(p.read_text())['phase'], 'train')
        self.assertEqual(json.loads(p.read_text())['error_type'], 'RuntimeError')

    def test_exclusive_owner_lock_rejects_concurrent_run(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root/'.bp2b-native-owner.lock').open('a+b') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.run_fake(attempt='locked001')
        self.assertFalse((self.root/'seed-41'/'bp2b'/'attempt-locked001').exists())

    def test_missing_adapter_artifact_is_rejected_before_predict(self):
        class MissingTrainer(FakeTrainer):
            def fit(self, items, kind):
                result = super().fit(items, kind)
                Path(result['artifact']).unlink()
                return result
        with self.assertRaises(ValueError):
            self.run_fake(trainer_factory=MissingTrainer, attempt='missing001')
        receipt = json.loads((self.root/'seed-41'/'bp2b'/'attempt-missing001'/'FAILED.json').read_text())
        self.assertEqual(receipt['phase'], 'train')

    def test_wrong_adapter_digest_is_rejected_before_predict(self):
        class ForgedTrainer(FakeTrainer):
            def fit(self, items, kind):
                result = super().fit(items, kind)
                result['hash'] = '0' * 64
                return result
        with self.assertRaises(ValueError):
            self.run_fake(trainer_factory=ForgedTrainer, attempt='forged001')
        receipt = json.loads((self.root/'seed-41'/'bp2b'/'attempt-forged001'/'FAILED.json').read_text())
        self.assertEqual(receipt['phase'], 'train')

    def test_outside_adapter_artifact_is_rejected_before_predict(self):
        class OutsideTrainer(FakeTrainer):
            def fit(self, items, kind):
                result = super().fit(items, kind)
                outside = self.out.parents[3] / 'outside-fake-adapter.gguf'
                outside.write_bytes(Path(result['artifact']).read_bytes())
                result['artifact'] = str(outside)
                return result
        with self.assertRaises(ValueError):
            self.run_fake(trainer_factory=OutsideTrainer, attempt='outside001')
        receipt = json.loads((self.root/'seed-41'/'bp2b'/'attempt-outside001'/'FAILED.json').read_text())
        self.assertEqual(receipt['phase'], 'train')

    def test_symlink_adapter_artifact_is_rejected_before_predict(self):
        class LinkTrainer(FakeTrainer):
            def fit(self, items, kind):
                result = super().fit(items, kind)
                path = Path(result['artifact'])
                real = path.with_suffix('.original')
                path.rename(real)
                path.symlink_to(real)
                return result
        with self.assertRaises(ValueError):
            self.run_fake(trainer_factory=LinkTrainer, attempt='symlink001')
        receipt = json.loads((self.root/'seed-41'/'bp2b'/'attempt-symlink001'/'FAILED.json').read_text())
        self.assertEqual(receipt['phase'], 'train')

    def test_prepared_source_manifest_must_match_all_frozen_plan_fields(self):
        original_prepare = nr.prepare
        cases = (
            ('train_sha256', '0' * 64, 'trainsha'),
            ('scoring_only_sha256', '0' * 64, 'scorehash'),
            ('selected_indices', list(reversed(nr.plan(41, 'bp2b')['selected_indices'])), 'indices'),
        )
        for key, changed, attempt in cases:
            with self.subTest(key=key):
                def altered_prepare(root, seed):
                    manifest = dict(original_prepare(root, seed))
                    manifest[key] = changed
                    return manifest
                with patch.object(nr, 'prepare', side_effect=altered_prepare):
                    with self.assertRaises(ValueError):
                        self.run_fake(attempt=attempt)
                self.assertFalse((self.root/'seed-41'/'bp2b'/('attempt-' + attempt)).exists())

    def test_invalid_prediction_schema_preserves_failed_receipt(self):
        def leak_keys(tr, facing):
            return [{'case_id': p['case_id'], 'text': 'X', 'answer_keys': ['BAD']}
                    for p in facing]
        with self.assertRaises(ValueError):
            self.run_fake(predictor=leak_keys, attempt='bad001')
        p = self.root/'seed-41'/'bp2b'/'attempt-bad001'/'FAILED.json'
        self.assertEqual(json.loads(p.read_text())['phase'], 'predict')


if __name__ == '__main__':
    unittest.main()
