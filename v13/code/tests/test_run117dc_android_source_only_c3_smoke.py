"""Run117DC software-only Android pin/topology tests, no device/native proof."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117dc_android_source_only_c3_smoke as dc


class FakeManager:
    revision_value = dc.MODEL_REV
    def __init__(self, home):
        self.home = Path(home)
    def path_for(self, role):
        assert role == "C3_LANGUAGE"
        return self.home / "models" / dc.MODEL_FILE
    def revision(self, role):
        return self.revision_value


class AndroidSourceOnlyLocalPin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.installed = self.root / "installed"
        self.model = self.installed / "models" / dc.MODEL_FILE
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"synthetic-model-bytes")
        self.model_sha = hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.stage = self.installed / "bin/.llama-b10964-test/release"
        self.stage.mkdir(parents=True)
        self.binary = self.stage / "llama-server"
        self.binary.write_bytes(b"synthetic-runner-bytes")
        self.binary_sha = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        self.link = self.installed / "bin/llama-server"
        self.link.symlink_to(self.binary.resolve())
        self.manifest = self.installed / "config/runner.json"
        self.manifest.parent.mkdir()
        self.data = {"tag": "b10964", "platform": "android-arm64",
                     "binary_sha256": self.binary_sha}
        self.manifest.write_text(json.dumps(self.data))
        self.patches = [
            patch.object(dc, "platform_tag", return_value="android-arm64"),
            patch.object(dc, "ModelManager", FakeManager),
            patch.object(dc, "MODEL_SHA", self.model_sha),
            patch.object(dc, "MODEL_SIZE", len(self.model.read_bytes())),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_valid_local_build_is_only_self_consistent(self):
        self.assertEqual(dc.android_pin(self.installed), self.model)
        self.assertEqual(dc.PLATFORM, "android-arm64")
        self.assertEqual(dc.SCHEMA,
                         "v13.run117dc.android_local_source_only_c3_unverified_runner.v1")

    def test_wrong_revision_model_bytes_and_symlink_refused(self):
        with patch.object(FakeManager, "revision_value", "old-230m"):
            with self.assertRaisesRegex(ValueError, "C3_PIN_RED"):
                dc.android_pin(self.installed)
        self.model.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "C3_PIN_RED"):
            dc.android_pin(self.installed)
        self.model.write_bytes(b"synthetic-model-bytes")
        self.model.unlink()
        real = self.model.parent / "real-model.gguf"
        real.write_bytes(b"synthetic-model-bytes")
        self.model.symlink_to(real)
        with self.assertRaisesRegex(ValueError, "C3_PIN_RED"):
            dc.android_pin(self.installed)

    def test_manifest_wrong_platform_tag_hash_and_symlink_refused(self):
        for key, bad in (("platform", "linux-x86_64"),
                         ("tag", "other"),
                         ("binary_sha256", "0"*64)):
            with self.subTest(key=key):
                self.manifest.write_text(json.dumps(dict(self.data, **{key: bad})))
                with self.assertRaisesRegex(ValueError, "RUNNER_BINDING_RED"):
                    dc.android_pin(self.installed)
        self.manifest.write_text(json.dumps(self.data))
        self.assertEqual(dc.android_pin(self.installed), self.model)
        self.manifest.unlink()
        self.manifest.symlink_to(self.root / "absent")
        with self.assertRaisesRegex(ValueError, "RUNNER_MANIFEST_RED"):
            dc.android_pin(self.installed)

    def test_runner_symlink_escape_and_chain_refused(self):
        outside = self.root / "outside/llama-server"
        outside.parent.mkdir()
        outside.write_bytes(self.binary.read_bytes())
        self.link.unlink()
        self.link.symlink_to(outside.resolve())
        with self.assertRaisesRegex(ValueError, "RUNNER_BINDING_RED"):
            dc.android_pin(self.installed)
        self.link.unlink()
        alias = self.installed / "bin/alias"
        alias.symlink_to(self.binary.resolve())
        self.link.symlink_to(alias)
        with self.assertRaisesRegex(ValueError, "RUNNER_BINDING_RED"):
            dc.android_pin(self.installed)

    def test_linux_refused_without_touching_installed(self):
        with patch.object(dc, "platform_tag", return_value="linux-x86_64"):
            with self.assertRaisesRegex(ValueError, "ANDROID_ONLY"):
                dc.run_phone(self.installed, self.root / "probe", self.root / "raw")
        self.assertFalse((self.root / "probe").exists())
        self.assertFalse((self.root / "raw").exists())

    def test_isolated_paths_and_existing_outputs_required(self):
        with self.assertRaisesRegex(ValueError, "ISOLATED_PATHS_REQUIRED"):
            dc.run_phone(self.installed, self.installed / "probe", self.root / "raw")
        with self.assertRaisesRegex(ValueError, "ISOLATED_PATHS_REQUIRED"):
            dc.run_phone(self.installed, self.root / "probe", self.installed / "raw")
        with self.assertRaisesRegex(ValueError, "ISOLATED_PATHS_REQUIRED"):
            dc.run_phone(self.installed, self.root / "probe", self.root / "probe/raw")
        (self.root / "probe").mkdir()
        with self.assertRaises(FileExistsError):
            dc.run_phone(self.installed, self.root / "probe", self.root / "raw")

    def test_manual_only_no_automatic_download_or_delivery(self):
        self.assertFalse(hasattr(dc, "download_model"))
        self.assertEqual(dc.MODEL_FILE, "LFM2.5-350M-QAD-Q4_0.gguf")
        self.assertEqual(dc.MODEL_REV,
                         "657e078c94084481950a2d555a941481f715536b")


if __name__ == "__main__":
    unittest.main()
