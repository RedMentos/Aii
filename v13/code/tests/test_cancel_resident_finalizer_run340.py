"""Run340: coordinator finalizer releases native residents only after terminal non-FINAL turns.

Fake inert PID holders, real Runtime worker/SQLite; not a native process-reap proof.
"""
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime


class Resident:
    def __init__(self, role, pid, fail=False):
        self.role, self.pid, self.fail = role, pid, fail
        self.purpose = 'generate'
        self.alive = True
        self.unloads = 0

    def pids(self):
        return [self.pid] if self.alive else []

    def unload(self):
        self.unloads += 1
        if self.fail:
            raise RuntimeError('synthetic unload failure')
        self.alive = False
        return {'process_reaped': True, 'was_loaded': True}


class Finalizer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.b1 = Resident('B1_DETAIL', 340001)
        self.b2 = Resident('B2_GIST', 340002)
        self.r.pool.resident[('B1_DETAIL', 'generate')] = self.b1
        self.r.pool.resident[('B2_GIST', 'generate')] = self.b2
        self.r.pool.current = self.b1
        self.assertEqual(self.r.pool.pids(), [340001, 340002])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def finish(self, status, *, raise_after_message=False):
        def fake_turn(e):
            mid = self.r.store.message(self.r.session, e['event_id'], 'assistant')
            self.r.store.append_message(mid, 'RUN340_PARTIAL')
            if raise_after_message:
                raise RuntimeError('synthetic interrupted turn')
            if status != 'DRAFT':
                self.r.store.finish_message(mid, status, {'model_generated': False})
        eid = self.r.submit('RUN340 actual persisted worker turn')
        deadline = time.monotonic() + 8
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        return eid

    def test_error_reaps_all_residents(self):
        eid = self.finish('ERROR')
        self.assertEqual(self.r.last_answer()['status'], 'ERROR')
        self.assertEqual(self.r.store.one('SELECT state FROM accepted_turns WHERE event_id=?', (eid,))['state'], 'ERROR')
        self.assertEqual(self.r.pool.pids(), [])
        self.assertEqual((self.b1.unloads, self.b2.unloads), (1, 1))
        self.assertEqual(self.r.store.integrity(True), [])

    def test_unfinished_message_is_interrupted_and_reaps(self):
        eid = self.finish('DRAFT', raise_after_message=True)
        self.assertEqual(self.r.last_answer()['status'], 'INTERRUPTED')
        self.assertEqual(self.r.store.one('SELECT state FROM accepted_turns WHERE event_id=?', (eid,))['state'], 'INTERRUPTED')
        self.assertEqual(self.r.pool.pids(), [])
        self.assertEqual((self.b1.unloads, self.b2.unloads), (1, 1))

    def test_final_keeps_both_residents(self):
        self.finish('FINAL')
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')
        self.assertEqual(self.r.pool.pids(), [340001, 340002])
        self.assertEqual((self.b1.unloads, self.b2.unloads), (0, 0))

    def test_one_failed_unload_does_not_skip_other_role(self):
        self.b1.fail = True
        self.finish('ERROR')
        self.assertEqual(self.b1.unloads, 1)
        self.assertEqual(self.b2.unloads, 1)
        self.assertFalse(self.b2.alive)
        # The failed B1 is not falsely reported as reaped; log the failure.
        self.assertTrue(self.b1.alive)
        self.assertEqual(self.r.store.one("SELECT count(*) AS n FROM telemetry WHERE kind='turn_resident_cleanup_failed'")['n'], 1)


if __name__ == '__main__':
    unittest.main()
