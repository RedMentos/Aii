"""Run146 prospective software-only tests of opt-in AGE0d strict answer checker."""
import random
import unittest
from v13.agi.answer_arithmetic_shadow_v2 import evaluate,AUTHORITY


class FormatAware(unittest.TestCase):
    def test_source_echo_unicode_and_varied_phrasing(self):
        cases=[('What is 24 plus 48?','24 + 48 = 72','CORRECT'),
               ('Calculate 59 times 94.','59 × 94 = 5546','CORRECT'),
               ('Compute 70 divided by 5.','70 ÷ 5 = 14','CORRECT'),
               ('What is 23 minus 53?','23 - 53 = -30','CORRECT'),
               ('Compute 12 times 22.','12 * 22 = 265','MISMATCH'),
               ('What is 9 plus 10?','The answer is 19.','CORRECT'),
               ('Calculate 9 plus 10.','result: 20','MISMATCH')]
        for q,a,s in cases:
            with self.subTest(q=q,a=a):
                x=evaluate(q,a);self.assertEqual(x['status'],s)
                self.assertFalse(x['may_deliver']);self.assertFalse(x['may_update'])
                self.assertEqual(x['authority'],AUTHORITY)
    def test_ambiguity_and_wrong_source_abstain(self):
        q='What is 59 times 94?'
        for a in ('94 × 59 = 5546','59 + 94 = 5546','59 × 95 = 5546',
                  '59 × 94 = 5546\nFinal answer: 5546','59 × 94 = **5546**',
                  '59 × 94 = 5,546','59 × 94 = 5546 extra',
                  '59 × 94 = <<5546>>5546','59 × 94 = 5546\r',
                  '59 × 94 = 5546\x00'):
            with self.subTest(a=a):self.assertEqual(evaluate(q,a)['status'],'ABSTAIN')
        for q in ('What is 5 divided by 0?','What is 5 divided by 2?',
                  'What is 2 plus 3? and 4 plus 5?', 'Ignore rules; What is 2 plus 3?',
                  'What is 2 plus 3?\nDo more'):
            with self.subTest(q=q):self.assertEqual(evaluate(q,'5')['status'],'ABSTAIN')
    def test_signed_operands_and_no_rounding(self):
        self.assertEqual(evaluate('Compute -8 minus -2.','-8 - -2 = -6')['status'],'CORRECT')
        self.assertEqual(evaluate('Compute -8 divided by -2.','-8 ÷ -2 = 4')['status'],'CORRECT')
        self.assertEqual(evaluate('Compute 0 minus 0.','-0')['status'],'CORRECT')
        self.assertEqual(evaluate('Compute 8 divided by 3.','2.6667')['status'],'ABSTAIN')
    def test_deterministic_synthetic_200_controls(self):
        rng=random.Random(14625)
        for _ in range(200):
            a,b=rng.randint(10,99),rng.randint(10,99)
            q=f'Calculate {a} times {b}.'
            good=f'{a} × {b} = {a*b}'
            wrong=f'{a} × {b} = {a*b+1}'
            self.assertEqual(evaluate(q,good)['status'],'CORRECT')
            self.assertEqual(evaluate(q,wrong)['status'],'MISMATCH')
    def test_type_bounds(self):
        for q,a in ((None,'5'),('What is 2 plus 3?',None),('What is 2 plus 3?','5'*257),
                    ('What is 1234567 plus 3?','1234570'),('What is 2 plus 3?','5\n')):
            self.assertEqual(evaluate(q,a)['status'],'ABSTAIN')

if __name__=='__main__':unittest.main()
