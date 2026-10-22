"""Forced key-order consumer follow-up: alias order survives sort_keys and de-aliases exactly."""
import json
import unittest

from scripts import consumer_order_ablation as ablation
from scripts.rule_transport_ablation import FIXTURES
from v13.common import dumps
from v13.utility import score_decision


class ForcedOrder(unittest.TestCase):
    def test_sorted_transport_keeps_computation_before_decision(self):
        sent = json.loads(dumps(ablation.forced_schema()))  # what the runner actually sends
        self.assertEqual(list(sent['properties']), ['a_project', 'b_options', 'c_action'])
        self.assertEqual(list(sent['properties']['b_options']['items']['properties']),
                         ['a_entity', 'b_cost', 'c_days', 'd_local', 'e_remaining', 'f_eligible'])

    def test_dealias_is_exact_inverse_and_aliased_raw_is_not_scored_as_correct(self):
        for fixture in FIXTURES:
            oracle = fixture['oracle']
            aliased = {ablation.TOP[k]: v for k, v in oracle.items()}
            aliased['b_options'] = [{ablation.OPTION[k]: v for k, v in o.items()} for o in oracle['options']]
            self.assertTrue(score_decision(ablation.dealias(dumps(aliased)), oracle)['exact'])
            self.assertFalse(score_decision(dumps(aliased), oracle)['exact'])
        self.assertEqual(ablation.dealias('not json'), 'not json')

    def test_schema_constraints_unchanged_apart_from_names(self):
        from tests.integration_step2_utility import SCHEMA
        forced = ablation.forced_schema()
        self.assertEqual(forced['properties']['c_action'], SCHEMA['properties']['action'])
        self.assertEqual(forced['properties']['b_options']['items']['properties']['f_eligible'],
                         SCHEMA['properties']['options']['items']['properties']['eligible'])


if __name__ == '__main__': unittest.main()
