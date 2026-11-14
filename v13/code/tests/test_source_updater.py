"""Git-backed updater tests: real local Git fetch/delta/rollback; no network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from v13 import source_updater as u


def git(root, *args):
    proc = subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.stdout.strip()


class SourceUpdateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.tmp = Path(self.dir.name)
        self.remote = self.tmp / "remote.git"
        self.base = self.tmp / "publisher"
        self.phone = self.tmp / "phone"
        self.state = self.tmp / "state"
        self.state.mkdir(mode=0o700)
        self.patch_origin = mock.patch.object(u, "EXPECTED_ORIGINS", (str(self.remote),))
        self.patch_history = mock.patch.object(u, "HISTORY", self.state / "history.json")
        self.patch_lock = mock.patch.object(u, "LOCK", self.state / "lock")
        self.patch_running = mock.patch.object(u, "_runtime_active", return_value=False)
        for p in (self.patch_origin, self.patch_history, self.patch_lock, self.patch_running):
            p.start()
            self.addCleanup(p.stop)
        subprocess.run(["git", "init", "--bare", str(self.remote)], capture_output=True, check=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.base)], capture_output=True, check=True)
        git(self.base, "config", "user.name", "Device Tests")
        git(self.base, "config", "user.email", "device-tests@example.invalid")
        git(self.base, "checkout", "-b", "v13-test")
        (self.base / "v13/code/v13").mkdir(parents=True)
        (self.base / "v13/code/v13/__init__.py").write_text("ANSWER = 1\n")
        git(self.base, "add", ".")
        git(self.base, "commit", "-m", "initial")
        git(self.base, "push", "-u", "origin", "v13-test")
        subprocess.run(["git", "clone", "--single-branch", "--branch", "v13-test",
                        str(self.remote), str(self.phone)], capture_output=True, check=True)
        self.initial = git(self.phone, "rev-parse", "HEAD")

    def publish(self, content="ANSWER = 2\n"):
        (self.base / "v13/code/v13/__init__.py").write_text(content)
        git(self.base, "add", ".")
        git(self.base, "commit", "-m", "new source")
        git(self.base, "push", "origin", "v13-test")
        return git(self.base, "rev-parse", "HEAD")

    def publish_phone_package(self):
        source = Path(u.__file__).parent
        for required in u.REQUIRED_PHONE_MODULES:
            file = self.base / required
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes((source / Path(required).name).read_bytes())
        excluded = self.base / "v13/code/specs/outside-phone-package.json"
        excluded.parent.mkdir(parents=True, exist_ok=True)
        excluded.write_text("{}\n")
        self.publish()
        git(self.phone, "pull", "--ff-only", "origin", "v13-test")

    def import_phone_modules(self):
        return subprocess.run(
            [sys.executable, "-c",
             "from v13 import pipeline_agent, runtime_deploy, diagnostic_push, "
             "mobile_dashboard, owner_read_bridge; from v13.common import atomic_write"],
            cwd=self.tmp, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(self.phone / "v13/code"),
                 "HOME": str(self.tmp / "isolated-home"), "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=15)

    def test_old_sparse_checkout_restores_new_phone_bridge_modules(self):
        self.publish_phone_package()
        git(self.phone,"sparse-checkout","init","--no-cone")
        git(self.phone,"sparse-checkout","set","--no-cone",
            "v13/code/v13/__init__.py")
        self.assertFalse((self.phone / u.PHONE_PACKAGE / "remote_chat.py").exists())
        status=u.ensure_sparse_phone_modules(self.phone)
        self.assertEqual(status["status"],"MIGRATED")
        self.assertTrue(all((self.phone/p).is_file() for p in u.REQUIRED_PHONE_MODULES))
        imports = self.import_phone_modules()
        self.assertEqual(imports.returncode, 0, imports.stderr)
        self.assertFalse((self.phone / "v13/code/specs/outside-phone-package.json").exists())
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"],"ALREADY_PRESENT")

    def test_old_six_modules_do_not_hide_new_dependencies_or_future_modules(self):
        self.publish_phone_package()
        missing = {"runtime_deploy.py", "diagnostic_push.py", "common.py"}
        old_modules = [p for p in u.REQUIRED_PHONE_MODULES if Path(p).name not in missing]
        git(self.phone, "sparse-checkout", "set", "--no-cone", *old_modules)
        # All six files checked by the former migration already exist. Its
        # early return left the real pipeline and monitor imports broken.
        for name in ("remote_chat.py", "phone_monitor.py", "chat_service.py",
                     "pipeline_agent.py", "lifecycle.py", "mobile_dashboard.html"):
            self.assertTrue((self.phone / u.PHONE_PACKAGE / name).is_file())
        self.assertNotEqual(self.import_phone_modules().returncode, 0)
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"], "MIGRATED")
        imports = self.import_phone_modules()
        self.assertEqual(imports.returncode, 0, imports.stderr)
        # A later release introduces a dependency absent from today's list.
        # The migrated directory pattern must receive it on normal Git FF.
        future = "v13/code/v13/future_phone_dependency/__init__.py"
        (self.base / future).parent.mkdir()
        (self.base / future).write_text("VALUE = 42\n")
        expected = self.publish()
        git(self.phone, "pull", "--ff-only", "origin", "v13-test")
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), expected)
        self.assertEqual((self.phone / future).read_text(), "VALUE = 42\n")
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"], "ALREADY_PRESENT")
        self.assertFalse((self.phone / "v13/code/specs/outside-phone-package.json").exists())
        self.assertFalse(git(self.phone, "status", "--porcelain", "--untracked-files=no"))

    def test_all_present_exact_file_patterns_still_migrate_for_future_dependencies(self):
        self.publish_phone_package()
        git(self.phone, "sparse-checkout", "set", "--no-cone", *u.REQUIRED_PHONE_MODULES)
        self.assertTrue(all((self.phone / p).is_file() for p in u.REQUIRED_PHONE_MODULES))
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"], "MIGRATED")
        self.assertIn("/" + u.PHONE_PACKAGE, git(self.phone, "sparse-checkout", "list").splitlines())
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"], "ALREADY_PRESENT")

    def test_full_phone_package_is_unchanged_without_enabling_sparse_checkout(self):
        self.publish_phone_package()
        self.assertEqual(u.ensure_sparse_phone_modules(self.phone)["status"], "ALREADY_PRESENT")
        self.assertFalse((self.phone / ".git/info/sparse-checkout").exists())

    def test_committed_symlink_in_phone_package_is_rejected(self):
        self.publish_phone_package()
        (self.base / u.PHONE_PACKAGE / "unsafe.py").symlink_to("../../outside")
        self.publish()
        git(self.phone, "pull", "--ff-only", "origin", "v13-test")
        git(self.phone, "sparse-checkout", "set", "--no-cone", "v13/code/v13/__init__.py")
        with self.assertRaises(u.UpdateDenied):
            u.ensure_sparse_phone_modules(self.phone)
        self.assertFalse((self.phone / u.PHONE_PACKAGE / "unsafe.py").is_symlink())

    def test_untracked_symlink_in_old_sparse_phone_package_is_rejected(self):
        self.publish_phone_package()
        git(self.phone, "sparse-checkout", "set", "--no-cone", "v13/code/v13/__init__.py")
        outside = self.tmp / "outside.py"
        outside.write_text("never overwritten\n")
        (self.phone / u.PHONE_PACKAGE / "common.py").symlink_to(outside)
        with self.assertRaises(u.UpdateDenied):
            u.ensure_sparse_phone_modules(self.phone)
        self.assertEqual(outside.read_text(), "never overwritten\n")

    def test_uncommitted_phone_module_never_materialized(self):
        with self.assertRaises(u.UpdateDenied):
            u.ensure_sparse_phone_modules(self.phone)

    def test_git_delta_fast_forward_and_rollback(self):
        next_commit = self.publish()
        report = u.status(self.phone)
        self.assertEqual(report["status"], "UPDATE_AVAILABLE")
        self.assertEqual(report["available"], next_commit)
        self.assertEqual(u.apply(self.phone)["status"], "UPDATED")
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), next_commit)
        self.assertEqual(u.status(self.phone)["status"], "UP_TO_DATE")
        self.assertEqual(u.rollback(self.phone)["status"], "ROLLED_BACK")
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), self.initial)

    def test_dirty_files_not_overwritten(self):
        self.publish()
        (self.phone / "v13/code/v13/__init__.py").write_text("PERSONAL = True\n")
        with self.assertRaises(u.UpdateDenied):
            u.apply(self.phone)
        self.assertEqual((self.phone / "v13/code/v13/__init__.py").read_text(),
                         "PERSONAL = True\n")

    def test_running_v13_blocks_update(self):
        self.publish()
        with mock.patch.object(u, "_runtime_active", return_value=True):
            with self.assertRaises(u.UpdateDenied):
                u.apply(self.phone)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), self.initial)

    def test_bad_syntax_auto_reverts(self):
        self.publish("def invalid(:\n")
        with self.assertRaises(u.UpdateDenied):
            u.apply(self.phone)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), self.initial)
        self.assertEqual((self.phone / "v13/code/v13/__init__.py").read_text(), "ANSWER = 1\n")

    def test_dashboard_source_updates_independent_of_v13_runtime(self):
        # The control-panel source has its own checkout and can be changed
        # without touching the model data or V13's running Python modules.
        self.publish_phone_package()
        self.publish("ANSWER = 3\n")
        with mock.patch.object(u, "_runtime_active", return_value=True):
            result = u.apply_dashboard(self.phone)
        self.assertEqual(result["status"], "UPDATED")
        self.assertTrue(result["restart_required"])
        self.assertTrue((self.phone / "v13/code/v13/mobile_dashboard.html").is_file())

    def test_dashboard_up_to_date_restores_missing_sparse_dependencies(self):
        self.publish_phone_package()
        git(self.phone, "sparse-checkout", "set", "--no-cone",
            *[p for p in u.REQUIRED_PHONE_MODULES
              if Path(p).name not in {"common.py", "runtime_deploy.py", "diagnostic_push.py"}])
        before = git(self.phone, "rev-parse", "HEAD")
        self.assertNotEqual(self.import_phone_modules().returncode, 0)
        result = u.apply_dashboard(self.phone, expected_tip=before)
        self.assertEqual(result["status"], "UP_TO_DATE")
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), before)
        imports = self.import_phone_modules()
        self.assertEqual(imports.returncode, 0, imports.stderr)

    def test_dashboard_fast_forward_materializes_complete_sparse_package(self):
        self.publish_phone_package()
        git(self.phone, "sparse-checkout", "set", "--no-cone",
            "v13/code/v13/__init__.py", "v13/code/v13/mobile_dashboard.html")
        expected = self.publish("ANSWER = 3\n")
        result = u.apply_dashboard(self.phone, expected_tip=expected)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["current"], expected)
        imports = self.import_phone_modules()
        self.assertEqual(imports.returncode, 0, imports.stderr)
        self.assertFalse((self.phone / "v13/code/specs/outside-phone-package.json").exists())

    def test_dashboard_migration_failure_after_fast_forward_restores_old_commit(self):
        self.publish_phone_package()
        git(self.phone, "sparse-checkout", "set", "--no-cone",
            "v13/code/v13/__init__.py", "v13/code/v13/mobile_dashboard.html")
        before = git(self.phone, "rev-parse", "HEAD")
        (self.base / u.PHONE_PACKAGE / "unsafe.py").symlink_to("../../outside")
        expected = self.publish()
        with self.assertRaises(u.UpdateDenied):
            u.apply_dashboard(self.phone, expected_tip=expected)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), before)
        self.assertEqual((self.phone / u.PHONE_PACKAGE / "__init__.py").read_text(), "ANSWER = 2\n")
        self.assertFalse((self.phone / u.PHONE_PACKAGE / "unsafe.py").is_symlink())
        self.assertFalse(git(self.phone, "status", "--porcelain", "--untracked-files=no"))

    def test_dashboard_source_reverts_when_template_missing(self):
        self.publish()
        with self.assertRaises(u.UpdateDenied):
            u.apply_dashboard(self.phone)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), self.initial)

    def test_bad_origin_not_accepted(self):
        with mock.patch.object(u, "EXPECTED_ORIGINS", ("https://github.com/no/other",)):
            with self.assertRaises(u.UpdateDenied):
                u.status(self.phone)

    def test_branch_rewrite_not_accepted(self):
        # The phone first runs commit B; remote is force-rewritten from A to C.
        # A -> C alone is a valid fast-forward from A and must not be rejected.
        self.publish()
        self.assertEqual(u.apply(self.phone)["status"], "UPDATED")
        current = git(self.phone, "rev-parse", "HEAD")
        git(self.base, "reset", "--hard", self.initial)
        (self.base / "v13/code/v13/__init__.py").write_text("ANSWER = 999\n")
        git(self.base, "add", ".")
        git(self.base, "commit", "-m", "divergent")
        git(self.base, "push", "--force", "origin", "v13-test")
        with self.assertRaises(u.UpdateDenied):
            u.apply(self.phone)
        self.assertEqual(git(self.phone, "rev-parse", "HEAD"), current)


if __name__ == "__main__":
    unittest.main()
