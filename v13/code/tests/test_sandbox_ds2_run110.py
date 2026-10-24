"""Run110 WP-DS2 preregistered lab-only policy semantics and DS1 retention."""
import math
import random
import unittest

from v13 import sandbox as S


class DS2PolicyTests(unittest.TestCase):
    def test_new_policies_are_explicit_and_no_native_runtime_authority(self):
        self.assertIn('lp_goal', S.POLICIES)
        self.assertIn('lp_goal_novelty', S.POLICIES)
        self.assertEqual(S.Agent('lp_goal', random.Random(1)).policy, 'lp_goal')
        self.assertEqual(S.Agent('lp_goal_novelty', random.Random(1)).policy, 'lp_goal_novelty')

    def test_combination_equals_existing_lp_plus_existing_goal(self):
        agent = S.Agent('lp_goal', random.Random(1))
        base = S.Agent('lp', random.Random(1))
        word, action, hunger = 'apfel', 'eat', .6
        intrinsic = base.value(word, action, hunger)
        pragmatic = S.PRAGMATIC * hunger * S.predictive(agent.counts(word, action))[S.OUTCOMES.index('EATEN')] * S.HUNGER_RELIEF[word]
        self.assertAlmostEqual(agent.value(word, action, hunger), intrinsic + pragmatic, 12)

    def test_word_novelty_modulator_is_generic_and_decays(self):
        goal = S.Agent('lp_goal', random.Random(1))
        novel = S.Agent('lp_goal_novelty', random.Random(1))
        for word in ('pilz', 'apfel', 'new_unknown_word'):
            before = novel.value(word, 'touch', .4) - goal.value(word, 'touch', .4)
            self.assertAlmostEqual(before, S.WORD_NOVELTY_GAIN, 12)
            goal.observe(word, 'touch', 0)
            novel.observe(word, 'touch', 0)
            after = novel.value(word, 'touch', .4) - goal.value(word, 'touch', .4)
            self.assertAlmostEqual(after, S.WORD_NOVELTY_GAIN / math.sqrt(2), 12)

    def test_policy_does_not_look_up_hidden_true_table(self):
        goal = S.Agent('lp_goal_novelty', random.Random(3))
        original = S.TRUE
        try:
            S.TRUE = None
            self.assertGreater(goal.value('pilz', 'touch', .6), 0)
        finally:
            S.TRUE = original

    def test_new_policies_run_deterministically_and_keep_ds1_outputs(self):
        for policy in ('lp_goal', 'lp_goal_novelty'):
            a = S.run(policy, 7, steps=250, new_kind_at=100)
            b = S.run(policy, 7, steps=250, new_kind_at=100)
            self.assertEqual(a, b)
            self.assertEqual(a['steps'], 250)
            self.assertGreater(a['interactions'], 0)
        self.assertEqual(S.Agent('lp', random.Random(1)).value('apfel', 'eat', .7), S.NOVELTY)
        self.assertEqual(S.Agent('novelty', random.Random(1)).value('apfel', 'eat', .7), 1.)


if __name__ == '__main__':
    unittest.main()
