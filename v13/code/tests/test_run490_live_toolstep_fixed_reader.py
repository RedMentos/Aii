"""Run490: actual Runtime -> ToolStep -> JEF fixed reader -> shadow guard, no models.

Unlike Run489's archived consumer-packet replay, these tests traverse the
production ToolStep proposal, policy, source-verified quote interface and
read-only shadow transaction with Age-0 gates still in force.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13.toolstep import ToolStep
from v13.agi import hub

CURRENT = ('Project Alder. Decide between Option A and Option B from the latest '
           'supplier data sheet, using the earlier kickoff rules.')
OPTIONS = ('Option A: cost 90 euros, duration 4 days, local true. '
           'Option B: cost 110 euros, duration 3 days, local false.')
RULES = 'Budget 140 euros. Deadline 5 days. Local-only requirement: true.'


class LiveToolStepFixedReader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.cfg['eligibility_reader'] = 'fixed'
        self.r.sleep.cycle.set_policy('enabled', 'off')
        hub(self.r).tools.enable('eligibility')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def plan(self, current, analyst_quotes):
        event = self.r.store.event(self.r.session, current)
        offers = [{'offer_id': 'B1'}, {'offer_id': 'B2'}]
        analysts = [{'role': role, 'verified_quotes': [{'text': q} for q in quotes],
                     'hypothesis': {'summary': 'Budget 999 euros. Deadline 1 days.'}}
                    for role, quotes in analyst_quotes]
        with patch.object(self.r.cognition, 'analyst_context', return_value=analysts), \
             patch.object(self.r.pool, 'get', side_effect=AssertionError('MODEL_READ_FORBIDDEN')):
            proposal = ToolStep(self.r).plan(event, current, offers=offers, version=1)
        return event, proposal

    def test_both_roles_propose_correct_decision_without_c3(self):
        event, proposal = self.plan(CURRENT, [('B1_DETAIL', [OPTIONS]), ('B2_GIST', [RULES])])
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal['tool'], 'eligibility')
        self.assertEqual(proposal['args']['budget'], 140)
        self.assertEqual(proposal['args']['deadline'], 5)
        self.assertIs(proposal['args']['local_only'], True)
        self.assertEqual(proposal['args']['a_cost'], 90)
        self.assertEqual(proposal['args']['b_cost'], 110)
        self.assertNotEqual(proposal['status'], 'APPROVED')  # Age-0 cannot promote.
        shadow = ToolStep(self.r).shadow(event, proposal)
        self.assertEqual(shadow['result']['action'], 'A')
        self.assertEqual(shadow['result']['options'][0]['remaining'], 50)
        packet = self.r.store.one(
            "SELECT payload FROM packets WHERE kind='ToolProposal' AND event_id=?",
            (event['event_id'],))
        self.assertEqual(json.loads(packet['payload'])['truth_authority'], 0)

    def test_missing_b2_rule_stays_unknown_despite_fake_hypothesis(self):
        event, proposal = self.plan(CURRENT, [('B1_DETAIL', [OPTIONS])])
        self.assertIsNotNone(proposal)
        self.assertNotIn('budget', proposal['args'])
        self.assertNotIn('deadline', proposal['args'])
        self.assertNotIn('local_only', proposal['args'])
        shadow = ToolStep(self.r).shadow(event, proposal)
        self.assertEqual(shadow['result']['action'], 'UNKNOWN')
        self.assertIsNone(shadow['result']['options'][0]['remaining'])

    def test_current_revision_overrides_earlier_b2_rules(self):
        current = ('Project Delta. Decide between Option A and Option B. '
                   'Revision 4 supersedes kickoff rules: Budget 100 euros. '
                   'Deadline 4 days. Local-only requirement: true.')
        options = ('Option A: cost 70 euros, duration 5 days, local true. '
                   'Option B: cost 90 euros, duration 3 days, local true.')
        old = 'Budget 160 euros. Deadline 8 days. Local-only requirement: false.'
        event, proposal = self.plan(current, [('B1_DETAIL', [options]), ('B2_GIST', [old])])
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal['args']['budget'], 100)
        self.assertEqual(proposal['args']['deadline'], 4)
        self.assertIs(proposal['args']['local_only'], True)
        self.assertEqual(ToolStep(self.r).shadow(event, proposal)['result']['action'], 'B')

    def test_missing_option_quotes_never_invent_an_option(self):
        event, proposal = self.plan(CURRENT, [('B2_GIST', [RULES])])
        # The fixed reader lacks both option clauses. The C3 fallback is
        # unavailable in this source-only test, so no proposal is emitted.
        self.assertIsNone(proposal)
        unavailable = self.r.store.one(
            "SELECT id FROM telemetry WHERE kind='tool_step_unavailable'")
        self.assertIsNotNone(unavailable)

    def test_all_values_current_source_needs_no_body_or_c3(self):
        current = ('Project Alder. Decide between Option A and Option B. '
                   'Budget 140 euros. Deadline 5 days. Local-only requirement: true. '
                   + OPTIONS)
        event, proposal = self.plan(current, [])
        self.assertIsNotNone(proposal)
        self.assertEqual(ToolStep(self.r).shadow(event, proposal)['result']['action'], 'A')


if __name__ == '__main__':
    unittest.main()
