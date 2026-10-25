"""Run347 RED-first: bounded per-action coverage policy under hunger constraint."""
import math
import random
import unittest
from v13 import sandbox as S


class DS2BoundedCoverageRun347(unittest.TestCase):
    def test_policy_is_registered(self):
        self.assertIn("lp_goal_coverage", S.POLICIES)

    def test_undercovered_pair_gets_exact_bounded_bonus(self):
        base = S.Agent("lp_goal", random.Random(11))
        covered = S.Agent("lp_goal_coverage", random.Random(11))
        delta = covered.value("stein", "push", .2) - base.value("stein", "push", .2)
        self.assertAlmostEqual(delta, .75, places=9)

    def test_coverage_bonus_expires_after_eight_visits(self):
        base = S.Agent("lp_goal", random.Random(12))
        covered = S.Agent("lp_goal_coverage", random.Random(12))
        base.visits[("stein", "push")] = 8
        covered.visits[("stein", "push")] = 8
        self.assertAlmostEqual(covered.value("stein", "push", .2),
                               base.value("stein", "push", .2), places=9)

    def test_hunger_gate_disables_extra_exploration_at_point_six(self):
        base = S.Agent("lp_goal", random.Random(13))
        covered = S.Agent("lp_goal_coverage", random.Random(13))
        self.assertAlmostEqual(covered.value("stein", "push", .60),
                               base.value("stein", "push", .60), places=9)

    def test_new_policy_is_deterministic_and_records_actual_new_kind(self):
        a = S.run("lp_goal_coverage", 501, steps=700, new_kind_at=300)
        b = S.run("lp_goal_coverage", 501, steps=700, new_kind_at=300)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a["new_kind_interactions"], 0)
        self.assertTrue(math.isfinite(a["new_kind_final_kl"]))


if __name__ == "__main__":
    unittest.main()
