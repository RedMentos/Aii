import json
import tempfile
import unittest
from pathlib import Path

from scripts.rule_transport_ablation import FIXTURES
from scripts.calc_tool_span_ablation import NEW_FIXTURES
from v13.agi import eligibility as E
from v13.common import dumps
from v13.utility import score_decision

CASES = {f['id']: f for f in FIXTURES+NEW_FIXTURES}


def opts(f):
    return [{k: o[k] for k in ('entity', 'cost', 'days', 'local')} for o in f['oracle']['options']]


def quotes(f):
    return [] if f['control'] == 'corrupt_prior' else [f['prior']]


def truth(f):
    """What a perfect reader extracts: current override if stated, else earlier rules; None when missing."""
    rules = {k: (next(iter(E.stated_values(k, f['current'])), None) or None) for k in ('budget', 'deadline', 'local_only')}
    if f['control'] == 'current_override':
        rules['local_only'] = next(iter(E.stated_values('local_only', f['current'])))
        return rules
    if f['control'] == 'corrupt_prior': return {'budget': None, 'deadline': None, 'local_only': None}
    return {k: next(iter(E.stated_values(k, f['prior'])), None) for k in ('budget', 'deadline', 'local_only')}


class EligibilityToolTests(unittest.TestCase):
    def test_perfect_reader_is_exact_on_all_sixteen_cases(self):
        for f in CASES.values():
            d = E.decide(truth(f), opts(f), f['current'], quotes(f))
            answer = {'project': f['id'], 'action': d['action'], 'options': d['options']}
            self.assertTrue(score_decision(dumps(answer), f['oracle'])['exact'], (f['id'], d))
            self.assertEqual(d['rejected'], [], f['id'])

    def test_invented_budget_equal_to_option_cost_is_rejected(self):
        f = CASES['Wren']  # missing budget, option A costs 50
        d = E.decide({'budget': 50, 'deadline': 8, 'local_only': False}, opts(f), f['current'], quotes(f))
        self.assertEqual(d['action'], 'UNKNOWN')
        self.assertIn('budget:not_stated', d['rejected'])

    def test_hypothesis_number_is_not_evidence(self):
        f = CASES['Yarrow']
        d = E.decide({'budget': 80, 'deadline': 6, 'local_only': True}, opts(f), f['current'], quotes(f))
        self.assertEqual(d['action'], 'UNKNOWN')

    def test_stale_earlier_rule_conflicts_with_current_override(self):
        f = CASES['Umber']  # earlier local-only true, current false
        d = E.decide({'budget': 48, 'deadline': 6, 'local_only': True}, opts(f), f['current'], quotes(f))
        self.assertEqual(d['action'], 'UNKNOWN')
        self.assertIn('local_only:conflicts_current', d['rejected'])

    def test_option_values_must_stay_with_their_entity(self):
        f = CASES['Mira']
        swapped = opts(f); swapped[0]['cost'], swapped[1]['cost'] = swapped[1]['cost'], swapped[0]['cost']
        d = E.decide({'budget': 61, 'deadline': 8, 'local_only': False}, swapped, f['current'], quotes(f))
        self.assertEqual(d['action'], 'UNKNOWN')
        self.assertIn('A:option_not_stated', d['rejected'])

    def test_stated_patterns(self):
        self.assertTrue(E.stated('budget', 61, 'Budget 61 euros.'))
        self.assertTrue(E.stated('budget', 43, 'replace earlier rules: budget 43 euros, deadline 4 days'))
        self.assertFalse(E.stated('budget', 6, 'Budget 61 euros.'))
        self.assertFalse(E.stated('budget', 45, 'Option A: cost 45 euros'))
        self.assertTrue(E.stated('local_only', False, 'Local-only requirement: false.'))
        self.assertTrue(E.stated('local_only', True, 'local-only requirement true.'))
        self.assertFalse(E.stated('budget', -1, 'Budget -1 euros'))
        self.assertEqual(E.stated_values('budget', 'No budget has been supplied.'), set())

    def test_registry_runs_it_as_read_local_tool(self):
        from v13.store import Store
        from v13.agi.tools import ToolRegistry
        with tempfile.TemporaryDirectory() as d:
            from v13.config import initialize
            home = Path(d); initialize(home)
            reg = ToolRegistry(Store(home))
            self.assertEqual(reg.tools['eligibility'].risk, 'READ_LOCAL')
            f = CASES['Tarn']
            args = {'current': f['current'], 'quotes': f['prior'], 'a_cost': 38, 'a_days': 6, 'a_local': True,
                    'b_cost': 35, 'b_days': 4, 'b_local': True, 'budget': 40, 'deadline': 5, 'local_only': True}
            self.assertEqual(reg.call('eligibility', args)['status'], 'DENIED')  # off until the user enables it
            reg.enable('eligibility')
            tx = reg.call('eligibility', args)
            self.assertEqual(tx['status'], 'EXECUTED')
            self.assertEqual(tx['result']['action'], 'B')

    def test_text_args_are_read_local_only_and_still_length_bound(self):
        from v13.agi.tools import ToolSpec
        from v13.transaction import check_args
        with self.assertRaises(ValueError):
            ToolSpec('bad_writer', lambda text: None, risk='WRITE_LOCAL', schema={'text': 'text'})
        self.assertEqual(check_args({'t': 'text'}, {'t': 'a; b'}), [])
        self.assertEqual(check_args({'t': 'str'}, {'t': 'a; b'}), ['unsafe_arg:t'])
        self.assertEqual(check_args({'t': 'text'}, {'t': 'x'*4001}), ['unsafe_arg:t'])


if __name__ == '__main__':
    unittest.main()
