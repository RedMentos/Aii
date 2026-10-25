"""Run142 fresh no-placeholder native cohort prereg fixture."""
import unittest
from scripts.age0d_c3_noplaceholder_run142 import tasks,SEED,SYSTEM
from v13.agi.answer_arithmetic_shadow import evaluate

class NoPlaceholderFixture(unittest.TestCase):
    def test_fresh_80_tasks_and_prompt(self):
        a,b=tasks(),tasks()
        self.assertEqual(a,b)
        self.assertEqual(SEED,14225)
        self.assertEqual(len(a),80)
        self.assertEqual(len({t['question'] for t in a}),80)
        self.assertEqual({op:sum(t['op']==op for t in a) for op in ('plus','minus','times','divided by')},
                         {'plus':10,'minus':20,'times':40,'divided by':10})
        self.assertEqual(SYSTEM,'You are a calculator. For each question, output a single decimal integer representing the arithmetic result.')
        for t in a:
            self.assertEqual(evaluate(t['question'],f"The answer is {t['truth']}.")['status'],'CORRECT')

if __name__=='__main__':unittest.main()
