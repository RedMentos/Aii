"""Run147 prospective fixture and bounded independent format label tests."""
import unittest
from scripts.age0d_c3_varied_run147 import tasks,label_answer,summarize,SEED,SYSTEM,EXCLUDED_PRIOR
from v13.agi.answer_arithmetic_shadow_v2 import evaluate

class Run147Fixture(unittest.TestCase):
    def test_fresh_96_and_fixed_prompt(self):
        a=tasks();self.assertEqual(a,tasks());self.assertEqual(SEED,14725)
        self.assertEqual(len(a),96);self.assertEqual(len({x['question'] for x in a}),96)
        self.assertFalse({x['question'] for x in a}&EXCLUDED_PRIOR)
        self.assertNotIn(' N.',SYSTEM);self.assertNotIn('<number>',SYSTEM)
        for op in ('plus','minus','times','divided by'):
            for phrasing in ('What is','Calculate','Compute'):
                self.assertEqual(sum(x['op']==op and x['phrasing']==phrasing for x in a),8)
        for x in a:self.assertEqual(evaluate(x['question'],x['truth'])['status'],'CORRECT')
    def test_independent_label_formats_and_ambiguity(self):
        for s,v in [('12 × 13 = 156','156'),('12 * 13 = 155','155'),('The answer is 12.','12'),
                    ('Result: -5','-5'),('12 ÷ 3 = 4','4')]:
            self.assertEqual(label_answer(s),v)
        for s in ['12 × 13 = **156**','12 × 13 = 156\nFinal: 156','12 × 13 = 156 extra',
                  '12 × 13 = 1,56','<number>','N','12 × 13 = 156\r']:
            self.assertIsNone(label_answer(s),s)
    def test_thresholds_preserve_insufficient_and_gate(self):
        a=[dict(id=i,phrasing='What is',truth='5',label=None,new_check='ABSTAIN',old_check='ABSTAIN') for i in range(96)]
        x=summarize(a);self.assertEqual((x['K1'],x['K2'],x['K3']),('INSUFFICIENT','INSUFFICIENT','FAIL'))
        self.assertEqual(x['gate'],'UNVERIFIED')
        for i in range(12):a[i].update(label='5',new_check='CORRECT')
        for i in range(12,24):a[i].update(label='4',new_check='MISMATCH')
        x=summarize(a);self.assertEqual(x['K1'],'PASS');self.assertEqual(x['K2'],'PASS')
        self.assertEqual(x['K3'],'FAIL');self.assertEqual(x['gate'],'UNVERIFIED')
        a[95]['error']='TimeoutError'
        x=summarize(a);self.assertEqual((x['K1'],x['K2'],x['K3']),('INSUFFICIENT','INSUFFICIENT','FAIL'))

if __name__=='__main__':unittest.main()
