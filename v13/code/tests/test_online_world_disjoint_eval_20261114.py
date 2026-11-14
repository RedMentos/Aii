"""Offline-only disjoint holdout, replay ablation, restart tests."""
import unittest
from v13.online_world_evaluation import evaluate_disjoint
from v13 import world_model


def row(i, prefix):
    x = (i % 17) / 20
    return {"action_id": f"{prefix}-{i}", "s": [x, x/2, 0.2, 0.1],
            "y": [0.3 + x/3, 0.2 + x/4, 0.1 + x/5],
            "a": world_model.ACTIONS[i % len(world_model.ACTIONS)]}


class DisjointRetentionTests(unittest.TestCase):
    def test_before_after_replay_ablation_and_restart(self):
        result = evaluate_disjoint(
            [row(i, "train") for i in range(60)],
            [row(i, "holdout") for i in range(60, 80)])
        self.assertTrue(result["disjoint_action_ids"])
        self.assertEqual(result["train_count"], 60)
        self.assertEqual(result["holdout_count"], 20)
        for label, steps in (("replay_off", 60), ("replay_on", 180)):
            part = result["ablations"][label]
            self.assertEqual(part["trained"], 60)
            self.assertEqual(part["optimizer_steps"], steps)
            self.assertEqual(part["checkpoint_cursor_count"], 60)
            self.assertAlmostEqual(part["holdout_mse_after"],
                                   part["restart_holdout_mse"], places=12)
            self.assertTrue(part["holdout_mse_before"] >= 0)

    def test_holdout_overlap_rejected_before_learning(self):
        train = [row(1, "same")]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            evaluate_disjoint(train, train)

    def test_duplicate_train_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_disjoint([row(1, "x"), row(1, "x")], [row(2, "y")])

    def test_empty_cohort_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_disjoint([], [row(2, "y")])


if __name__ == "__main__":
    unittest.main()
