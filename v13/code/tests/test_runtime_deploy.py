"""Network-free staged deployment regression: real launcher switch, immutable snapshots.

No Android phone, model downloads or GitHub access. Tests only source/data
separation, rollback boundaries and fail-closed conditions.
"""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest import mock

from v13 import runtime_deploy as d


class RuntimeDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.checkout = self.root / "checkout"
        self.code = self.checkout / "v13/code"
        for rel in d.REQUIRED:
            path = self.code / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("fake fixture " + rel).encode())
        for rel in d.COPY_SUBTREES:
            (self.code / rel).mkdir(parents=True, exist_ok=True)
        self.home = self.root / "data-home"
        (self.home / "bin").mkdir(parents=True)
        (self.home / "models").mkdir(parents=True)
        (self.home / "config").mkdir(parents=True)
        (self.home / "data/db").mkdir(parents=True)
        self.launcher = self.home / "bin/v13"
        self.old = b"#!/bin/sh\necho old\n"
        self.launcher.write_bytes(self.old)
        (self.home / "models/model.gguf").write_bytes(b"GGUF_NOT_A_REAL_MODEL")
        (self.home / "config/settings.json").write_text('{"threads":4}')
        (self.home / "data/db/brain.sqlite3").write_bytes(b"EXISTING_DB_DO_NOT_CHANGE")
        self.private = self.root / "private"
        self.builds = self.root / "builds"
        self.commit = "d" * 40
        self.source_patch = mock.patch.object(d, "_source",
            return_value=(self.checkout, self.code, self.commit))
        self.stop_patch = mock.patch.object(d, "_check_stopped")
        self.selftest_patch = mock.patch.object(d, "_selftest")
        for patch in (self.source_patch, self.stop_patch, self.selftest_patch):
            patch.start()
            self.addCleanup(patch.stop)

    def _run(self):
        return d.deploy(self.checkout, home=self.home, private=self.private,
                        builds=self.builds, ci_verified=True)

    def test_switches_actual_launcher_with_full_canon_and_preserves_userdata(self):
        first = self._run()
        self.assertEqual(first["status"], "DEPLOYED")
        path = Path(first["code"])
        self.assertTrue((path / d.CANON).is_file())
        self.assertIn(str(path).encode(), self.launcher.read_bytes())
        self.assertIn(b'--home', self.launcher.read_bytes())
        self.assertEqual((self.home/"models/model.gguf").read_bytes(), b"GGUF_NOT_A_REAL_MODEL")
        self.assertEqual((self.home/"data/db/brain.sqlite3").read_bytes(), b"EXISTING_DB_DO_NOT_CHANGE")
        self.assertEqual((self.home/"config/settings.json").read_text(), '{"threads":4}')
        self.assertEqual(self._run()["status"], "UP_TO_DATE")
        marker = json.loads((self.private/d.MARKER_NAME).read_text())
        self.assertEqual(marker["commit"], self.commit)
        self.assertEqual(hashlib.sha256(self.launcher.read_bytes()).hexdigest(), marker["launcher_sha256"])
        self.assertEqual(Path(marker["backup_launcher"]).read_bytes(), self.old)

    def test_staging_failure_retains_old_launcher_and_memory(self):
        with mock.patch.object(d, "_selftest", side_effect=d.RuntimeDeployError("broken staged runtime")):
            with self.assertRaises(d.RuntimeDeployError):
                self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)
        self.assertEqual((self.home/"data/db/brain.sqlite3").read_bytes(), b"EXISTING_DB_DO_NOT_CHANGE")

    def test_active_runtime_blocks_before_switch(self):
        with mock.patch.object(d, "_check_stopped", side_effect=d.RuntimeDeployError("running")):
            with self.assertRaises(d.RuntimeDeployError):
                self._run()
        self.assertEqual(self.launcher.read_bytes(), self.old)

    def test_symlink_launcher_rejected(self):
        self.launcher.unlink()
        self.launcher.symlink_to(self.home / "config/settings.json")
        with self.assertRaises(d.RuntimeDeployError):
            self._run()
        self.assertEqual((self.home/"config/settings.json").read_text(), '{"threads":4}')


if __name__ == "__main__":
    unittest.main()
