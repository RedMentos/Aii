"""Adversarial source-only Run488 answer->oracle rescore tests."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(HERE))
import run488_native378_independent_rescore as mod


class Native378RescoreTests(unittest.TestCase):
    def answer(self, name):
        return json.dumps(mod.oracle(name), sort_keys=True)

    def row(self, name='Alder'):
        answer = self.answer(name)
        return {'fixture': name, 'variant': 'both_exact', 'status': 'RECORDED',
                'oracle_visible_to_native': False, 'answer': answer,
                'score': mod.score_answer(answer, mod.oracle(name))}

    def test_six_distinct_oracles_and_revision_precedence(self):
        expected = {'Alder': 'A', 'Beacon': 'B', 'Cypress': 'B',
                    'Delta': 'B', 'Ember': 'A', 'Fable': 'NONE'}
        self.assertEqual({name: mod.oracle(name)['action'] for name in mod.SPECS}, expected)
        self.assertEqual(mod.oracle('Delta')['options'][0]['remaining'], 30)
        self.assertEqual(mod.oracle('Ember')['options'][0]['remaining'], 35)

    def test_perfect_rows_and_reversed_options(self):
        for name in mod.SPECS:
            with self.subTest(name=name):
                row = self.row(name)
                self.assertEqual(mod.verify_row(row, name), 1.0)
                obj = json.loads(row['answer'])
                obj['options'].reverse()
                self.assertEqual(mod.score_answer(json.dumps(obj), mod.oracle(name))['utility'], 1.0)

    def test_wrong_action_only_is_11_of_12(self):
        obj = mod.oracle('Alder')
        obj['action'] = 'B'
        result = mod.score_answer(json.dumps(obj), mod.oracle('Alder'))
        self.assertEqual(result['utility'], 11/12)
        self.assertEqual(result['contradictions'], ['action'])

    def test_boolean_int_is_not_correct(self):
        obj = mod.oracle('Alder')
        obj['options'][0]['local'] = 1
        result = mod.score_answer(json.dumps(obj), mod.oracle('Alder'))
        self.assertEqual(result['utility'], 11/12)
        self.assertFalse(result['field_checks']['A.local'])

    def test_invalid_duplicate_json_key_fails_closed(self):
        answer = '{"project":"Alder","project":"Alder","action":"A","options":[]}'
        result = mod.score_answer(answer, mod.oracle('Alder'))
        self.assertEqual(result['utility'], 0)
        self.assertEqual(result['contradictions'], ['invalid:duplicate JSON key'])

    def test_wrong_stored_score_rejected(self):
        row = self.row()
        row['score']['utility'] = 0.5
        with self.assertRaisesRegex(ValueError, 'ANSWER_UTILITY_SCORE_MISMATCH'):
            mod.verify_row(row, 'Alder')

    def test_wrong_stored_field_checks_rejected(self):
        row = self.row()
        row['score']['field_checks']['A.cost'] = False
        with self.assertRaisesRegex(ValueError, 'ANSWER_FIELD_CHECKS_MISMATCH'):
            mod.verify_row(row, 'Alder')

    def test_answer_swap_and_missing_raw_rejected(self):
        row = self.row()
        row['answer'] = self.answer('Beacon')
        with self.assertRaisesRegex(ValueError, 'ANSWER_UTILITY_SCORE_MISMATCH|ANSWER_FIELD_CHECKS_MISMATCH'):
            mod.verify_row(row, 'Alder')
        row = self.row()
        del row['answer']
        with self.assertRaisesRegex(ValueError, 'RAW_ANSWER_MISSING'):
            mod.verify_row(row, 'Alder')

    def test_oracle_visibility_or_row_status_rejected(self):
        for key, value in [('oracle_visible_to_native', True), ('status', 'ERROR'),
                           ('fixture', 'Beacon')]:
            row = self.row()
            row[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ROW_IDENTITY_OR_LEAK'):
                mod.verify_row(row, 'Alder')

    def test_score_schema_mismatch_rejected(self):
        row = self.row()
        row['score']['bonus'] = True
        with self.assertRaisesRegex(ValueError, 'SCORE_FIELDS_CHANGED'):
            mod.verify_row(row, 'Alder')


if __name__ == '__main__':
    unittest.main()
