"""Run647: AG5 learning progress must not treat a duplicate terminal hook as new evidence."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.common import dumps as original_dumps
from v13.runtime import Runtime
from v13.agi import hub, live


class CuriosityEventOnceRun647(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.g = hub(self.r)

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, 'Explain the fictional Alder budget')

    def final(self, event):
        mid = self.r.store.message(self.r.session, event['event_id'], 'assistant', 'Alder budget: 100 units')
        self.r.store.finish_message(mid, 'FINAL', {})

    def observations(self):
        return self.g.curiosity.box.load()[0]['regions'].get('route:unknown', {'visits': 0, 'errors': []})

    def test_duplicate_error_is_one_error(self):
        e = self.event()
        live.goal_turn(self.r, e, {}, 'ERROR')
        live.goal_turn(self.r, e, {}, 'ERROR')
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [1.0]))

    def test_duplicate_final_is_one_success_proxy(self):
        e = self.event()
        self.final(e)
        live.goal_turn(self.r, e, {}, 'FINAL')
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [0.0]))

    def test_first_terminal_error_is_not_rewritten_by_later_final(self):
        e = self.event()
        live.goal_turn(self.r, e, {}, 'ERROR')
        self.final(e)
        live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [1.0]))

    def test_two_source_events_remain_two_observations(self):
        for _ in range(2):
            e = self.event()
            self.final(e)
            live.goal_turn(self.r, e, {}, 'FINAL')
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (2, [0.0, 0.0]))

    def test_restart_replay_does_not_increment_visits(self):
        e = self.event()
        live.goal_turn(self.r, e, {}, 'ERROR')
        eid, session = e['event_id'], self.r.session
        self.r.close()
        self.r = Runtime(Path(self.tmp.name))
        self.g = hub(self.r)
        self.assertFalse(self.g.curiosity.observe_once('route:unknown', 0.0, eid, session))
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [1.0]))

    def test_wrong_session_event_and_region_fail_closed(self):
        e = self.event()
        c = self.g.curiosity
        with self.assertRaises(ValueError):
            c.observe_once('route:unknown', 1., e['event_id'], 'foreign-session')
        with self.assertRaises(ValueError):
            c.observe_once('route:unknown', 1., 'missing-event', self.r.session)
        self.assertTrue(c.observe_once('route:unknown', 1., e['event_id'], self.r.session))
        with self.assertRaises(ValueError):
            c.observe_once('route:other', 0., e['event_id'], self.r.session)
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [1.0]))

    def test_invalid_error_types_fail_closed(self):
        e = self.event()
        for bad in (True, '0', None, float('nan'), float('inf'), -float('inf'), 10**1000):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.g.curiosity.observe_once('route:unknown', bad, e['event_id'], self.r.session)
        self.assertEqual(self.observations()['visits'], 0)

    def test_serialization_failure_rolls_back_state_and_receipt(self):
        e = self.event()
        calls = [0]
        def fail_second(payload):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError('injected receipt serialization failure')
            return original_dumps(payload)
        with patch('v13.agi.curiosity.dumps', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.g.curiosity.observe_once('route:unknown', 1., e['event_id'], self.r.session)
        self.assertEqual(self.observations()['visits'], 0)
        self.assertTrue(self.g.curiosity.observe_once('route:unknown', 1., e['event_id'], self.r.session))
        self.assertEqual((self.observations()['visits'], self.observations()['errors']), (1, [1.0]))


if __name__ == '__main__':
    unittest.main()
