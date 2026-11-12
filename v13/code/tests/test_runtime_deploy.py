"""Network-free staged deployment regression: real launcher switch, immutable snapshots.

No Android phone, model downloads or GitHub access. Tests only source/data
separation, rollback boundaries and fail-closed conditions.
"""
from pathlib import Path
import hashlib
import json
import subprocess
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

    def test_unverified_ci_never_switches_launcher(self):
        with mock.patch("v13.source_updater.ci_passed", return_value=False):
            with self.assertRaises(d.RuntimeDeployError):
                d.deploy(self.checkout, home=self.home, private=self.private,
                         builds=self.builds)
        self.assertEqual(self.launcher.read_bytes(), self.old)


class RuntimeSourcePreparationTests(unittest.TestCase):
    """Real Git fixtures exercise old/missing checkouts, without network."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.seed = self.base / "release"
        self.seed.mkdir()
        self.git(self.seed, "init", "--initial-branch=" + d.SOURCE_BRANCH)
        self.git(self.seed, "config", "user.name", "Synthetic fixture")
        self.git(self.seed, "config", "user.email", "fixture@example.invalid")
        self.git(self.seed, "remote", "add", "origin", d.REPO_ORIGIN[1])
        for rel in d.REQUIRED:
            target = self.seed / "v13/code" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# synthetic source fixture\n")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "Synthetic runtime release")
        self.target = self.base / "runtime-source"

    @staticmethod
    def git(root, *args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    def local_clones(self):
        real_run = subprocess.run
        def run(args, **kwargs):
            if args[:2] == ["git", "clone"]:
                self.assertEqual(args[-2], d.REPO_ORIGIN[1])
                proc = real_run([*args[:-2], str(self.seed), args[-1]], **kwargs)
                if proc.returncode == 0:
                    real_run(["git", "-C", args[-1], "remote", "set-url", "origin",
                              d.REPO_ORIGIN[1]], check=True, capture_output=True)
                return proc
            return real_run(args, **kwargs)
        return mock.patch.object(d.subprocess, "run", side_effect=run)

    def test_missing_runtime_checkout_is_prepared_on_fixed_release(self):
        with self.local_clones():
            result = d.prepare_source(self.target)
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(result["commit"], self.git(self.seed, "rev-parse", "HEAD"))
        self.assertEqual(self.git(self.target, "branch", "--show-current"), d.SOURCE_BRANCH)
        self.assertEqual(self.git(self.target, "remote", "get-url", "origin"), d.REPO_ORIGIN[1])
        for rel in d.REQUIRED:
            self.assertTrue((self.target / "v13/code" / rel).is_file(), rel)
        self.assertFalse(list(self.base.glob(".v13-source-*")))
        self.assertEqual(d.prepare_source(self.target)["status"], "READY")

    def test_existing_incomplete_sparse_checkout_is_migrated(self):
        with self.local_clones():
            d.prepare_source(self.target)
        self.git(self.target, "sparse-checkout", "set", "--no-cone",
                 "v13/code/v13/common.py")
        self.assertFalse((self.target / "v13/code" / d.CANON).exists())
        previous = self.git(self.target, "rev-parse", "HEAD")
        d.prepare_source(self.target)
        self.assertEqual(self.git(self.target, "rev-parse", "HEAD"), previous)
        self.assertTrue((self.target / "v13/code" / d.CANON).is_file())
        self.assertEqual(self.git(self.target, "status", "--porcelain"), "")

    def test_existing_untrusted_checkout_and_local_edits_are_retained(self):
        with self.local_clones():
            d.prepare_source(self.target)
        path = self.target / "v13/code/v13/common.py"
        path.write_text("# local edit that must survive\n")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertIn("must survive", path.read_text())
        self.git(self.target, "restore", ".")
        self.git(self.target, "remote", "set-url", "origin", "https://example.invalid/untrusted.git")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertTrue(path.is_file())

    def test_failed_download_removes_only_owned_staging_directory(self):
        sentinel = self.base / "existing-user-data"
        sentinel.write_text("preserve")
        with mock.patch.object(d.subprocess, "run", return_value=mock.Mock(returncode=1)):
            with self.assertRaises(d.RuntimeDeployError):
                d.prepare_source(self.target)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.base.glob(".v13-source-*")))
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_symlink_source_is_refused_without_modifying_target(self):
        self.target.symlink_to(self.seed, target_is_directory=True)
        before = self.git(self.seed, "rev-parse", "HEAD")
        with self.assertRaises(d.RuntimeDeployError):
            d.prepare_source(self.target)
        self.assertEqual(self.git(self.seed, "rev-parse", "HEAD"), before)


if __name__ == "__main__":
    unittest.main()
