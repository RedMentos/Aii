"""Run139 distinct fixed-seed C3 challenge cohort, model-free fixture tests."""
import unittest
from scripts.age0d_c3_challenge_run139 import tasks,SEED,SYSTEM
from v13.agi.answer_arithmetic_shadow import evaluate

class ChallengeFixture(unittest.TestCase):
    def test_fixed_new_cohort(self):
        a,b=tasks(),tasks()
        self.assertEqual(a,b)
        self.assertEqual(SEED,13925)
        self.assertEqual(len(a),80)
        self.assertEqual({op:sum(t['op']==op for t in a) for op in ('plus','minus','times','divided by')},
                         {'plus':10,'minus':20,'times':40,'divided by':10})
        self.assertEqual(len({t['question'] for t in a}),80)
        self.assertNotIn('<number>',SYSTEM)
        for t in a:
            self.assertEqual(evaluate(t['question'],f"The answer is {t['truth']}.")['status'],'CORRECT')

if __name__=='__main__':unittest.main()
