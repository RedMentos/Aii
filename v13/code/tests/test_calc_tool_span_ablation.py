import json
import unittest

from scripts import calc_tool_span_ablation as span
from v13.common import dumps
from v13.utility import score_decision


def fx(name):
    return span.ALL_FIXTURES[name]


def extraction(f, budget, bq, deadline, dq, local, lq):
    return dumps({'project': f['id'], 'options': [{k: o[k] for k in ('entity', 'cost', 'days', 'local')} for o in f['oracle']['options']],
                  'budget_quote': bq, 'budget': budget, 'deadline_quote': dq, 'deadline': deadline,
                  'local_only_quote': lq, 'local_only': local})


class SpanGuardTests(unittest.TestCase):
    def test_new_fixtures_are_balanced_and_disjoint(self):
        actions = [f['oracle']['action'] for f in span.NEW_FIXTURES]
        self.assertEqual(actions.count('UNKNOWN'), 4)
        self.assertEqual(sorted(a for a in actions if a != 'UNKNOWN'), ['A', 'B', 'B', 'B'])
        self.assertFalse({f['id'] for f in span.NEW_FIXTURES} & {f['id'] for f in span.RECORDED_FIXTURES})
        self.assertEqual(len(span.FIXTURE_ORDER), 16)

    def test_override_cases_change_the_answer(self):
        for name in ('Umber', 'Vale'):
            f = fx(name); p = dict(zip(('name', 'b', 'd', 'l', 'a', 'bb', 'c'), next(x for x in span.NEW_PARAMETERS if x[0] == name)))
            prior_action, _ = span.w2.eligibility(p['b']+19, p['d']+3, not p['l'], [{k: o[k] for k in ('entity', 'cost', 'days', 'local')} for o in f['oracle']['options']])
            self.assertNotEqual(prior_action, f['oracle']['action'], name)

    def test_correct_span_extraction_is_exact(self):
        f = fx('Tarn'); msg = span.constructed_messages(f)
        raw = extraction(f, 40, 'Budget 40 euros.', 5, 'Deadline 5 days.', True, 'Local-only requirement: true.')
        answer, info = span.run_span_tool(raw, msg)
        self.assertEqual(info['rejected_unbound'], [])
        self.assertTrue(score_decision(answer, f['oracle'])['exact'])

    def test_invented_budget_equal_to_a_cost_passes_token_guard_but_not_span_guard(self):
        f = fx('Wren'); msg = span.constructed_messages(f)
        old = dumps({'project': 'Wren', 'options': json.loads(extraction(f, 0, '', 0, '', False, ''))['options'],
                     'budget': 50, 'deadline': 8, 'local_only': False})
        self.assertNotEqual(json.loads(span.w2.run_tool(old, msg)[0])['action'], 'UNKNOWN')  # token guard fooled
        raw = extraction(f, 50, 'Option A: cost 50 euros', 8, 'Deadline 8 days.', False, 'Local-only requirement: false.')
        answer, info = span.run_span_tool(raw, msg)
        self.assertEqual(json.loads(answer)['action'], 'UNKNOWN')
        self.assertIn('budget', info['rejected_unbound'])

    def test_hypothesis_number_is_not_evidence(self):
        f = fx('Yarrow'); msg = span.constructed_messages(f)
        self.assertIn('80 euros', msg[1]['content'])
        raw = extraction(f, 80, 'The budget is probably 80 euros.', 6, 'Deadline 6 days.', True, 'Local-only requirement: true.')
        self.assertEqual(json.loads(span.run_span_tool(raw, msg)[0])['action'], 'UNKNOWN')

    def test_corrupt_prior_is_not_delivered(self):
        msg = span.constructed_messages(fx('Alder'))
        self.assertNotIn('71', msg[1]['content'])
        self.assertEqual(json.loads(msg[1]['content'])['analysts'][0]['verified_quotes'], [])

    def test_span_rules(self):
        texts = ['Project X. Budget 61 euros. Deadline 8 days. Local-only requirement: false.']
        self.assertTrue(span.span_bound('budget', 61, 'Budget 61 euros.', texts))
        self.assertFalse(span.span_bound('budget', 61, 'Budget 61 euros!', texts))  # not an exact substring
        self.assertFalse(span.span_bound('deadline', 61, 'Budget 61 euros.', texts))  # wrong rule word
        self.assertFalse(span.span_bound('budget', 6, 'Budget 61 euros.', texts))  # token, not prefix
        self.assertTrue(span.span_bound('local_only', False, 'Local-only requirement: false.', texts))
        self.assertFalse(span.span_bound('local_only', True, 'Local-only requirement: false.', texts))
        self.assertTrue(span.span_bound('budget', None, None, texts))

    def test_schema_order_and_fields(self):
        self.assertEqual(list(span.SPAN_SCHEMA['properties'])[2:], ['budget_quote', 'budget', 'deadline_quote', 'deadline',
                                                                    'local_only_quote', 'local_only'])
        self.assertNotIn('action', span.SPAN_SCHEMA['properties'])


if __name__ == '__main__':
    unittest.main()
