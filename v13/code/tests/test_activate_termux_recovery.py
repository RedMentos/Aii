"""Reversible activation with real tiny SQLite backups, no native inference."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/activate_termux_recovery.py"
SPEC = importlib.util.spec_from_file_location("termux_recovery_activation", SCRIPT)
activation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(activation)


class ActivationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.stage = self.tmp / "candidate code"
        (self.stage / "v13").mkdir(parents=True)
        (self.stage / "v13/__init__.py").write_text("")
        (self.stage / "v13/__main__.py").write_text(
            "import json, sys\nprint(json.dumps({'source': __file__, 'argv': sys.argv[1:]}))\n")
        self.manifest()
        self.home = self.tmp / "runtime home"
        for name in ("bin", "config", "data/db", "models"):
            (self.home / name).mkdir(parents=True)
        self.launcher = self.home / "bin/v13"
        self.original_launcher = b"#!/bin/sh\nprintf 'original launcher\\n'\n"
        self.launcher.write_bytes(self.original_launcher)
        self.launcher.chmod(0o700)
        self.settings = self.home / "config/settings.json"
        self.settings.write_text('{"learning_mode":"RECORD_ONLY"}\n')
        self.model = self.home / "models/synthetic-model.bin"
        self.model.write_bytes(b"tiny fixture, never an inference model")
        self.database = self.home / "data/db/brain.sqlite3"
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE messages (text TEXT)")
            connection.execute("INSERT INTO messages VALUES ('original synthetic message')")

    def manifest(self):
        files = {path.relative_to(self.stage).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in self.stage.rglob("*") if path.is_file() and path.name != "INTEGRATION_STAGE.json"}
        (self.stage / "INTEGRATION_STAGE.json").write_text(json.dumps(
            {"status": "SHADOW_REVIEW_ONLY", "files_sha256": files}, sort_keys=True))

    def snapshot(self):
        return {path.relative_to(self.home).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.home.rglob("*") if path.is_file()}

    def rows(self, database=None):
        with sqlite3.connect(database or self.database) as connection:
            return connection.execute("SELECT text FROM messages ORDER BY rowid").fetchall()

    def test_default_validation_performs_no_writes(self):
        before = self.snapshot()
        result = activation.operate(self.stage, self.home)
        self.assertEqual(result["status"], "CHECKED_NO_ACTION")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / "recovery-state").exists())

    def test_altered_manifest_bytes_refuse_before_backup_or_launcher_write(self):
        before = self.snapshot()
        (self.stage / "v13/__main__.py").write_text("raise RuntimeError('changed stage')\n")
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            activation.operate(self.stage, self.home, action="activate")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / "recovery-state").exists())

    def test_invalid_python_refuses_even_with_matching_manifest(self):
        (self.stage / "v13/bad.py").write_text("def broken(:\n")
        self.manifest()
        with self.assertRaises(SyntaxError):
            activation.operate(self.stage, self.home, action="activate")
        self.assertFalse((self.home / "recovery-state").exists())

    def test_symlinked_stage_file_refuses(self):
        (self.stage / "v13/linked.py").symlink_to(self.stage / "v13/__init__.py")
        self.manifest()
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            activation.operate(self.stage, self.home, action="activate")
        self.assertFalse((self.home / "recovery-state").exists())

    def test_activation_backs_up_privately_and_launcher_selects_exact_stage(self):
        before = self.snapshot()
        receipt = activation.operate(self.stage, self.home, action="activate")
        self.assertEqual(receipt["status"], "ACTIVE")
        self.assertFalse(receipt["canonical_promotion"])
        self.assertEqual(Path(receipt["prior_launcher_path"]).read_bytes(), self.original_launcher)
        self.assertEqual(Path(receipt["settings_backup"]).read_bytes(), self.settings.read_bytes())
        self.assertEqual(self.rows(receipt["database_backup"]), self.rows())
        for name, checksum in before.items():
            if name != "bin/v13":
                self.assertEqual(hashlib.sha256((self.home / name).read_bytes()).hexdigest(), checksum, name)
        for path in (self.home / "recovery-state").rglob("*"):
            self.assertEqual(path.stat().st_mode & 0o077, 0, str(path))
        self.assertEqual(self.launcher.read_text().splitlines()[0],
                         "#!" + str(Path(shutil.which("bash")).resolve()))
        result = subprocess.run([str(self.launcher), "inspect"],
                                cwd=self.tmp, capture_output=True, text=True, check=True,
                                env=dict(os.environ, PYTHONPATH="/invalid/untrusted-source"))
        output = json.loads(result.stdout)
        self.assertEqual(output["source"], str(self.stage / "v13/__main__.py"))
        self.assertEqual(output["argv"], ["--home", str(self.home), "inspect"])
        self.assertFalse((self.stage / "v13/__pycache__").exists())

    def test_same_activation_is_idempotent(self):
        first = activation.operate(self.stage, self.home, action="activate")
        before = self.snapshot()
        second = activation.operate(self.stage, self.home, action="activate")
        self.assertEqual(second["status"], "ALREADY_ACTIVE")
        self.assertEqual(second["prior_launcher_path"], first["prior_launcher_path"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(list((self.home / "recovery-state").glob("activation-*"))), 1)

    def test_rollback_restores_launcher_and_preserves_new_messages_and_settings(self):
        receipt = activation.operate(self.stage, self.home, action="activate")
        with sqlite3.connect(self.database) as connection:
            connection.execute("INSERT INTO messages VALUES ('new synthetic message')")
        self.settings.write_text('{"learning_mode":"RECORD_ONLY","new_setting":true}\n')
        settings = self.settings.read_bytes()
        result = activation.operate(self.stage, self.home, action="rollback")
        self.assertEqual(result["status"], "ROLLED_BACK")
        self.assertEqual(self.launcher.read_bytes(), self.original_launcher)
        self.assertEqual(self.rows(), [("original synthetic message",), ("new synthetic message",)])
        self.assertEqual(self.rows(receipt["database_backup"]), [("original synthetic message",)])
        self.assertEqual(self.settings.read_bytes(), settings)
        self.assertEqual(activation.operate(self.stage, self.home, action="rollback")["status"], "ALREADY_ROLLED_BACK")

    def test_foreign_launcher_edit_refuses_rollback(self):
        activation.operate(self.stage, self.home, action="activate")
        self.launcher.write_bytes(b"#!/bin/sh\nprintf 'foreign launcher\\n'\n")
        edited = self.launcher.read_bytes()
        with self.assertRaisesRegex(ValueError, "rollback lease refused"):
            activation.operate(self.stage, self.home, action="rollback")
        self.assertEqual(self.launcher.read_bytes(), edited)

    def test_running_owned_v13_is_untouched_and_refuses_before_writes(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)", "v13"])
        try:
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "V13 is running"):
                activation.operate(self.stage, self.home, action="activate")
            self.assertIsNone(process.poll())
            self.assertEqual(self.snapshot(), before)
            self.assertFalse((self.home / "recovery-state").exists())
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_missing_or_symlinked_runtime_is_never_created_or_replaced(self):
        self.launcher.unlink()
        self.launcher.symlink_to(self.model)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            activation.operate(self.stage, self.home, action="activate")
        self.assertTrue(self.launcher.is_symlink())
        self.assertFalse((self.home / "recovery-state").exists())

    def test_broken_candidate_does_not_prevent_launcher_only_rollback(self):
        activation.operate(self.stage, self.home, action="activate")
        (self.stage / "v13/__main__.py").write_text("invalid Python (\n")
        activation.operate(self.stage, self.home, action="rollback")
        self.assertEqual(self.launcher.read_bytes(), self.original_launcher)

    def test_platform_parent_alias_allows_activation_and_rollback(self):
        # Models Android's /data/data -> /data/user/0 ancestor alias. The owned
        # runtime/stage leaves and everything inside them remain real paths.
        alias = self.tmp.parent / (self.tmp.name + "-platform-alias")
        alias.symlink_to(self.tmp, target_is_directory=True)
        self.addCleanup(alias.unlink)
        aliased_home = alias / self.home.name
        aliased_stage = alias / self.stage.name
        receipt = activation.operate(aliased_stage, aliased_home, action="activate")
        self.assertEqual(receipt["home"], str(self.home))
        self.assertEqual(receipt["code_dir"], str(self.stage))
        activation.operate(aliased_stage, aliased_home, action="rollback")
        self.assertEqual(self.launcher.read_bytes(), self.original_launcher)

    def test_owned_root_leaf_symlink_and_internal_directory_symlink_refuse(self):
        alias = self.tmp / "runtime-leaf-alias"
        alias.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            activation.operate(self.stage, alias, action="activate")
        original_bin = self.home / "bin"
        moved_bin = self.home / "moved-bin"
        original_bin.rename(moved_bin)
        original_bin.symlink_to(moved_bin, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            activation.operate(self.stage, self.home, action="activate")
        self.assertFalse((self.home / "recovery-state").exists())

    def test_prepared_before_swap_can_roll_back_then_activate_again(self):
        receipt = activation.operate(self.stage, self.home, action="activate")
        # Simulate interruption after PREPARED receipt, before launcher swap.
        self.launcher.write_bytes(self.original_launcher)
        active = self.home / "recovery-state/ACTIVE.json"
        receipt["status"] = "PREPARED"
        active.write_text(json.dumps(receipt))
        active.chmod(0o600)
        rolled_back = activation.operate(self.stage, self.home, action="rollback")
        self.assertEqual(rolled_back["status"], "ALREADY_ROLLED_BACK")
        self.assertEqual(json.loads(active.read_text())["status"], "ROLLED_BACK")
        self.assertEqual(activation.operate(self.stage, self.home, action="activate")["status"], "ACTIVE")

    def test_missing_bash_refuses_before_recovery_writes(self):
        before = self.snapshot()
        with mock.patch.object(activation.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "bash interpreter is missing"):
                activation.operate(self.stage, self.home, action="activate")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / "recovery-state").exists())

    def test_invalid_bash_shebang_path_refuses_before_recovery_writes(self):
        invalid = self.tmp / "bash\ninvalid"
        invalid.write_text("#!/bin/sh\nexit 0\n")
        invalid.chmod(0o700)
        before = self.snapshot()
        with mock.patch.object(activation.shutil, "which", return_value=str(invalid)):
            with self.assertRaisesRegex(ValueError, "invalid bash interpreter"):
                activation.operate(self.stage, self.home, action="activate")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / "recovery-state").exists())


if __name__ == "__main__":
    unittest.main()
