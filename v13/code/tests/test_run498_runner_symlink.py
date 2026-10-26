"""Run498 actual bootstrap runner symlink containment + byte-gate adversarial tests."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run496_heldout10_native_pilot as P
import run491_step2_heldout10 as F


class RunnerSymlink(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "installed"
        self.bin = self.home / "bin"
        self.bin.mkdir(parents=True)
        self.target = self.bin / "b10964" / "build" / "bin" / "llama-server"
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"pinned-test-binary")
        self.runner = self.bin / "llama-server"

    def tearDown(self):
        self.tmp.cleanup()

    def test_actual_bootstrap_style_absolute_internal_symlink_allowed(self):
        self.runner.symlink_to(self.target)
        self.assertTrue(P.runner_target_within_bin(self.home, self.runner))
        self.assertTrue(self.runner.is_symlink())

    def test_regular_binary_inside_bin_allowed(self):
        self.runner.write_bytes(b"pinned-test-binary")
        self.assertTrue(P.runner_target_within_bin(self.home, self.runner))

    def test_external_symlink_refused_even_if_file_exists(self):
        outside = Path(self.tmp.name) / "outside-llama-server"
        outside.write_bytes(b"pinned-test-binary")
        self.runner.symlink_to(outside)
        self.assertFalse(P.runner_target_within_bin(self.home, self.runner))

    def test_broken_symlink_refused(self):
        self.runner.symlink_to(self.bin / "b10964" / "missing")
        self.assertFalse(P.runner_target_within_bin(self.home, self.runner))

    def test_indirect_symlink_escape_refused(self):
        outside = Path(self.tmp.name) / "outside-llama-server"
        outside.write_bytes(b"pinned-test-binary")
        intermediate = self.bin / "b10964" / "redirect"
        intermediate.symlink_to(outside)
        self.runner.symlink_to(intermediate)
        self.assertFalse(P.runner_target_within_bin(self.home, self.runner))

    def test_verify_installed_still_enforces_exact_hash_and_metadata(self):
        self.runner.symlink_to(self.target)
        (self.home / "config").mkdir()
        (self.home / "config" / "runner.json").write_text(
            json.dumps({"tag": "b10964", "binary_sha256": F.RUNNER_SHA256}))
        import v13.models as models
        import v13.common as common
        import v13.memory_server as memory
        roles = ("needle", "language", "body", "gist")
        class FakeManager:
            installed = {k: {"exact_revision": "pin"} for k in roles}
            def __init__(self, home): self.home = home
            def verify(self, deep=False):
                if not deep: raise AssertionError("DEEP_HASH_REQUIRED")
                return {k: {"ok": True, "hash_checked": True} for k in roles}
            def path_for(self, role): return Path(role)
        def file_hash(path):
            if Path(path) == self.runner:
                return self.runner_hash
            return F.MODEL_SHA256[str(path)]
        self.runner_hash = F.RUNNER_SHA256
        catalog = {"models": {k: {"revision": "pin"} for k in roles}}
        with patch.object(models, "ModelManager", FakeManager), \
             patch.object(models, "catalog", return_value=catalog), \
             patch.object(common, "file_hash", side_effect=file_hash), \
             patch.object(memory, "runtime_library_hashes", return_value={"libggml.so": "verified"}):
            good = P.verify_installed(self.home)
            self.assertEqual(good["runner_sha256"], F.RUNNER_SHA256)
            self.assertIs(good["native_executed"], False)
            self.runner_hash = "0" * 64
            with self.assertRaisesRegex(ValueError, "PINNED_RUNNER_BINARY_CHANGED"):
                P.verify_installed(self.home)
            self.runner_hash = F.RUNNER_SHA256
            (self.home / "config" / "runner.json").write_text(
                json.dumps({"tag": "b10963", "binary_sha256": F.RUNNER_SHA256}))
            with self.assertRaisesRegex(ValueError, "PINNED_RUNNER_METADATA_CHANGED"):
                P.verify_installed(self.home)


if __name__ == "__main__":
    unittest.main()
