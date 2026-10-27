"""RED for AGE0d ambiguous thousands/decimal punctuation; no runtime authority."""
import unittest
from scripts.age0d_answer_audit import audit
from tests.test_age0d_answer_audit import FROZEN_ROWS
from scripts.age0d_answer_audit import score_cases


class LocaleAmbiguityReview(unittest.TestCase):
    def test_ambiguous_question_separators_abstain(self):
        for q in ('What is 1,234 + 1?', 'Berechne 1.234 + 1'):
            with self.subTest(q=q):
                self.assertEqual(audit(q, '1235')['status'], 'ABSTAIN')

    def test_ambiguous_answer_separators_abstain(self):
        for answer in ('4,000', '4.000'):
            with self.subTest(answer=answer):
                self.assertEqual(audit('What is 2+2?', answer)['status'], 'ABSTAIN')
        self.assertEqual(audit('What is 1234+0?', '1,234')['status'], 'ABSTAIN')

    def test_unambiguous_decimal_controls_and_frozen_rows(self):
        self.assertEqual(audit('What is 0.125 + 0.125?', '0.25')['status'], 'CORRECT')
        self.assertEqual(audit('Berechne 3,5 + 2,25', '5,75')['status'], 'CORRECT')
        self.assertEqual(audit('What is 2+2?', '4,0')['status'], 'CORRECT')
        self.assertEqual(score_cases(FROZEN_ROWS)['unexpected'], 0)


if __name__ == '__main__':
    unittest.main()
