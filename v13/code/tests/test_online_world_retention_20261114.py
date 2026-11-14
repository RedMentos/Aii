"""Synthetic two-phase T8 retention and replay regression; no native phone claims."""
import unittest
from v13.online_world_retention import evaluate_retention
from v13 import world_model


def row(i, prefix, shift=0.0):
    x = (i % 13) / 20
    return {"action_id": f"{prefix}-{i}", "s": [x, x/2, 0.2, 0.1],
            "y": [0.3 + x/3 + shift, 0.2 + x/4 + shift, 0.1 + x/5],
            "a": world_model.ACTIONS[i % len(world_model.ACTIONS)]}


class RetentionRegression(unittest.TestCase):
    def cohorts(self):
        return ([row(i, "old") for i in range(32)],
                [row(i, "new", 0.2) for i in range(32, 64)],
                [row(i, "old-test") for i in range(64, 72)],
                [row(i, "new-test", 0.2) for i in range(72, 80)])

    def test_forgetting_replay_restart(self):
        result = evaluate_retention(*self.cohorts())
        self.assertEqual(result["old_train_count"], 32)
        self.assertEqual(result["new_holdout_count"], 8)
        for label, steps in (("replay_off", 64), ("replay_on", 192)):
            metrics = result["ablations"][label]
            self.assertEqual(metrics["optimizer_steps"], steps)
            self.assertEqual(metrics["checkpoint_cursor_count"], 64)
            self.assertTrue(metrics["restart_verified"])
            self.assertAlmostEqual(
                metrics["old_forgetting_delta"],
                metrics["old_holdout_after_phase2"] - metrics["old_holdout_after_phase1"])
            self.assertAlmostEqual(
                metrics["new_learning_delta"],
                metrics["new_holdout_after_phase2"] - metrics["new_holdout_after_phase1"])

    def test_reject_cross_cohort_overlap(self):
        cohorts = self.cohorts()
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            evaluate_retention(cohorts[0], cohorts[1], cohorts[0], cohorts[3])

    def test_reject_empty_cohort(self):
        cohorts = self.cohorts()
        with self.assertRaises(ValueError):
            evaluate_retention(cohorts[0], [], cohorts[2], cohorts[3])

    def test_one_pass_iterables(self):
        cohorts = self.cohorts()
        result = evaluate_retention(*(iter(group) for group in cohorts))
        self.assertEqual(result["ablations"]["replay_off"]["checkpoint_cursor_count"], 64)


if __name__ == "__main__":
    unittest.main()
