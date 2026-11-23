import json
import unittest

from scripts import calc_tool_ablation as calc
from scripts.rule_transport_ablation import FIXTURES
from v13.common import dumps
from v13.utility import score_decision

SYSTEM = {'role': 'system', 'content': 'x'}


def messages(current, quotes=(), summary='Budget 99 euros.'):
    user = {'analysts': [{'hypothesis': {'summary': summary}, 'verified_quotes': [{'text': q} for q in quotes]}],
            'current_source': current}
    return [SYSTEM, {'role': 'user', 'content': dumps(user)}]


def extraction(fixture, budget, deadline, local_only):
    return dumps({'project': fixture['id'], 'options': [{k: o[k] for k in ('entity', 'cost', 'days', 'local')}
                                                        for o in fixture['oracle']['options']],
                  'budget': budget, 'deadline': deadline, 'local_only': local_only})


class CalcToolTests(unittest.TestCase):
    def test_recipe_reproduces_every_oracle(self):
        for name, budget, deadline, local, *_ in __import__('scripts.rule_transport_ablation', fromlist=['x']).PARAMETERS:
            f = next(x for x in FIXTURES if x['id'] == name)
            action, options = calc.eligibility(budget, deadline, local if budget is not None else None,
                                               [{k: o[k] for k in ('entity', 'cost', 'days', 'local')} for o in f['oracle']['options']])
            answer = {'project': name, 'action': action, 'options': options}
            self.assertTrue(score_decision(dumps(answer), f['oracle'])['exact'], name)

    def test_tool_path_with_correct_extraction_is_exact(self):
        f = next(x for x in FIXTURES if x['id'] == 'Mira')
        msg = messages(f['current'], [f['prior']])
        answer, info = calc.run_tool(extraction(f, 61, 8, False), msg)
        self.assertTrue(score_decision(answer, f['oracle'])['exact'])
        self.assertEqual(info['rejected_ungrounded'], [])

    def test_invented_budget_is_rejected_to_unknown(self):
        f = next(x for x in FIXTURES if x['id'] == 'Nacre')
        msg = messages(f['current'])  # no rule delivered; the analyst summary's 99 is a hypothesis, not evidence
        answer, info = calc.run_tool(extraction(f, 99, 9, False), msg)
        self.assertEqual(json.loads(answer)['action'], 'UNKNOWN')
        self.assertIn('budget', info['rejected_ungrounded'])
        self.assertTrue(score_decision(answer, f['oracle'])['exact'])

    def test_null_rule_gives_unknown(self):
        f = next(x for x in FIXTURES if x['id'] == 'Quill')
        answer, _ = calc.run_tool(extraction(f, None, 7, True), messages(f['current']))
        self.assertTrue(score_decision(answer, f['oracle'])['exact'])

    def test_grounding_is_token_exact(self):
        self.assertTrue(calc.grounded(61, 'Budget 61 euros.'))
        self.assertFalse(calc.grounded(6, 'Budget 61 euros.'))
        self.assertFalse(calc.grounded(1, 'cost 1.5'))
        self.assertTrue(calc.grounded(None, ''))

    def test_bad_extraction_is_not_repaired(self):
        f = FIXTURES[0]
        answer, info = calc.run_tool('{"project":"Mira"}', messages(f['current']))
        self.assertIsNone(answer)
        self.assertEqual(info['error'], 'extract_schema')

    def test_schema_orders(self):
        self.assertEqual(list(calc.schema('action_first')['properties']), ['project', 'action', 'options'])
        self.assertEqual(list(calc.schema('options_first')['properties']), ['project', 'options', 'action'])
        self.assertEqual(list(calc.EXTRACT_SCHEMA['properties'])[-3:], ['budget', 'deadline', 'local_only'])
        self.assertNotIn('action', calc.EXTRACT_SCHEMA['properties'])

    def test_decision_exact_ignores_only_project(self):
        f = FIXTURES[0]
        answer = json.loads(calc.run_tool(extraction(f, 61, 8, False), messages(f['current'], [f['prior']]))[0])
        answer['project'] = 'Project Mira'
        score = score_decision(dumps(answer), f['oracle'])
        self.assertFalse(score['exact'])
        self.assertTrue(calc.decision_exact(score))
        answer['action'] = 'B'
        self.assertFalse(calc.decision_exact(score_decision(dumps(answer), f['oracle'])))


if __name__ == '__main__':
    unittest.main()
