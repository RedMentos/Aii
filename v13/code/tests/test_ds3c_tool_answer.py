"""WP-DS3c: unit-free tool sentence, family-F generator and strict scoring (no models)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import ds3c_tool_answer as C  # noqa: E402
import ds3b_name_check as D  # noqa: E402


def row(fid, text, op, vals, value, answer, ok=True, nums=None, checks=None):
    return {'fixture': fid, 'text': text, 'nums': nums or [value], 'checks': checks or {}, 'expression_correct': True,
            'pass1': {'pass': False, 'output': '', 'features': None},
            'expression': {'operation': op, 'values': [{'name': n, 'number': v} for n, v in vals], 'value': value},
            'pass3': {'pass': ok, 'output': answer, 'features': None}}


SHOP = 'Cakes sold this week: Alder 40, Birch 90, Cedar 60. Which bakery sold the most cakes, and how many more than the bakery that sold the fewest?'
TRIP = 'Trip costs: hotel 100 euros, fuel 50 euros. The planner wrote that the trip cost 165 euros. Is that correct? What is the sum?'


class DS3cTests(unittest.TestCase):
    def test_family_f_is_deterministic_and_has_four_kinds(self):
        a = C.tasks_f(71); self.assertEqual(a, C.tasks_f(71)); self.assertEqual(len(a), 60)
        self.assertEqual({f.rstrip('0123456789') for f, *_ in a}, {'shop', 'trip', 'team', 'parcel'})

    def test_repair_sentences_are_unit_free_and_flag_stated_numbers(self):
        r = row('trip00', TRIP, 'total', [('hotel', 100), ('fuel', 50)], 150, '')
        self.assertEqual(C.repair_text(r), 'No, the stated number 165 is wrong. The exact total is 150.')
        s = row('shop00', SHOP, 'difference_max_min', [('Alder', 40), ('Birch', 90), ('Cedar', 60)], 50, '')
        self.assertEqual(C.repair_text(s), 'Birch has the largest value (90) and Alder the smallest (40); the difference is 50.')

    def test_policies(self):
        r = row('shop00', SHOP, 'difference_max_min', [('Alder', 40), ('Birch', 90), ('Cedar', 60)], 50,
                'Cedar sold the most cakes. The difference is 50.', ok=False, checks={'shop': '(?i)Birch', 'diff': r'\b50\b'})
        self.assertEqual(C.decide(r, 'recipe_always'), ('tool', False, False))
        self.assertEqual(C.decide(r, 'check'), ('abstain', None, None))
        self.assertEqual(C.decide(r, 'check_repair'), ('repair', True, True))

    def test_strict_rejects_wrong_least_item_the_regex_accepts(self):
        r = row('shop00', SHOP, 'difference_max_min', [], 50, '')
        self.assertFalse(C.strict(r, 'Birch sold the most. Cedar sold the fewest... Cedar had the least. The difference is 50.', True))


if __name__ == '__main__':
    unittest.main()
