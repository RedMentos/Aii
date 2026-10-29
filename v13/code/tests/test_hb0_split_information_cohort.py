"""HB0 structural information necessity, provenance and non-promotion tests."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import hb0_split_information_cohort as hb0
from scripts import context_option_safe_scope_candidate as safe


class HB0SplitInformationCohort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = hb0.fixtures()

    def test_preregistered_count_balance_and_counterfactual_necessity(self):
        checks = hb0.validate(self.rows)
        self.assertEqual(checks["rows"], 150)
        self.assertEqual(checks["families"], 25)
        self.assertEqual(checks["action_counts"], {"A": 50, "B": 50, "NONE": 50})
        self.assertEqual(checks["calibration_rows"], 30)
        self.assertEqual(checks["structural_holdout_rows"], 120)
        by_family = defaultdict(dict)
        for row in self.rows:
            by_family[row["family"]][(row["sheet_index"], row["rule_index"])] = row["oracle_action"]
        self.assertEqual(len(by_family), 25)
        for grid in by_family.values():
            self.assertEqual(len(grid), 6)
            self.assertEqual(Counter(grid.values()), Counter({"A": 2, "B": 2, "NONE": 2}))
            for r in range(3):
                self.assertNotEqual(grid[(0, r)], grid[(1, r)])
            for s in range(2):
                self.assertGreater(len({grid[(s, r)] for r in range(3)}), 1)

    def test_deterministic_hash_and_disjoint_family_partitions(self):
        again = hb0.fixtures()
        self.assertEqual(hb0._sha(self.rows), hb0._sha(again))
        calibration = {r["family"] for r in self.rows if r["partition"] == "calibration"}
        heldout = {r["family"] for r in self.rows if r["partition"] == "structural_holdout"}
        self.assertEqual(calibration, set(range(5)))
        self.assertEqual(heldout, set(range(5, 25)))
        self.assertFalse(calibration & heldout)

    def test_single_source_views_abstain_and_full_source_control(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                current = row["current"]
                for history in (
                    [], [row["b1_source"]], [row["b2_source"]],
                    [row["foreign_distractor"]],
                    [row["b1_source"], row["foreign_distractor"]],
                    [row["foreign_distractor"], row["b2_source"]],
                ):
                    self.assertEqual(safe.decide_safe(current, history)["action"], "UNKNOWN")
                self.assertEqual(safe.decide_safe(current, row["history"])["action"],
                                 row["oracle_action"])

    def test_duplicate_project_identity_rejected(self):
        rows = deepcopy(self.rows)
        rows[1]["id"] = rows[0]["id"]
        with self.assertRaisesRegex(ValueError, "HB0_ID_RED"):
            hb0.validate(rows)

    def test_missing_body_source_rejected(self):
        rows = deepcopy(self.rows)
        rows[0]["history"].remove(rows[0]["b1_source"])
        with self.assertRaisesRegex(ValueError, "HB0_SOURCE_OR_ORACLE_TAMPER_RED"):
            hb0.validate(rows)

    def test_tampered_oracle_rejected(self):
        rows = deepcopy(self.rows)
        rows[0]["oracle_action"] = "B" if rows[0]["oracle_action"] != "B" else "A"
        with self.assertRaisesRegex(ValueError, "HB0_SOURCE_OR_ORACLE_TAMPER_RED"):
            hb0.validate(rows)

    def test_answer_bearing_current_rejected(self):
        rows = deepcopy(self.rows)
        rows[0]["current"] += " Budget 999 euros."
        with self.assertRaisesRegex(ValueError, "HB0_SOURCE_OR_ORACLE_TAMPER_RED"):
            hb0.validate(rows)

    def test_evidence_report_no_promotion(self):
        report = hb0.inspect()
        self.assertEqual(report["status"], "SYNTHETIC_STRUCTURAL_READY_NO_GATE")
        self.assertEqual(report["evidence_kind"], "SOFTWARE_SYNTHETIC_NO_MODEL")
        self.assertEqual(report["native_calls"], 0)
        self.assertFalse(report["model_called"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_status"], "UTILITY_FAIL")
        self.assertEqual(report["b3_status"], "FAIL")
        self.assertEqual(report["jepa_weight"], 0)
        self.assertFalse(report["redmi_measured"])
        self.assertFalse(report["whole_system_complete"])

    def test_cli_fresh_file_only(self):
        with TemporaryDirectory() as d:
            out = Path(d) / "hb0.json"
            self.assertEqual(hb0.main(["--out", str(out)]), 0)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(saved["fixture_sha256"], hb0._sha(self.rows))
            self.assertEqual(len(saved["fixtures"]), 150)
            with self.assertRaisesRegex(FileExistsError, "FRESH_HB0_EVIDENCE_REQUIRED"):
                hb0.main(["--out", str(out)])


if __name__ == "__main__":
    unittest.main()
