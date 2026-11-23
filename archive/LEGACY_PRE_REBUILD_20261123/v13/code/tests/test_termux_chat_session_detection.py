"""V13 Termux install: default interactive mode must not be missed.

The tested classifier is extracted from the real installer, without executing
any installation or signaling a process.
"""
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


def _classifier():
    install = (Path(__file__).resolve().parents[1]
               / "scripts/termux_one_command.sh").read_text()
    begin = "# V13_SESSION_CLASSIFIER_BEGIN"
    end = "# V13_SESSION_CLASSIFIER_END"
    assert install.count(begin) == 1 and install.count(end) == 1
    source = install.split(begin, 1)[1].split(end, 1)[0]
    namespace = {"os": os, "Path": Path}
    exec(compile(source, "<V13 verified installer classifier>", "exec"), namespace)
    return namespace["v13_process_mode"]


class DefaultChatSessionTests(unittest.TestCase):
    def setUp(self):
        self.f = _classifier()
        self.launcher = "/data/data/com.termux/files/home/v13/bin/v13"
        self.home = "/data/data/com.termux/files/home/v13"

    def classify(self, argv):
        return self.f(argv, self.launcher, self.home)

    def test_default_cli_is_an_active_chat(self):
        self.assertEqual(self.classify(
            ["python", "-P", "-m", "v13", "--home", self.home]), "CHAT")

    def test_explicit_chat_is_an_active_chat(self):
        self.assertEqual(self.classify(
            ["python", "-m", "v13", "--home", self.home, "chat"]), "CHAT")

    def test_default_home_implicitly_is_chat(self):
        self.assertEqual(self.classify(["python", "-m", "v13"]), "CHAT")

    def test_legacy_bootstrap_default_is_chat(self):
        self.assertEqual(self.classify(
            ["python", "-S", "-c", "bootstrap", self.launcher,
             "/data/data/com.termux/files/home/.v13-runtime-builds/x/code",
             "--home", self.home]), "CHAT")

    def test_short_lived_diagnostic_is_not_killed_as_chat(self):
        for command in ("doctor", "probe", "download", "selftest", "ask",
                        "source-answer", "restore", "--help"):
            self.assertEqual(self.classify(
                ["python", "-m", "v13", "--home", self.home, command]), "OTHER")

    def test_different_home_is_not_killed_as_chat(self):
        self.assertEqual(self.classify(
            ["python", "-m", "v13", "--home", "/tmp/other/v13"]), "OTHER")

    def test_unrelated_python_or_v13_service_is_not_chat(self):
        self.assertIsNone(self.classify(["python", "-m", "v13.chat_service", "serve"]))
        self.assertIsNone(self.classify(["python", "-c", "print('v13')"]))


def _store_lock_probe():
    install = (Path(__file__).resolve().parents[1] /
               "scripts/termux_one_command.sh").read_text()
    a, b = "# V13_STORE_LOCK_CHECK_BEGIN", "# V13_STORE_LOCK_CHECK_END"
    assert install.count(a) == 1 and install.count(b) == 1
    raw = install.split(a, 1)[1].split(b, 1)[0]
    namespace = {"os": os, "fcntl": fcntl, "stat": stat, "Path": Path}
    exec(compile(raw, "<V13 verified Store lock guard>", "exec"), namespace)
    return namespace["checked_store_lock_available"]


class InstallerStoreLockGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v13-store-lock-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        (self.home / "data").mkdir()
        self.lock = self.home / "data/coordinator.lock"
        self.probe = _store_lock_probe()

    def test_absent_lock_is_idle(self):
        self.assertTrue(self.probe(self.home))
        self.assertFalse(self.lock.exists())

    def test_free_lock_is_read_only_and_preserved(self):
        self.lock.write_text("stale previous pid")
        before = self.lock.stat()
        self.assertTrue(self.probe(self.home))
        after = self.lock.stat()
        self.assertEqual(self.lock.read_text(), "stale previous pid")
        self.assertEqual((before.st_dev, before.st_ino, before.st_size),
                         (after.st_dev, after.st_ino, after.st_size))

    def test_another_process_holding_lock_is_not_idle(self):
        self.lock.write_text("owned by live chat")
        program = ("import fcntl,os,sys; f=open(sys.argv[1],'a+');"
                   "fcntl.flock(f,fcntl.LOCK_EX); print('READY',flush=True);"
                   "sys.stdin.read(1)")
        child = subprocess.Popen([sys.executable, "-c", program, str(self.lock)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "READY")
            self.assertFalse(self.probe(self.home))
            self.assertEqual(self.lock.read_text(), "owned by live chat")
        finally:
            child.stdin.close()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()
        self.assertTrue(self.probe(self.home))

    def test_symlink_lock_never_followed(self):
        outside = self.home / "outside"
        outside.write_text("keep")
        self.lock.symlink_to(outside)
        with self.assertRaises(RuntimeError):
            self.probe(self.home)
        self.assertEqual(outside.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
