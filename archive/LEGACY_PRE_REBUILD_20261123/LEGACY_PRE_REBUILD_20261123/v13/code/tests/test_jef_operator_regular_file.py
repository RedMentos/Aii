"""Linux/Android local-input regular-file guard; no native inference."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import cohort


@unittest.skipUnless(hasattr(os, "O_NOFOLLOW") and hasattr(os, "mkfifo"),
                     "Linux/Android regular-file guard")
class JefOperatorRegularFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def fixture(self):
        row = cohort()[0]
        path = self.root / "valid.json"
        path.write_text(json.dumps({
            "project": row["id"], "domain": row["domain"],
            "policy_source": row["b2_source"],
            "sheet_source": row["b1_source"],
            "current": row["current"],
        }), encoding="utf-8")
        return path

    def test_real_fifo_without_writer_is_rejected_without_block(self):
        fifo = self.root / "source.fifo"
        os.mkfifo(fifo)
        home = self.root / "no_runtime"
        script = Path(cli.__file__).resolve()
        result = subprocess.run(
            [sys.executable, str(script), "--home", str(home),
             "--input-file", str(fifo), "--mode", "synthetic_exact",
             "--operator-opt-in", "--callback-opt-in"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "INPUT_RED")
        self.assertFalse(payload["runtime_opened"])
        self.assertFalse(home.exists())

    def test_directory_and_symlink_refused_before_runtime(self):
        valid = self.fixture()
        directory = self.root / "directory"
        directory.mkdir()
        link = self.root / "linked.json"
        link.symlink_to(valid)
        for name, path in (("directory", directory), ("symlink", link)):
            with self.subTest(name=name):
                home = self.root / ("home_" + name)
                result = cli.run(home, path, "synthetic_exact",
                                 operator_opt_in=True, callback_opt_in=True)
                self.assertEqual(result["status"], "INPUT_RED")
                self.assertFalse(result["runtime_opened"])
                self.assertFalse(home.exists())

    def test_nonregular_fd_closed_after_rejection(self):
        directory = self.root / "directory"
        directory.mkdir()
        real_open = os.open
        opened = []
        def tracking_open(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            opened.append(fd)
            return fd
        with patch.object(cli.os, "open", side_effect=tracking_open):
            with self.assertRaisesRegex(ValueError,
                                        "INPUT_NOT_REGULAR_RED"):
                cli._read_input(directory)
        self.assertEqual(len(opened), 1)
        with self.assertRaises(OSError):
            os.fstat(opened[0])

    def test_open_error_refused_before_runtime(self):
        path = self.fixture()
        home = self.root / "no_runtime"
        with patch.object(cli.os, "open", side_effect=OSError("injected")):
            result = cli.run(home, path, "synthetic_exact",
                             operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "INPUT_RED")
        self.assertFalse(home.exists())

    def test_regular_file_retains_shadow_draft_preflight(self):
        path = self.fixture()
        result = cli.run(self.root / "home", path, "synthetic_exact",
                         operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_DRAFT_PREFLIGHT_READY")
        self.assertEqual(result["c6_status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["native_model_called"])


if __name__ == "__main__":
    unittest.main()
