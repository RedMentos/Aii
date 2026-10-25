"""Run215 RED-first: JEF open questions must bind to their own event source.

Actual Store/Executive with two sessions, synthetic OfferPackets and persisted
state tampering. No native C2, model training, age or gate promotion.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.config import initialize
from v13.contracts import packet
from v13.executive import Executive
from v13.store import Store


class ExecutiveOpenQuestionLineageRun215(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.a = self.s.new_session()
        self.b = self.s.new_session()
        self.x = Executive(self.s)
        self.ea = self.s.event(self.a, 'RUN215_ALPHA question')
        self.eb = self.s.event(self.b, 'RUN215_BETA private question')
        self.x.begin(self.ea, self.a, self.cfg)
        self.x.begin(self.eb, self.b, self.cfg)
        self.offer = packet(
            'OfferPacket', 'B1_DETAIL', self.ea['event_id'],
            self.ea['brain_generation_id'], [self.ea['source_ref']],
            role='B1_DETAIL', based_on_state_version=1,
            deadline_monotonic_ns=time.monotonic_ns() + 10**9,
            evidence_refs=[self.ea['source_ref']],
            offer={'summary': 'hypothesis only',
                   'uncertainty': 'RUN215_UNCERTAIN',
                   'needs_reentry': True},
            confidence=0.,
        )
        self.s.add_packet('OfferPacket', self.offer)
        self.x.update(self.ea, self.a, offers=[self.offer])
        self.assertEqual(len(self.x.view(self.a)['open_questions']), 1)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def replace_question_ref(self, ref):
        key = 'C1_EXEC:' + self.a
        state, version = self.s.state(key, {})
        state['open_questions'][0]['source_ref'] = ref
        self.s.set_state(key, state, expected=version)

    def test_foreign_session_source_cannot_be_reported_as_own_open_question(self):
        self.replace_question_ref(self.eb['source_ref'])
        self.assertEqual(self.x.view(self.a)['open_questions'], [])
        self.assertNotIn('RUN215_BETA', json.dumps(self.x.report_context(self.a)))
        self.assertNotIn('RUN215_BETA', json.dumps(self.x.control_view(self.a, self.ea)))

    def test_same_session_unrelated_source_cannot_be_rebound_to_old_offer(self):
        later = self.s.event(self.a, 'RUN215_UNRELATED same-session text')
        self.replace_question_ref(later['source_ref'])
        self.assertEqual(self.x.view(self.a)['open_questions'], [])
        self.assertNotIn('RUN215_UNRELATED', json.dumps(self.x.report_context(self.a)))

    def test_valid_question_remains_source_bound_after_store_restart(self):
        expected = self.x.report_context(self.a)['unresolved_observer_hypotheses']
        self.s.close()
        self.s = Store(self.home)
        self.x = Executive(self.s)
        self.assertEqual(self.x.report_context(self.a)['unresolved_observer_hypotheses'], expected)
        self.assertEqual(self.x.view(self.a)['open_questions'][0]['source_ref'],
                         self.ea['source_ref'])


if __name__ == '__main__':
    unittest.main()
