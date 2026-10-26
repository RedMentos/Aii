"""Run610 preregistered SQLite regression: FINAL assistant with unfinished user."""
import unittest
from v13 import sleep_offline as S
from v13.history import native_history, native_history_since
from tests.test_run609_sleep_digest_backlog import SleepBacklog


class PartialUserPair(unittest.TestCase):
    setUp = SleepBacklog.setUp
    tearDown = SleepBacklog.tearDown
    turn = SleepBacklog.turn
    assistant_ids = SleepBacklog.assistant_ids

    def test_final_assistant_partial_user_recovered_exactly_once(self):
        for i in range(3):
            self.turn(i)
        ids = self.assistant_ids()
        user = self.r.store.one(
            "SELECT id FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1 OFFSET 1",
            (self.r.session,))
        self.assertIsNotNone(user)
        with self.r.store.tx() as c:
            c.execute("UPDATE messages SET status='STREAMING' WHERE id=?", (user['id'],))
        # A FINAL assistant is not enough: both rows must be FINAL.
        latest_before, _ = native_history(self.r.store, self.r.session, '', 3)
        self.assertEqual(len(latest_before), 4)
        rows, _, high, deferred = native_history_since(self.r.store, self.r.session, 0, 64)
        self.assertEqual(len(rows), 4)
        self.assertEqual(high, ids[-1])
        self.assertEqual(deferred, [ids[1]])

        first = S.digest(self.r.store)
        self.assertEqual(first['turns'], 2)
        state = S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(state['until'], ids[-1])
        self.assertEqual(state['pending'], [ids[1]])
        self.assertEqual([e['msg'] for e in state['entries']], [ids[0], ids[2]])

        with self.r.store.tx() as c:
            c.execute("UPDATE messages SET status='FINAL' WHERE id=?", (user['id'],))
        second = S.digest(self.r.store)
        self.assertEqual(second['turns'], 1)
        state = S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(state['pending'], [])
        self.assertEqual([e['msg'] for e in state['entries']], ids)
        self.assertEqual(len({e['event_id'] for e in state['entries']}), 3)
        self.assertEqual(S.digest(self.r.store)['turns'], 0)

    def test_revoked_completed_pair_does_not_become_pending(self):
        for i in range(3):
            self.turn(i)
        ids = self.assistant_ids()
        event = self.r.store.one(
            "SELECT event_id FROM messages WHERE id=?", (ids[1],))
        source = self.r.store.one(
            "SELECT source_id FROM events WHERE id=?", (event['event_id'],))
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?", (source['source_id'],))
        rows, _, high, deferred = native_history_since(self.r.store, self.r.session, 0, 64)
        self.assertEqual(high, ids[-1])
        self.assertEqual(deferred, [])
        self.assertNotIn(ids[1], [x['id'] for x in rows])
        first = S.digest(self.r.store)
        self.assertEqual(first['pending'], 0)
        self.assertEqual(S.digest(self.r.store)['turns'], 0)


if __name__ == '__main__':
    unittest.main()
