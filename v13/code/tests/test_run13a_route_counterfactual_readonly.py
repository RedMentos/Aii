"""Run13A read-only route/output counterfactual synthetic guard tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import c2_body_run13a_route_counterfactual_readonly as m

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")


def synthetic_report():
    cases = json.loads(FIXTURE.read_text())["cases"]
    rows = []
    for i, c in enumerate(cases):
        for arm in m.ORDER[i]:
            auto = arm == "F_NATIVE_AUTO"
            chosen = i in (2, 6, 7)
            if arm == "A_C3_ONLY":
                output = f"c3-{i}"
            elif arm == "B_B1_ONLY":
                output = f"b1-{i}"
            elif arm == "C_B2_ONLY":
                output = f"b2-{i}"
            else:
                output = f"b1-{i}" if chosen else f"c3-{i}"
            flags = {
                "valid_native": True, "body_offer_roles": [],
                "expected_offer_roles": [], "observer_mode": "off",
                "native_c2_invocation": auto,
                "native_c2_selected": auto and chosen,
                "route": "both" if auto and chosen else "simple",
                "runner_role": ("B1_DETAIL" if auto and chosen
                                else "C3_LANGUAGE"),
            }
            numeric = 2 if arm == "C_B2_ONLY" and i in (1, 3, 7) else 0
            full = arm == "C_B2_ONLY" and i in (1, 7)
            row = {
                "index": len(rows), "fixture": c["project"], "arm": arm,
                "final_output": output, "flags": flags,
                "score": {"correct": numeric},
                "full_task": {"strict_full": full},
            }
            if auto:
                row["strict_admission"] = {"matches": True}
            rows.append(row)
    numeric = {a: sum(r["score"]["correct"] for r in rows if r["arm"] == a)
               for a in m.ARMS}
    full = {a: sum(r["full_task"]["strict_full"] for r in rows if r["arm"] == a)
            for a in m.ARMS}
    return {
        "fixtures": cases, "rows": rows, "seed": 211,
        "arms": list(m.ARMS), "arm_order": [list(o) for o in m.ORDER],
        "score_totals_out_of_16": numeric,
        "strict_full_totals_out_of_8": full,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        **{k: False for k in m.NEGATIVE},
    }


class Run13ARouteCounterfactualTests(unittest.TestCase):
    def test_exact_string_match_counts_and_negative_gates(self):
        r = m.analyze_report(synthetic_report())
        self.assertEqual(r["f_identical_to_some_single_arm"], 8)
        self.assertEqual(r["f_identical_output_arm_counts"],
                         {"A_C3_ONLY": 5, "B_B1_ONLY": 3})
        self.assertEqual(r["final_role_counts"],
                         {"C3_LANGUAGE": 5, "B1_DETAIL": 3})
        self.assertEqual(r["route_counts"], {"simple": 5, "both": 3})
        self.assertEqual(r["f_native_selected"], 3)
        self.assertEqual((r["f_numeric"], r["b2_numeric"]), (0, 6))
        self.assertEqual((r["f_full"], r["b2_full"]), (0, 2))
        self.assertFalse(r["comparative_utility_proven"])
        self.assertFalse(r["step2_gate_promoted"])

    def test_missing_arm_rejected(self):
        d = synthetic_report()
        d["rows"][0]["arm"] = "F_NATIVE_AUTO"
        with self.assertRaisesRegex(ValueError, "ARM_OR_PROJECT"):
            m.analyze_report(d)

    def test_fixture_mutation_rejected(self):
        d = synthetic_report()
        d["fixtures"][0]["budget"] += 1
        with self.assertRaisesRegex(ValueError, "FROZEN_SOURCE"):
            m.analyze_report(d)

    def test_promotion_rejected(self):
        d = synthetic_report()
        d["step2_gate_promoted"] = True
        with self.assertRaisesRegex(ValueError, "GATE_CHANGED"):
            m.analyze_report(d)

    def test_missing_strict_c2_rejected(self):
        d = synthetic_report()
        next(r for r in d["rows"] if r["arm"] == "F_NATIVE_AUTO")[
            "strict_admission"]["matches"] = False
        with self.assertRaisesRegex(ValueError, "C2_STRICT"):
            m.analyze_report(d)

    def test_bad_score_rejected(self):
        d = synthetic_report()
        d["rows"][0]["score"]["correct"] = 3
        with self.assertRaisesRegex(ValueError, "ROW_INVALID"):
            m.analyze_report(d)

    def test_tampered_report_totals_rejected(self):
        d = synthetic_report()
        d["score_totals_out_of_16"]["C_B2_ONLY"] = 8
        with self.assertRaisesRegex(ValueError, "FROZEN_TOTALS"):
            m.analyze_report(d)

    def test_original_zip_absence_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "ZIP_MISSING"):
                m.inspect_zip(Path(td) / "missing.zip")


if __name__ == "__main__":
    unittest.main()
