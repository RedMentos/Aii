"""Review-only AGE0d exact result representability; no runtime correction authority."""
import unittest
from scripts.age0d_answer_audit import audit


class ExactRepresentabilityTests(unittest.TestCase):
    def test_unrepresentable_exact_results_abstain(self):
        cases = (
            ('What is 0.000000000001 * 0.000000000001?', '0'),
            ('What is 0.000000000001 / 2?', '0'),
            ('What is 999999999999 + 1?', '999999999999'),
            ('What is 1000000 * 1000000?', '0'),
        )
        for question, answer in cases:
            with self.subTest(question=question):
                report = audit(question, answer)
                self.assertEqual(report['status'], 'ABSTAIN')
                self.assertFalse(report['delivery_allowed'])
                self.assertEqual(report['authority'], 'NONE')

    def test_exact_representable_controls_remain_correct(self):
        cases = (
            ('What is 0.000000000001 * 2?', '0.000000000002'),
            ('What is 2 / 4?', '0.5'),
            ('What is 999999999999 - 1?', '999999999998'),
            ('Berechne 3,5 + 2,25', '5,75'),
        )
        for question, answer in cases:
            with self.subTest(question=question):
                self.assertEqual(audit(question, answer)['status'], 'CORRECT')

    def test_supported_wrong_answer_still_mismatch(self):
        report = audit('What is 2 * 3?', '5')
        self.assertEqual(report['status'], 'MISMATCH')
        self.assertFalse(report['delivery_allowed'])


if __name__ == '__main__':
    unittest.main()
