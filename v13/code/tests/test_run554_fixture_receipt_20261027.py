"""Run554 synthetic fixture receipt vs explicit nonanswer: no native promotion."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_jef_goal_run554 as P
from v13.agi.live import _goal_explicit_nonanswer


class Run554FixtureReceiptRegression(unittest.TestCase):
    def test_fixture_answer_is_explicitly_synthetic_and_not_an_abstention(self):
        self.assertIn("fictional", P.FIXTURE_ANSWER)
        self.assertIn("RUN554-ORBIT", P.FIXTURE_ANSWER)
        self.assertFalse(_goal_explicit_nonanswer(P.FIXTURE_ANSWER))
        self.assertTrue(_goal_explicit_nonanswer("I do not know."))

    def test_original_run315_nonanswer_cannot_close_user_goal(self):
        with tempfile.TemporaryDirectory() as d, patch.object(P, "FIXTURE_ANSWER", "I do not know."):
            root = Path(d)
            report = P.probe(root / "home", None, root / "nonanswer.json",
                             native=False, timeout=30)
            self.assertEqual(report["status"], "INTEGRATION_FAIL")
            self.assertFalse(report["integration_pass"])
            self.assertEqual(report["evidence_level"], "FIXTURE_ONLY")
            self.assertFalse(report["native"])
            checks = report["checks"]
            self.assertTrue(checks["final"])
            self.assertTrue(checks["own_final_receipt"])
            self.assertFalse(checks["goal_done"])
            self.assertFalse(checks["receipt_note"])
            self.assertFalse(checks["reopened"])
            self.assertTrue(checks["model_operator_refused"])
            self.assertTrue(checks["manual_completed"])
            self.assertTrue(checks["restart_persisted"])
            self.assertFalse(checks["native_generated"])

    def test_positive_run554_fixture_receipt_stays_fixture_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = P.probe(root / "home", None, root / "receipt.json",
                             native=False, timeout=30)
            self.assertEqual(report["status"], "COMPLETE")
            self.assertTrue(report["integration_pass"])
            self.assertEqual(report["answer"]["text"], P.FIXTURE_ANSWER)
            self.assertTrue(report["answer"]["runner"]["fixture_only"])
            self.assertFalse(report["checks"]["native_generated"])
            self.assertTrue(report["checks"]["goal_done"])
            self.assertTrue(report["checks"]["receipt_note"])


if __name__ == "__main__":
    unittest.main()
