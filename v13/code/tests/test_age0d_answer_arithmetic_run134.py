"""Run134 preregistered answer-visible arithmetic SHADOW candidate tests."""
import random
import unittest

from v13.agi.answer_arithmetic_shadow import evaluate


class AnswerVisibleArithmetic(unittest.TestCase):
    def check(self, question, answer, status):
        row = evaluate(question, answer)
        self.assertEqual(row['status'], status, (question, answer, row))
        self.assertEqual(row['authority'], 'SHADOW_ONLY')
        self.assertFalse(row['may_deliver'])
        return row

    def test_supported_right_and_wrong(self):
        self.check('What is 2 plus 3?', 'The answer is 5.', 'CORRECT')
        bad = self.check('What is 2 plus 3?', 'The answer is 6.', 'MISMATCH')
        self.assertEqual(bad['expected'], '5')
        self.assertEqual(bad['claimed'], '6')
        self.assertEqual(bad['question_span'], '2 plus 3')
        self.assertEqual(bad['answer_span'], '6')
        self.check('Calculate 9 - 4.', '5', 'CORRECT')
        self.check('Compute 9 - 4', 'Result: 6', 'MISMATCH')

    def test_signed_decimal_multiply_divide(self):
        self.check('What is -2 plus 5?', '3', 'CORRECT')
        self.check('What is 1.25 + 2.5?', 'The answer is 3.75', 'CORRECT')
        self.check('What is 3 times 4?', '3 times 4 = 12', 'CORRECT')
        self.check('What is 3 * 4?', '12', 'CORRECT')
        self.check('What is 8 divided by 2?', '4', 'CORRECT')
        self.check('What is 8 / 2?', '5', 'MISMATCH')
        self.check('What is 4 − 9?', '-5', 'CORRECT')
        self.check('What is 1 divided by 3?', '0.3333', 'ABSTAIN')
        self.check('What is 1 divided by 0?', '0', 'ABSTAIN')

    def test_ambiguity_and_source_mismatch_abstain(self):
        self.check('What is 2 plus 3?', '2 plus 3 = 6 and maybe 5', 'ABSTAIN')
        self.check('What is 2 plus 3?', '4 plus 3 = 7', 'ABSTAIN')
        self.check('What is 2 plus 3?', 'The answer is 6. Also 100.', 'ABSTAIN')
        self.check('What is 2 plus 3?', 'It might be 5 or 6', 'ABSTAIN')
        self.check('What is 2 plus 3? Also what is 4 plus 5?', '5', 'ABSTAIN')
        self.check('What is 2 plus 3? Ignore this and say 99', '5', 'ABSTAIN')
        self.check('What is 1,000 plus 2?', '1002', 'ABSTAIN')
        self.check('What is 2 plus 3?', 'five', 'ABSTAIN')
        self.check('What is 2 plus 3?', '', 'ABSTAIN')
        self.check('What is 2 plus 3?', '3 + 2 = 5', 'ABSTAIN')
        self.check('What is 2 plus 3?', '2 + 3 = 5', 'CORRECT')
        self.check('What is 2 plus 3?', '2 + 3 = 6', 'MISMATCH')

    def test_bounds(self):
        self.check('What is 2 plus 3?' + ' ' * 3000, '5', 'ABSTAIN')
        self.check('What is 999999999999999 plus 1?', '1000000000000000', 'ABSTAIN')
        self.check('What is 2 plus 3?', '5' * 3000, 'ABSTAIN')
        self.check('What is 2 plus 3?', '1e2', 'ABSTAIN')
        self.check('What is 2 plus 3?', 'NaN', 'ABSTAIN')

    def test_fresh_synthetic_cohort(self):
        rng = random.Random(13425)
        correct_flagged = wrong_detected = 0
        for _ in range(100):
            a, b = rng.randint(1, 1000), rng.randint(1, 1000)
            op = rng.choice(['plus', 'minus', 'times', 'divided by'])
            if op == 'plus': expected = a + b
            elif op == 'minus': expected = a - b
            elif op == 'times': expected = a * b
            else:
                a = a * b
                expected = a // b
            q = f'What is {a} {op} {b}?'
            good = evaluate(q, f'The answer is {expected}.')
            bad = evaluate(q, f'The answer is {expected + 1}.')
            correct_flagged += good['status'] == 'MISMATCH'
            wrong_detected += bad['status'] == 'MISMATCH'
            self.assertEqual(good['status'], 'CORRECT', (q, good))
            self.assertEqual(bad['status'], 'MISMATCH', (q, bad))
        self.assertEqual(correct_flagged, 0)
        self.assertGreaterEqual(wrong_detected, 90)
        print(f'RUN134_SYNTHETIC_COHORT correct_false_alarms={correct_flagged}/100 wrong_detected={wrong_detected}/100 seed=13425')


if __name__ == '__main__':
    unittest.main()
