"""Termux EACCES after both linkat paths: safe named publish and cleanup.

Only synthetic data in temporary private directories. No model or real chat is
accessed. Real os.link is used for atomic no-clobber final publication.
"""
import errno
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from v13 import source_lifecycle_candidate as lifecycle


class NamedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v13-android-named-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = b"Redmi source publication under unprivileged Android"
        self.key = hashlib.sha256(self.data).hexdigest()
        self.path = self.root / self.key

    def test_actual_file_publish_after_android_permission_error(self):
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EACCES,
                                                           "proc/self/fd denied")):
            self.assertEqual(lifecycle.verify_or_create_blob(self.path, self.data, self.key),
                             "CREATED")
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertEqual({x.name for x in self.root.iterdir()}, {self.key})
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(lifecycle.verify_or_create_blob(self.path, self.data, self.key),
                         "EXISTING")

    def test_missing_proc_entry_is_recoverable_via_regular_hardlink(self):
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=FileNotFoundError(errno.ENOENT, "proc hidden")):
            self.assertEqual(lifecycle.verify_or_create_blob(self.path, self.data, self.key),
                             "CREATED")
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_repeated_existing_name_cannot_be_replaced(self):
        self.path.write_bytes(b"CORRUPTED EXISTING CONTENT")
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EPERM, "denied")):
            with self.assertRaises(ValueError):
                lifecycle.verify_or_create_blob(self.path, self.data, self.key)
        self.assertEqual(self.path.read_bytes(), b"CORRUPTED EXISTING CONTENT")
        self.assertFalse(list(self.root.glob(".v13-pending-*")))

    def test_both_regular_publication_methods_denied_leave_no_temporary_file(self):
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EACCES, "proc denied")):
            with mock.patch.object(lifecycle, "_hardlink_named_no_replace",
                                   side_effect=PermissionError(errno.EACCES,
                                                               "hardlink unavailable")):
                with mock.patch.object(lifecycle, "_rename_named_no_replace",
                                       side_effect=PermissionError(errno.EACCES,
                                                                   "rename unavailable")):
                    with self.assertRaises(PermissionError):
                        lifecycle.verify_or_create_blob(self.path, self.data, self.key)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_android_python_without_os_link_can_publish(self):
        # Termux/bionic's CPython 3.14 does not export os.link.
        present = hasattr(os, "link")
        original = getattr(os, "link", None)
        if present:
            delattr(os, "link")
        try:
            self.assertFalse(hasattr(os, "link"))
            with mock.patch.object(lifecycle, "_link_anonymous",
                                   side_effect=PermissionError(errno.EACCES,
                                                               "proc denied")):
                self.assertEqual(
                    lifecycle.verify_or_create_blob(self.path, self.data, self.key),
                    "CREATED")
            self.assertEqual(self.path.read_bytes(), self.data)
            self.assertEqual({x.name for x in self.root.iterdir()}, {self.key})
        finally:
            if present:
                setattr(os, "link", original)

    def test_named_hardlink_uses_ordinary_paths_without_special_flags(self):
        calls = []
        def pretend(src_dir_fd, src, dst_dir_fd, dst, flags):
            calls.append((src_dir_fd, src, dst_dir_fd, dst, flags))
            return 0
        import types
        with mock.patch.object(lifecycle.ctypes, "CDLL",
                               return_value=types.SimpleNamespace(linkat=pretend)):
            lifecycle._hardlink_named_no_replace(21, "pending", "final")
        self.assertEqual(calls, [(21, b"pending", 21, b"final", 0)])

    def test_android_hardlink_denied_renameat2_still_publishes(self):
        # Mirrors Termux's previously working integrated-stage renameat2.
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EACCES, "anon denied")):
            with mock.patch.object(lifecycle, "_hardlink_named_no_replace",
                                   side_effect=PermissionError(errno.EPERM, "hardlink denied")):
                self.assertEqual(lifecycle.verify_or_create_blob(self.path, self.data,
                                                                  self.key), "CREATED")
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertFalse(list(self.root.glob(".v13-pending-*")))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_renameat2_refuses_existing_final_filename(self):
        stage = self.root / "stage"
        stage.write_bytes(self.data)
        self.path.write_bytes(b"PROTECTED EXISTING")
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaises(FileExistsError):
                lifecycle._rename_named_no_replace(fd, "stage", self.key)
        finally:
            os.close(fd)
        self.assertEqual(self.path.read_bytes(), b"PROTECTED EXISTING")
        self.assertEqual(stage.read_bytes(), self.data)

    def test_renameat2_denied_fails_closed_without_temp_copy(self):
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EACCES, "anon denied")):
            with mock.patch.object(lifecycle, "_hardlink_named_no_replace",
                                   side_effect=PermissionError(errno.EACCES, "hardlink denied")):
                with mock.patch.object(lifecycle, "_rename_named_no_replace",
                                       side_effect=PermissionError(errno.EACCES, "rename denied")):
                    with self.assertRaises(PermissionError):
                        lifecycle.verify_or_create_blob(self.path, self.data, self.key)
        self.assertFalse(self.path.exists())
        self.assertFalse(list(self.root.glob(".v13-pending-*")))

    def test_crash_recovery_reaps_only_digest_bound_pending(self):
        pending_a = ".v13-pending-" + self.key + "-" + "a" * 24
        other_hash = "b" * 64
        pending_b = ".v13-pending-" + other_hash + "-" + "b" * 24
        unrelated = ".v13-pending-invalid"
        for name in (pending_a, pending_b, unrelated):
            (self.root / name).write_bytes(b"SYNTHETIC-PRIVATE")
        self.assertEqual(lifecycle.cleanup_pending(self.root, self.key), 1)
        self.assertFalse((self.root / pending_a).exists())
        self.assertTrue((self.root / pending_b).exists())
        self.assertTrue((self.root / unrelated).exists())
        self.assertEqual(lifecycle.cleanup_pending(self.root), 1)
        self.assertTrue((self.root / unrelated).exists())

    def test_symlink_stage_is_never_followed_or_deleted(self):
        legitimate = self.root / "safe-file"
        legitimate.write_text("keep")
        bad = self.root / (".v13-pending-" + self.key + "-" + "c" * 24)
        bad.symlink_to(legitimate)
        with self.assertRaises(ValueError):
            lifecycle.cleanup_pending(self.root)
        self.assertEqual(legitimate.read_text(), "keep")
        self.assertTrue(bad.is_symlink())


if __name__ == "__main__":
    unittest.main()
