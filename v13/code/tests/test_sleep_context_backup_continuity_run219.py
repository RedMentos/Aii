"""Run219: persisted Sleep digest and C3 context survive backup without stale sources.

Actual Runtime/SQLite/SleepOffline with deterministic C3 double. Source-bound
software integration only; no native inference, TTT training or age promotion.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.backup import backup, restore
from v13.runtime import Runtime
from v13 import sleep_offline as S


class SleepDigestBackupContinuityRun219(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.wire()

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def wire(self):
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.r.cfg['history_turns'] = 6
        self.r._route = Mock(return_value=('simple', {'source': 'RUN219_ROUTE_SEAM'}))
        self.r.learner.output_delta = Mock(return_value=None)
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={},
            generate=lambda messages, *a, **k: iter(['RUN219_C3_DOUBLE']),
        ))

    def turn(self, text):
        eid = self.r.submit(text)
        deadline = time.monotonic() + 15
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), 'Runtime turn did not finish')
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')
        return eid

    def prepare(self):
        for marker in ('RUN219_ALPHA', 'RUN219_BETA', 'RUN219_GAMMA'):
            self.turn('Source-bound context ' + marker)
        self.assertEqual(S.digest(self.r.store)['turns'], 3)
        self.r.cfg['history_turns'] = 0
        self.assertEqual(len(S.context_items(self.r.store, self.r.session)), 3)

    def restart_from(self, snapshot):
        self.r.close()
        self.r = None
        safety = restore(self.home, snapshot)
        self.assertTrue(safety.is_file())
        self.r = Runtime(self.home)
        self.wire()
        self.r.cfg['history_turns'] = 0

    def test_backup_restores_exact_source_bound_digest_without_later_turn(self):
        self.prepare()
        before = S.context_items(self.r.store, self.r.session)
        snapshot = backup(self.r.store)
        self.turn('Source-bound context RUN219_POST_SNAPSHOT')
        S.digest(self.r.store)
        self.restart_from(snapshot)
        after = S.context_items(self.r.store, self.r.session)
        self.assertEqual(after, before)
        self.assertNotIn('RUN219_POST_SNAPSHOT', json.dumps(after))
        S.stage_ttt(self.r.store, self.home)
        rows = [json.loads(line) for line in
                (self.home / 'exports/sleep-ttt-candidates.jsonl').read_text().splitlines()]
        self.assertFalse(any('RUN219_POST_SNAPSHOT' in json.dumps(x) for x in rows))
        self.assertTrue(all(x['status'] == 'CANDIDATE_NOT_TRAINED' for x in rows))
        self.assertEqual(self.r.cfg['learning_mode'], 'RECORD_ONLY')

    def test_revoking_restored_earlier_source_invalidates_digest_lineage(self):
        self.prepare()
        snapshot = backup(self.r.store)
        self.restart_from(snapshot)
        row = self.r.store.one(
            'SELECT e.source_id FROM events e JOIN messages m ON m.event_id=e.id '
            "WHERE m.role='user' AND m.text LIKE ? LIMIT 1",
            ('%RUN219_ALPHA%',),
        )
        self.assertIsNotNone(row)
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (row['source_id'],))
        context = '\n'.join(S.context_items(self.r.store, self.r.session))
        self.assertNotIn('RUN219_ALPHA', context)
        self.assertNotIn('RUN219_BETA', context,
                         'transitively dependent digest must not be trusted')
        S.stage_ttt(self.r.store, self.home)
        rows = (self.home / 'exports/sleep-ttt-candidates.jsonl').read_text()
        self.assertNotIn('RUN219_ALPHA', rows)


if __name__ == '__main__':
    unittest.main()
