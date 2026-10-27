"""Run644: curiosity's learning-error signal needs a durable, non-abstaining
FINAL answer, not merely a caller-provided status or grounded_error.
Model-free SQLite integration; does not establish semantic correctness.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub, live


class CuriosityReceiptRun644(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, 'Explain the fictional Alder budget')

    def last_error(self):
        return self.g.curiosity.box.load()[0]['regions']['route:unknown']['errors'][-1]

    def final(self, event, text, metadata=None):
        mid = self.r.store.message(self.r.session, event['event_id'], 'assistant', text)
        self.r.store.finish_message(mid, 'FINAL', metadata or {})

    def test_caller_final_without_persisted_answer_is_not_success(self):
        e = self.event()
        live._save(self.r.store, e['event_id'], grounded_error=0.0)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.last_error(), 1.0)

    def test_explicit_nonanswer_final_is_not_learning_success(self):
        e = self.event()
        live.goal_turn(self.r, e, {}, 'ERROR')
        e = self.event()
        self.final(e, "I don't know.")
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.last_error(), 1.0)

    def test_calibrated_abstention_is_not_learning_success(self):
        e = self.event()
        self.final(e, 'Alder budget: 100 units', {'metacog_abstain': True})
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.last_error(), 1.0)

    def test_normal_durable_final_remains_success(self):
        e = self.event()
        self.final(e, 'Alder budget: 100 units')
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.last_error(), 0.0)

    def test_nonfinal_status_with_stored_answer_is_not_success(self):
        e = self.event()
        self.final(e, 'Alder budget: 100 units')
        live.goal_turn(self.r, e, {}, 'ERROR')
        self.assertEqual(self.last_error(), 1.0)


if __name__ == '__main__':
    unittest.main()
