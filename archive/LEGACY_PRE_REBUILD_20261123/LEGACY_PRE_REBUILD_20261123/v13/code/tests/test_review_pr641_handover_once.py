"""Independent Claude PR641 review: one source event cannot count as eight
independent head/rule agreement observations on retries/re-entry.
Software-only SQLite; does not test native head accuracy.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import route_supersede as RS


class RouteHandoverOnceReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.question = 'How much is half of 120?'
        self.rule = RS.add(self.r.store, 'simple', ['half'], apply_now=True)
        self.rid = self.rule['id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, self.question)['event_id']

    def decide(self, event, route='simple', head='head-A'):
        return RS.decide(self.r.store, self.question,
                         head=lambda: (route, head), event_id=event)

    def test_one_event_retried_eight_times_is_not_eight_agreements(self):
        event = self.event()
        for _ in range(RS.HANDOVER_N):
            self.assertIsNotNone(self.decide(event)[0])
        st = RS.status(self.r.store, self.rid, 'head-A')
        self.assertEqual(st['observed'], 1)
        self.assertEqual(st['agree_in_a_row'], 1)
        self.assertFalse(st['learned'])
        with self.assertRaises(ValueError):
            RS.set_handover(self.r.store, self.rid, True, 'head-A')

    def test_distinct_events_still_allow_human_handover(self):
        for _ in range(RS.HANDOVER_N):
            self.assertIsNotNone(self.decide(self.event())[0])
        self.assertTrue(RS.status(self.r.store, self.rid, 'head-A')['learned'])
        RS.set_handover(self.r.store, self.rid, True, 'head-A')
        rule, info = self.decide(self.event())
        self.assertIsNone(rule)
        self.assertEqual(info['source'], 'RULE_CARRIED_BY_HEAD')

    def test_repeated_event_latest_disagreement_wins_without_double_count(self):
        event = self.event()
        self.decide(event, 'simple')
        self.decide(event, 'detail')
        st = RS.status(self.r.store, self.rid, 'head-A')
        self.assertEqual(st['observed'], 1)
        self.assertEqual(st['agree_in_a_row'], 0)
        self.assertFalse(st['learned'])
        self.assertIsNotNone(self.decide(self.event(), 'detail')[0])


if __name__ == '__main__':
    unittest.main()
