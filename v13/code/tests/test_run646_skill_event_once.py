"""Run646 preregistered AG4 exactly-once durable source-event receipts (SQLite, no model)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.agi import hub, live

TRIGGER = 'summarize the fictional Alder plan'


class SkillEventOnceRun646(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.g = hub(self.r)
        self.g.skills.propose('alder_summary', [{'route': 'gist'}], trigger=TRIGGER)
        self.g.skills.set_stage('alder_summary', 'TRUSTED')

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def event(self):
        e = self.r.store.event(self.r.session, TRIGGER)
        self.assertEqual(live.skill_route(self.r, e, TRIGGER, 'simple', False, {}), 'gist')
        return e

    def answer(self, event):
        mid = self.r.store.message(self.r.session, event['event_id'], 'assistant', 'Alder plan: allocate 100 units.')
        self.r.store.finish_message(mid, 'FINAL', {})

    def counts(self):
        s = self.g.skills.get('alder_summary')
        return s['uses'], s['successes']

    def test_duplicate_final_after_turn_is_one_success(self):
        e = self.event()
        self.answer(e)
        live.after_turn(self.r, e, {}, 'FINAL')
        live.after_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.counts(), (1, 1))

    def test_duplicate_failure_and_later_final_are_one_failure(self):
        e = self.event()
        live.after_turn(self.r, e, {}, 'ERROR')
        self.answer(e)
        live.after_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.counts(), (1, 0))

    def test_distinct_events_are_distinct_experiences(self):
        for _ in range(2):
            e = self.event()
            self.answer(e)
            live.after_turn(self.r, e, {}, 'FINAL')
        self.assertEqual(self.counts(), (2, 2))

    def test_receipt_survives_store_reopen(self):
        e = self.event()
        self.answer(e)
        live.after_turn(self.r, e, {}, 'FINAL')
        eid, session = e['event_id'], self.r.session
        self.r.close()
        self.r = Runtime(Path(self.tmp.name))
        self.g = hub(self.r)
        self.assertFalse(self.g.skills.record_once('alder_summary', True, eid, session))
        self.assertEqual(self.counts(), (1, 1))

    def test_wrong_session_or_event_is_not_a_valid_receipt(self):
        e = self.event()
        with self.assertRaises(ValueError):
            self.g.skills.record_once('alder_summary', True, e['event_id'], 'foreign-session')
        with self.assertRaises(ValueError):
            self.g.skills.record_once('alder_summary', True, 'missing-event', self.r.session)
        self.assertEqual(self.counts(), (0, 0))

    def test_event_cannot_be_reattributed_to_different_skill(self):
        e = self.event()
        self.g.skills.propose('other_skill', [{'route': 'detail'}], trigger='other')
        self.assertTrue(self.g.skills.record_once('alder_summary', True, e['event_id'], self.r.session))
        with self.assertRaises(ValueError):
            self.g.skills.record_once('other_skill', True, e['event_id'], self.r.session)
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.g.skills.get('other_skill')['uses'], 0)

    def test_failed_mutation_rolls_back_counter_and_receipt(self):
        e = self.event()
        with patch.object(self.g.skills, '_advance', side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError):
                self.g.skills.record_once('alder_summary', True, e['event_id'], self.r.session)
        self.assertEqual(self.counts(), (0, 0))
        self.assertTrue(self.g.skills.record_once('alder_summary', True, e['event_id'], self.r.session))
        self.assertEqual(self.counts(), (1, 1))


if __name__ == '__main__':
    unittest.main()
