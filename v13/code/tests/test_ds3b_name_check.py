"""WP-DS3b entity uncertainty and answer<->tool cross-check on synthetic rows (no models)."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import ds3b_name_check as D  # noqa: E402

COMPARE = ('Monthly rainfall in millimetres: Cork 300, Lyon 700, Graz 450. Which city had the most rain, and how many '
           'millimetres more than the city with the least?')
SUMMARY = ('Expense report. Items: cables 20 euros, snacks 30 euros. Summary line at the bottom: "Total: 60 euros." '
           'Is the summary line correct? Give the correct total.')


def tool_row(text, op, vals, value, answer, ok=True):
    return {'fixture': 'compare00' if op == 'difference_max_min' else 'summary00', 'text': text, 'nums': [value],
            'checks': {}, 'pass1': {'pass': False, 'features': None, 'output': ''},
            'expression': {'operation': op, 'values': [{'name': n, 'number': v} for n, v in vals], 'value': value},
            'pass3': {'pass': ok, 'features': {'digit_min_logprob': 0.}, 'output': answer, 'tokens': []}}


CMP = [('Cork', 300), ('Lyon', 700), ('Graz', 450)]


class CrossCheckTests(unittest.TestCase):
    def test_right_city_and_value_passes(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Lyon had the most rain with 700 mm, Cork the least. The difference is 400 mm.')
        self.assertEqual(D.cross_check(r), (True, 'ok'))

    def test_wrong_city_with_right_number_fails(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Graz had the most rain. The difference is 400 mm.')
        self.assertEqual(D.cross_check(r), (False, 'wrong_largest'))

    def test_missing_value_fails(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Lyon had the most rain; it had 250 mm more.')
        self.assertEqual(D.cross_check(r), (False, 'value_missing'))

    def test_more_than_clause_names_the_smaller_item_without_failing(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Lyon had the most rain. That is 400 mm more than Cork.')
        self.assertTrue(D.cross_check(r)[0])

    def test_full_check_catches_wrong_least_city(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Lyon had the most rain. Graz had the least. The difference is 400 mm.')
        self.assertTrue(D.cross_check(r)[0]); self.assertEqual(D.cross_check(r, True), (False, 'wrong_smallest'))

    def test_stated_wrong_total_must_be_flagged(self):
        vals = [('cables', 20), ('snacks', 30)]
        self.assertEqual(D.cross_check(tool_row(SUMMARY, 'total', vals, 50, 'The correct total is 50 euros.')), (False, 'stated_number_not_flagged'))
        self.assertTrue(D.cross_check(tool_row(SUMMARY, 'total', vals, 50, 'No, the total is 50 euros, not 60.'))[0])

    def test_no_tool_means_no_check(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'x'); r['pass3'] = None
        self.assertIsNone(D.cross_check(r))

    def test_repair_sentence_names_largest_and_value(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, '')
        r['checks'] = {'city': '(?i)Lyon'}; self.assertTrue(D.bench_score(D.repair_text(r), r))

    def test_strict_scoring_rejects_false_most_claim_the_bench_accepts(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, '')
        self.assertFalse(D.strict_ok(r, 'Graz had the most rain. Lyon had 700 mm. The difference is 400 mm.', True))
        self.assertTrue(D.strict_ok(r, 'Lyon had the most rain with 700 mm. The difference is 400 mm.', True))


class EntityTests(unittest.TestCase):
    def test_entity_words_skip_sentence_initial(self):
        self.assertEqual(D.entity_words(COMPARE), {'Cork', 'Lyon', 'Graz'})

    def test_entity_min_logprob_uses_only_name_tokens(self):
        turn = {'tokens': [{'token': 'Gr', 'logprob': -2.}, {'token': 'az', 'logprob': -.1}, {'token': ' had', 'logprob': -3.},
                           {'token': ' 4', 'logprob': -.2}], 'features': {'digit_min_logprob': -.2}}
        self.assertEqual(D.entity_min_logprob(turn, COMPARE), -2.)
        self.assertAlmostEqual(D.conf(turn, COMPARE, True), math.exp(-2.)); self.assertAlmostEqual(D.conf(turn, COMPARE, False), math.exp(-.2))

    def test_policies_abstain_on_failed_check(self):
        r = tool_row(COMPARE, 'difference_max_min', CMP, 400, 'Graz had the most rain. The difference is 400 mm.', ok=False)
        reg = {'calibrators_digit': {}, 'calibrators_entity': {}, 't_digit': .5, 't_entity': .5}
        self.assertEqual(D.decide(r, 'check', reg)[0], 'abstain'); self.assertEqual(D.decide(r, 'ds3b', reg)[0], 'abstain')
        self.assertEqual(D.decide(r, 'recipe_always', reg)[:2], ('tool', False)); self.assertEqual(D.decide(r, 'check_repair', reg)[0], 'repair')


if __name__ == '__main__':
    unittest.main()
