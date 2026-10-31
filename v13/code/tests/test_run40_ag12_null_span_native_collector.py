"""Run40 native collector software guards; no models or native runner used."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run40_ag12_null_span_native import ROLES, hypotheses, run


def report(none=0, changed=0, finite=40, null=40):
    result = {}
    for lang in ("de", "en"):
        by_role = {
            role: {"native_calls": 88,
                   "native_field_min_types": {
                       "field_min_none_span": none if role == ROLES[0] else 0,
                       "field_min_finite": 88 - none if role == ROLES[0] else 88},
                   "finite_source_counts": {"field_min_prob": 88},
                   "null_source_counts": {"field_min_prob": 88}}
            for role in ROLES}
        result[lang] = {"aggregate": {
            "items": 88, "role_calls": 264, "by_role": by_role,
            "changed_votes": {"finite_null_all": changed},
            "correct": {"finite_all": finite, "null_all": null}}}
    return result


class Run40NativeCollectorContract(unittest.TestCase):
    def test_hypotheses_are_descriptive_not_completion(self):
        h = hypotheses(report(none=5, changed=3, finite=40, null=42))
        self.assertEqual(h["none_span_role_calls"], 10)
        self.assertEqual(h["finite_null_changed_votes"], 6)
        self.assertEqual(h["finite_correct_all"], 80)
        self.assertEqual(h["null_correct_all"], 84)
        self.assertTrue(h["H1_native_none_span_present"])
        self.assertTrue(h["H2_null_finite_vote_change"])
        self.assertTrue(h["H3_null_not_worse_than_finite"])
        h = hypotheses(report(none=0, changed=0, finite=50, null=40))
        self.assertFalse(h["H1_native_none_span_present"])
        self.assertFalse(h["H2_null_finite_vote_change"])
        self.assertFalse(h["H3_null_not_worse_than_finite"])

    def test_wrong_language_and_role_counts_fail_closed(self):
        r = report()
        del r["en"]
        with self.assertRaisesRegex(ValueError, "LANGUAGE_IDENTITY"):
            hypotheses(r)
        r = report()
        r["de"]["aggregate"]["by_role"][ROLES[0]]["native_calls"] = 87
        with self.assertRaisesRegex(ValueError, "SOURCE_COUNT"):
            hypotheses(r)

    def test_platform_and_existing_paths_fail_before_install(self):
        with tempfile.TemporaryDirectory() as d:
            home, out = Path(d) / "home", Path(d) / "out"
            with patch("scripts.run40_ag12_null_span_native.platform.system",
                       return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "LINUX_X86_64_ONLY"):
                    run(home, out)
            self.assertFalse(home.exists())
            self.assertFalse(out.exists())
            out.mkdir()
            with patch("scripts.run40_ag12_null_span_native.platform.system",
                       return_value="Linux"), patch(
                       "scripts.run40_ag12_null_span_native.platform.machine",
                       return_value="x86_64"):
                with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                    run(home, out)

    def test_failed_prerequisite_preserves_red_report_and_negative_gates(self):
        with tempfile.TemporaryDirectory() as d:
            home, out = Path(d) / "home", Path(d) / "out"
            with patch("scripts.run40_ag12_null_span_native.platform.system",
                       return_value="Linux"), patch(
                       "scripts.run40_ag12_null_span_native.platform.machine",
                       return_value="x86_64"), patch(
                       "scripts.run40_ag12_null_span_native.install",
                       side_effect=OSError("synthetic-install-failure")):
                with self.assertRaisesRegex(RuntimeError, "RUN40_NATIVE_RED"):
                    run(home, out)
            r = json.loads((out / "REPORT.json").read_text())
            self.assertEqual(r["status"], "RED")
            self.assertIn("synthetic-install-failure", r["error"])
            self.assertEqual(r["age0"], "RECORD_ONLY")
            self.assertEqual(r["step2"], "UTILITY_FAIL")
            self.assertEqual(r["jepa_weight"], 0)
            self.assertFalse(r["whole_system_complete"])
            self.assertNotIn("native_answers", r)


if __name__ == "__main__":
    unittest.main()
