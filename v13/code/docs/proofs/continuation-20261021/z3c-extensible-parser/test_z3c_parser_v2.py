"""Software checks for WP-Z3c (dev data and own sentences only; holdouts are never parsed here)."""
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parser_v2 as P
import z3c_run as R

LEX = P.load_lexicon()


def read(*texts):
    return P.parse(list(texts), LEX)['rules']


class LexiconTests(unittest.TestCase):
    def test_every_entry_has_evidence_and_known_class(self):
        P.validate(LEX)
        for e in LEX['entries']:
            self.assertIn(e['class'], P.CLASSES)
            self.assertTrue(e['evidence'])

    def test_extend_adds_with_evidence_only(self):
        new = P.extend(LEX, 'tops out at', 'max', 'example sentence for the extension test')
        self.assertEqual(len(new['entries']), len(LEX['entries']) + 1)
        self.assertNotIn('tops out at', [e['term'] for e in LEX['entries']])  # original untouched
        with self.assertRaises(ValueError):
            P.extend(LEX, 'foo', 'max', '')
        with self.assertRaises(ValueError):
            P.extend(LEX, 'foo', 'max', 'holdout_author sentence')
        with self.assertRaises(ValueError):
            P.extend(LEX, 'foo', 'no_such_class', 'x')

    def test_extension_changes_reading(self):
        s = 'Project X. Our spending tops out at 40 euros.'
        self.assertEqual(read(s)['budget'], P.UNREADABLE)
        new = P.extend(LEX, 'tops out at', 'max', 'example sentence for the extension test')
        self.assertEqual(P.parse([s], new)['rules']['budget'], 40)


class DevTests(unittest.TestCase):
    def test_dev_cohorts_read_exactly(self):
        for f in R.B.cohorts():
            self.assertEqual(read(*[s['text'] for s in f['sources']]), f['truth_rules'], f['id'])

    def test_dev_decisions_exact_no_wrong(self):
        for f in R.B.cohorts():
            row = R.rows_for(dict(f, cohort='dev'), LEX)[1]
            self.assertTrue(row['decision_exact'], f['id'])
            self.assertFalse(row['wrong_commit'], f['id'])

    def test_current_source_states_no_rule(self):
        f = R.base_fixtures()[0]
        self.assertEqual(read(R.G.render_current(f['public'])), {r: None for r in P.RULES})


class OwnSentenceTests(unittest.TestCase):
    """Sentences written for this test, not taken from any holdout."""

    def test_local_polarity(self):
        cases = {'Only local suppliers may be used.': True,
                 'Suppliers must be local.': True,
                 'Non-local suppliers are forbidden.': True,
                 "Remote suppliers aren't allowed.": True,
                 'Remote suppliers are welcome.': False,
                 'It does not need to be local.': False,
                 'Local options are not required.': False,
                 'Locality is irrelevant here.': False,
                 'Local-only requirement: false.': False}
        for s, want in cases.items():
            self.assertIs(read('Project X. ' + s)['local_only'], want, s)

    def test_local_refusals(self):
        for s in ('Only remote suppliers are allowed.',      # remote required: not this rule
                  'Local suppliers are allowed.',            # says nothing about non-local
                  'Locality matters.',                       # no direction
                  'Local suppliers are forbidden.',          # local forbidden: not this rule
                  'Suppliers are local.'):                   # no predicate
            self.assertEqual(read('Project X. ' + s)['local_only'], P.UNREADABLE, s)

    def test_numeric_reading(self):
        self.assertEqual(read('Project X. Spending may not exceed 40 euros.')['budget'], 40)
        self.assertEqual(read('Project X. The budget is forty-two euros.')['budget'], 42)
        self.assertEqual(read('Project X. We need it in 6 days.')['deadline'], 6)
        self.assertEqual(read('Project X. Max €35.')['budget'], 35)

    def test_numeric_refusals(self):
        for s, rule in (('We must spend at least 20 euros.', 'budget'),
                        ('It takes more than 3 days.', 'deadline'),
                        ('The kickoff costs 10 euros.', 'budget')):
            self.assertEqual(read('Project X. ' + s)[rule], P.UNREADABLE, s)
        r = read('Project X. The deadline is two weeks.')
        self.assertEqual(r['deadline'], P.UNREADABLE)  # other unit, never 2 days

    def test_unaccounted_number_blocks_everything(self):
        r = read('Project X. Budget 40 euros. Deadline 3 days. Local-only requirement: true. Room 12 is booked.')
        self.assertEqual(set(r.values()), {P.UNREADABLE})

    def test_hedged_sentence_ignored(self):
        r = read('Project X. A budget of 50 euros was suggested. Budget 40 euros.')
        self.assertEqual(r['budget'], 40)
        r = read('Project X. Someone wondered whether remote suppliers are allowed.')
        self.assertIsNone(r['local_only'])
        r = read('Project X. Is the deadline 4 days?')
        self.assertIsNone(r['deadline'])

    def test_conflict(self):
        self.assertEqual(read('Project X. Budget 40 euros.', 'Project X. At most 45 euros may be spent.')['budget'],
                         P.CONFLICT)

    def test_combined_clauses(self):
        r = read('Project X. We need it within 5 days, and remote options are fine.')
        self.assertEqual((r['deadline'], r['local_only']), (5, False))


class CohortTests(unittest.TestCase):
    def test_author_holdout_sealed_and_shaped(self):
        h = R.holdout_author_cohort()
        self.assertEqual(len(h), 57)
        kinds = [f['kind'] for f in h]
        self.assertEqual((kinds.count('decoy_missing'), kinds.count('decoy_extra')), (12, 6))
        for f in h:
            self.assertEqual(R.B.oracle_from_truth(f), f['oracle'])
            if f['kind'] == 'decoy_missing':
                self.assertEqual(f['oracle']['action'], 'UNKNOWN')

    def test_author_holdout_never_canonical_form(self):
        for f in R.holdout_author_cohort():
            for s in f['sources']:
                self.assertFalse(any(R.G.facts([s['text']]).values()), s['text'])

    def test_generation_filter(self):
        self.assertEqual(R.generation_filter('Budget 44 euros.', 'We may spend up to 44 euros.'), [])
        self.assertIn('numbers_changed', R.generation_filter('Budget 44 euros.', 'We may spend up to 45 euros.'))
        self.assertIn('canonical_form', R.generation_filter('Budget 44 euros.', 'Budget 44 euros.'))
        self.assertIn('not_one_sentence', R.generation_filter('Budget 44 euros.', 'Spend 44 euros. Not more.'))

    def test_verdict_order(self):
        def row(c, exact, wrong, kind='complementary'):
            return {'cohort': c, 'arm': 'parser_v2', 'kind': kind, 'decision_exact': exact, 'wrong_commit': wrong,
                    'action_correct': exact, 'read_ok': {r: True for r in P.RULES}}
        good = [row(c, True, False) for c in R.COHORTS for _ in range(30)]
        self.assertEqual(R.summarize(good)['verdict'], 'PARSER_V2_CARRIES')
        few = [r for r in good if not (r['cohort'] == 'holdout_model')][:] + [row('holdout_model', True, False)] * 5
        self.assertEqual(R.summarize(few)['verdict'], 'PARSER_V2_CARRIES_AUTHOR_ONLY')
        unsafe = good + [row('holdout_author', False, True)] * 3
        self.assertEqual(R.summarize(unsafe)['verdict'], 'PARSER_V2_UNSAFE')
        reg = good + [row('dev_canonical', False, False)]
        self.assertEqual(R.summarize(reg)['verdict'], 'PARSER_V2_REGRESSION')
        weak = [r for r in good if r['cohort'] != 'holdout_author'] + [row('holdout_author', False, False)] * 30
        s = R.summarize(weak, probe={'local_correct': .6, 'decoy_null': .7})
        self.assertEqual((s['verdict'], s['secondary']), ('PARSER_V2_SAFE_NOT_SUFFICIENT', 'C3_TRAINING_WORTH_A_PACKAGE'))


if __name__ == '__main__':
    unittest.main()
