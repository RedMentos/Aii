"""Disjoint T8 predictor evaluation; synthetic evidence only."""
import unittest
from v13 import online_world_holdout as H
from v13 import world_model


class HoldoutTests(unittest.TestCase):
    @staticmethod
    def rows(n=120):
        actions = world_model.ACTIONS
        return [
            {"action_id": "t8-%03d" % i,
             "s": [i % 7 / 10, 0.0, 0.1, 0.2],
             "a": actions[i % len(actions)],
             "y": [0.2 + (i % len(actions)) / 10, 1.0, 0.3]}
            for i in range(n)]

    def test_partition_disjoint_and_order_invariant(self):
        rows = self.rows()
        a, b = H.partition(rows)
        c, d = H.partition(list(reversed(rows)))
        self.assertFalse(set(x["action_id"] for x in a) &
                         set(x["action_id"] for x in b))
        self.assertEqual({x["action_id"] for x in a},
                         {x["action_id"] for x in c})
        self.assertEqual({x["action_id"] for x in b},
                         {x["action_id"] for x in d})

    def test_duplicate_fails_closed(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            H.partition(rows + [rows[0]])

    def test_numeric_updates_and_restart_and_ablation(self):
        report = H.evaluate_rows(self.rows())
        self.assertEqual(report["status"], "SYNTHETIC_OR_T8_OFFLINE_ONLY")
        self.assertGreater(report["train"], report["holdout"])
        for variant in ("replay", "no_replay"):
            self.assertGreater(report[variant]["numeric_updates"], 0)
            self.assertAlmostEqual(
                report[variant]["early_train_delta_mse"],
                report[variant]["early_train_mse_after"] -
                report[variant]["early_train_mse_before"])
            self.assertAlmostEqual(report[variant]["after_mse"],
                                   report[variant]["restart_mse"])
        self.assertGreater(report["python_peak_bytes"], 0)

    def test_insufficient_evidence_not_promoted(self):
        report = H.evaluate_rows(self.rows(5))
        self.assertEqual(report["status"], "INSUFFICIENT_DISJOINT_T8")
        self.assertNotIn("utility_proven", report)


if __name__ == "__main__":
    unittest.main()
