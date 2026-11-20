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

    def test_link_failure_reaps_temporary_name_and_does_not_publish(self):
        original = os.link
        def blocked(src, dst, **kwargs):
            if src.startswith(".v13-pending-"):
                raise PermissionError(errno.EACCES, "hardlink unavailable")
            return original(src, dst, **kwargs)
        with mock.patch.object(lifecycle, "_link_anonymous",
                               side_effect=PermissionError(errno.EACCES, "proc denied")):
            with mock.patch.object(lifecycle.os, "link", side_effect=blocked):
                with self.assertRaises(PermissionError):
                    lifecycle.verify_or_create_blob(self.path, self.data, self.key)
        self.assertEqual(list(self.root.iterdir()), [])

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
