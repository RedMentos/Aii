import unittest
from v13 import step2_scorer as s


class T(unittest.TestCase):
    def setUp(self):
        self.f = {'budget': 214, 'costs': {'Amber': 127, 'Indigo': 192}, 'expected': {'Amber': 87, 'Indigo': 22}}

    def test_arithmetic_ok(self):
        a = 'Option Amber: 214 - 127 = 87. Option Indigo: 214 - 192 = 22.'
        self.assertEqual(s.score(self.f, a)['ok'], 2)

    def test_wrong_arithmetic_is_wrong_commit(self):
        a = 'Amber: 214 - 127 = 87. Indigo: 214 - 192 = 72.'
        r = s.score(self.f, a)
        self.assertEqual((r['ok'], r['wrong_commit']), (1, 1))

    def test_left_phrase_german(self):
        a = 'Bei Amber bleiben 87 Euro, bei Indigo bleiben 22 Euro übrig.'
        self.assertEqual(s.score(self.f, a)['ok'], 2)

    def test_budget_repeat_is_missing(self):
        a = 'Das Budget ist 214 Euro. Amber kostet 127 Euro, Indigo kostet 192 Euro.'
        r = s.score(self.f, a)
        self.assertEqual((r['ok'], r['wrong_commit']), (0, 0))

    def test_fixtures_do_not_leak(self):
        for f in s.make_fixtures(7, 9, 'de'):
            for v in f['expected'].values():
                self.assertNotIn(str(v), f['question'])
            self.assertEqual(len(f['expected']), 2)
            self.assertTrue(all(v > 0 for v in f['expected'].values()))

    def test_verdict(self):
        base = {'ok': 5, 'wrong_commit': 0, 'max': 18}
        arms = {'c3_only': {'ok': 0, 'wrong_commit': 0, 'max': 18}, 'one_body': base, 'two_same_weights': base,
                'two_distinct_weights': {'ok': 9, 'wrong_commit': 0, 'max': 18}}
        self.assertEqual(s.verdict(arms), 'DISTINCT_BODIES_SUPPORTED')
        arms['two_distinct_weights'] = base
        self.assertEqual(s.verdict(arms), 'NO_GAIN')


if __name__ == '__main__':
    unittest.main()
