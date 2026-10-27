"""WP-Z12d offline read-only local SQLite bridge: synthetic-only software tests."""
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import world_jepa_readonly_store as local
from scripts import world_jepa_digital_shadow as bridge
from v13 import world_model as wm


def fixture(path, n=64):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE actions(id TEXT,event_id TEXT,status TEXT,expected TEXT,outcome TEXT,created REAL)')
    db.execute('CREATE TABLE packets(kind TEXT,event_id TEXT,payload TEXT)')
    for i in range(n):
        event = 'synthetic-event-' + str(i)
        route = wm.ACTIONS[i % len(wm.ACTIONS)]
        exp = json.dumps({'forecast': {'input_chars': 100+i, 'resource_state': 'NORMAL'}})
        outcome = json.dumps({'action_duration_s': .2 + i*.01, 'characters': 50+i})
        db.execute('INSERT INTO actions VALUES(?,?,?,?,?,?)',
                   ('synthetic-action-'+str(i), event, 'FINAL', exp, outcome, 1720000000.+i))
        db.execute('INSERT INTO packets VALUES(?,?,?)',
                   ('ActionSelection', event, json.dumps({'route_hint': route})))
    db.commit()
    db.close()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReadOnlyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'observed.sqlite'
        fixture(self.db)

    def test_64_observed_transitions_no_mutation_no_raw_id_export(self):
        before = sha(self.db)
        with patch.object(bridge, 'STEPS', 0):
            result = local.run_db(self.db)
        self.assertEqual(result['n'], 64)
        self.assertEqual(result['scope'], 'OBSERVED_DIGITAL_OUTCOME_SHADOW_NOT_NEXT_WORLD_STATE')
        self.assertEqual(result['train_n']+result['heldout_n'], 64)
        self.assertFalse(result['runtime_wired'])
        self.assertFalse(result['utility_proven'])
        self.assertFalse(result['model_weights_persisted'])
        self.assertEqual(result['negative_gates_unchanged']['jepa_weight'], 0)
        self.assertEqual(before, sha(self.db))
        self.assertFalse(any(Path(str(self.db)+s).exists() for s in ('-wal','-shm','-journal')))
        self.assertNotIn('synthetic-action-', json.dumps(result))
        self.assertNotIn('synthetic-event-', json.dumps(result))

    def test_readonly_connection_rejects_mutation(self):
        store = local.ReadOnlyStore(self.db)
        try:
            self.assertEqual(len(wm.transitions(store)), 64)
            with self.assertRaises(PermissionError):
                store.rows('DELETE FROM actions')
            with self.assertRaises(sqlite3.OperationalError):
                store.conn.execute("INSERT INTO actions(id) VALUES('bad')")
        finally:
            store.close()
        self.assertEqual(len(wm.transitions(local.ReadOnlyStore(self.db))), 64)

    def test_cli_requires_ack_and_sanitizes_invalid_paths(self):
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(self.db)], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(self.db)+'-missing', '--ack-closed-store'], stdout=out), 2)
        self.assertNotIn(str(self.db), out.getvalue())

    def test_cli_valid_synthetic_smoke(self):
        out = io.StringIO()
        with patch.object(bridge, 'STEPS', 0):
            code = local.main(['--db', str(self.db), '--ack-closed-store'], stdout=out)
        self.assertEqual(code, 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report['n'], 64)
        self.assertFalse(report['utility_proven'])
        self.assertNotIn('synthetic-action-', out.getvalue())

    def test_sidecars_and_symlink_fail_closed(self):
        wal = Path(str(self.db)+'-wal')
        wal.write_bytes(b'synthetic WAL marker')
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            local.run_db(self.db)
        wal.unlink()
        link = Path(self.tmp.name) / 'alias.sqlite'
        link.symlink_to(self.db)
        with self.assertRaisesRegex(ValueError, 'regular'):
            local.run_db(link)

    def test_missing_schema_and_too_few_rows_fail_sanitized(self):
        empty = Path(self.tmp.name) / 'empty.sqlite'
        sqlite3.connect(empty).close()
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(empty), '--ack-closed-store'], stdout=out), 2)
        self.assertNotIn(str(empty), out.getvalue())
        small = Path(self.tmp.name) / 'small.sqlite'
        fixture(small, n=16)
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(small), '--ack-closed-store'], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['reason'], 'CLOSED_STORE_INVALID_OR_INSUFFICIENT')


if __name__ == '__main__':
    unittest.main()
