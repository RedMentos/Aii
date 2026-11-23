"""Run12I: replay row and provenance packet must commit as one SQLite unit.

Real Store/SQLite, no model, no learning or Sleep promotion. Includes injected
packet-insert failure, preflight failure, restart and source binding.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.sleep import ReplayQueue
from v13.store import Store


class ReplayEnqueueAtomicRun12I(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / 'data/db').mkdir(parents=True)
        self.s = Store(self.home)
        self.event = self.s.event(self.s.new_session(), 'Replay source')
        self.q = ReplayQueue(self.s)

    def tearDown(self):
        if not self.s.closed:
            self.s.close()
        self.tmp.cleanup()

    def enqueue(self, **kwargs):
        return self.q.enqueue(self.event['event_id'], 'EPISODIC', .8,
                              'HUMAN_CORRECTION', [self.event['source_ref']], **kwargs)

    def counts(self):
        return (self.s.one('SELECT count(*) AS n FROM replay')['n'],
                self.s.one("SELECT count(*) AS n FROM packets WHERE kind='ReplayItem'")['n'])

    def test_packet_insert_failure_rolls_back_replay_row(self):
        with self.s.tx() as c:
            c.execute('''CREATE TRIGGER run12i_fail_packet BEFORE INSERT ON packets
                         WHEN NEW.kind='ReplayItem'
                         BEGIN SELECT RAISE(ABORT, 'injected packet failure'); END''')
        with self.assertRaises(sqlite3.IntegrityError):
            self.enqueue()
        self.assertEqual(self.counts(), (0, 0))
        with self.s.tx() as c:
            c.execute('DROP TRIGGER run12i_fail_packet')
        self.assertEqual(self.s.schema_audit()['structure'], 'PASS')
        self.enqueue()
        self.assertEqual(self.counts(), (1, 1))

    def test_packet_construction_failure_before_transaction(self):
        # Duplicate replay_id keyword causes packet() to refuse before INSERT.
        with self.assertRaises(TypeError):
            self.enqueue(extra={'replay_id': 'unbound'})
        self.assertEqual(self.counts(), (0, 0))

    def test_successful_pair_persists_and_restarts(self):
        rid = self.enqueue()
        self.assertEqual(self.counts(), (1, 1))
        row = self.s.one('SELECT * FROM replay WHERE id=?', (rid,))
        packet = json.loads(self.s.one("SELECT payload FROM packets WHERE kind='ReplayItem'")['payload'])
        self.assertEqual(row['event_id'], packet['event_id'])
        self.assertEqual(packet['replay_id'], rid)
        self.assertEqual(packet['source_refs'], [self.event['source_ref']])
        self.assertEqual(packet['fact_write_authority'], 0)
        self.assertEqual(packet['stage'], 'QUEUED')
        self.s.close()
        self.s = Store(self.home)
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.s.one('SELECT id FROM replay')['id'], rid)

    def test_foreign_key_failure_leaves_no_packet(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.q.enqueue('evt_nonexistent', 'EPISODIC', .8,
                           'HUMAN_CORRECTION', [self.event['source_ref']])
        self.assertEqual(self.counts(), (0, 0))

    def test_duplicate_replay_id_rolls_back_second_packet(self):
        with patch('v13.sleep.uid', return_value='replay_fixed'):
            self.enqueue()
            with self.assertRaises(sqlite3.IntegrityError):
                self.enqueue()
        self.assertEqual(self.counts(), (1, 1))


if __name__ == '__main__':
    unittest.main()
