"""Run449 source-only tests: diagnostics never turn a failing suite GREEN."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run449_classify_fullsuite_red import classify


def sample():
    return ("""
======================================================================
ERROR: test_x (test_source_handoff_candidate.SourceHandoffCandidate)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "test_x.py", line 1
ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate
======================================================================
ERROR: test_torch (test_body_fp32_master_micro_run166.SomeCase)
----------------------------------------------------------------------
Traceback (most recent call last):
ModuleNotFoundError: No module named 'torch'
======================================================================
FAIL: test_mocked_stage2_calls_one_new_arm_and_keeps_gate_red (test_run404_stage2_resume.Run404Stage2Tests)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: Lists differ: [] != [(False, True, 1)]
----------------------------------------------------------------------
Ran 3 tests in 0.2s

FAILED (failures=1, errors=2, skipped=0)
""").encode()


class Run449RedClassifierTests(unittest.TestCase):
    def test_known_categories_are_still_red_and_hash_bound(self):
        d = classify(sample(), "EXIT=1\n")
        self.assertEqual(d["status"], "RED_FULL_SUITE_UNRESOLVED")
        self.assertEqual((d["tests_run"], d["failures"], d["errors"]), (3, 1, 2))
        self.assertEqual(d["unclassified"], 0)
        self.assertEqual(d["categories"], {
            "FROZEN_RUNTIME_IDENTITY_REFUSAL": 1,
            "OPTIONAL_TORCH_UNAVAILABLE": 1,
            "STAGE1_SYNTHETIC_RECEIPT_NOT_REUSABLE": 1})
        self.assertFalse(d["canonical_gate_pass"])
        self.assertEqual(d["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(d["jepa_weight"], 0)
        self.assertFalse(d["redmi_measured"])

    def test_missing_heading_never_silently_passes(self):
        raw = sample().replace(b"FAIL: test_mocked_stage2", b"NOTE: test_mocked_stage2")
        with self.assertRaisesRegex(ValueError, "HEADINGS"):
            classify(raw, "EXIT=1")

    def test_zero_exit_or_duplicate_summary_refused(self):
        with self.assertRaisesRegex(ValueError, "RED_EXIT"):
            classify(sample(), "EXIT=0")
        with self.assertRaisesRegex(ValueError, "UNIQUE"):
            classify(sample() + b"\nFAILED (failures=1, errors=2, skipped=0)\n", "EXIT=1")

    def test_unknown_failure_is_reported_unclassified_not_ignored(self):
        raw = sample().replace(b"ModuleNotFoundError: No module named 'torch'",
                               b"RuntimeError: novel failure")
        d = classify(raw, "EXIT=1")
        self.assertEqual(d["unclassified"], 1)
        self.assertEqual(d["status"], "RED_FULL_SUITE_UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
