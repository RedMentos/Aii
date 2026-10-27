"""Standard-library-only preregistered LP3 dataset/decision checks; no model."""
import copy
import unittest

from scripts.lp3_heldout_utility import (
    FACTS, SEED, STEPS, LR, fixture, audit_fixture, classify, summarize,
)


class LP3HeldoutPilotTests(unittest.TestCase):
    def test_preregistered_fixture_has_six_train_twelve_heldout_and_no_leak(self):
        rows = fixture()
        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(len(x['heldout']) for x in rows), 12)
        self.assertTrue(audit_fixture(rows))
        self.assertEqual(len({x['key'] for x in rows}), 6)
        self.assertEqual(len({x['answer'] for x in rows}), 6)
        self.assertEqual(SEED, 109)
        self.assertEqual(STEPS, 24)
        self.assertEqual(LR, 0.005)
        for index, row in enumerate(rows):
            self.assertEqual(row['key'], FACTS[index][0])
            self.assertTrue(all(row['key'] in p for p in row['heldout']))
            self.assertTrue(all(FACTS[(index + 1) % 6][0] in p
                                for p in row['wrong_sources']))

    def test_fixture_mutation_fails_closed(self):
        rows = fixture()
        altered = copy.deepcopy(rows)
        altered[0]['wrong_sources'][0] = altered[0]['heldout'][0]
        with self.assertRaises(ValueError):
            audit_fixture(altered)
        altered = copy.deepcopy(rows)
        altered[0]['wrong_sources'][0] += ' ' + altered[0]['answer']
        with self.assertRaises(ValueError):
            audit_fixture(altered)
        altered = copy.deepcopy(rows)
        altered[0]['heldout'][0] = altered[0]['train']
        with self.assertRaises(ValueError):
            audit_fixture(altered)

    def test_fixed_decision_rule_rejects_equal_control_gains(self):
        before = dict(own_ce=2.0, wrong_ce=2.0, zero_ce=2.0,
                      own_top1=1, wrong_top1=1, zero_top1=1)
        after = dict(own_ce=1.0, wrong_ce=1.0, zero_ce=1.0,
                     own_top1=4, wrong_top1=4, zero_top1=4)
        status, criteria = classify(before, after, 1.0, 1.0, True)
        self.assertEqual(status, 'LP3_HELDOUT_NO_ATTRIBUTABLE_SIGNAL')
        self.assertFalse(criteria['own_gain_over_wrong_gain_at_least_0_03'])

    def test_fixed_decision_rule_signal_requires_integrity_and_retention(self):
        before = dict(own_ce=2.0, wrong_ce=2.0, zero_ce=2.0,
                      own_top1=1, wrong_top1=1, zero_top1=1)
        after = dict(own_ce=1.0, wrong_ce=1.6, zero_ce=1.7,
                     own_top1=6, wrong_top1=2, zero_top1=2)
        status, criteria = classify(before, after, 1.0, 1.1, True)
        self.assertEqual(status, 'LP3_HELDOUT_ATTRIBUTABLE_SIGNAL')
        self.assertTrue(all(criteria.values()))
        self.assertEqual(classify(before, after, 1.0, 1.2, True)[0],
                         'LP3_HELDOUT_NO_ATTRIBUTABLE_SIGNAL')
        self.assertEqual(classify(before, after, 1.0, 1.1, False)[0],
                         'LP3_HELDOUT_NO_ATTRIBUTABLE_SIGNAL')

    def test_summarize_counts_all_examples(self):
        rows = [{'own_ce': 1.0, 'wrong_ce': 2.0, 'zero_ce': 3.0,
                 'base_ce': 4.0, 'own_top1': 1, 'wrong_top1': 0,
                 'zero_top1': 0, 'base_top1': 1},
                {'own_ce': 3.0, 'wrong_ce': 4.0, 'zero_ce': 5.0,
                 'base_ce': 6.0, 'own_top1': 0, 'wrong_top1': 1,
                 'zero_top1': 0, 'base_top1': 0}]
        summary = summarize(rows)
        self.assertEqual(summary['own_ce'], 2.0)
        self.assertEqual(summary['wrong_ce'], 3.0)
        self.assertEqual(summary['own_top1'], 1)
        self.assertEqual(summary['wrong_top1'], 1)


if __name__ == '__main__':
    unittest.main()
