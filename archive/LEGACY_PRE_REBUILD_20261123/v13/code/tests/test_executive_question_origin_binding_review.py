"""Persisted unresolved questions must bind to their originating offer event."""
import tempfile
import time
import unittest
from pathlib import Path

from v13.config import initialize
from v13.store import Store
from v13.executive import Executive
from v13.contracts import packet


class C1QuestionOriginBindingReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.executive = Executive(self.store)
        self.event = self.store.event(self.session, 'Original question source')
        self.executive.begin(self.event, self.session, self.cfg)

    def offer(self, event):
        ref = event['source_ref']
        item = packet('OfferPacket', 'B1_DETAIL', event['event_id'],
                      event['brain_generation_id'], [ref],
                      role='B1_DETAIL', based_on_state_version=1,
                      deadline_monotonic_ns=time.monotonic_ns() + 10**9,
                      evidence_refs=[ref],
                      offer={'summary': 'unresolved', 'uncertainty': 'Need clarification',
                             'needs_reentry': True}, confidence=0.0)
        self.store.add_packet('OfferPacket', item)
        self.executive.update(event, self.session, offers=[item])
        return item

    def inject_question(self, source, offer):
        key = 'C1_EXEC:' + self.session
        state, version = self.store.state(key, {})
        state['open_questions'] = [{
            'source_ref': source, 'offer_packet_id': offer['packet_id'],
            'uncertainty': 'Need clarification', 'authority': 'UNRESOLVED_HYPOTHESIS'}]
        self.store.set_state(key, state, expected=version)

    def test_other_session_source_cannot_attach_to_real_offer(self):
        offer = self.offer(self.event)
        other_session = self.store.new_session()
        other_event = self.store.event(other_session, 'FOREIGN_UNRELATED_REQUEST')
        self.inject_question(other_event['source_ref'], offer)
        self.assertEqual(self.executive.view(self.session)['open_questions'], [])
        self.assertEqual(self.executive.report_context(self.session)['unresolved_observer_hypotheses'], [])

    def test_different_same_session_event_source_cannot_attach_to_offer(self):
        next_event = self.store.event(self.session, 'Next event request')
        self.executive.begin(next_event, self.session, self.cfg)
        offer = self.offer(next_event)
        self.inject_question(self.event['source_ref'], offer)
        self.assertEqual(self.executive.view(self.session)['open_questions'], [])

    def test_old_offer_cannot_be_relabelled_as_new_question_source(self):
        offer = self.offer(self.event)
        next_event = self.store.event(self.session, 'New unrelated request')
        self.executive.begin(next_event, self.session, self.cfg)
        self.inject_question(next_event['source_ref'], offer)
        self.assertEqual(self.executive.view(self.session)['open_questions'], [])

    def test_real_question_survives_new_turn_without_becoming_fact(self):
        self.offer(self.event)
        next_event = self.store.event(self.session, 'Another user turn')
        self.executive.begin(next_event, self.session, self.cfg)
        view = self.executive.view(self.session)
        self.assertEqual(len(view['open_questions']), 1)
        result = self.executive.report_context(self.session)['unresolved_observer_hypotheses']
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['source_request'], 'Original question source')
        self.assertEqual(result[0]['uncertainty'], 'Need clarification')
        self.assertEqual(result[0]['authority'], 'UNRESOLVED_HYPOTHESIS')


if __name__ == '__main__':
    unittest.main()
