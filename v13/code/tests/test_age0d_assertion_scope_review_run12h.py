"""Run12H independent Age0d assertion-scope negative review (synthetic only).

These examples are *not* real model-answer calibration and confer no authority.
"""
import unittest
from v13 import age0d_answer_arithmetic_shadow_run12f as a


class AssertionScopeReviewRun12H(unittest.TestCase):
    def assert_no_authority(self, result):
        self.assertEqual(result['authority'], 'SHADOW_ONLY_NO_DELIVERY')
        for key in ('delivery_allowed', 'learning_allowed', 'age_promotion',
                    'whole_answer_verified'):
            self.assertIs(result[key], False)

    def test_non_assertions_must_abstain(self):
        cases = (
            'It is not true that 2 + 2 = 5.',
            '2 + 2 = 5 is untrue.',
            'It is never correct that 2 + 2 = 5.',
            'If 2 + 2 = 5, arithmetic would collapse.',
            'Suppose 2 + 2 = 5 for the sake of argument.',
            'Assuming 2 + 2 = 5, the premise is inconsistent.',
            'What if 2 + 2 = 5?',
            'Is 2 + 2 = 5?',
            '2 + 2 = 5?',
            '2 + 2 != 5; the proposed equation is not valid.',
            '2 + 2 ≠ 5; the claim is false.',
            'Es stimmt nicht, dass 2 + 2 = 5.',
            'Wenn 2 + 2 = 5 wäre, wäre die Prämisse falsch.',
            'Angenommen, 2 + 2 = 5, dann wäre das ein Widerspruch.',
            'Die Gleichung 2 + 2 = 5 ist unwahr.',
            '2 + 2 = 5 is hypothetical, not a factual result.',
        )
        for answer in cases:
            with self.subTest(answer=answer):
                result = a.inspect('Review the statement', answer)
                self.assertEqual(result['status'], 'ABSTAIN')
                self.assert_no_authority(result)

    def test_asserted_mismatches_still_detected_shadow_only(self):
        for answer in ('2 + 2 = 5.', '7 * 3 = 20.', '2 + 2 = 4, 7 * 3 = 20.'):
            with self.subTest(answer=answer):
                result = a.inspect('Check the arithmetic', answer)
                self.assertEqual(result['status'], 'POSSIBLE_ARITHMETIC_ERROR_SHADOW')
                self.assert_no_authority(result)

    def test_plain_correct_equations_still_consistent(self):
        result = a.inspect('Check the arithmetic', '2 + 2 = 4, 7 * 3 = 21.')
        self.assertEqual(result['status'], 'LOCAL_ARITHMETIC_CONSISTENT')
        self.assert_no_authority(result)

    def test_bare_integer_pair_unaffected(self):
        self.assertEqual(a.inspect('What is 2 + 2?', '5')['status'],
                         'POSSIBLE_ARITHMETIC_ERROR_SHADOW')
        self.assertEqual(a.inspect('What is 2 + 2?', '4')['status'],
                         'LOCAL_ARITHMETIC_CONSISTENT')


if __name__ == '__main__':
    unittest.main()
