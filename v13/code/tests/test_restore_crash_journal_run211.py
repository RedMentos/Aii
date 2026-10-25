"""Run211: restore journal must survive missing stage and finish interrupted swaps.

Actual Runtime/SQLite backup/recovery, synthetic crash boundaries, no native models.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from v13.backup import backup, recover_startup, unpack_verified
from v13.runtime import Runtime


class RestoreCrashJournalRun211(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.session = self.r.session

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def close_runtime(self):
        if self.r is not None:
            self.r.close()
            self.r = None

    def feedback(self, query, value):
        e = self.r.store.event(self.session, query)
        return self.r.memory.feedback(e['event_id'], 'fact', value, key=query)

    def journal(self, stage, old):
        p = self.home/'restore_pending.json'
        p.write_text(json.dumps({'stage':str(stage.relative_to(self.home)),
                                 'old':str(old.relative_to(self.home)),
                                 'safety_backup':'synthetic-offline-test'}))
        return p

    def test_missing_restore_stage_cannot_silently_discard_pending_journal(self):
        self.feedback('Run211 alpha?', '120 synthetic units')
        self.close_runtime()
        stage = self.home/'tmp/run211-stage-missing'
        old = self.home/'tmp/run211-old-missing'
        pending = self.journal(stage, old)
        with self.assertRaisesRegex(ValueError, 'Restore'):
            recover_startup(self.home)
        self.assertTrue(pending.exists(), 'incomplete restore must remain reviewable')
        self.assertFalse(stage.exists())

    def test_partial_swap_finishes_after_restart_without_losing_snapshot(self):
        mid = self.feedback('Run211 alpha?', '120 synthetic units')
        snapshot = backup(self.r.store)
        self.feedback('Run211 beta?', '999 synthetic units')
        self.close_runtime()
        stage = self.home/'tmp/run211-stage'
        old = self.home/'tmp/run211-old'
        stage.mkdir()
        unpack_verified(snapshot, stage, 1<<30)
        pending = self.journal(stage, old)
        # Crash after live DB directory moved to safety but before restored DB moves in.
        saved = old/'data/db'
        saved.parent.mkdir(parents=True)
        os.replace(self.home/'data/db', saved)
        recover_startup(self.home)
        self.assertFalse(pending.exists())
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual([m['id'] for m in self.r.memory.recall('Run211 alpha?', self.session)], [mid])
        # Lexical recall may return the *alpha* memory for a related query;
        # inspect exact persisted key identity instead of claiming no fuzzy hit.
        self.assertEqual(self.r.store.one(
            'SELECT COUNT(*) AS n FROM memories WHERE key_text=?', ('Run211 beta?',)
        )['n'], 0)
        self.assertTrue((old/'data/db/brain.sqlite3').is_file())


if __name__ == '__main__':
    unittest.main()
