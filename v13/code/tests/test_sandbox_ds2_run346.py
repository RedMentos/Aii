"""Run346 preregistered DS2 telemetry and policy semantics, lab only."""
import math
import random
import unittest

from v13 import sandbox as S


class DS2TelemetryRun346(unittest.TestCase):
    def test_new_kind_telemetry_is_observed_and_finite(self):
        result = S.run("lp_goal_novelty", 401, steps=700, new_kind_at=300)
        self.assertIn("new_kind_interactions", result)
        self.assertIn("new_kind_final_kl", result)
        self.assertIs(type(result["new_kind_interactions"]), int)
        self.assertGreaterEqual(result["new_kind_interactions"], 0)
        self.assertTrue(math.isfinite(result["new_kind_final_kl"]))
        self.assertGreaterEqual(result["new_kind_final_kl"], 0)

    def test_no_new_kind_has_no_fabricated_measurement(self):
        result = S.run("lp_goal_novelty", 402, steps=400, new_kind_at=None)
        self.assertEqual(result["new_kind_interactions"], 0)
        self.assertIsNone(result["new_kind_final_kl"])

    def test_new_kind_telemetry_is_seed_deterministic(self):
        a = S.run("lp_goal_novelty", 403, steps=650, new_kind_at=250)
        b = S.run("lp_goal_novelty", 403, steps=650, new_kind_at=250)
        self.assertEqual(a, b)

    def test_word_novelty_is_only_in_combined_policy(self):
        combined = S.Agent("lp_goal_novelty", random.Random(7))
        before = combined.value(S.NEW_KIND, "touch", 0)
        combined.word_visits[S.NEW_KIND] = 100
        after = combined.value(S.NEW_KIND, "touch", 0)
        self.assertGreater(before, after)
        goal_only = S.Agent("lp_goal", random.Random(7))
        v0 = goal_only.value(S.NEW_KIND, "touch", 0)
        goal_only.word_visits[S.NEW_KIND] = 100
        self.assertEqual(v0, goal_only.value(S.NEW_KIND, "touch", 0))

    def test_hunger_goal_rewards_expected_eating(self):
        agent = S.Agent("lp_goal_novelty", random.Random(9))
        self.assertGreater(agent.value("apfel", "eat", 1.0),
                           agent.value("apfel", "eat", 0.0))


if __name__ == "__main__":
    unittest.main()
