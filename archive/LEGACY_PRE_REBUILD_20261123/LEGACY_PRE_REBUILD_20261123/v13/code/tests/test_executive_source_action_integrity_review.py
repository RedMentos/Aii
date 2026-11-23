"""Independent RED/GREEN C1 source/action persisted-state binding counterexamples."""
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class C1SourceActionIntegrityReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.executive = Executive(self.store)
        self.original = 'Source-bound user request'
        self.event = self.store.event(self.session, self.original)
        self.executive.begin(self.event, self.session, self.cfg)

    def corrupt(self, **fields):
        key = 'C1_EXEC:' + self.session
        state, version = self.store.state(key, {})
        state.update(fields)
        self.store.set_state(key, state, expected=version)

    def test_persisted_goal_must_equal_source_bytes(self):
        self.corrupt(goal='INJECTED FALSE GOAL')
        view = self.executive.view(self.session)
        self.assertEqual(view['goal'], self.original)
        self.assertEqual(view['active_task']['exact_task'], self.original)
        self.assertEqual(self.executive.report_context(self.session)['task_request']['exact_request'],
                         self.original)

    def test_malformed_action_intents_fail_closed_without_crash(self):
        for bad in (['LOCAL_TEXT_REPORT'], 123, 'LOCAL_TEXT_REPORT', True):
            with self.subTest(kind=type(bad).__name__):
                self.corrupt(current_action_intent=bad)
                self.assertIsNone(self.executive.view(self.session)['current_action_intent'])
                self.assertIsNone(self.executive.report_context(self.session)['action_type'])
                self.assertIsNone(self.executive.control_view(self.session, self.event)['current_action_intent'])

    def test_fabricated_or_cross_event_action_is_not_current(self):
        self.corrupt(current_action_intent={
            'action_id': 'fabricated', 'corollary_packet_id': None,
            'type': 'LOCAL_TEXT_REPORT'})
        self.assertIsNone(self.executive.report_context(self.session)['action_type'])
        original_action = self.store.start_action(
            self.event['event_id'], self.event['brain_generation_id'])
        next_event = self.store.event(self.session, 'Next real request')
        self.executive.begin(next_event, self.session, self.cfg)
        self.corrupt(current_action_intent={
            'action_id': original_action, 'corollary_packet_id': None,
            'type': 'LOCAL_TEXT_REPORT'})
        self.assertIsNone(self.executive.view(self.session)['current_action_intent'])

    def test_valid_same_event_action_survives_and_task_source_remains_exact(self):
        self.executive.task(self.session, 'Explicit operator task')
        action = self.store.start_action(
            self.event['event_id'], self.event['brain_generation_id'])
        self.executive.update(self.event, self.session, action_id=action)
        view = self.executive.view(self.session)
        self.assertEqual(view['current_action_intent']['action_id'], action)
        self.assertEqual(self.executive.report_context(self.session)['action_type'],
                         'LOCAL_TEXT_REPORT')
        self.corrupt(goal='FORGED', current_action_intent={
            'action_id': action, 'corollary_packet_id': 'FORGED',
            'type': 'LOCAL_TEXT_REPORT'})
        self.assertEqual(self.executive.view(self.session)['goal'], self.original)
        self.assertIsNone(self.executive.report_context(self.session)['action_type'])
        self.assertEqual(self.executive.report_context(self.session)['task_request']['exact_request'],
                         'Explicit operator task')


if __name__ == '__main__':
    unittest.main()
