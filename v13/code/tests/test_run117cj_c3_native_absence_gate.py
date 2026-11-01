"""Run117CJ: synthetic Run83 test cannot turn absent native weights into proof.

Actual Runtime/Store, no mock of native runner/model hashes. This is a
negative preflight only: no model download or native inference.
"""
from pathlib import Path
import json
import tempfile
import unittest

from scripts import run83_jef_body_c3_interference_native as native


class Run83NativeAbsenceGate(unittest.TestCase):
    def test_fresh_home_missing_native_c3_fails_closed_and_retains_raw(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "raw"
            report = native.run(root / "home", out)
            self.assertEqual(report["status"], "STRUCTURAL_RED", report)
            self.assertEqual(report["error_type"], "Unavailable")
            self.assertEqual(report["cases"], [])
            self.assertEqual(report["native_call_count"], 0)
            self.assertEqual(report["body_native_call_count"], 0)
            self.assertFalse(report["whole_system_complete"])
            self.assertFalse(report["output_committed"])
            self.assertEqual(report["learning_authority"], 0)
            self.assertEqual(report["delivery_authority"], 0)
            self.assertTrue(report["closed_store_ok"])
            self.assertEqual(json.loads((out / "report.json").read_text()), report)

    def test_real_native_entrypoint_remains_unpatched_by_synthetic_test(self):
        # A distinct test imports the real Runtime, not DryRuntime. The
        # production entrypoint must remain the real class.
        from v13.runtime import Runtime
        self.assertIs(native.cli.Runtime, Runtime)


if __name__ == "__main__":
    unittest.main()
