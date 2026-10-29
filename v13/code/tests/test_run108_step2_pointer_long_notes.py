"""Run108 source-transport stress: explicit negative structural outcomes, no native."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run108_step2_pointer_long_notes import (
    HEADER, evaluate, fixtures, main, run, values,
)


class Step2PointerLongNoteStructural(unittest.TestCase):
    def test_expected_boundary_and_no_gate_promotion(self):
        report = run()
        self.assertEqual(report["status"], "TRANSPORT_BOUNDARY_OBSERVED")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["evidence_kind"], "DETERMINISTIC_SOFTWARE_NO_MODEL")

    def test_short_full_rule_vs_long_header_coverage_failure(self):
        cases = fixtures()
        short = evaluate("SHORT", cases["SHORT"])
        long = evaluate("LONG", cases["LONG"])
        self.assertEqual(short["header_values"], {
            "budget": [100], "deadline": [5], "local_only": [True]})
        self.assertNotEqual(long["header_values"], short["header_values"])
        self.assertGreaterEqual(long["rule_bearing_choices"], 3)
        self.assertLessEqual(long["header_span_chars"], 200)

    def test_revision_is_ambiguous_and_not_promoted_to_truth(self):
        row = evaluate("REVISED", fixtures()["REVISED"])
        self.assertEqual(row["header_values"], {
            "budget": [100, 120], "deadline": [5, 7],
            "local_only": [True, False]})
        self.assertTrue(row["revision_ambiguous"])
        self.assertFalse(row["semantic_truth_authority"])
        self.assertFalse(row["model_called"])

    def test_choice_cap_loses_late_rule_sentences(self):
        row = evaluate("CAP24", fixtures()["CAP24"])
        self.assertGreater(row["sentence_count"], 24)
        self.assertEqual(row["choice_count"], 24)
        self.assertEqual(row["rule_bearing_choices"], 0)
        self.assertIn(HEADER, fixtures()["CAP24"])
        self.assertEqual(values("No budget here."), {
            "budget": [], "deadline": [], "local_only": []})

    def test_closed_report_requires_fresh_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            self.assertEqual(main(["--out", str(out)]), 0)
            data = json.loads(out.read_text())
            self.assertEqual(data["status"], "TRANSPORT_BOUNDARY_OBSERVED")
            with self.assertRaises(FileExistsError):
                main(["--out", str(out)])


if __name__ == "__main__":
    unittest.main()
