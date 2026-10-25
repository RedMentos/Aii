"""Run216 RED-first: JEF current_action_intent is not trusted after persistence.

Actual Store/Executive with two sessions and synthetic local text actions.
No native model, external tools, training, age or acceptance promotion.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.executive import Executive
from v13.store import Store


class ExecutiveActionIntentLineageRun216(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.a = self.s.new_session()
        self.b = self.s.new_session()
        self.x = Executive(self.s)
        self.ea = self.s.event(self.a, 'RUN216_ALPHA action')
        self.eb = self.s.event(self.b, 'RUN216_BETA action')
        self.x.begin(self.ea, self.a, self.cfg)
        self.x.begin(self.eb, self.b, self.cfg)
        self.aa = self.s.start_action(self.ea['event_id'], self.ea['brain_generation_id'])
        self.ab = self.s.start_action(self.eb['event_id'], self.eb['brain_generation_id'])
        self.x.update(self.ea, self.a, action_id=self.aa)
        self.x.update(self.eb, self.b, action_id=self.ab)
        self.assertEqual(self.x.view(self.a)['current_action_intent']['action_id'], self.aa)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def inject(self, **fields):
        key = 'C1_EXEC:' + self.a
        state, version = self.s.state(key, {})
        state['current_action_intent'].update(fields)
        self.s.set_state(key, state, expected=version)

    def test_foreign_session_action_cannot_enter_control_view(self):
        foreign = self.x.view(self.b)['current_action_intent']
        self.inject(**foreign)
        self.assertIsNone(self.x.view(self.a)['current_action_intent'])
        self.assertNotIn(self.ab, json.dumps(self.x.control_view(self.a, self.ea)))

    def test_same_event_action_with_foreign_corollary_is_rejected(self):
        foreign_copy = self.x.view(self.b)['current_action_intent']['corollary_packet_id']
        self.inject(corollary_packet_id=foreign_copy)
        self.assertIsNone(self.x.view(self.a)['current_action_intent'])

    def test_unrecognized_action_type_cannot_enter_report_or_control(self):
        self.inject(type='EXTERNAL_NETWORK')
        self.assertIsNone(self.x.view(self.a)['current_action_intent'])
        self.assertNotIn('EXTERNAL_NETWORK', json.dumps(self.x.report_context(self.a)))
        self.assertNotIn('EXTERNAL_NETWORK', json.dumps(self.x.control_view(self.a, self.ea)))

    def test_valid_action_survives_store_restart(self):
        expected = self.x.view(self.a)['current_action_intent']
        self.s.close()
        self.s = Store(self.home)
        self.x = Executive(self.s)
        self.assertEqual(self.x.view(self.a)['current_action_intent'], expected)
        self.assertEqual(self.x.report_context(self.a)['action_type'], 'LOCAL_TEXT_REPORT')


if __name__ == '__main__':
    unittest.main()
