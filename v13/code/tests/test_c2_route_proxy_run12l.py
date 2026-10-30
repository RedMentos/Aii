"""Run12L frozen source-only scorer tests; native proof requires separate run."""
import json
from pathlib import Path
import unittest

from scripts.c2_route_proxy_score_run12l import load_fixture, score

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/c2_route_proxy_run12l_20261030.json"


def fake_rows(fixture, changes=None):
    changes = changes or {}
    rows = []
    for i, case in enumerate(fixture["cases"]):
        route = changes.get(i, case["expected_scaffold"])
        selected = i in changes
        rows.append({
            "index": i, "prompt": case["prompt"],
            "route": route,
            "route_info": {
                "source": "NATIVE_C2_ADVISORY" if selected else "BOOT_SCAFFOLD",
                "scaffold": case["expected_scaffold"],
            },
            "strict_admission": {
                "matches": True, "selected": selected,
                "scaffold": case["expected_scaffold"],
            },
            "source_exact": True, "no_live_answer": True,
            "c3_called": False, "body_called": False,
            "jepa_weight": 0,
            "native_c2_invocation_valid_before_release": True,
            "needle_process_reaped": True,
        })
    return rows


class Run12LProxyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE)

    def test_frozen_cohort_and_roles(self):
        self.assertEqual(len(self.fixture["cases"]), 15)
        self.assertEqual([c["reference_route"] for c in self.fixture["cases"][:12]],
                         ["simple"] * 4 + ["detail"] * 4 + ["gist"] * 4)
        self.assertEqual([c["expected_scaffold"] for c in self.fixture["cases"][12:]],
                         ["detail", "gist", "both"])

    def test_frozen_fixture_tamper_rejected(self):
        data = json.loads(FIXTURE.read_text())
        data["cases"][0]["prompt"] += " modified"
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                load_fixture(path)

    def test_no_native_selection_fails_proxy(self):
        report = score(self.fixture, fake_rows(self.fixture))
        self.assertTrue(report["native_c2_proven"])
        self.assertEqual(report["scaffold_correct_first12"], 4)
        self.assertEqual(report["final_correct_first12"], 4)
        self.assertFalse(report["proxy_threshold_met"])
        self.assertFalse(report["route_semantic_utility_proven"])

    def test_three_correct_improvements_pass_proxy_only(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist"})
        report = score(self.fixture, rows)
        self.assertEqual(report["net_correct_gain_first12"], 3)
        self.assertEqual(report["native_admissions_first12"], 3)
        self.assertEqual(report["greeting_regressions"], 0)
        self.assertTrue(report["proxy_threshold_met"])
        for flag in ("route_semantic_utility_proven", "step2_gate_promoted",
                     "b3_promoted", "body_jepa_available", "redmi_measured",
                     "whole_system_complete"):
            self.assertFalse(report[flag], flag)
        self.assertEqual(report["jepa_weight"], 0)

    def test_greeting_regression_blocks_proxy(self):
        rows = fake_rows(self.fixture, {
            0: "gist", 4: "detail", 5: "detail", 8: "gist", 9: "gist",
        })
        report = score(self.fixture, rows)
        self.assertGreaterEqual(report["net_correct_gain_first12"], 2)
        self.assertEqual(report["greeting_regressions"], 1)
        self.assertFalse(report["proxy_threshold_met"])

    def test_native_failure_blocks_even_with_improvement(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist"})
        rows[2]["needle_process_reaped"] = False
        report = score(self.fixture, rows)
        self.assertFalse(report["native_c2_proven"])
        self.assertFalse(report["proxy_threshold_met"])

    def test_foreign_or_ambiguous_admission_blocks(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist"})
        rows[4]["strict_admission"]["matches"] = False
        self.assertFalse(score(self.fixture, rows)["proxy_threshold_met"])

    def test_non_simple_native_override_blocks(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist",
                                        12: "simple"})
        self.assertFalse(score(self.fixture, rows)["proxy_threshold_met"])

    def test_wrong_prompt_identity_blocks(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist"})
        rows[0]["prompt"] = "foreign source"
        self.assertFalse(score(self.fixture, rows)["proxy_threshold_met"])

    def test_partial_rows_fail_closed(self):
        rows = fake_rows(self.fixture, {4: "detail", 5: "detail", 8: "gist"})[:14]
        report = score(self.fixture, rows)
        self.assertEqual(report["case_count"], 14)
        self.assertFalse(report["native_c2_proven"])
        self.assertFalse(report["proxy_threshold_met"])


if __name__ == "__main__":
    unittest.main()
