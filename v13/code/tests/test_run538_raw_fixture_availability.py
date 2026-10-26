"""Run538: cloud-only pinned raw audit does not break offline phone selftest."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class RawFixtureAvailabilityTests(unittest.TestCase):
    def run_raw_tests(self, source):
        env = os.environ.copy()
        env.pop("RUN534_RAW_JSON", None)
        if source is not None:
            env["RUN534_RAW_JSON"] = source
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        return subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "tests.test_run534_independent_z12a_audit"],
            cwd=str(Path(__file__).resolve().parents[1]), env=env,
            capture_output=True, text=True, timeout=30)

    def test_no_cloud_artifact_is_explicit_skip_not_selftest_error(self):
        result = self.run_raw_tests(None)
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("skipped", result.stderr)
        self.assertIn("pinned Run531 raw artifact not bundled", result.stderr)

    def test_explicit_missing_raw_path_is_error_not_skip(self):
        result = self.run_raw_tests("/nonexistent/run534-frozen-raw.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileNotFoundError", result.stderr)
        self.assertNotIn("OK (skipped", result.stderr)

    def test_provided_original_raw_remains_strict(self):
        source = os.environ.get("RUN534_RAW_JSON")
        if source is None:
            self.skipTest("original pinned Run531 raw only available in exact-head Actions")
        result = self.run_raw_tests(source)
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("Ran 13 tests", result.stderr)
        self.assertNotIn("skipped", result.stderr)


if __name__ == "__main__":
    unittest.main()
