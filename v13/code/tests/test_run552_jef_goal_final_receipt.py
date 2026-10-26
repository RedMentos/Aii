"""Run552: a similar user turn is not proof that a user goal was answered.

Model-free SQLite/Runtime tests; a FINAL text receipt is necessary, not semantic
proof of correctness or task completion. No new Age or autonomous authority.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi import hub, live

TOPIC = 'Plane das Budget für Projekt Aurora im Mai'
SIMILAR = 'Plane das Budget für Projekt Aurora im Mai bitte'


class Run552JefGoalReceipt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.g = hub(self.r)
        self.first = self.r.store.event(self.r.session, TOPIC)
        live.goal_turn(self.r, self.first, {}, 'ERROR')
        self.goal_id = self.g.goals.tree('OPEN')[0]['id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, text=SIMILAR):
        return self.r.store.event(self.r.session, text)

    def answer(self, event, text='Aurora Budgetplan', status='FINAL', session=None):
        mid = self.r.store.message(session or self.r.session, event['event_id'], 'assistant', text)
        if status != 'DRAFT':
            self.r.store.finish_message(mid, status, {})
        return mid

    def is_done(self):
        return self.g.goals.get(self.goal_id)['status'] == 'DONE'

    def test_final_status_without_message_does_not_complete(self):
        e = self.event()
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertFalse(self.is_done())
        self.assertEqual(len(self.g.goals.tree('OPEN')), 2)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(len(self.g.goals.tree('OPEN')), 2)

    def test_blank_final_and_nonfinal_messages_do_not_complete(self):
        for text, status in [('  ', 'FINAL'), ('answer', 'DRAFT'),
                             ('answer', 'ERROR'), ('answer', 'CANCELLED'),
                             ('answer', 'DEADLINE')]:
            with self.subTest(status=status, text=text):
                e = self.event()
                self.answer(e, text, status)
                live.goal_turn(self.r, e, {}, 'FINAL')
                self.assertFalse(self.is_done())

    def test_cross_session_final_is_not_a_receipt_for_current_session(self):
        e = self.event()
        other = self.r.store.new_session('Other')
        self.answer(e, session=other)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertFalse(self.is_done())

    def test_real_final_same_topic_completes_and_survives_restart(self):
        e = self.event()
        mid = self.answer(e)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertTrue(self.is_done())
        self.assertIn('message '+str(mid), self.g.goals.get(self.goal_id)['notes'][-1])
        self.r.close()
        self.r = Runtime(self.home)
        self.g = hub(self.r)
        self.assertTrue(self.is_done())

    def test_real_final_unrelated_topic_does_not_complete(self):
        e = self.event('What is the weather in Paris?')
        self.answer(e)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertFalse(self.is_done())

    def test_clarify_cannot_complete_even_with_final_message(self):
        e = self.event()
        self.answer(e)
        live.goal_turn(self.r, e, {'clarify': {'apply': True}}, 'FINAL')
        self.assertFalse(self.is_done())

    def test_status_error_cannot_complete_even_if_final_message_exists(self):
        e = self.event()
        self.answer(e)
        live.goal_turn(self.r, e, {}, 'ERROR')
        self.assertFalse(self.is_done())


if __name__ == '__main__':
    unittest.main()
