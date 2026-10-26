"""Run612 real SQLite/Runtime/Operator Sleep A digest progress status tests."""
import json
import unittest

from v13.operator import Operator
from v13 import sleep_offline as S
from v13.runtime import Runtime
from tests.test_run609_sleep_digest_backlog import SleepBacklog


class SleepProgressStatus(unittest.TestCase):
    setUp = SleepBacklog.setUp
    tearDown = SleepBacklog.tearDown
    turn = SleepBacklog.turn
    assistant_ids = SleepBacklog.assistant_ids

    def status(self):
        return json.loads(Operator(self.r).run(":sleep digest status"))

    def test_before_after_digest_and_new_turn(self):
        state_before = self.r.store.state(S.KEY, None)
        zero = self.status()
        self.assertEqual(zero['unscanned_assistant_rows'], 0)
        self.assertFalse(zero['has_work'])
        self.assertEqual(zero['fact_authority'], 0)
        self.assertEqual(self.r.store.state(S.KEY, None), state_before)
        for i in range(4):
            self.turn(i)
        before = self.status()
        self.assertEqual(before['unscanned_assistant_rows'], 4)
        self.assertEqual(before['unscanned_final_assistant_rows'], 4)
        self.assertTrue(before['has_work'])
        self.assertEqual(before['max_turns_per_digest'], 64)
        self.assertEqual(before['unscanned_source_validity'], 'NOT_EVALUATED')
        self.assertEqual(S.digest(self.r.store)['turns'], 4)
        after = self.status()
        self.assertEqual(after['retained_entries'], 4)
        self.assertEqual(after['unscanned_assistant_rows'], 0)
        self.assertEqual(after['deferred_assistant_ids'], 0)
        self.assertFalse(after['has_work'])
        self.turn(5)
        self.assertEqual(self.status()['unscanned_final_assistant_rows'], 1)
        self.assertTrue(self.status()['has_work'])

    def test_legacy_backfill_visible_without_state_mutation(self):
        for i in range(3):
            self.turn(i)
        S.digest(self.r.store)
        st, version = S._load(self.r.store)
        st['sessions'][self.r.session].pop('cursor_version')
        self.r.store.set_state(S.KEY, st, expected=version)
        before = self.r.store.state(S.KEY, None)
        status = self.status()
        self.assertEqual(status['unscanned_assistant_rows'], 0)
        self.assertTrue(status['legacy_backfill_required'])
        self.assertTrue(status['has_work'])
        self.assertEqual(self.r.store.state(S.KEY, None), before)
        self.assertEqual(S.digest(self.r.store)['turns'], 0)
        self.assertFalse(self.status()['legacy_backfill_required'])

    def test_bad_state_fails_closed(self):
        for i in range(2):
            self.turn(i)
        S.digest(self.r.store)
        for key, value in [('until', '2'), ('pending', 'not a list'),
                           ('entries', {'bad': 1})]:
            with self.subTest(key=key):
                st, ver = S._load(self.r.store)
                original = st['sessions'][self.r.session][key]
                st['sessions'][self.r.session][key] = value
                self.r.store.set_state(S.KEY, st, expected=ver)
                with self.assertRaises(ValueError):
                    self.status()
                st, ver = S._load(self.r.store)
                st['sessions'][self.r.session][key] = original
                self.r.store.set_state(S.KEY, st, expected=ver)

    def test_restart_status_is_read_only_and_preserves_active_session(self):
        for i in range(3):
            self.turn(i)
        S.digest(self.r.store)
        self.turn(4)
        expected = self.status()
        current = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.r.session, current)
        self.assertEqual(self.status(), expected)
        self.assertEqual(self.r.store.meta('last_session'), current)


if __name__ == '__main__':
    unittest.main()
