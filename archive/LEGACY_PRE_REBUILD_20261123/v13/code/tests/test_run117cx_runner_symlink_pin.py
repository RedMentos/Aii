"""Run117CX software-only canonical runner symlink pin controls."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117cv_qwen_c3_native as cv


class CanonicalRunnerSymlinkPin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "installed"
        self.bin = self.home / "bin"
        self.stage = self.bin / ".llama-b10964-testnonce" / "release"
        self.stage.mkdir(parents=True)
        self.target = self.stage / "llama-server"
        self.target.write_bytes(b"synthetic binary bytes for pin topology test")
        self.digest = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.runner = self.bin / "llama-server"
        self.runner.symlink_to(self.target.resolve())
        self.manifest = self.home / "config/runner.json"
        self.manifest.parent.mkdir()
        self.data = {"tag": "b10964", "platform": "linux-x86_64",
                     "binary_sha256": self.digest, "version": "synthetic"}
        self.manifest.write_text(json.dumps(self.data))
        self.pin = patch.object(cv, "RUNNER_SHA", self.digest)
        self.pin.start()

    def tearDown(self):
        self.pin.stop()
        self.tmp.cleanup()

    def test_valid_canonical_in_home_symlink_and_actual_hash(self):
        self.assertTrue(self.runner.is_symlink())
        self.assertEqual(cv.file_hash(self.runner), self.digest)
        self.assertTrue(cv.runner_binding_valid(self.home))

    def test_wrong_manifest_hash_tag_and_platform_refused(self):
        for field, wrong in (("binary_sha256", "0" * 64),
                             ("tag", "unregistered"),
                             ("platform", "android-arm64")):
            with self.subTest(field=field):
                bad = dict(self.data, **{field: wrong})
                self.manifest.write_text(json.dumps(bad))
                self.assertFalse(cv.runner_binding_valid(self.home))
        self.manifest.write_text(json.dumps(self.data))
        self.assertTrue(cv.runner_binding_valid(self.home))

    def test_runner_escape_and_symlink_chain_refused(self):
        outside = Path(self.tmp.name) / "outside" / "llama-server"
        outside.parent.mkdir()
        outside.write_bytes(self.target.read_bytes())
        self.runner.unlink()
        self.runner.symlink_to(outside.resolve())
        self.assertFalse(cv.runner_binding_valid(self.home))
        self.runner.unlink()
        alias = self.bin / "alias"
        alias.symlink_to(self.target.resolve())
        self.runner.symlink_to(alias.resolve(strict=False))
        # Direct link to alias, not to the staged regular file.
        self.runner.unlink()
        self.runner.symlink_to(alias)
        self.assertFalse(cv.runner_binding_valid(self.home))

    def test_wrong_staging_directory_and_regular_file_refused(self):
        wrong = self.bin / "wrong-stage" / "release" / "llama-server"
        wrong.parent.mkdir(parents=True)
        wrong.write_bytes(self.target.read_bytes())
        self.runner.unlink()
        self.runner.symlink_to(wrong.resolve())
        self.assertFalse(cv.runner_binding_valid(self.home))
        self.runner.unlink()
        self.runner.write_bytes(self.target.read_bytes())
        self.assertFalse(cv.runner_binding_valid(self.home))

    def test_mutated_binary_and_missing_manifest_refused(self):
        self.target.write_bytes(b"changed")
        self.assertFalse(cv.runner_binding_valid(self.home))
        self.target.write_bytes(b"synthetic binary bytes for pin topology test")
        self.manifest.unlink()
        self.assertFalse(cv.runner_binding_valid(self.home))

    def test_manifest_symlink_refused(self):
        copy = self.home / "config/real.json"
        copy.write_text(json.dumps(self.data))
        self.manifest.unlink()
        self.manifest.symlink_to(copy)
        self.assertFalse(cv.runner_binding_valid(self.home))


if __name__ == "__main__":
    unittest.main()
