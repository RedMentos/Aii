"""Run598: real SQLite backup publication is atomic, no-clobber and durable."""
import errno
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import backup as B


class BackupNoClobber(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.store.source("SYNTHETIC SOURCE", "RUN598_TEST")
        self.dest = self.home / "backups" / "run598.tar.gz"

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def pending(self):
        return list(self.dest.parent.glob("." + self.dest.name + ".pending-*"))

    def test_complete_tar_and_source_closure_with_no_partial(self):
        out = B.backup(self.r.store, self.dest)
        self.assertEqual(out, self.dest)
        self.assertTrue(out.is_file())
        with tarfile.open(out, "r:gz") as tf:
            self.assertIn("backup_manifest.json", tf.getnames())
            self.assertIn("data/db/brain.sqlite3", tf.getnames())
        with tempfile.TemporaryDirectory(dir=self.home / "tmp") as tmp:
            manifest = B.unpack_verified(out, Path(tmp), 1 << 29)
            self.assertEqual(manifest["format"], 1)
        self.assertEqual(self.pending(), [])
        self.assertFalse(self.dest.with_suffix(".partial").exists())

    def test_race_creating_target_immediately_before_publish_cannot_overwrite(self):
        real_link = os.link
        def concurrent_create(src, dst, *args, **kwargs):
            Path(dst).write_bytes(b"OTHER OWNER")
            return real_link(src, dst, *args, **kwargs)
        with patch.object(B.os, "link", side_effect=concurrent_create):
            with self.assertRaisesRegex(ValueError, "existiert bereits"):
                B.backup(self.r.store, self.dest)
        self.assertEqual(self.dest.read_bytes(), b"OTHER OWNER")
        self.assertEqual(self.pending(), [])

    def test_existing_file_and_broken_symlink_both_refuse_clobber(self):
        self.dest.write_bytes(b"PREEXISTING")
        with self.assertRaisesRegex(ValueError, "existiert bereits"):
            B.backup(self.r.store, self.dest)
        self.assertEqual(self.dest.read_bytes(), b"PREEXISTING")
        self.dest.unlink()
        self.dest.symlink_to(self.home / "nonexistent-target")
        with self.assertRaisesRegex(ValueError, "existiert bereits"):
            B.backup(self.r.store, self.dest)
        self.assertTrue(self.dest.is_symlink())
        self.assertEqual(self.pending(), [])

    def test_archive_failure_leaves_no_final_or_temp(self):
        with patch.object(B.tarfile.TarFile, "add",
                          side_effect=RuntimeError("simulated archive failure")):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                B.backup(self.r.store, self.dest)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.pending(), [])

    def test_unsupported_hardlinks_fail_closed_without_partial_final(self):
        with patch.object(B.os, "link",
                          side_effect=OSError(errno.EOPNOTSUPP, "unsupported filesystem")):
            with self.assertRaises(OSError):
                B.backup(self.r.store, self.dest)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.pending(), [])

    def test_directory_fsync_failure_does_not_claim_success_or_leave_temp(self):
        real_fsync = os.fsync
        def fail_dir(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError(errno.EIO, "directory sync failed")
            return real_fsync(fd)
        with patch.object(B.os, "fsync", side_effect=fail_dir):
            with self.assertRaises(OSError):
                B.backup(self.r.store, self.dest)
        self.assertTrue(self.dest.is_file())  # complete archive, durability not claimed
        self.assertEqual(self.pending(), [])
        with tarfile.open(self.dest, "r:gz") as tf:
            self.assertIn("backup_manifest.json", tf.getnames())


if __name__ == "__main__":
    unittest.main()
