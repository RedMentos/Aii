"""Seed71 frozen out-of-template German SHADOW audit tests; no model/tool."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.listarith_de_seed71_stress_eval import (
    FIXTURE_BLOB, DETECTOR_BLOB, fixture_rows, metrics, evaluate, blob_sha,
    FIXTURE, ORIGINAL_SEED67, ORIGINAL_SEED67_BLOB,
)
from v13.agi import listarith_de_shadow, listarith


class Seed71FrozenStress(unittest.TestCase):
    def test_frozen_identity_and_balanced_disjoint_labels(self):
        rows = fixture_rows()
        self.assertEqual(len(rows), 36)
        self.assertEqual(blob_sha(FIXTURE), FIXTURE_BLOB)
        self.assertEqual(blob_sha(Path(listarith_de_shadow.__file__)), DETECTOR_BLOB)
        self.assertEqual(blob_sha(ORIGINAL_SEED67), ORIGINAL_SEED67_BLOB)
        self.assertEqual(len(set(r["text"] for r in rows)), 36)
        self.assertEqual([sum(r["expected"] == k for r in rows)
                          for k in ("total", "difference_max_min", None)], [12, 12, 12])

    def test_metrics_all_correct_pass(self):
        rows = [{"expected": x["expected"], "proposal": x["expected"],
                 "tag": x["tag"]} for x in fixture_rows()]
        result = metrics(rows)
        self.assertEqual(result["correct"], 36)
        self.assertEqual(result["none_false_positive"], 0)
        self.assertEqual(result["status"], "SHADOW_GENERALIZATION_PASS")

    def test_negation_false_positive_fails_even_if_35_correct(self):
        rows = [{"expected": x["expected"], "proposal": x["expected"],
                 "tag": x["tag"]} for x in fixture_rows()]
        index = next(i for i, x in enumerate(rows) if x["expected"] is None
                     and x["tag"] == "negation")
        rows[index]["proposal"] = "total"
        result = metrics(rows)
        self.assertEqual(result["correct"], 35)
        self.assertEqual(result["none_false_positive"], 1)
        self.assertEqual(result["negation_false_positive"], 1)
        self.assertEqual(result["status"], "SHADOW_GENERALIZATION_RED")

    def test_supported_class_recall_threshold(self):
        rows = [{"expected": x["expected"], "proposal": x["expected"],
                 "tag": x["tag"]} for x in fixture_rows()]
        for row in rows:
            if row["expected"] == "total":
                row["proposal"] = None
        self.assertEqual(metrics(rows)["status"], "SHADOW_GENERALIZATION_RED")

    def test_invalid_label_and_row_count_refused(self):
        rows = [{"expected": x["expected"], "proposal": x["expected"],
                 "tag": x["tag"]} for x in fixture_rows()]
        with self.assertRaisesRegex(ValueError, "METRIC_ROW_COUNT"):
            metrics(rows[:-1])
        bad = copy.deepcopy(rows)
        bad[0]["proposal"] = "execute_tool"
        with self.assertRaisesRegex(ValueError, "METRIC_LABEL_INVALID"):
            metrics(bad)

    def test_actual_evaluation_raw_and_negative_gates(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "stress_report.json"
            report = evaluate(out)
            stored = json.loads(out.read_text())
            self.assertEqual(report, stored)
            self.assertEqual(len(report["rows"]), 36)
            self.assertEqual(report["metric"]["total"], 36)
            self.assertIn(report["metric"]["status"],
                          ("SHADOW_GENERALIZATION_RED", "SHADOW_GENERALIZATION_PASS"))
            self.assertEqual(report["evidence_level"], "SYNTHETIC_SOFTWARE_ONLY")
            self.assertEqual(report["live_consumers"], 0)
            self.assertFalse(report["native_model_inference"])
            self.assertFalse(report["redmi_measured"])
            self.assertFalse(report["step2_gate_promoted"])
            self.assertFalse(report["b3_promoted"])
            self.assertFalse(report["body_jepa_available"])
            self.assertFalse(report["whole_system_complete"])
            self.assertEqual(report["jepa_weight"], 0)
            self.assertEqual(report["learning_mode"], "RECORD_ONLY")
            self.assertTrue(all(x["authority"] == "SHADOW_ONLY" for x in report["rows"]))
            with self.assertRaises(FileExistsError):
                evaluate(out)

    def test_original_english_recipe_unchanged(self):
        self.assertEqual(listarith.operation("Items: A 12, B 30. What is the total?"), "total")
        self.assertEqual(listarith.operation(
            "Items: A 12, B 30. How much more is the largest than the smallest?"),
            "difference_max_min")
        self.assertIsNone(listarith.operation("Items: A 12, B 30. What is the average?"))

    def test_no_live_tool_or_numeric_result(self):
        self.assertEqual(listarith_de_shadow.AUTHORITY, "SHADOW_ONLY")
        self.assertFalse(hasattr(listarith_de_shadow, "tool"))
        self.assertFalse(hasattr(listarith_de_shadow, "run"))
        for row in fixture_rows():
            got = listarith_de_shadow.propose(row["text"])
            self.assertEqual(set(got), {"proposal", "authority", "reason"})
            self.assertIn(got["proposal"], ("total", "difference_max_min", None))


if __name__ == "__main__":
    unittest.main()
