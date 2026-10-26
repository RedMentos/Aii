"""Run624: bounded Sleep A liveness across >8 independent SQLite chat sessions."""
import unittest
from v13.operator import Operator
from v13.runtime import Runtime
from v13 import sleep_offline as S
from tests.test_run609_sleep_digest_backlog import SleepBacklog


class SleepSessionFairness(unittest.TestCase):
    setUp = SleepBacklog.setUp
    tearDown = SleepBacklog.tearDown
    turn = SleepBacklog.turn

    def seed(self, count):
        ids = []
        for i in range(count):
            if i:
                Operator(self.r).run(':new')
            ids.append(self.r.session)
            self.turn(i)
        self.assertEqual(len(set(ids)), count)
        return ids

    def entries(self, ids):
        state = S._load(self.r.store)[0]
        return {sid: state['sessions'].get(sid, {}).get('entries', []) for sid in ids}

    def test_twelve_sessions_all_visited_without_duplicate_entries(self):
        ids = self.seed(12)
        first = S.digest(self.r.store)
        self.assertEqual(first['sessions'], S.SESSIONS_MAX)
        self.assertEqual(first['turns'], S.SESSIONS_MAX)
        second = S.digest(self.r.store)
        self.assertEqual(second['sessions'], 4)  # completed hot sessions are skipped
        self.assertEqual(second['turns'], 4)
        entries = self.entries(ids)
        self.assertEqual([len(entries[sid]) for sid in ids], [1] * 12)
        self.assertTrue(all(e[0]['event_id'] for e in entries.values()))
        self.assertEqual(S.digest(self.r.store)['turns'], 0)
        self.assertEqual(S.view(self.r.store, ids[0])['fact_authority'], 0)

    def test_newest_four_are_served_while_older_sessions_rotate(self):
        ids = self.seed(12)
        newest = ids[-4:]
        first = S.digest(self.r.store)
        self.assertEqual(first['turns'], 8)
        self.assertTrue(all(self.entries(ids)[sid] for sid in newest))
        self.turn(100)  # newest session remains active and gains a new FINAL turn
        second = S.digest(self.r.store)
        self.assertEqual(second['turns'], 5)  # one hot turn + four older sessions
        self.assertEqual(len(self.entries(ids)[ids[-1]]), 2)
        self.assertTrue(all(self.entries(ids)[sid] for sid in ids))
        self.assertEqual(self.r.session, ids[-1])

    def test_cursor_survives_restart_and_drains_seventeen_sessions(self):
        ids = self.seed(17)
        self.assertEqual(S.digest(self.r.store)['turns'], 8)
        state = S._load(self.r.store)[0]
        self.assertTrue(state['session_cursor'])
        current = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.r.session, current)
        total = 8
        for _ in range(4):
            total += S.digest(self.r.store)['turns']
        self.assertEqual(total, 17)
        self.assertTrue(all(len(self.entries(ids)[sid]) == 1 for sid in ids))
        self.assertEqual(S.digest(self.r.store)['turns'], 0)
        self.assertEqual(self.r.store.meta('last_session'), current)

    def test_invalid_fair_cursor_fails_closed(self):
        ids = self.seed(2)
        for bad in (42, None, 'x' * 257):
            with self.subTest(cursor=repr(bad)[:30]):
                st, version = S._load(self.r.store)
                st['session_cursor'] = bad
                self.r.store.set_state(S.KEY, st, expected=version)
                before = self.r.store.state(S.KEY, None)
                with self.assertRaises(ValueError):
                    S.digest(self.r.store)
                self.assertEqual(self.r.store.state(S.KEY, None), before)
        self.assertEqual(len(ids), 2)


if __name__ == '__main__':
    unittest.main()
