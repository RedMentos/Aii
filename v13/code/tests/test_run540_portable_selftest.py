"""Run540 portable phone-install smoke is explicit, bounded and never a full-suite PASS."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from v13.__main__ import main


class PortableSelftestContract(unittest.TestCase):
    def test_portable_executes_exact_27_live_checks_without_models(self):
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env.update(V13_NO_AUTOSTART="1", NO_MODEL_DOWNLOADS="1",
                       HF_HUB_OFFLINE="1", PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            result = subprocess.run(
                [sys.executable, "-m", "v13", "--home", home, "selftest", "--portable"],
                cwd=Path(__file__).resolve().parents[1], env=env,
                capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stderr[-4000:])
            self.assertIn("PORTABLE_SELFTEST", result.stdout)
            self.assertIn("NOT full regression", result.stdout)
            self.assertIn("Ran 94 tests", result.stderr)
            self.assertNotIn("FAILED", result.stderr)
            self.assertNotIn("No module named 'torch'", result.stderr)

    def test_default_selftest_keeps_unfiltered_discovery(self):
        class Good:
            testsRun = 1
            def wasSuccessful(self):
                return True
        with tempfile.TemporaryDirectory() as home, \
             patch("v13.__main__.unittest.defaultTestLoader.discover", return_value=unittest.TestSuite()) as discover, \
             patch("v13.__main__.unittest.TextTestRunner") as runner, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            runner.return_value.run.return_value = Good()
            self.assertEqual(main(["--home", home, "selftest"]), 0)
            discover.assert_called_once()
            self.assertEqual(discover.call_args.kwargs["pattern"], "test_*.py")
            self.assertIn("FULL_SELFTEST", output.getvalue())

    def test_portable_zero_or_missing_tests_cannot_pass(self):
        class Fake:
            testsRun = 0
            def wasSuccessful(self):
                return True
        with tempfile.TemporaryDirectory() as home, \
             patch("v13.__main__.unittest.defaultTestLoader.loadTestsFromName", return_value=unittest.TestSuite()) as loader, \
             patch("v13.__main__.unittest.TextTestRunner") as runner:
            runner.return_value.run.return_value = Fake()
            self.assertEqual(main(["--home", home, "selftest", "--portable"]), 1)
            self.assertEqual(loader.call_count, 3)


if __name__ == "__main__":
    unittest.main()
