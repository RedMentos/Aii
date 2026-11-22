import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13 import runtime_deploy as d


class RuntimeActivationJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "phone"
        (self.home / "bin").mkdir(parents=True)
        self.launcher = self.home / "bin" / "v13"
        self.old_launcher = b"old verified launcher\n"
        self.new_launcher = b"new verified launcher\n"
        self.launcher.write_bytes(self.old_launcher)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.private.chmod(0o700)

    def prepare(self, *, old_marker=False, new_marker=True):
        marker_path = self.private / d.MARKER_NAME
        old_marker_bytes = None
        if old_marker:
            old_marker_bytes = json.dumps({
                "schema": "v13.runtime-deploy/1",
                "launcher_sha256": hashlib.sha256(self.old_launcher).hexdigest(),
                "commit": "a" * 40,
                "code": "/synthetic/old/code",
                "stage_manifest_sha256": "b" * 64,
            }, sort_keys=True).encode("utf-8")
            d._atomic_file(marker_path, old_marker_bytes, 0o600)
        backup_launcher = self.private / "launcher-backup-0123456789abcdef.sh"
        d._atomic_file(backup_launcher, self.old_launcher, 0o600)
        backup_marker = None
        if old_marker_bytes is not None:
            backup_marker = self.private / "marker-backup-0123456789abcdef.json"
            d._atomic_file(backup_marker, old_marker_bytes, 0o600)
        new_marker_bytes = None
        if new_marker:
            new_marker_bytes = json.dumps({
                "schema": "v13.runtime-deploy/1",
                "launcher_sha256": hashlib.sha256(self.new_launcher).hexdigest(),
                "commit": "c" * 40,
                "code": "/synthetic/new/code",
                "stage_manifest_sha256": "d" * 64,
            }, sort_keys=True).encode("utf-8")
        return old_marker_bytes, new_marker_bytes, backup_launcher, backup_marker

    def crash_transaction(self, point, *, old_marker=False, new_marker=True):
        old_marker_bytes, new_marker_bytes, backup_launcher, backup_marker = self.prepare(
            old_marker=old_marker, new_marker=new_marker)
        script = f"""
import os
from pathlib import Path
from v13 import runtime_deploy as d
home = Path({str(self.home)!r})
private = Path({str(self.private)!r})
launcher = home / "bin" / "v13"
marker = private / d.MARKER_NAME
journal = private / d.ACTIVATION_JOURNAL_NAME
point = {point!r}
real_atomic = d._atomic_file
real_remove = d._remove_private_file
def crash_atomic(dest, data, mode=0o600):
    result = real_atomic(dest, data, mode)
    dest = Path(dest)
    if point == "launcher" and dest == launcher:
        os._exit(71)
    if point == "marker" and dest == marker:
        os._exit(72)
    if point == "committed" and dest == journal and b'"phase": "COMMITTED"' in data:
        os._exit(73)
    return result
def crash_remove(path, private_path):
    result = real_remove(path, private_path)
    if point == "unlink" and Path(path) == marker:
        os._exit(74)
    return result
d._atomic_file = crash_atomic
d._remove_private_file = crash_remove
d._activation_transaction(
    home, private,
    old_launcher={self.old_launcher!r},
    old_marker={old_marker_bytes!r},
    new_launcher={self.new_launcher!r},
    new_marker={new_marker_bytes!r},
    backup_launcher=Path({str(backup_launcher)!r}),
    backup_marker=Path({str(backup_marker)!r}) if {backup_marker is not None!r} else None,
)
"""
        env = os.environ.copy()
        code_root = str(Path(d.__file__).resolve().parents[1])
        env["PYTHONPATH"] = code_root + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([sys.executable, "-c", script], env=env,
                              capture_output=True, timeout=15, check=False)
        return proc, old_marker_bytes, new_marker_bytes

    def test_process_exit_after_launcher_replace_restores_first_install_pair(self):
        proc, old_marker, new_marker = self.crash_transaction("launcher")
        self.assertEqual(proc.returncode, 71, proc.stderr.decode("utf-8", "replace"))
        self.assertNotEqual(self.launcher.read_bytes(), self.old_launcher)
        self.assertEqual(d._recover_activation(self.home, self.private), "ROLLED_BACK_INCOMPLETE")
        self.assertEqual(self.launcher.read_bytes(), self.old_launcher)
        self.assertFalse((self.private / d.MARKER_NAME).exists())
        self.assertFalse((self.private / d.ACTIVATION_JOURNAL_NAME).exists())

    def test_process_exit_after_marker_replace_restores_previous_deployment(self):
        proc, old_marker, new_marker = self.crash_transaction("marker", old_marker=True)
        self.assertEqual(proc.returncode, 72, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(d._recover_activation(self.home, self.private), "ROLLED_BACK_INCOMPLETE")
        self.assertEqual(self.launcher.read_bytes(), self.old_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), old_marker)
        self.assertFalse((self.private / d.ACTIVATION_JOURNAL_NAME).exists())

    def test_process_exit_after_marker_unlink_restores_rollback_pair(self):
        proc, old_marker, _ = self.crash_transaction(
            "unlink", old_marker=True, new_marker=False)
        self.assertEqual(proc.returncode, 74, proc.stderr.decode("utf-8", "replace"))
        self.assertFalse((self.private / d.MARKER_NAME).exists())
        self.assertEqual(d._recover_activation(self.home, self.private), "ROLLED_BACK_INCOMPLETE")
        self.assertEqual(self.launcher.read_bytes(), self.old_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), old_marker)

    def test_process_exit_after_durable_commit_keeps_new_pair(self):
        proc, _, new_marker = self.crash_transaction("committed")
        self.assertEqual(proc.returncode, 73, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(self.launcher.read_bytes(), self.new_launcher)
        self.assertEqual(d._recover_activation(self.home, self.private), "COMMITTED")
        self.assertEqual(self.launcher.read_bytes(), self.new_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), new_marker)
        self.assertFalse((self.private / d.ACTIVATION_JOURNAL_NAME).exists())

    def test_tampered_backup_fails_closed_without_overwriting_current_launcher(self):
        proc, _, _ = self.crash_transaction("launcher")
        self.assertEqual(proc.returncode, 71)
        backup = self.private / "launcher-backup-0123456789abcdef.sh"
        backup.write_bytes(b"tampered")
        current = self.launcher.read_bytes()
        with self.assertRaisesRegex(d.RuntimeDeployError, "backup hash mismatch"):
            d._recover_activation(self.home, self.private)
        self.assertEqual(self.launcher.read_bytes(), current)
        self.assertTrue((self.private / d.ACTIVATION_JOURNAL_NAME).is_file())

    def test_unknown_launcher_fails_closed_without_restoring_over_it(self):
        proc, _, _ = self.crash_transaction("launcher")
        self.assertEqual(proc.returncode, 71)
        self.launcher.write_bytes(b"external replacement")
        with self.assertRaisesRegex(d.RuntimeDeployError, "unknown launcher"):
            d._recover_activation(self.home, self.private)
        self.assertEqual(self.launcher.read_bytes(), b"external replacement")

    def test_journal_symlink_fails_closed_without_touching_launcher(self):
        proc, _, _ = self.crash_transaction("launcher")
        self.assertEqual(proc.returncode, 71)
        current_launcher = self.launcher.read_bytes()
        journal = self.private / d.ACTIVATION_JOURNAL_NAME
        outside = self.root / "outside-journal"
        outside.write_text("not an activation journal", encoding="utf-8")
        journal.unlink()
        journal.symlink_to(outside)
        with self.assertRaisesRegex(d.RuntimeDeployError, "journal is a symbolic link"):
            d._recover_activation(self.home, self.private)
        self.assertEqual(self.launcher.read_bytes(), current_launcher)
        self.assertTrue(journal.is_symlink())

    def test_backup_symlink_fails_closed_without_touching_launcher(self):
        proc, _, _ = self.crash_transaction("launcher")
        self.assertEqual(proc.returncode, 71)
        current_launcher = self.launcher.read_bytes()
        backup = self.private / "launcher-backup-0123456789abcdef.sh"
        outside = self.root / "outside-backup"
        outside.write_bytes(self.old_launcher)
        backup.unlink()
        backup.symlink_to(outside)
        with self.assertRaisesRegex(d.RuntimeDeployError, "Runtime transaction backup path invalid"):
            d._recover_activation(self.home, self.private)
        self.assertEqual(self.launcher.read_bytes(), current_launcher)
        self.assertTrue(backup.is_symlink())

    def test_unknown_marker_fails_closed_without_overwriting_current_pair(self):
        proc, _, _ = self.crash_transaction("marker", old_marker=True)
        self.assertEqual(proc.returncode, 72)
        current_launcher = self.launcher.read_bytes()
        marker = self.private / d.MARKER_NAME
        marker.write_bytes(b"unknown external marker")
        with self.assertRaisesRegex(d.RuntimeDeployError, "unknown marker"):
            d._recover_activation(self.home, self.private)
        self.assertEqual(self.launcher.read_bytes(), current_launcher)
        self.assertEqual(marker.read_bytes(), b"unknown external marker")
        self.assertTrue((self.private / d.ACTIVATION_JOURNAL_NAME).exists())

    def test_atomic_file_fsyncs_parent_directory_after_replace(self):
        dest = self.private / "fsync-check"
        with mock.patch.object(d, "_fsync_directory") as fsync_dir:
            d._atomic_file(dest, b"durable", 0o600)
        fsync_dir.assert_called_once_with(self.private)
        self.assertEqual(dest.read_bytes(), b"durable")


    def test_pending_journal_forces_deploy_even_when_pair_looks_current(self):
        source = self.root / "source"
        installed = self.root / "installed"
        source.mkdir()
        installed.mkdir()
        canon = installed / d.CANON
        canon.parent.mkdir(parents=True, exist_ok=True)
        canon.write_bytes(b"canon")
        ui = installed / d.UI_SOURCE
        ui.parent.mkdir(parents=True, exist_ok=True)
        ui.write_bytes(b"same pinned ui")
        source_ui = source / d.UI_SOURCE
        source_ui.parent.mkdir(parents=True, exist_ok=True)
        source_ui.write_bytes(b"same pinned ui")
        ui_sha = hashlib.sha256(ui.read_bytes()).hexdigest()
        manifest = {"files_sha256": {d.UI_SOURCE: ui_sha}, "replaced_files": []}
        manifest_path = installed / d.STAGE_MANIFEST
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_sha = "e" * 64
        commit = "a" * 40
        record = {
            "code": str(installed), "commit": commit,
            "build_profile": d.BUILD_PROFILE,
            "source_ui_sha256": ui_sha, "derived_ui_sha256": ui_sha,
            "ui_builder_sha256": ui_sha, "stage_manifest_sha256": manifest_sha,
            "launcher_sha256": hashlib.sha256(self.launcher.read_bytes()).hexdigest(),
        }
        with mock.patch.object(d, "_source", return_value=(source, source, commit)), \
             mock.patch.object(d, "_marker", return_value=record), \
             mock.patch.object(d, "_launcher", return_value=self.launcher), \
             mock.patch.object(d, "_verify_stage", return_value=manifest_sha), \
             mock.patch.object(d, "UI_SOURCE_SHA256", ui_sha), \
             mock.patch.object(d, "UI_DERIVED_SHA256", ui_sha), \
             mock.patch.object(d, "UI_BUILDER_SHA256", ui_sha):
            self.assertFalse(d.needs_deploy(source, home=self.home, private=self.private))
            (self.private / d.ACTIVATION_JOURNAL_NAME).write_text("pending", encoding="utf-8")
            self.assertTrue(d.needs_deploy(source, home=self.home, private=self.private))


    def test_recovery_without_journal_is_noop_even_when_runtime_home_is_missing(self):
        missing_home = self.root / "not-installed"
        private = self.root / "empty-private"
        private.mkdir(mode=0o700)
        with mock.patch.object(d, "_check_stopped") as stopped:
            self.assertEqual(
                d.recover_pending_activation(home=missing_home, private=private), "NONE")
        stopped.assert_not_called()
        self.assertFalse(missing_home.exists())

    def test_preexisting_journal_blocks_new_transaction(self):
        old_marker, new_marker, backup, backup_marker = self.prepare()
        journal = self.private / d.ACTIVATION_JOURNAL_NAME
        journal.write_text("untrusted")
        with self.assertRaisesRegex(d.RuntimeDeployError, "journal already exists"):
            d._activation_transaction(
                self.home, self.private,
                old_launcher=self.old_launcher, old_marker=old_marker,
                new_launcher=self.new_launcher, new_marker=new_marker,
                backup_launcher=backup, backup_marker=backup_marker)
        self.assertEqual(self.launcher.read_bytes(), self.old_launcher)




class RuntimeRollbackIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkout = self.root / "checkout"
        self.code = self.checkout / "v13" / "code"
        for rel in d.REQUIRED:
            path = self.code / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("fixture " + rel).encode("utf-8"))
        for rel in d.COPY_SUBTREES:
            (self.code / rel).mkdir(parents=True, exist_ok=True)
        actual_code = Path(d.__file__).resolve().parents[1]
        for rel in (d.UI_SOURCE, "v13/operator.py", d.UI_BUILDER):
            target = self.code / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((actual_code / rel).read_bytes())
        self.home = self.root / "phone-home"
        (self.home / "bin").mkdir(parents=True)
        (self.home / "models").mkdir()
        (self.home / "data" / "db").mkdir(parents=True)
        self.launcher = self.home / "bin" / "v13"
        self.old_launcher = b"#!/bin/sh\necho original\n"
        self.launcher.write_bytes(self.old_launcher)
        (self.home / "models" / "model.gguf").write_bytes(b"GGUF_DO_NOT_TOUCH")
        (self.home / "data" / "db" / "brain.sqlite3").write_bytes(b"SQLITE_DO_NOT_TOUCH")
        self.private = self.root / "private"
        self.builds = self.root / "builds"
        self.commit = "d" * 40
        self.source_patch = mock.patch.object(
            d, "_source", return_value=(self.checkout, self.code, self.commit))
        self.source_mock = self.source_patch.start()
        self.addCleanup(self.source_patch.stop)
        self.stop_patch = mock.patch.object(d, "_check_stopped")
        self.selftest_patch = mock.patch.object(d, "_selftest")
        self.stop_patch.start()
        self.selftest_patch.start()
        self.addCleanup(self.stop_patch.stop)
        self.addCleanup(self.selftest_patch.stop)

        def fake_stage(source, target, *, expected_commit=None):
            target.mkdir(mode=0o700)
            d._copy(source, target)
            d._apply_plain_ui_recovery(source, target)
            hashes = {
                p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in target.rglob("*") if p.is_file()
            }
            manifest = {"status": "SHADOW_REVIEW_ONLY", "files_sha256": hashes}
            (target / d.STAGE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
            return d._verify_stage(target)

        self.stage_patch = mock.patch.object(
            d, "_stage_integrated_runtime", side_effect=fake_stage)
        self.stage_patch.start()
        self.addCleanup(self.stage_patch.stop)

    def deploy(self, commit=None):
        if commit is not None:
            self.source_mock.return_value = (self.checkout, self.code, commit)
        return d.deploy(self.checkout, home=self.home, private=self.private,
                        builds=self.builds, ci_verified=True)

    def test_second_deploy_rollback_restores_previous_launcher_and_marker(self):
        first = self.deploy()
        first_launcher = self.launcher.read_bytes()
        first_marker = (self.private / d.MARKER_NAME).read_bytes()
        self.assertEqual(first["status"], "DEPLOYED")
        second = self.deploy("e" * 40)
        self.assertEqual(second["status"], "DEPLOYED")
        self.assertNotEqual(self.launcher.read_bytes(), first_launcher)
        current_marker = json.loads((self.private / d.MARKER_NAME).read_text())
        self.assertEqual(Path(current_marker["backup_launcher"]).read_bytes(), first_launcher)
        self.assertEqual(Path(current_marker["backup_marker"]).read_bytes(), first_marker)
        receipt = d.rollback(home=self.home, private=self.private, builds=self.builds)
        self.assertEqual(receipt["status"], "ROLLED_BACK")
        self.assertEqual(self.launcher.read_bytes(), first_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), first_marker)
        self.assertEqual((self.home / "models" / "model.gguf").read_bytes(), b"GGUF_DO_NOT_TOUCH")
        self.assertEqual((self.home / "data" / "db" / "brain.sqlite3").read_bytes(), b"SQLITE_DO_NOT_TOUCH")

    def test_first_install_rollback_restores_original_launcher_and_removes_marker(self):
        self.assertEqual(self.deploy()["status"], "DEPLOYED")
        receipt = d.rollback(home=self.home, private=self.private, builds=self.builds)
        self.assertEqual(receipt["status"], "ROLLED_BACK_LEGACY")
        self.assertEqual(self.launcher.read_bytes(), self.old_launcher)
        self.assertEqual(self.launcher.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.private / d.MARKER_NAME).exists())
        self.assertEqual((self.home / "models" / "model.gguf").read_bytes(), b"GGUF_DO_NOT_TOUCH")
        self.assertEqual((self.home / "data" / "db" / "brain.sqlite3").read_bytes(), b"SQLITE_DO_NOT_TOUCH")

    def test_tampered_previous_launcher_backup_fails_closed(self):
        self.deploy()
        self.deploy("e" * 40)
        current_launcher = self.launcher.read_bytes()
        current_marker = (self.private / d.MARKER_NAME).read_bytes()
        record = json.loads(current_marker)
        Path(record["backup_launcher"]).write_bytes(b"tampered launcher")
        with self.assertRaisesRegex(d.RuntimeDeployError, "launcher backup integrity"):
            d.rollback(home=self.home, private=self.private, builds=self.builds)
        self.assertEqual(self.launcher.read_bytes(), current_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), current_marker)

    def test_active_runtime_refuses_rollback_before_mutation(self):
        self.deploy()
        self.deploy("e" * 40)
        current_launcher = self.launcher.read_bytes()
        current_marker = (self.private / d.MARKER_NAME).read_bytes()
        with mock.patch.object(d, "_check_stopped",
                               side_effect=d.RuntimeDeployError("running")):
            with self.assertRaisesRegex(d.RuntimeDeployError, "running"):
                d.rollback(home=self.home, private=self.private, builds=self.builds)
        self.assertEqual(self.launcher.read_bytes(), current_launcher)
        self.assertEqual((self.private / d.MARKER_NAME).read_bytes(), current_marker)


if __name__ == "__main__":
    unittest.main()
