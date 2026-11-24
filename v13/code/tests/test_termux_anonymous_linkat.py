"""Regression for Redmi/Termux O_TMPFILE -> linkat ENOENT.

The synthetic first-call ENOENT models an unprivileged Android process.
No model, user SQLite, persisted chat, remote tokens or network is used.
"""
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from v13 import source_lifecycle_candidate as lifecycle


class _FirstEnoentLinkat:
    def __init__(self, real):
        self.real = real
        self.calls = []

    def __call__(self, srcfd, src, dirfd, dest, flags):
        self.calls.append((srcfd, src, dirfd, dest, flags))
        if len(self.calls) == 1:
            ctypes.set_errno(errno.ENOENT)
            return -1
        return self.real(srcfd, src, dirfd, dest, flags)


class TermuxAnonymousLinkatTests(unittest.TestCase):
    def test_enoent_uses_proc_self_fd_with_symlink_follow(self):
        fake = _FirstEnoentLinkat(lambda *a: 0)
        with mock.patch.object(lifecycle.ctypes, "CDLL",
                               return_value=types.SimpleNamespace(linkat=fake)):
            lifecycle._link_anonymous(41, 43, "a" * 64)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.calls[0][4], lifecycle.AT_EMPTY_PATH)
        self.assertEqual(fake.calls[1],
                         (getattr(os, "AT_FDCWD", -100), b"/proc/self/fd/41",
                          43, b"a" * 64, lifecycle.AT_SYMLINK_FOLLOW))

    def test_no_fallback_for_existing_final_name(self):
        calls = []
        def existing(*args):
            calls.append(args)
            ctypes.set_errno(errno.EEXIST)
            return -1
        with mock.patch.object(lifecycle.ctypes, "CDLL",
                               return_value=types.SimpleNamespace(linkat=existing)):
            with self.assertRaises(FileExistsError):
                lifecycle._link_anonymous(41, 43, "b" * 64)
        self.assertEqual(len(calls), 1)

    def test_fallback_failure_does_not_silently_claim_success(self):
        calls = []
        def denied(*args):
            calls.append(args)
            ctypes.set_errno(errno.ENOENT if len(calls) == 1 else errno.EACCES)
            return -1
        with mock.patch.object(lifecycle.ctypes, "CDLL",
                               return_value=types.SimpleNamespace(linkat=denied)):
            with self.assertRaises(PermissionError):
                lifecycle._link_anonymous(41, 43, "c" * 64)
        self.assertEqual(len(calls), 2)

    def test_real_tmpfile_pub_after_simulated_android_enoent(self):
        with tempfile.TemporaryDirectory(prefix="v13-termux-anon-") as home:
            folder = Path(home)
            contents = b"Android-source-roundtrip-no-visible-temp"
            key = hashlib.sha256(contents).hexdigest()
            original = ctypes.CDLL(None, use_errno=True).linkat
            fake = _FirstEnoentLinkat(original)
            try:
                with mock.patch.object(lifecycle.ctypes, "CDLL",
                                       return_value=types.SimpleNamespace(linkat=fake)):
                    self.assertEqual(lifecycle.verify_or_create_blob(folder / key,
                                                                    contents, key),
                                     "CREATED")
            except OSError as exc:
                if exc.errno in (errno.EOPNOTSUPP, errno.EINVAL, errno.ENOSYS):
                    self.skipTest("O_TMPFILE or linkat not supported by this test filesystem")
                raise
            self.assertEqual((folder / key).read_bytes(), contents)
            self.assertEqual({p.name for p in folder.iterdir()}, {key})
            self.assertEqual(fake.calls[0][4], lifecycle.AT_EMPTY_PATH)
            self.assertEqual(fake.calls[1][4], lifecycle.AT_SYMLINK_FOLLOW)
            self.assertEqual(lifecycle.verify_or_create_blob(folder / key,
                                                             contents, key),
                             "EXISTING")


if __name__ == "__main__":
    unittest.main()
