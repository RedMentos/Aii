"""Run12M source-only frozen cohort and fail-closed utility pilot tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import c2_c3_body_paired_native_run12m as m
from scripts import c2_body_disjoint_paired181_run11v as frozen

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/c2_body_paired_run12m_20261030.json"


def rows_for(utility=None, selected=True):
    utility = utility or {"A_C3_ONLY": 0, "B_B1_ONLY": 1,
                          "C_B2_ONLY": 2, "F_NATIVE_AUTO": 4}
    rows = []
    for i in range(4):
        for arm in m.ARM_ORDER[i]:
            row = {
                "arm": arm, "flags": {"valid_native": True,
                                      "native_c2_invocation": arm == "F_NATIVE_AUTO"},
                "score": {"correct": utility[arm] // 4},
                "secondary_score": {"correct": 0},
            }
            if arm == "F_NATIVE_AUTO":
                row["strict_admission"] = {
                    "matches": True, "selected": selected,
                }
            rows.append(row)
    return rows


class Run12MTests(unittest.TestCase):
    def setUp(self):
        self.data = m.load_fixture(FIXTURE)

    def test_frozen_fixture_hash_and_disjoint_prompt(self):
        self.assertEqual(m.fixture_hash(self.data["cases"]), m.FIXTURE_SHA256)
        self.assertEqual(len(self.data["cases"]), 4)
        old = {frozen.prompt(f) for f in frozen.FIXTURES}
        self.assertFalse(old & {frozen.prompt(f) for f in self.data["cases"]})
        self.assertEqual(frozen.SEED, 181)

    def test_latin_square_four_arms(self):
        self.assertEqual(len(m.ARM_ORDER), 4)
        self.assertEqual(set(m.ARMS), set(frozen.ARMS) -
                         {"D_DISTINCT_BOTH", "E_SHARED_DUAL_COLD"})
        for position in range(4):
            for arm in m.ARMS:
                self.assertEqual(sum(arm == row[position]
                                     for row in m.ARM_ORDER), 1)
        for row in m.ARM_ORDER:
            self.assertEqual(set(row), set(m.ARMS))

    def test_tampered_fixture_rejected(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "changed.json"
            f = json.loads(FIXTURE.read_text())
            f["cases"][0]["a_cost"] += 1
            path.write_text(json.dumps(f))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                m.load_fixture(path)

    def test_valid_synthetic_signal_never_promotes_gate(self):
        # Four synthetic points on native-auto versus <=2 best single.
        r = m.summarize(rows_for())
        self.assertTrue(r["all_native_structurally_valid"])
        self.assertEqual(r["native_c2_invocations"], 4)
        self.assertEqual(r["native_c2_strict_matches"], 4)
        self.assertTrue(r["native_auto_utility_pilot_signal_not_gate"])
        for key in ("step2_gate_promoted", "b3_promoted",
                    "body_jepa_available", "redmi_measured",
                    "whole_system_complete", "comparative_utility_proven"):
            self.assertFalse(r[key], key)
        self.assertEqual(r["jepa_weight"], 0)
        self.assertEqual(r["learning_mode"], "RECORD_ONLY")

    def test_native_not_selected_fails_signal(self):
        r = m.summarize(rows_for(selected=False))
        self.assertTrue(r["all_native_structurally_valid"])
        self.assertFalse(r["native_auto_utility_pilot_signal_not_gate"])

    def test_best_single_not_beaten_fails_signal(self):
        rows = rows_for({"A_C3_ONLY": 0, "B_B1_ONLY": 3,
                         "C_B2_ONLY": 4, "F_NATIVE_AUTO": 4})
        r = m.summarize(rows)
        self.assertFalse(r["native_auto_utility_pilot_signal_not_gate"])

    def test_missing_strict_native_proof_fails_closed(self):
        rows = rows_for()
        next(x for x in rows if x["arm"] == "F_NATIVE_AUTO")[
            "strict_admission"]["matches"] = False
        r = m.summarize(rows)
        self.assertFalse(r["all_native_structurally_valid"])
        self.assertFalse(r["native_auto_utility_pilot_signal_not_gate"])

    def test_native_failure_fails_closed(self):
        rows = rows_for()
        rows[0]["flags"]["valid_native"] = False
        r = m.summarize(rows)
        self.assertFalse(r["all_native_structurally_valid"])
        self.assertFalse(r["native_auto_utility_pilot_signal_not_gate"])

    def test_incomplete_rows_fail_closed(self):
        r = m.summarize(rows_for()[:15])
        self.assertEqual(r["status"], "PILOT_PARTIAL_RED")
        self.assertFalse(r["all_native_structurally_valid"])

    def test_source_bound_frozen_scorer_still_used(self):
        f = self.data["cases"][0]
        ans = "Birch leaves 163 Euro and Onyx leaves 41 Euro."
        correct = frozen.score_pair(f, ans)
        wrong = frozen.score_pair(f, "Birch leaves 999 Euro and Onyx leaves 999 Euro.")
        self.assertEqual(correct["out_of"], 2)
        self.assertLessEqual(wrong["correct"], correct["correct"])
        self.assertEqual(frozen.score_primary(f, ans)["out_of"], 2)


if __name__ == "__main__":
    unittest.main()
