"""Adversarial tests for registered LP3 readiness source identity (software only).

These use synthetic bytes and never download/execute a model. The genuine
preregistered candidate and fixtures are NOT replaced in the repository.
"""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_native_readiness.py'
spec = importlib.util.spec_from_file_location('lp3_readiness_run15', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class TestRegisteredReadiness(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.master = self.root / 'snapshot'
        self.master.mkdir()
        self.candidate = self.root / 'lp3_memory_key_candidate.py'
        (self.root / 'lp2_assignment_objective.py').write_text('fake LP2 source')
        (self.root / 'lora_bench.py').write_text('fake LoRA source')

    def check(self):
        return mod.inspect(self.master, self.candidate, modules={k: True for k in mod.REQUIRED_DEPS},
                           process_scan=lambda: [], memory_limit=4_294_967_296)

    def test_empty_asset_list_cannot_claim_native_readiness(self):
        self.candidate.write_text('PINNED_MASTER_SHA256 = "' + 'a'*64 + '"\n'
                                  'PINNED_HF_REVISION = "fake"\nHF_ASSETS = ()\n')
        report = self.check()
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertIn('candidate:registered_source_mismatch', report['missing'])
        self.assertIn('asset:model.safetensors', report['missing'])

    def test_replaced_fixture_bytes_cannot_claim_registered_readiness(self):
        data = b'synthetic weight'
        self.candidate.write_text('PINNED_MASTER_SHA256 = "' + hashlib.sha256(data).hexdigest() + '"\n'
                                  'PINNED_HF_REVISION = "fake"\n'
                                  'HF_ASSETS = ("model.safetensors",)\n')
        (self.master / 'model.safetensors').write_bytes(data)
        report = self.check()
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertIn('fixture:lp2_assignment_objective.py:registered_source_mismatch', report['missing'])
        self.assertIn('fixture:lora_bench.py:registered_source_mismatch', report['missing'])

    def test_edited_candidate_constants_never_override_independent_registration(self):
        data = b'weight'
        self.candidate.write_text('PINNED_MASTER_SHA256 = "' + hashlib.sha256(data).hexdigest() + '"\n'
                                  'PINNED_HF_REVISION = "another-revision"\n'
                                  'HF_ASSETS = ("model.safetensors",)\n')
        (self.master / 'model.safetensors').write_bytes(data)
        report = self.check()
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['snapshot_revision'], mod.REGISTERED_HF_REVISION)
        self.assertIn('candidate:registered_constants_mismatch', report['missing'])

    def test_exact_git_blob_identity_and_positive_synthetic_control(self):
        data = b'synthetic model'
        digest = hashlib.sha256(data).hexdigest()
        self.candidate.write_text('PINNED_MASTER_SHA256 = "' + digest + '"\n'
                                  'PINNED_HF_REVISION = "test-revision"\n'
                                  'HF_ASSETS = ("model.safetensors", "config.json")\n')
        (self.master / 'model.safetensors').write_bytes(data)
        (self.master / 'config.json').write_text('{}')
        expected = {p: blob((self.root / p).read_bytes()) for p in
                    ('lp3_memory_key_candidate.py', 'lp2_assignment_objective.py', 'lora_bench.py')}
        with patch.object(mod, 'REGISTERED_MASTER_SHA256', digest), \
             patch.object(mod, 'REGISTERED_HF_REVISION', 'test-revision'), \
             patch.object(mod, 'REGISTERED_HF_ASSETS', ('model.safetensors', 'config.json')), \
             patch.object(mod, 'REGISTERED_SOURCE_GIT_BLOBS', expected):
            report = self.check()
            self.assertEqual(report['status'], 'LOCAL_ASSETS_READY_OWNER_UNVERIFIED')
            self.assertTrue(report['registered_source_blobs_match'])
            self.assertFalse(report['owner_confirmed'])
            self.assertFalse(report['native_executed'])
            (self.root / 'lora_bench.py').write_text('modified')
            modified = self.check()
            self.assertEqual(modified['status'], 'BLOCKED')
            self.assertIn('fixture:lora_bench.py:registered_source_mismatch', modified['missing'])

    def test_original_pr50_candidate_matches_independent_git_blob(self):
        source = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_memory_key_candidate.py'
        self.assertEqual(mod.git_blob_sha1(source), mod.REGISTERED_SOURCE_GIT_BLOBS[source.name])


if __name__ == '__main__':
    unittest.main()
