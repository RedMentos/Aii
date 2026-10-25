"""Run210: real Store backup/restore preserves source-bound human corrections and forget.

Software/SQLite integration with Runtime and offline restore; no model inference.
"""
import tempfile
import unittest
from pathlib import Path

from v13.backup import backup, restore
from v13.runtime import Runtime

QUERY = 'Run210 Project Alpha budget?'
VALUE = '120 synthetic euros'
OTHER = 'Run210 Project Beta budget?'


class BackupRestoreMemoryRun210(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.session = self.r.session

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def restart(self):
        if self.r is not None:
            self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def feedback(self, query, value):
        e = self.r.store.event(self.session, query)
        return self.r.memory.feedback(e['event_id'], 'fact', value, key=query)

    def test_backup_restore_recovers_correction_and_discards_later_mutations(self):
        mid = self.feedback(QUERY, VALUE)
        snapshot = backup(self.r.store)
        self.assertTrue(snapshot.is_file())
        self.restart()
        self.feedback(OTHER, '999 synthetic euros')
        self.assertEqual(len(self.r.memory.recall(OTHER, self.session)), 1)
        self.r.close(); self.r = None
        safety = restore(self.home, snapshot)
        self.assertTrue(safety.is_file())
        self.restart()
        self.assertEqual([m['id'] for m in self.r.memory.recall(QUERY, self.session)], [mid])
        self.assertEqual(self.r.memory.recall(OTHER, self.session), [])
        self.assertFalse((self.home/'restore_pending.json').exists())

    def test_backup_after_forget_cannot_resurrect_a_revoked_correction(self):
        mid = self.feedback(QUERY, VALUE)
        self.r.memory.forget(mid)
        self.assertEqual(self.r.memory.recall(QUERY, self.session), [])
        snapshot = backup(self.r.store)
        self.r.close(); self.r = None
        restore(self.home, snapshot)
        self.restart()
        self.assertEqual(self.r.memory.recall(QUERY, self.session), [])
        self.assertEqual(self.r.store.one('SELECT active FROM memories WHERE id=?', (mid,))['active'], 0)

    def test_corrupt_backup_rejected_without_modifying_live_memory(self):
        mid = self.feedback(QUERY, VALUE)
        snapshot = backup(self.r.store)
        corrupted = self.home/'backups/corrupt-run210.tar.gz'
        data = bytearray(snapshot.read_bytes())
        data[-8] ^= 0x40
        corrupted.write_bytes(data)
        self.r.close(); self.r = None
        with self.assertRaisesRegex(ValueError, 'Gzip'):
            restore(self.home, corrupted)
        self.restart()
        self.assertEqual([m['id'] for m in self.r.memory.recall(QUERY, self.session)], [mid])
        self.assertFalse((self.home/'restore_pending.json').exists())


    def test_operator_backup_and_offline_restore_instruction(self):
        from v13.operator import Operator
        self.feedback(QUERY, VALUE)
        snapshot = Path(Operator(self.r).run(':backup'))
        self.assertTrue(snapshot.is_file())
        instruction = Operator(self.r).run(':restore ' + str(snapshot))
        self.assertIn('offline', instruction)
        self.assertIn('--confirm', instruction)
        self.assertEqual(len(self.r.memory.recall(QUERY, self.session)), 1)


if __name__ == '__main__':
    unittest.main()
