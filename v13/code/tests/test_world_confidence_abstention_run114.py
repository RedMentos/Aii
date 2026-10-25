"""Run114: historical World Model confidence ablation must not invent predictions."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ablation_world_model_confidence as A
from v13 import world_model as WM


class WorldConfidenceAbstentionRun114(unittest.TestCase):
    def setUp(self):
        self.old_q = A.Q
        A.Q = 6

    def tearDown(self):
        A.Q = self.old_q

    def test_one_abstention_keeps_exact_denominator_and_reason(self):
        count = [0]

        def response(store, state, action):
            count[0] += 1
            if count[0] == 1:
                return {
                    "prediction": None,
                    "confidence": 0.0,
                    "label": "SIMULATION_UNCERTAIN",
                    "reason": "IMPOSSIBLE_PREDICTED_OUTCOME",
                    "authority": "HYPOTHESIS",
                }
            return {
                "prediction": dict(zip(WM.TARGETS, [1.0, 0.5, 1.0])),
                "confidence": 0.6,
                "coverage": {"samples": 12},
                "model_spread": 0.1,
                "label": "SIMULATION_SUPPORTED",
                "authority": "HYPOTHESIS",
            }

        with mock.patch.object(WM, "counterfactual", side_effect=response):
            r = A.run_seed(13)
        self.assertEqual(count[0], 6)
        self.assertEqual(r["queries_n"], 6)
        self.assertEqual(r["evaluated_n"], 5)
        self.assertEqual(r["abstained_n"], 1)
        self.assertEqual(r["abstention_reasons"], {"IMPOSSIBLE_PREDICTED_OUTCOME": 1})
        self.assertEqual(r["labels"]["supported_n"] + r["labels"]["uncertain_n"], 5)

    def test_all_abstentions_cannot_generate_rank_or_false_success(self):
        missing = {
            "prediction": None,
            "confidence": 0.0,
            "label": "SIMULATION_UNCERTAIN",
            "reason": "NO_WORLD_MODEL",
            "authority": "HYPOTHESIS",
        }
        with mock.patch.object(WM, "counterfactual", return_value=missing):
            r = A.run_seed(13)
            summary = A.run_all(seeds=[13])
        self.assertEqual(r["evaluated_n"], 0)
        self.assertEqual(r["abstained_n"], 6)
        self.assertEqual(r["abstention_reasons"], {"NO_WORLD_MODEL": 6})
        self.assertIsNone(r["confidence"]["primary"])
        self.assertIsNone(r["labels"]["supported_mean_err"])
        self.assertEqual(summary["verdict"], "INCOMPLETE_ABSTENTION")
        self.assertEqual(summary["complete_seeds"], [])
        self.assertEqual(summary["incomplete_seeds"], [13])

    def test_real_world_model_guard_preserved(self):
        # Run113's real error must turn into a reported abstention, never a
        # fabricated numerical error or a relaxation of World Model guards.
        r = A.run_seed(13)
        self.assertEqual(r["fit_status"], "FITTED")
        self.assertEqual(r["evaluated_n"] + r["abstained_n"], 6)
        self.assertEqual(
            r["labels"]["supported_n"] + r["labels"]["uncertain_n"],
            r["evaluated_n"],
        )


if __name__ == "__main__":
    unittest.main()
