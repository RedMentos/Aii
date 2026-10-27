"""Independent audit of persisted Linux file-world action/overlap receipts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import world_jepa_shadow_lifecycle as lifecycle
from tests.test_world_jepa_shadow_lifecycle import rows_fixture


def sample(seed=212, n=160):
    rows = rows_fixture(n)
    for i, row in enumerate(rows):
        row['a0'] = 1000.0 + i * .1
        row['a1'] = row['a0'] + .01
    log = [{'op': 'write_short', 'slot': 0, 't0': 2000.0,
            't1': 2000.1, 'ok': True, 'changed': True}]
    schedule = {'seed': seed + 7, 't0': 1999.0,
                'items': [{'op': 'write_short', 'slot': 0, 'at': 1.0}]}
    raw_log = (json.dumps(log[0]) + '\n').encode()
    raw_schedule = json.dumps(schedule).encode()
    return rows, raw_log, raw_schedule


class WorldFileTimingReceiptTests(unittest.TestCase):
    def test_consistent_timing_and_world_log(self):
        rows, log, schedule = sample()
        receipt = lifecycle.validate_timing_rows(rows, log, schedule, seed=212)
        self.assertEqual(len(receipt), len(rows))
        self.assertEqual(receipt[0]['a'], rows[0]['a'])
        self.assertEqual(receipt[0]['world'], False)
        self.assertEqual(receipt[0]['world_changed'], False)

    def test_forged_world_overlap_flag_fails_closed(self):
        rows, log, schedule = sample()
        rows[0]['world'] = True
        rows[0]['world_changed'] = True
        with self.assertRaises(ValueError):
            lifecycle.validate_timing_rows(rows, log, schedule, seed=212)

    def test_missing_or_reversed_timing_fails_closed(self):
        rows, log, schedule = sample()
        del rows[0]['a0']
        with self.assertRaises(ValueError):
            lifecycle.validate_timing_rows(rows, log, schedule, seed=212)
        rows, log, schedule = sample()
        rows[0]['a1'] = rows[0]['a0'] - 1.
        with self.assertRaises(ValueError):
            lifecycle.validate_timing_rows(rows, log, schedule, seed=212)

    def test_log_schedule_mismatch_and_empty_log_fail_closed(self):
        rows, log, schedule = sample()
        bad = json.loads(schedule)
        bad['items'][0]['op'] = 'remove'
        with self.assertRaises(ValueError):
            lifecycle.validate_timing_rows(rows, log, json.dumps(bad).encode(), seed=212)
        with self.assertRaises(ValueError):
            lifecycle.validate_timing_rows(rows, b'', schedule, seed=212)

    def test_main_persists_and_verifies_independent_timing_sidecar(self):
        rows, log, schedule = sample()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'export'
            def collect(work, seed, count, held):
                (work / 'world-212.log').write_bytes(log)
                (work / 'world-212.json').write_bytes(schedule)
                return rows
            with patch.object(lifecycle.z12b, 'collect_train', side_effect=collect):
                self.assertEqual(lifecycle.main(['--seed', '212', '--train', '160',
                                                 '--steps', '10', '--output-dir', str(out)]), 0)
            manifest = json.loads((out / 'manifest.json').read_text())
            receipt_raw = (out / 'row_intervals.json').read_bytes()
            self.assertEqual(hashlib.sha256(receipt_raw).hexdigest(),
                             manifest['row_intervals_sha256'])
            self.assertEqual(len(json.loads(receipt_raw)), 160)
            self.assertTrue(manifest['world_overlap_recomputed'])
            self.assertEqual(lifecycle.verify_timing_export(out)['row_intervals_sha256'],
                             manifest['row_intervals_sha256'])
            # Tampering is detected by a read-only recheck after restart.
            (out / 'row_intervals.json').write_bytes(receipt_raw + b' ')
            with self.assertRaises(ValueError):
                lifecycle.verify_timing_export(out)

    def test_mismatched_main_labels_reject_before_export_directory(self):
        rows, log, schedule = sample()
        rows[3]['world_changed'] = True
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'export'
            def collect(work, seed, count, held):
                (work / 'world-212.log').write_bytes(log)
                (work / 'world-212.json').write_bytes(schedule)
                return rows
            with patch.object(lifecycle.z12b, 'collect_train', side_effect=collect):
                with self.assertRaises(ValueError):
                    lifecycle.main(['--seed', '212', '--train', '160', '--steps', '10',
                                    '--output-dir', str(out)])
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
