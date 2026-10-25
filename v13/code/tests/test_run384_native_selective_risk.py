"""Run384 field-only confidence audit controls; no native model or AG9 writes."""
import copy
import math
import unittest

from scripts import run384_native_selective_risk as A


def row(arm, answer, correct, confidence, field=True, source=None):
    return {
        "arm": arm, "answer": answer, "correct_exact": correct,
        "confidence": confidence, "field_supported": field,
        "confidence_source": source or ("field_min_prob" if field else "mean_prob"),
        "status": "FINAL", "can_train_body": False,
    }


class NativeSelectiveRiskRun384(unittest.TestCase):
    def report(self):
        return {
            "revision": "test-native",
            "evidence_level": "LINUX_NATIVE_C3_ONLY",
            "rows": [
                row("A", "14", True, .95),
                row("A", "wrong", False, .80),
                row("A", "", False, .99, field=False),
                row("A", "7", True, .40),
                row("B", "", False, .99, field=False),
            ],
        }

    def test_field_only_thresholds_never_accept_fallback_or_empty(self):
        out = A.audit_report(self.report(), "abc123")
        self.assertEqual(out["source_sha256"], "abc123")
        a = out["arms"]["A"]
        self.assertEqual(a["n"], 4)
        self.assertEqual(a["field_supported"], 3)
        self.assertEqual(a["field_only_calibration"]["bins"][-1]["n"], 1)
        self.assertEqual(a["selective"]["0.90"]["accepted"], 1)
        self.assertEqual(a["selective"]["0.90"]["accepted_wrong"], 0)
        self.assertEqual(a["selective"]["0.90"]["rejected_correct"], 1)
        self.assertEqual(a["selective"]["0.75"]["accepted"], 2)
        self.assertEqual(a["selective"]["0.75"]["selective_risk"], .5)
        self.assertEqual(a["selective"]["0.25"]["accepted"], 3)
        self.assertEqual(a["calibration_status"], "UNDERPOWERED")
        b = out["arms"]["B"]
        self.assertEqual(b["selective"]["0.25"]["accepted"], 0)
        self.assertIsNone(b["selective"]["0.25"]["selective_risk"])
        self.assertEqual(b["field_only_calibration"]["ece"], None)

    def test_invalid_scores_or_evidence_fail_closed(self):
        for bad in (math.nan, math.inf, -0.1, 1.1, True, "0.8"):
            with self.subTest(confidence=repr(bad)):
                x = self.report()
                x["rows"][0]["confidence"] = bad
                with self.assertRaises(ValueError):
                    A.audit_report(x, "hash")
        for field, value in (
            ("status", "ERROR"),
            ("can_train_body", True),
            ("field_supported", 1),
            ("correct_exact", 1),
            ("confidence_source", "mean_prob"),
            ("empty", True),
            ("wrong_nonempty", True),
        ):
            with self.subTest(field=field):
                x = self.report()
                x["rows"][0][field] = value
                with self.assertRaises(ValueError):
                    A.audit_report(x, "hash")

    def test_minimum_support_does_not_activate_calibration(self):
        x = self.report()
        x["rows"] = [row("A", "14", True, .9) for _ in range(20)]
        out = A.audit_report(x, "hash")
        self.assertEqual(out["arms"]["A"]["calibration_status"],
                         "DESCRIPTIVE_ONLY_NOT_HELDOUT")
        self.assertEqual(out["arms"]["A"]["field_supported"], 20)


if __name__ == "__main__":
    unittest.main()
