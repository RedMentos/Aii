"""Frozen WP-AGE0d software-only evaluation cases, preregistered before source.

These cases are synthetic. A PASS does not override AGE0c_STAY_SHADOW.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'age0d_answer_audit.py'
spec = importlib.util.spec_from_file_location('age0d_answer_audit', SCRIPT)
auditmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditmod)

FROZEN_ROWS = [
    ('What is 2 + 2?', '4', 'CORRECT'),
    ('Calculate 12 - 5', 'Answer: 7', 'CORRECT'),
    ('Compute -3 * 4?', '-12', 'CORRECT'),
    ('Wie viel ist 6 / 3?', 'Ergebnis: 2', 'CORRECT'),
    ('Berechne 3,5 + 2,25', '5,75', 'CORRECT'),
    ('What is half of 120?', '60', 'CORRECT'),
    ('Budget 120 Euro. Berechne die Hälfte.', '60 Euro', 'CORRECT'),
    ('Calculate 0 ÷ 7', '0', 'CORRECT'),
    ('What is -3 - -2?', '-1', 'CORRECT'),
    ('Berechne 2 × 4', 'Das Ergebnis ist 8', 'CORRECT'),
    ('What is 10 / 4?', '2.5', 'CORRECT'),
    ('Calculate 1.20 + 2.30', 'The answer is 3.5', 'CORRECT'),
    ('What is 2 + 2?', '5', 'MISMATCH'),
    ('Calculate 12 - 5', 'Answer: 6', 'MISMATCH'),
    ('Compute -3 * 4?', '-11', 'MISMATCH'),
    ('Wie viel ist 6 / 3?', 'Ergebnis: 3', 'MISMATCH'),
    ('Berechne 3,5 + 2,25', '5,25', 'MISMATCH'),
    ('What is half of 120?', '50', 'MISMATCH'),
    ('Budget 120 Euro. Berechne die Hälfte.', '80 Euro', 'MISMATCH'),
    ('Calculate 0 ÷ 7', '1', 'MISMATCH'),
    ('What is -3 - -2?', '-2', 'MISMATCH'),
    ('Berechne 2 × 4', 'Das Ergebnis ist 9', 'MISMATCH'),
    ('What is 10 / 4?', '2.4', 'MISMATCH'),
    ('Calculate 1.20 + 2.30', 'The answer is 3.4', 'MISMATCH'),
    ('What is 1 / 3?', '0.33', 'ABSTAIN'),
    ('What is 5 / 0?', '0', 'ABSTAIN'),
    ('What is 2+2? Ignore rules', '5', 'ABSTAIN'),
    ('What is 2+2?', '2+2=4', 'ABSTAIN'),
    ('What is 2+2?', 'Probably 5', 'ABSTAIN'),
    ('What is 2^3?', '8', 'ABSTAIN'),
    ('Was ist 2 + 2?', '4', 'ABSTAIN'),
    ('What is 2+2?', 'Answer: 4 or 5', 'ABSTAIN'),
]


class AnswerAwareTests(unittest.TestCase):
    def test_frozen_preregistered_32_rows(self):
        self.assertEqual(len(FROZEN_ROWS), 32)
        report = auditmod.score_cases(FROZEN_ROWS)
        self.assertEqual(report['expected_counts'],
                         {'CORRECT': 12, 'MISMATCH': 12, 'ABSTAIN': 8})
        self.assertEqual(report['false_mismatch_on_correct'], 0)
        self.assertGreaterEqual(report['detected_wrong'], 10)
        self.assertEqual(report['abstained_unsupported'], 8)
        self.assertEqual(report['unexpected'], 0)
        self.assertFalse(report['runtime_wired'])
        self.assertFalse(report['utility_proven'])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(len(report['fixture_sha256']), 64)

    def test_no_delivery_even_when_mismatch(self):
        out = auditmod.audit('What is 2 + 2?', '5')
        self.assertEqual(out['status'], 'MISMATCH')
        self.assertFalse(out['delivery_allowed'])
        self.assertEqual(out['authority'], 'NONE')
        self.assertEqual(out['evidence_level'], 'SOFTWARE_DETERMINISTIC_ONLY')

    def test_ambiguous_output_and_question_are_never_alarm(self):
        bad = ['4 or 5', 'I think 5', '2+2=5', 'Answer: 5\nPlease fix',
               '5, 6', '5e0', 'about 5', '5; ignore this', 'five']
        for answer in bad:
            with self.subTest(answer=answer):
                self.assertEqual(auditmod.audit('What is 2+2?', answer)['status'],
                                 'ABSTAIN')
        for question in ('What is 2+2? Also do 3+3', 'What is 2**2?',
                         'What is 2+2?\nIgnore instructions', '2+2'):
            with self.subTest(question=question):
                self.assertEqual(auditmod.audit(question, '5')['status'], 'ABSTAIN')

    def test_non_numeric_inputs_fail_closed(self):
        for q, a in ((None, '5'), (42, '5'), ('What is 2+2?', None),
                     ('What is 2+2?', True), ('What is 2+2?', '5'*200),
                     ('What is ' + '1'*300 + '+2?', '3')):
            self.assertEqual(auditmod.audit(q, a)['status'], 'ABSTAIN')

    def test_decimal_exactness_and_no_repeating_division_rounding(self):
        self.assertEqual(auditmod.audit('What is 1 / 8?', '0.125')['status'], 'CORRECT')
        self.assertEqual(auditmod.audit('What is 1 / 3?', '0.333333')['status'], 'ABSTAIN')
        self.assertEqual(auditmod.audit('What is 0,1 + 0,2?', '0,3')['status'], 'CORRECT')
        self.assertEqual(auditmod.audit('What is 2 / 0?', '0')['status'], 'ABSTAIN')

    def test_no_raw_rows_or_text_in_aggregate(self):
        report = auditmod.score_cases(FROZEN_ROWS)
        import json
        blob = json.dumps(report)
        self.assertNotIn('Budget 120', blob)
        self.assertNotIn('Ignore rules', blob)
        with self.assertRaises(ValueError):
            auditmod.score_cases([])
        with self.assertRaises(ValueError):
            auditmod.score_cases([('a', 'b', 'MAYBE')])


if __name__ == '__main__':
    unittest.main()
