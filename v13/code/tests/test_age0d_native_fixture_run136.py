"""Run136 native prereg fixture tests (no model or network)."""
import unittest
from v13.agi.answer_arithmetic_shadow import evaluate
from scripts.age0d_c3_native_eval_run136 import tasks, parse_answer, summarize

class NativeFixture(unittest.TestCase):
    def test_registered_fresh_60_tasks_deterministic(self):
        a=tasks();b=tasks()
        self.assertEqual(a,b)
        self.assertEqual(len(a),60)
        self.assertEqual({x['op'] for x in a},{'plus','minus','times','divided by'})
        self.assertEqual({op:sum(x['op']==op for x in a) for op in {'plus','minus','times','divided by'}},
                         {'plus':15,'minus':15,'times':15,'divided by':15})
        self.assertEqual(len({x['question'] for x in a}),60)
        for row in a:
            self.assertEqual(evaluate(row['question'],f"The answer is {row['truth']}.")['status'],'CORRECT')

    def test_independent_truth_parser(self):
        self.assertEqual(parse_answer('The answer is -12.'),'-12')
        self.assertEqual(parse_answer('4'),'4')
        self.assertEqual(parse_answer('The answer is -0.'),'0')
        self.assertIsNone(parse_answer('Maybe 4 or 5'))
        self.assertIsNone(parse_answer('Answer 5 and 6'))

    def test_summary_denominators_and_insufficient(self):
        rows=[{'truth':'5','parsed':'5','check':'CORRECT'},
              {'truth':'5','parsed':'6','check':'MISMATCH'},
              {'truth':'5','parsed':None,'check':'ABSTAIN'}]
        s=summarize(rows)
        self.assertEqual(s['correct_count'],1)
        self.assertEqual(s['wrong_count'],1)
        self.assertEqual(s['unknown_truth_count'],1)
        self.assertEqual(s['false_alarm_numerator'],0)
        self.assertEqual(s['wrong_detected'],1)
        self.assertEqual(s['thresholds']['K1'],'INSUFFICIENT')
        self.assertEqual(s['thresholds']['K2'],'INSUFFICIENT')
        self.assertEqual(s['thresholds']['K3'],'PASS')

if __name__=='__main__':unittest.main()
