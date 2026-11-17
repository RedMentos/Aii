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

    def test_state_action_groups_never_cross_holdout(self):
        rows = self.rows(240)
        train, holdout = H.partition(rows)
        group = lambda r: (r["a"], tuple(r["s"]))
        self.assertFalse({group(r) for r in train} &
                         {group(r) for r in holdout})
        reversed_train, reversed_holdout = H.partition(list(reversed(rows)))
        self.assertEqual([r["action_id"] for r in train],
                         [r["action_id"] for r in reversed_train])
        self.assertEqual([r["action_id"] for r in holdout],
                         [r["action_id"] for r in reversed_holdout])

    def test_identical_state_group_never_leaks(self):
        rows = self.rows(120)
        rows[0]["s"] = list(rows[1]["s"])
        rows[0]["a"] = rows[1]["a"]
        train, holdout = H.partition(rows)
        self.assertEqual(
            rows[0]["action_id"] in {r["action_id"] for r in train},
            rows[1]["action_id"] in {r["action_id"] for r in train})

    def test_repeated_event_ids_do_not_fake_independent_holdout(self):
        # Many distinct T8 receipts can describe only a few distinct states.
        # Repetitions must not satisfy the independent holdout evidence gate.
        rows = self.rows(240)
        for i, row in enumerate(rows):
            row["s"] = [0.0, 0.0, 0.1, 0.2]
            row["a"] = world_model.ACTIONS[i % 2]
        report = H.evaluate_rows(rows)
        self.assertEqual(report["status"], "INSUFFICIENT_INDEPENDENT_T8_GROUPS")
        self.assertEqual(report["train_groups"] + report["holdout_groups"], 2)
        self.assertNotIn("utility_proven", report)

    def test_report_counts_independent_groups(self):
        report = H.evaluate_rows(self.rows(240))
        self.assertEqual(report["status"], "SYNTHETIC_OR_T8_OFFLINE_ONLY")
        self.assertLess(report["train_groups"], report["train"])
        self.assertLess(report["holdout_groups"], report["holdout"])

    def test_duplicate_fails_closed(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            H.partition(rows + [rows[0]])

    def test_numeric_updates_and_restart_and_ablation(self):
        report = H.evaluate_rows(self.rows())
        self.assertEqual(report["status"], "SYNTHETIC_OR_T8_OFFLINE_ONLY")
        self.assertGreater(report["train"], report["holdout"])
        self.assertGreaterEqual(report["frozen_action_mean_baseline_mse"], 0)
        self.assertEqual(
            report["predictor_beats_frozen_baseline"],
            report["replay"]["outcome_after_mse"] <
            report["frozen_outcome_baseline_mse"])
        self.assertEqual(
            report["utility_proven"],
            report["predictor_beats_frozen_baseline"] and
            report["replay"]["outcome_after_mse"] < report["replay"]["outcome_before_mse"] and
            report["replay"]["outcome_after_mse"] < report["nearest_state_outcome_baseline_mse"])
        for variant in ("replay", "no_replay"):
            self.assertGreater(report[variant]["numeric_updates"], 0)
            self.assertAlmostEqual(report[variant]["outcome_after_mse"],
                                   report[variant]["outcome_restart_mse"])
            self.assertAlmostEqual(
                report[variant]["early_train_delta_mse"],
                report[variant]["early_train_mse_after"] -
                report[variant]["early_train_mse_before"])
            self.assertAlmostEqual(
                report[variant]["early_forgetting_mse"],
                report[variant]["early_train_mse_after"] -
                report[variant]["early_after_initial_learning_mse"])
            self.assertAlmostEqual(
                report[variant]["early_holdout_retention_delta_mse"],
                report[variant]["early_holdout_mse_after_later"] -
                report[variant]["early_holdout_mse_after_initial"])
            self.assertAlmostEqual(report[variant]["after_mse"],
                                   report[variant]["restart_mse"])
        self.assertAlmostEqual(
            report["replay_minus_no_replay_early_forgetting_mse"],
            report["replay"]["early_forgetting_mse"] -
            report["no_replay"]["early_forgetting_mse"])
        self.assertAlmostEqual(
            report["replay_minus_no_replay_early_holdout_retention_delta_mse"],
            report["replay"]["early_holdout_retention_delta_mse"] -
            report["no_replay"]["early_holdout_retention_delta_mse"])
        self.assertGreater(report["python_peak_bytes"], 0)

    def test_frozen_baseline_copies_observed_state(self):
        # Synthetic targets encode unchanged state plus deterministic
        # action-specific outcomes. A frozen action/outcome baseline can
        # predict these perfectly without learning a state transition.
        # Penalizing it for not copying state would create false utility.
        report = H.evaluate_rows(self.rows())
        self.assertAlmostEqual(
            report["frozen_action_mean_baseline_mse"], 0.0, places=12)
        self.assertAlmostEqual(report["frozen_outcome_baseline_mse"], 0.0, places=12)
        self.assertFalse(report["predictor_beats_frozen_baseline"])
        self.assertFalse(report["utility_proven"])

    def test_state_dependent_outcomes_have_nontrivial_baselines(self):
        # Deterministic state-dependent target: an action-only mean is
        # insufficient. No holdout target enters either baseline's fit.
        rows = self.rows(160)
        for row in rows:
            state = row["s"][0]
            row["y"] = [0.1 + 0.5 * state, 0.8 - 0.2 * state,
                        0.3 + state * state]
        report = H.evaluate_rows(rows)
        self.assertGreater(report["frozen_outcome_baseline_mse"], 0)
        self.assertGreaterEqual(report["nearest_state_outcome_baseline_mse"], 0)
        self.assertEqual(
            report["utility_proven"],
            report["replay"]["outcome_after_mse"] <
            report["replay"]["outcome_before_mse"] and
            report["replay"]["outcome_after_mse"] <
            min(report["frozen_outcome_baseline_mse"],
                report["nearest_state_outcome_baseline_mse"]))

    def test_insufficient_evidence_not_promoted(self):
        report = H.evaluate_rows(self.rows(5))
        self.assertEqual(report["status"], "INSUFFICIENT_DISJOINT_T8")
        self.assertNotIn("utility_proven", report)


if __name__ == "__main__":
    unittest.main()
