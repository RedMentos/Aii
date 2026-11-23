"""Run13Z source-disjoint heldout calibration quality; synthetic, no Store."""
from __future__ import annotations

import copy
import unittest

from v13.agi.metacog_heldout_shadow_run13z import audit_heldout


def samples(prefix, n, reversed_labels=False):
    rows = []
    for i in range(n):
        high = i >= n // 2
        rows.append({
            "source_id": f"{prefix}-{i:03d}",
            "confidence": 0.7 if high else 0.3,
            "correct": bool(high) != reversed_labels,
        })
    return rows


class HeldoutCalibration(unittest.TestCase):
    def test_train_looks_better_while_disjoint_heldout_degrades(self):
        train, heldout = samples("train", 20), samples("test", 10, True)
        original = copy.deepcopy((train, heldout))
        result = audit_heldout(train, heldout)
        self.assertEqual((train, heldout), original)
        self.assertEqual(result["status"], "HELDOUT_DEGRADATION")
        self.assertLess(result["train_calibrated"]["ece"], result["train_raw"]["ece"])
        self.assertGreater(result["heldout_calibrated"]["brier"],
                           result["heldout_raw"]["brier"] + 0.02)
        self.assertFalse(result["age_metric_admissible"])
        self.assertFalse(result["utility_gate_promoted"])
        self.assertFalse(result["store_written"])
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["learning_mode"], "RECORD_ONLY")
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertEqual(result["b3_status"], "NO_PROMOTION")
        self.assertEqual(result["body_jepa_status"], "UNAVAILABLE")
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["redmi_measured"])
        self.assertFalse(result["whole_system_complete"])

    def test_matching_heldout_control_is_only_shadow_signal(self):
        result = audit_heldout(samples("train", 20), samples("test", 10))
        self.assertEqual(result["status"], "HELDOUT_NONDEGRADATION_SHADOW")
        self.assertLess(result["heldout_calibrated"]["brier"],
                        result["heldout_raw"]["brier"])
        self.assertTrue(result["monotone"])
        self.assertEqual(result["calibrator_bins"], 10)
        self.assertFalse(result["age_metric_admissible"])

    def test_cross_split_source_overlap_and_duplicate_train_rejected(self):
        train, heldout = samples("train", 20), samples("test", 10)
        heldout[0]["source_id"] = train[0]["source_id"]
        with self.assertRaises(ValueError):
            audit_heldout(train, heldout)
        train, heldout = samples("train", 20), samples("test", 10)
        train[1]["source_id"] = train[0]["source_id"]
        with self.assertRaises(ValueError):
            audit_heldout(train, heldout)

    def test_nonfinite_confidence_nonbinary_label_and_bad_source_rejected(self):
        for field, value in (
            ("confidence", float("nan")),
            ("confidence", float("inf")),
            ("confidence", True),
            ("correct", "false"),
            ("correct", 0.5),
            ("source_id", ""),
            ("source_id", "bad\nsource"),
        ):
            with self.subTest(field=field, value=str(value)):
                train, heldout = samples("train", 20), samples("test", 10)
                train[0][field] = value
                with self.assertRaises(ValueError):
                    audit_heldout(train, heldout)

    def test_insufficient_support_and_extra_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            audit_heldout(samples("train", 19), samples("test", 10))
        with self.assertRaises(ValueError):
            audit_heldout(samples("train", 20), samples("test", 9))
        train, heldout = samples("train", 20), samples("test", 10)
        heldout[0]["leaked_answer"] = "NO"
        with self.assertRaises(ValueError):
            audit_heldout(train, heldout)


if __name__ == "__main__":
    unittest.main()
