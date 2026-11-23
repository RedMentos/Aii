"""C1 persisted goal history must not launder unrelated valid source IDs."""
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class C1GoalSequenceBindingReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.executive = Executive(self.store)
        self.event = self.store.event(self.session, 'Genuine current request')
        self.executive.begin(self.event, self.session, self.cfg)

    def inject_sequence(self, sequence):
        key = 'C1_EXEC:' + self.session
        state, version = self.store.state(key, {})
        state['goal_sequence'] = sequence
        self.store.set_state(key, state, expected=version)

    def test_other_session_goal_is_never_a_prior_goal(self):
        foreign_session = self.store.new_session()
        foreign_event = self.store.event(foreign_session, 'FOREIGN_PRIVATE_SESSION_GOAL')
        self.inject_sequence([
            {'event_id': foreign_event['event_id'], 'source_ref': foreign_event['source_ref']},
            {'event_id': self.event['event_id'], 'source_ref': self.event['source_ref']},
        ])
        view = self.executive.view(self.session)
        self.assertEqual([x['event_id'] for x in view['goal_sequence']], [self.event['event_id']])
        self.assertEqual(self.executive.effort_context(self.session, self.event)['prior_goals'], [])

    def test_same_session_event_cannot_claim_another_valid_source(self):
        next_event = self.store.event(self.session, 'Second genuine request')
        self.executive.begin(next_event, self.session, self.cfg)
        self.inject_sequence([
            {'event_id': self.event['event_id'], 'source_ref': next_event['source_ref']},
            {'event_id': next_event['event_id'], 'source_ref': next_event['source_ref']},
        ])
        view = self.executive.view(self.session)
        self.assertEqual([x['event_id'] for x in view['goal_sequence']], [next_event['event_id']])
        self.assertEqual(self.executive.effort_context(self.session, next_event)['prior_goals'], [])

    def test_missing_or_malformed_event_cannot_be_attributed(self):
        self.inject_sequence([
            {'event_id': 'FABRICATED_EVENT', 'source_ref': self.event['source_ref']},
            {'event_id': None, 'source_ref': self.event['source_ref']},
            {'event_id': ['not', 'a', 'string'], 'source_ref': self.event['source_ref']},
            {'event_id': self.event['event_id'], 'source_ref': self.event['source_ref']},
        ])
        view = self.executive.view(self.session)
        self.assertEqual([x['event_id'] for x in view['goal_sequence']], [self.event['event_id']])

    def test_valid_history_survives_and_current_event_is_excluded(self):
        next_event = self.store.event(self.session, 'Second genuine request')
        self.executive.begin(next_event, self.session, self.cfg)
        view = self.executive.view(self.session)
        self.assertEqual([x['event_id'] for x in view['goal_sequence']],
                         [self.event['event_id'], next_event['event_id']])
        self.assertEqual(self.executive.effort_context(self.session, next_event)['prior_goals'],
                         ['Genuine current request'])
        self.assertEqual(view['goal'], 'Second genuine request')


if __name__ == '__main__':
    unittest.main()
