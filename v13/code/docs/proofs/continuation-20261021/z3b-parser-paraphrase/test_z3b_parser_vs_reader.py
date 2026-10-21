"""Software checks for WP-Z3b (no native inference)."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('z3b', HERE / 'z3b_parser_vs_reader.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
FIXTURES = B.cohorts()
CANON = [f for f in FIXTURES if f['cohort'] == 'canonical']
PARA = [f for f in FIXTURES if f['cohort'] == 'paraphrase']


def texts(f):
    return [s['text'] for s in f['sources']]


class Z3bTests(unittest.TestCase):
    def test_cohort_shape_and_oracles(self):
        self.assertEqual((len(CANON), len(PARA)), (39, 39))
        for c, p in zip(CANON, PARA):
            self.assertEqual(p['canonical_id'], c['id'])
            self.assertEqual(p['oracle'], c['oracle'])
            self.assertEqual(B.oracle_from_truth(c), c['oracle'])
            self.assertEqual(p['public'], c['public'])

    def test_parser_reads_no_paraphrased_rule(self):
        for f in PARA:
            for t in texts(f):
                for rule in B.RULES:
                    self.assertEqual(B.E.stated_values(rule, t), set(), (f['id'], t))
                    self.assertEqual(B.G.facts([t])[rule], set())

    def test_paraphrase_keeps_every_number(self):
        for c, p in zip(CANON, PARA):
            self.assertEqual(B.numbers(texts(c)), B.numbers(texts(p)), p['id'])

    def test_parser_only_canonical_exact_paraphrase_unknown(self):
        for f in CANON:
            row = B.parser_row(f, 13)
            self.assertTrue(row['decision_exact'], f['id'])
        for f in PARA:
            row = B.parser_row(f, 13)
            self.assertEqual(row['tool']['action'], 'UNKNOWN')
            self.assertFalse(row['wrong_commit'])

    def test_true_reader_values_are_exact_on_both_cohorts(self):
        """Perfect reader (truth values, null for missing/conflict) through the grounded guard."""
        for f in FIXTURES:
            truth = {r: (None if v == B.CONFLICT else v) for r, v in f['truth_rules'].items()}
            current = B.G.render_current(f['public'])
            for hybrid in (False, True):
                result = B.grounded_decide(truth, B.Z.parse_options(current), current, texts(f), hybrid)
                raw = B.Z.tool_answer(f['public']['project'], result)
                self.assertTrue(B.summarize_answer(raw, f['oracle'])['decision_exact'], (f['id'], hybrid))

    def test_conflict_caught_without_parser(self):
        """A reader that picks one of two contradicting budgets is refused by the number accounting."""
        for f in (f for f in FIXTURES if f['kind'] == 'contradictory_rule'):
            current = B.G.render_current(f['public'])
            nums = sorted(B.numbers(texts(f)))
            reader = {'budget': nums[-1], 'deadline': nums[0], 'local_only': True}
            result = B.grounded_decide(reader, B.Z.parse_options(current), current, texts(f), False)
            self.assertEqual(result['action'], 'UNKNOWN', f['id'])
            self.assertIn('unaccounted_number', result['rejected'])

    def test_ungrounded_number_refused(self):
        f = next(f for f in PARA if f['kind'] == 'complementary')
        current = B.G.render_current(f['public'])
        truth = dict(f['truth_rules'])
        truth['budget'] += 1000
        result = B.grounded_decide(truth, B.Z.parse_options(current), current, texts(f), False)
        self.assertEqual(result['action'], 'UNKNOWN')
        self.assertIn('budget:not_grounded', result['rejected'])

    def test_parser_bool_replaces_only_local(self):
        f = next(f for f in CANON if f['kind'] == 'complementary' and f['truth_rules']['local_only'] is False)
        current = B.G.render_current(f['public'])
        reader = dict(f['truth_rules'], local_only=True)  # the measured Z3 C3 error
        self.assertTrue(B.summarize_answer(B.Z.tool_answer(f['public']['project'],
                        B.parser_bool_decide(reader, B.Z.parse_options(current), current, texts(f))),
                        f['oracle'])['decision_exact'])

    def test_verdict_order(self):
        rows = []
        for f in FIXTURES[:4] + PARA[:4]:
            for arm in B.ARMS:
                good = arm == 'r_hybrid' or (arm == 'parser_only' and f['cohort'] == 'canonical')
                ans = f['oracle'] if good else dict(f['oracle'], action='UNKNOWN', options=[
                    dict(o, remaining=None, eligible=None) for o in f['oracle']['options']])
                rows.append({'fixture': f['id'], 'kind': f['kind'], 'cohort': f['cohort'], 'seed': 13, 'arm': arm,
                             'status': 'RECORDED', 'read_ok': {r: True for r in B.RULES}}
                            | B.summarize_answer(json.dumps(ans), f['oracle']))
        s = B.summarize(rows, {'arms': B.ARMS, 'seeds': [13]})
        self.assertEqual(s['verdict'], 'C3_READER_BEATS_PARSER')
        self.assertEqual(s['arms_beating_parser'], ['r_hybrid'])


if __name__ == '__main__':
    unittest.main()
