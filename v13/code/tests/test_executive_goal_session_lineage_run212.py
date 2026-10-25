"""Run212: JEF C1 continuity cannot import another session's goal/source.

Actual Store + Executive, synthetic persisted-state tampering; no native C2.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive


class ExecutiveGoalSessionLineageRun212(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.a = self.s.new_session()
        self.b = self.s.new_session()
        self.x = Executive(self.s)
        self.ea = self.s.event(self.a, 'Run212 ALPHA private-session goal')
        self.eb = self.s.event(self.b, 'Run212 BETA foreign-session goal')
        self.x.begin(self.ea, self.a, self.cfg)
        self.x.begin(self.eb, self.b, self.cfg)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def mutate(self, fn):
        key = 'C1_EXEC:' + self.a
        st, version = self.s.state(key, {})
        fn(st)
        self.s.set_state(key, st, expected=version)

    def test_foreign_session_goal_and_sequence_cannot_enter_view_or_effort(self):
        def inject(st):
            st['goal_sequence'].append({'event_id':self.eb['event_id'], 'source_ref':self.eb['source_ref']})
            st['goal'] = 'Run212 BETA foreign-session goal'
            st['goal_source_ref'] = self.eb['source_ref']
        self.mutate(inject)
        view = self.x.view(self.a)
        self.assertNotIn('BETA', json.dumps(view))
        self.assertEqual(view['goal'], '')
        self.assertIsNone(view['goal_source_ref'])
        self.assertEqual([x['event_id'] for x in view['goal_sequence']], [self.ea['event_id']])
        self.assertNotIn('BETA', json.dumps(self.x.effort_context(self.a, self.ea)))

    def test_same_session_goal_remains_exact_and_usable(self):
        e2 = self.s.event(self.a, 'Run212 ALPHA second valid goal')
        self.x.begin(e2, self.a, self.cfg)
        view = self.x.view(self.a)
        self.assertEqual(view['goal'], 'Run212 ALPHA second valid goal')
        self.assertEqual([x['event_id'] for x in view['goal_sequence']],
                         [self.ea['event_id'], e2['event_id']])

    def test_same_session_event_id_cannot_be_rebound_to_wrong_source(self):
        e2 = self.s.event(self.a, 'Run212 ALPHA second valid goal')
        self.x.begin(e2, self.a, self.cfg)
        def inject(st):
            st['goal_sequence'].append({'event_id':e2['event_id'], 'source_ref':self.ea['source_ref']})
        self.mutate(inject)
        view = self.x.view(self.a)
        self.assertEqual([x['source_ref'] for x in view['goal_sequence']],
                         [self.ea['source_ref'], e2['source_ref']])


if __name__ == '__main__':
    unittest.main()
