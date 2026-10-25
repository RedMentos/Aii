"""Run117 locked fresh-seed selective-risk diagnostic; no World runtime changes."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ablation_world_selective_risk_run117 as A
from v13 import world_model as WM


class WorldSelectiveRiskRun117(unittest.TestCase):
    def test_locked_cohort_and_thresholds(self):
        self.assertEqual(A.SEEDS, tuple(range(200, 220)))
        self.assertEqual(A.QUERIES, 400)
        self.assertEqual(A.TOP_FRACTION, 0.25)
        self.assertEqual(A.MIN_VALID, 40)
        self.assertEqual(A.WIN_THRESHOLD, 16)
        self.assertEqual(set(A.ARMS), {"confidence", "samples_only", "spread_only", "random"})

    def test_deterministic_equal_query_denominator_and_selection(self):
        a = A.run_seed(200, query_limit=24)
        b = A.run_seed(200, query_limit=24)
        self.assertEqual(a, b)
        self.assertEqual(a["queries_n"], 24)
        self.assertEqual(a["valid_n"] + a["abstained_n"], 24)
        self.assertEqual(a["selected_k"], max(1, int(a["valid_n"] * 0.25)) if a["valid_n"] else 0)
        self.assertEqual(set(a["risk"]), set(A.ARMS))

    def test_abstentions_are_not_fabricated_as_errors(self):
        missing = {
            "prediction": None,
            "confidence": 0.0,
            "label": "SIMULATION_UNCERTAIN",
            "reason": "IMPOSSIBLE_PREDICTED_OUTCOME",
        }
        with mock.patch.object(WM, "counterfactual", return_value=missing):
            r = A.run_seed(200, query_limit=8)
        self.assertEqual(r["queries_n"], 8)
        self.assertEqual(r["valid_n"], 0)
        self.assertEqual(r["abstained_n"], 8)
        self.assertEqual(r["selected_k"], 0)
        self.assertEqual(r["abstention_reasons"], {"IMPOSSIBLE_PREDICTED_OUTCOME": 8})
        self.assertTrue(all(v is None for v in r["risk"].values()))
        self.assertFalse(r["eligible"])

    def test_incomplete_cohort_cannot_be_supported(self):
        empty = {"eligible": False, "risk": {a: None for a in A.ARMS}}
        with mock.patch.object(A, "run_seed", return_value=empty):
            result = A.run_all(seeds=(200,))
        self.assertEqual(result["verdict"], "INCOMPLETE")
        self.assertEqual(result["eligible_seeds"], 0)

    def test_positive_verdict_requires_all_three_paired_controls(self):
        def row(good):
            return {"eligible": True, "risk": {
                "confidence": 0.1 if good else 0.3,
                "samples_only": 0.2, "spread_only": 0.2, "random": 0.2}}
        all_good = {s: row(True) for s in A.SEEDS}
        self.assertEqual(A._verdict(all_good, A.SEEDS)["verdict"], "SUPPORTED_SYNTHETIC_SELECTIVE")
        one_bad = dict(all_good)
        for s in A.SEEDS[:5]:
            one_bad[s] = row(False)
        self.assertEqual(A._verdict(one_bad, A.SEEDS)["verdict"], "NOT_SUPPORTED_SYNTHETIC_SELECTIVE")


if __name__ == "__main__":
    unittest.main()
