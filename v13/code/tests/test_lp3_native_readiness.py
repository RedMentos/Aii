"""Software-only LP3 native preflight checks; never download or load a model."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_native_readiness.py'
spec = importlib.util.spec_from_file_location('lp3_readiness', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestNativeReadiness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.master = self.root / 'master'
        self.master.mkdir()
        self.candidate = self.root / 'candidate.py'
        self.candidate.write_text('PINNED_MASTER_SHA256 = "'+('a'*64)+'"\n'
                                  'HF_ASSETS = ("model.safetensors", "config.json")\n'
                                  'PINNED_HF_REVISION = "fixed"\n')
        (self.root / 'lp2_assignment_objective.py').write_text('fixture1')
        (self.root / 'lora_bench.py').write_text('fixture2')

    def check(self, **kwargs):
        return mod.inspect(self.master, self.candidate, modules={'torch': True,
                           'transformers': True, 'safetensors': True},
                           process_scan=lambda: [], memory_limit=1024, **kwargs)

    def test_native_process_argv_does_not_confuse_preflight_or_shell(self):
        self.assertTrue(mod.is_lp3_native_argv(['python', '/repo/lp3_memory_key_candidate.py', '--master', '/x']))
        self.assertFalse(mod.is_lp3_native_argv(['python', '/repo/lp3_native_readiness.py', '--candidate', '/repo/lp3_memory_key_candidate.py']))
        self.assertFalse(mod.is_lp3_native_argv(['bash', '-lc', 'python lp3_memory_key_candidate.py']))

    def test_missing_assets_are_reported_without_creating_evidence(self):
        result = self.check()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('asset:model.safetensors', result['missing'])
        self.assertEqual(sorted(p.name for p in self.master.iterdir()), [])
        self.assertFalse(result['native_executed'])

    def test_missing_dependency_is_hard_blocker(self):
        r = mod.inspect(self.master, self.candidate, modules={'torch': True,
                        'transformers': False, 'safetensors': True},
                        process_scan=lambda: [], memory_limit=1024)
        self.assertIn('python_module:transformers', r['missing'])

    def test_active_local_lp3_job_blocks(self):
        r = mod.inspect(self.master, self.candidate, modules={'torch': True,
                        'transformers': True, 'safetensors': True},
                        process_scan=lambda: [123], memory_limit=1024)
        self.assertIn('local_lp3_process_active', r['missing'])
        self.assertEqual(r['local_lp3_process_count'], 1)
        self.assertFalse(r['owner_confirmed'])

    def test_missing_fixture_is_blocker(self):
        (self.root / 'lora_bench.py').unlink()
        self.assertIn('fixture:lora_bench.py', self.check()['missing'])

    def test_corrupted_master_is_blocker(self):
        (self.master / 'model.safetensors').write_bytes(b'wrong')
        (self.master / 'config.json').write_bytes(b'{}')
        self.assertIn('asset:master_sha256_mismatch', self.check()['missing'])

    def test_hf_snapshot_symlinks_are_hashed_not_rejected(self):
        # Standard Hugging Face cache layout: snapshots/<rev>/name -> blobs/hash
        blob = self.root / 'blob'
        blob.write_bytes(b'wrong')
        (self.master / 'model.safetensors').symlink_to(blob)
        (self.master / 'config.json').write_text('{}')
        r = self.check()
        self.assertIn('model.safetensors', r['asset_symlinks_followed'])
        self.assertEqual(r['asset_hashes']['model.safetensors'], mod.file_sha256(blob))
        self.assertIn('asset:master_sha256_mismatch', r['missing'])
        self.assertNotIn('asset:model.safetensors', r['missing'])

    def test_candidate_is_parsed_not_executed(self):
        self.candidate.write_text(self.candidate.read_text() + '\nraise RuntimeError("never execute")\n')
        self.assertEqual(self.check()['status'], 'BLOCKED')

    def test_no_candidate_source_fails_closed(self):
        self.candidate.unlink()
        self.assertEqual(self.check()['reason'], 'CANDIDATE_SOURCE_UNREADABLE')

    def test_source_constants_cannot_be_dynamic_expressions(self):
        self.candidate.write_text('PINNED_MASTER_SHA256 = str(123)\n'
                                  'HF_ASSETS = ("model.safetensors",)\n'
                                  'PINNED_HF_REVISION = "fixed"\n')
        self.assertEqual(self.check()['reason'], 'CANDIDATE_SOURCE_UNREADABLE')


if __name__ == '__main__':
    unittest.main()
