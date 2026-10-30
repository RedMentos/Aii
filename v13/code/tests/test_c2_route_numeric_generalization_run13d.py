"""Run13D frozen C2 route-word transfer; synthetic learning, no active head."""
import unittest

from scripts import c2_route_numeric_generalization_run13d as R
from v13 import route_words as v1
from v13 import route_words_numeric_candidate as v2


class C2NumericGeneralizationRun13D(unittest.TestCase):
    def test_frozen_cohort_is_disjoint_balanced_and_revision_separated(self):
        data = R.cohort()
        self.assertEqual(R.COHORT_SHA256,
                         "563f530aac86a1e4ab5314d0833538ffe3587013742951e5a1cf9474a60c6140")
        self.assertEqual(len(data["train"]), 32)
        self.assertEqual(len(data["holdout"]), 32)
        self.assertEqual({y for _, y in data["train"]}, set(range(4)))
        self.assertEqual({y for _, y in data["holdout"]}, set(range(4)))
        self.assertEqual([sum(y == i for _, y in data["train"])
                          for i in range(4)], [8] * 4)
        self.assertNotEqual(v1.REVISION, v2.REVISION)
        self.assertNotEqual(v1.vector("half 7 please"),
                            v1.vector("half 7000000 please"))
        self.assertEqual(v2.vector("half 7 please"),
                         v2.vector("half 7000000 please"))

    def test_actual_numpy_training_reports_both_heads_and_negative_control(self):
        result = R.run()
        self.assertEqual(result["schema"], R.SCHEMA)
        self.assertEqual(result["evidence"],
                         "SYNTHETIC_WORD_CHANNEL_LEARNING_NOT_NATIVE")
        self.assertEqual(result["cohort_sha256"], R.COHORT_SHA256)
        self.assertNotEqual(result["v1"]["revision"], result["v2"]["revision"])
        for name in ("v1", "v2", "deranged_label_control"):
            metrics = result[name]
            self.assertTrue(metrics["gradient_check"], name)
            self.assertTrue(metrics["deterministic_repeat"], name)
            self.assertTrue(metrics["checkpoint_reload"], name)
            self.assertTrue(metrics["finite"], name)
            self.assertEqual(metrics["optimizer_steps"], 80)
            for split in ("train", "holdout"):
                self.assertEqual(metrics[split]["n"], 32)
                self.assertEqual(len(metrics[split]["confusion"]), 4)
                self.assertEqual(sum(map(sum, metrics[split]["confusion"])), 32)
                self.assertEqual(sum(metrics[split]["confusion"][i][i]
                                     for i in range(4)),
                                 metrics[split]["correct"])
        self.assertEqual(result["prospective_signal_not_gate"], (
            result["v2"]["holdout"]["correct"] >=
            result["v1"]["holdout"]["correct"] + 4 and
            result["v2"]["train"]["accuracy"] >=
            result["v1"]["train"]["accuracy"] - .05))
        for key, value in {
            "model_called": False, "native_calls": 0,
            "active_head_modified": False, "source_cohorts_modified": False,
            "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
            "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False,
        }.items():
            self.assertEqual(result[key], value)

    def test_repeated_synthetic_training_is_exactly_deterministic(self):
        first = R.run()
        second = R.run()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
