"""Pre-native source/snapshot binding regression; no actual master loaded."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_memory_key_candidate.py'
# The existing standalone test provides the fixture import before loading LP3.
import test_lp3_memory_key_candidate as existing
mod = existing.mod


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.master = root / 'hf'
        self.master.mkdir()
        self.src = root / 'src'
        self.src.mkdir()
        for name in mod.HF_ASSETS:
            data = b'fake pinned weight' if name == 'model.safetensors' else b'license text'
            if name.endswith('.json'):
                data = b'{"a": 1}'
            (self.master / name).write_bytes(data)
        for name in ('lp2_assignment_objective.py', 'lora_bench.py'):
            (self.src / name).write_text('FACTS = []\nHELDOUT = []\nNEAR_MISS = []\n')
        self.weight_sha = hashlib.sha256((self.master / 'model.safetensors').read_bytes()).hexdigest()
        self.original = mod.PINNED_MASTER_SHA256
        mod.PINNED_MASTER_SHA256 = self.weight_sha
        self.addCleanup(setattr, mod, 'PINNED_MASTER_SHA256', self.original)

    def test_all_assets_and_fixture_sources_are_bound(self):
        r = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        self.assertEqual(set(r['assets_sha256']), set(mod.HF_ASSETS))
        self.assertEqual(set(r['fixture_dependencies_sha256']), {'lp2_assignment_objective.py', 'lora_bench.py'})
        self.assertEqual(r['upstream_nonweight_asset_identity'], 'NOT_INDEPENDENTLY_VERIFIED')

    def test_postflight_unchanged_assets_sources_and_candidate(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        sha = mod._sha256_file(candidate)
        self.assertTrue(mod.verify_postflight_binding(
            self.master, snapshot, sha, source_root=self.src, script_path=candidate))
        self.assertEqual(mod._sha256_file(candidate), sha)

    def test_postflight_changed_weight_refused(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        (self.master / 'model.safetensors').write_bytes(b'changed after preflight')
        with self.assertRaises(ValueError):
            mod.verify_postflight_binding(self.master, snapshot, mod._sha256_file(candidate),
                                          source_root=self.src, script_path=candidate)

    def test_postflight_changed_tokenizer_refused(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        (self.master / 'tokenizer.json').write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'snapshot or fixture changed'):
            mod.verify_postflight_binding(self.master, snapshot, mod._sha256_file(candidate),
                                          source_root=self.src, script_path=candidate)

    def test_postflight_changed_transitive_fixture_refused(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        (self.src / 'lora_bench.py').write_text('FACTS = [1]\n')
        with self.assertRaisesRegex(ValueError, 'snapshot or fixture changed'):
            mod.verify_postflight_binding(self.master, snapshot, mod._sha256_file(candidate),
                                          source_root=self.src, script_path=candidate)

    def test_postflight_changed_candidate_refused(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        original_sha = mod._sha256_file(candidate)
        candidate.write_text('modified candidate\n')
        with self.assertRaisesRegex(ValueError, 'candidate source changed'):
            mod.verify_postflight_binding(self.master, snapshot, original_sha,
                                          source_root=self.src, script_path=candidate)

    def test_postflight_symlink_retarget_refused(self):
        candidate = self.src / 'candidate.py'
        candidate.write_text('fixed candidate\n')
        snapshot = mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
        original = self.master / 'config.json'
        alternate = self.src / 'other_config.json'
        alternate.write_text('{"other": true}')
        original.unlink()
        original.symlink_to(alternate)
        with self.assertRaisesRegex(ValueError, 'snapshot or fixture changed'):
            mod.verify_postflight_binding(self.master, snapshot, mod._sha256_file(candidate),
                                          source_root=self.src, script_path=candidate)

    def test_wrong_master_rejected(self):
        with self.assertRaisesRegex(ValueError, 'preregistered'):
            mod.preflight_binding(self.master, '0' * 64, source_root=self.src)
        (self.master / 'model.safetensors').write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'weight bytes'):
            mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)

    def test_missing_template_or_license_fails_closed(self):
        for name in ('chat_template.jinja', 'LICENSE'):
            p = self.master / name
            old = p.read_bytes()
            p.unlink()
            with self.assertRaisesRegex(ValueError, 'missing/empty'):
                mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)
            p.write_bytes(old)

    def test_missing_transitive_fixture_fails_closed(self):
        (self.src / 'lora_bench.py').unlink()
        with self.assertRaisesRegex(ValueError, 'fixture dependency'):
            mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)

    def test_corrupt_config_refused(self):
        (self.master / 'tokenizer_config.json').write_text('{not json')
        with self.assertRaisesRegex(ValueError, 'invalid HF snapshot JSON'):
            mod.preflight_binding(self.master, self.weight_sha, source_root=self.src)

    def test_real_cli_does_not_create_manifest_without_pinned_master(self):
        out = Path(self.temp.name) / 'output'
        r = subprocess.run([sys.executable, str(SCRIPT), '--master', str(self.master),
                            '--master-sha256', '0' * 64, '--out', str(out)],
                           capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(self.src)})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('HARD_BLOCKER', r.stderr)
        self.assertFalse((out / 'run_manifest.json').exists())

    def test_existing_attempt_refused_before_touching(self):
        out = Path(self.temp.name) / 'output'
        out.mkdir()
        (out / 'seed-31.json').write_text('old evidence')
        r = subprocess.run([sys.executable, str(SCRIPT), '--master', str(self.master),
                            '--master-sha256', '0' * 64, '--out', str(out)],
                           capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(self.src)})
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((out / 'seed-31.json').read_text(), 'old evidence')
        self.assertIn('existing attempt directory', r.stderr)

if __name__ == '__main__': unittest.main()
