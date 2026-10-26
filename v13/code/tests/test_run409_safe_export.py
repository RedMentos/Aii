"""Run409 synthetic no-model export and negative-history preservation controls."""
import fcntl
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run409_safe_export as m


class Run409ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.installed = self.root / "installed"
        (self.installed / "models").mkdir(parents=True)
        (self.installed / "bin").mkdir()
        (self.installed / "models" / "public.gguf").write_bytes(b"registered-public-model")
        self.attempt = self.work / "attempts/O_s20/attempt-0001"
        self.attempt.mkdir(parents=True)
        self.home = self.attempt / "arm_home"
        self.home.mkdir()
        (self.home / "models").symlink_to(self.installed / "models", target_is_directory=True)
        (self.home / "bin").symlink_to(self.installed / "bin", target_is_directory=True)
        (self.work / "RUN397_OWNER.lock").write_bytes(b"")
        (self.work / "RUN397_PROGRESS.json").write_text('{"failures_preserved":{"O_s20":[{"attempt":"attempts/O_s20/attempt-0001"}]}}')
        (self.attempt / "RUN397_FAILED.json").write_text('{"error_type":"synthetic failure"}')
        (self.work / "empty").mkdir()
        self.dest = self.root / "export"

    def check(self):
        return m.export(self.work, self.installed, self.dest)

    def test_export_preserves_all_raw_and_excludes_model_symlinks(self):
        result = self.check()
        self.assertEqual(result["status"], "EXPORT_VERIFIED_NO_MODEL_WEIGHTS")
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["redmi_measured"])
        self.assertTrue((self.dest / "empty").is_dir())
        self.assertEqual((self.dest / "RUN397_PROGRESS.json").read_bytes(),
                         (self.work / "RUN397_PROGRESS.json").read_bytes())
        self.assertEqual((self.dest / "attempts/O_s20/attempt-0001/RUN397_FAILED.json").read_bytes(),
                         (self.attempt / "RUN397_FAILED.json").read_bytes())
        self.assertFalse((self.dest / "attempts/O_s20/attempt-0001/arm_home/models").exists())
        self.assertFalse((self.dest / "attempts/O_s20/attempt-0001/arm_home/bin").exists())
        manifest = json.loads((self.dest / m.MANIFEST).read_text())
        self.assertEqual(set(manifest["omitted_installed_symlinks"]), {
            "attempts/O_s20/attempt-0001/arm_home/models",
            "attempts/O_s20/attempt-0001/arm_home/bin"})
        for name, meta in manifest["copied"].items():
            self.assertEqual(hashlib.sha256((self.dest / name).read_bytes()).hexdigest(),
                             meta["sha256"])
        self.assertTrue((self.installed / "models" / "public.gguf").exists())

    def test_unknown_symlink_directory_rejected(self):
        (self.work / "unrelated").symlink_to(self.installed / "models", target_is_directory=True)
        result = self.check()
        self.assertIn("UNSAFE_SYMLINK_DIRECTORY", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_symlink_to_wrong_installed_target_rejected(self):
        (self.home / "models").unlink()
        (self.home / "models").symlink_to(self.root, target_is_directory=True)
        result = self.check()
        self.assertIn("UNSAFE_SYMLINK_DIRECTORY", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_symlink_file_rejected(self):
        (self.work / "alias.json").symlink_to(self.work / "RUN397_PROGRESS.json")
        result = self.check()
        self.assertIn("UNSAFE_SYMLINK_FILE", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_unexpected_regular_gguf_rejected(self):
        (self.work / "model.gguf").write_bytes(b"model")
        result = self.check()
        self.assertIn("MODEL_OR_MANIFEST_FILE_IN_WORK", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_unexpected_regular_model_under_models_rejected(self):
        (self.work / "models").mkdir()
        (self.work / "models" / "renamed.dat").write_bytes(b"model")
        result = self.check()
        self.assertIn("MODEL_OR_MANIFEST_FILE_IN_WORK", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_existing_destination_not_overwritten(self):
        self.dest.mkdir()
        (self.dest / "owner").write_text("another owner")
        result = self.check()
        self.assertIn("DESTINATION_NOT_FRESH", str(result["errors"]))
        self.assertEqual((self.dest / "owner").read_text(), "another owner")

    def test_active_native_owner_lock_rejected(self):
        with (self.work / "RUN397_OWNER.lock").open("rb") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.check()
        self.assertIn("NATIVE_OWNER_ACTIVE", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_source_mutation_after_copy_fails_closed(self):
        original = m._copy_regular
        def changing(source, target):
            result = original(source, target)
            if source.name == "RUN397_PROGRESS.json":
                source.write_text("changed")
            return result
        with mock.patch.object(m, "_copy_regular", side_effect=changing):
            result = self.check()
        self.assertIn("SOURCE_CHANGED_AFTER_COPY", str(result["errors"]))
        self.assertFalse(self.dest.exists())

    def test_empty_work_rejected(self):
        work = self.root / "empty-work"
        work.mkdir()
        result = m.export(work, self.installed, self.dest)
        self.assertIn("EMPTY_EXPORT", str(result["errors"]))
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
