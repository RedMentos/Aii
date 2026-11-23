"""Closed observed-digital incremental World-JEPA readout: software-only SQLite tests."""
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import world_jepa_incremental_closedstore as local
from scripts import world_jepa_incremental_probe as probe
from tests.test_world_jepa_readonly_store import fixture, sha


class IncrementalClosedStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'closed.sqlite'
        fixture(self.db, n=64)

    def test_real_sqlite_readonly_trainonly_zero_step_diagnostic(self):
        before = sha(self.db)
        result = local.run_db(self.db, steps=0)
        self.assertEqual(result['n'], 64)
        self.assertEqual((result['train_n'], result['heldout_n']), (47, 17))
        self.assertEqual(result['scope'], 'OBSERVED_DIGITAL_INCREMENTAL_OUTCOME_SHADOW')
        self.assertEqual(result['seeds'], [3, 7])
        self.assertEqual(result['steps'], 0)
        self.assertEqual(len(result['per_seed']), 2)
        self.assertTrue(result['observed_store_readonly'])
        self.assertFalse(result['runtime_wired'])
        self.assertFalse(result['model_weights_persisted'])
        self.assertFalse(result['utility_proven'])
        self.assertEqual(result['negative_gates_unchanged']['jepa_weight'], 0)
        self.assertEqual(before, sha(self.db))
        self.assertFalse(any(Path(str(self.db)+s).exists() for s in ('-wal','-shm','-journal')))
        rendered = json.dumps(result, allow_nan=False)
        self.assertNotIn('synthetic-action-', rendered)
        self.assertNotIn('synthetic-event-', rendered)
        self.assertNotIn(str(self.db), rendered)

    def test_explicit_ack_and_sanitized_missing_store(self):
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(self.db)], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(self.db)+'-missing', '--ack-closed-store'], stdout=out), 2)
        self.assertNotIn(str(self.db), out.getvalue())

    def test_cli_does_not_export_raw_ids(self):
        out = io.StringIO()
        original = local.run_db
        with patch.object(local, 'run_db', side_effect=lambda p: original(p, steps=0)):
            self.assertEqual(local.main(['--db', str(self.db), '--ack-closed-store'], stdout=out), 0)
        report = json.loads(out.getvalue())
        self.assertTrue(report['observed_store_readonly'])
        self.assertNotIn('synthetic-action-', out.getvalue())
        self.assertNotIn('synthetic-event-', out.getvalue())

    def test_sidecar_symlink_and_insufficient_rows_fail_closed(self):
        wal = Path(str(self.db) + '-wal')
        wal.write_bytes(b'synthetic sidecar')
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            local.run_db(self.db, steps=0)
        wal.unlink()
        alias = Path(self.tmp.name) / 'alias.sqlite'
        alias.symlink_to(self.db)
        with self.assertRaisesRegex(ValueError, 'regular'):
            local.run_db(alias, steps=0)
        small = Path(self.tmp.name) / 'small.sqlite'
        fixture(small, n=16)
        out = io.StringIO()
        self.assertEqual(local.main(['--db', str(small), '--ack-closed-store'], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')

    def test_nonfinite_metrics_are_not_serialized(self):
        out = io.StringIO()
        with patch.object(local, 'run_db', return_value={'metric': float('nan')}):
            self.assertEqual(local.main(['--db', str(self.db), '--ack-closed-store'], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')


if __name__ == '__main__':
    unittest.main()
