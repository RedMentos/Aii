"""V13 Termux install: default interactive mode must not be missed.

The tested classifier is extracted from the real installer, without executing
any installation or signaling a process.
"""
import os
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
