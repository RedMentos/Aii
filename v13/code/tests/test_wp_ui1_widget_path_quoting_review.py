"""WP-UI1 review: generated widget commands must preserve literal path bytes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class WidgetPathQuotingReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "Home's folder"
        self.home.mkdir()
        self.app = self.root / "App's folder $(touch PAGER_PWNED)"
        self.app.mkdir()
        (self.app / "docs").mkdir()
        (self.app / "docs" / "BEFEHLE.md").write_text("Literal commands", encoding="utf-8")
        source = Path(__file__).resolve().parents[1] / "KNOEPFE_EINRICHTEN.sh"
        shutil.copy2(source, self.app / source.name)
        self.v13_home = self.root / "V13's data $(touch INJECTED)"
        self.stub = self.root / "bin"
        self.stub.mkdir()
        v13 = self.stub / "v13"
        v13.write_text('#!/bin/sh\nprintf "%s" "$V13_HOME" > "$V13_CAPTURE"\n',
                       encoding="utf-8")
        pager = self.stub / "less"
        pager.write_text('#!/bin/sh\nfor a; do :; done\nprintf "%s" "$a" > "$PAGER_CAPTURE"\n',
                         encoding="utf-8")
        v13.chmod(0o700)
        pager.chmod(0o700)
        self.env = dict(os.environ, HOME=str(self.home),
                        V13_HOME=str(self.v13_home), PREFIX="/usr",
                        V13_CAPTURE=str(self.root / "chat_capture"),
                        PAGER_CAPTURE=str(self.root / "pager_capture"),
                        PATH=str(self.stub) + os.pathsep + os.environ["PATH"])
        self.installer = self.app / "KNOEPFE_EINRICHTEN.sh"

    def tearDown(self):
        self.temp.cleanup()

    def run_shell(self, path, *args, input_text=None):
        return subprocess.run(["bash", str(path), *args], cwd=self.root,
                              env=self.env, input=input_text, text=True,
                              capture_output=True, timeout=10)

    def test_all_five_generated_scripts_parse_with_literal_paths(self):
        installed = self.run_shell(self.installer)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        for name in ("V13 Chat", "V13 Status", "V13 Befehle",
                     "tasks/V13 Notaus", "tasks/V13 Stillstand"):
            path = self.home / ".shortcuts" / name
            self.assertTrue(path.exists(), name)
            parsed = subprocess.run(["bash", "-n", str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(parsed.returncode, 0, name + ": " + parsed.stderr)
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_literal_paths_no_command_substitution_and_one_way_stop(self):
        self.assertEqual(self.run_shell(self.installer).returncode, 0)
        sc = self.home / ".shortcuts"
        chat = self.run_shell(sc / "V13 Chat")
        self.assertEqual(chat.returncode, 0, chat.stderr)
        self.assertEqual((self.root / "chat_capture").read_text(),
                         str(self.v13_home))
        pager = self.run_shell(sc / "V13 Befehle")
        self.assertEqual(pager.returncode, 0, pager.stderr)
        self.assertEqual((self.root / "pager_capture").read_text(),
                         str(self.app / "docs" / "BEFEHLE.md"))
        for name, flag in (("tasks/V13 Notaus", "NOTAUS"),
                           ("tasks/V13 Stillstand", "STILLSTAND")):
            result = self.run_shell(sc / name)
            self.assertEqual(result.returncode, 0, result.stderr)
            path = self.v13_home / "control" / flag
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.root / "INJECTED").exists())
        self.assertFalse((self.root / "PAGER_PWNED").exists())
        unrelated = sc / "unrelated"
        unrelated.write_text("keep")
        removed = self.run_shell(self.installer, "weg")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertTrue(unrelated.exists())
        self.assertFalse((sc / "V13 Chat").exists())
        self.assertFalse((sc / "tasks" / "V13 Notaus").exists())


if __name__ == "__main__":
    unittest.main()
