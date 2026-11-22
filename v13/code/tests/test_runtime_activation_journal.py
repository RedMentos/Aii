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


if __name__ == "__main__":
    unittest.main()
