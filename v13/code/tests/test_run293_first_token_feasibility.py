"""Run293: frozen actual-native 19-case output feasibility, no gate promotion."""
import json
from pathlib import Path
import unittest

import numpy as np

from v13.output_adapter_worker import first_token_feasibility


FIXTURE = Path(__file__).parent / "fixtures" / "run293_native_output_feasibility.json"


class Run293FirstTokenFeasibility(unittest.TestCase):
    def test_frozen_native_cohort_is_mathematically_below_unchanged_gate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "V13_RUN293_PINNED_NATIVE_LOGPROB_FEASIBILITY_V1")
        self.assertEqual(fixture["original_features_gzip_sha256"],
                         "23494e10dc101ab59b020c227a3e38815c77996d34f2f03d3d1abb2d4de89d58")
        rows = fixture["rows"]
        self.assertEqual([r["original_index"] for r in rows],
                         [3, 9, 10, 18, 32, 38, 48, 49, 50, 63, 72, 79, 88, 92, 98, 108, 112, 118, 119])
        base = np.asarray([r["base_log_probabilities"] for r in rows], dtype=float)
        y = np.asarray([r["target_index"] for r in rows], dtype=int)
        cap = fixture["max_bias"]
        result = first_token_feasibility(base, y, cap, fixture["native_token_ids"])
        self.assertEqual(result["n"], 19)
        self.assertEqual(result["feasible_count"], 13)
        self.assertEqual(result["infeasible_count"], 6)
        self.assertAlmostEqual(result["accuracy_upper_bound"], 13 / 19)
        self.assertLess(result["accuracy_upper_bound"], 0.8)
        self.assertEqual(result["per_native_token"]["549"]["feasible_count"], 13)
        self.assertEqual(result["per_native_token"]["20751"]["feasible_count"], 0)
        self.assertLess(result["per_native_token"]["20751"]["target_probability_ceiling_max"], 0.15)
        # Independent scalar replay of the optimistic logits: no matrix or
        # training objective shared with the implementation under test.
        scalar = []
        for row in rows:
            logits = row["base_log_probabilities"][:]
            target = row["target_index"]
            optimistic = [v + cap if j == target else v - cap if j < 2 else v
                          for j, v in enumerate(logits)]
            scalar.append(optimistic[target] >= max(v for j, v in enumerate(optimistic) if j != target))
        self.assertEqual(sum(scalar), 13)
        self.assertEqual(scalar, [r["target_index"] == 0 for r in rows])

    def test_synthetic_feasible_and_infeasible_competitors(self):
        b = np.log(np.asarray([[0.5, 0.2, 0.3], [0.01, 0.01, 0.98]], dtype=float))
        r = first_token_feasibility(b, np.asarray([0, 1]), 2, [549, 20751])
        self.assertEqual(r["feasible_count"], 1)
        self.assertEqual(r["infeasible_count"], 1)
        self.assertEqual(r["per_native_token"]["549"]["feasible_count"], 1)
        self.assertEqual(r["per_native_token"]["20751"]["feasible_count"], 0)

    def test_ties_are_counted_as_feasible_for_conservative_upper_bound(self):
        r = first_token_feasibility(np.zeros((1, 3)), np.asarray([0]), 0, [1, 2])
        self.assertEqual(r["feasible_count"], 1)

    def test_malformed_baselines_and_labels_rejected(self):
        with self.assertRaises(ValueError):
            first_token_feasibility([[float("nan"), 0, 0]], [0], 12)
        with self.assertRaises(ValueError):
            first_token_feasibility([[0, 0, 0]], [2], 12)
        with self.assertRaises(ValueError):
            first_token_feasibility([[0, 0, 0]], [0], float("inf"))
        with self.assertRaises(ValueError):
            first_token_feasibility([[0, 0, 0]], [0], 12, [549, 549])


if __name__ == "__main__":
    unittest.main()
