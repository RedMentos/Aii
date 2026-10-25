"""Run284 RED-first: cancelling a turn must release every resident native role.

Actual Runtime worker, SQLite turn, queue and RunnerPool lifecycle with fake
inert PID holders; no native model execution or fabricated process proof.
"""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime


class FakeResident:
    def __init__(self, role, pid):
        self.role = role
        self.purpose = 'generate'
        self.pid = pid
        self.alive = True
        self.unloads = 0

    def pids(self):
        return [self.pid] if self.alive else []

    def unload(self):
        self.unloads += 1
        self.alive = False
        return {'process_reaped': True, 'was_loaded': True}


class CancelResidentCleanupRun284(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.b1 = FakeResident('B1_DETAIL', 284001)
        self.b2 = FakeResident('B2_GIST', 284002)
        self.r.pool.resident[('B1_DETAIL', 'generate')] = self.b1
        self.r.pool.resident[('B2_GIST', 'generate')] = self.b2
        self.r.pool.current = self.b1
        self.assertEqual(self.r.pool.pids(), [284001, 284002])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def wait_idle(self):
        deadline = time.monotonic() + 8
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(self.r.idle())

    def install_turn(self, cancelled):
        started = threading.Event()
        def fake_turn(e):
            mid = self.r.store.message(self.r.session, e['event_id'], 'assistant')
            self.r.store.append_message(mid, 'RUN284_PARTIAL_OUTPUT')
            started.set()
            if cancelled:
                self.assertTrue(self.r.cancel_event.wait(5))
                status = 'CANCELLED'
            else:
                status = 'FINAL'
            self.r.store.finish_message(mid, status, {'model_generated': False})
        self.r._turn = fake_turn
        event_id = self.r.submit('RUN284 actual persisted turn')
        self.assertTrue(started.wait(5))
        return event_id

    def test_cancel_reaps_all_resident_roles_not_only_active_runner(self):
        eid = self.install_turn(cancelled=True)
        self.r.cancel()
        self.wait_idle()
        self.assertEqual(self.r.last_answer()['status'], 'CANCELLED')
        self.assertEqual(self.r.store.one('SELECT state FROM accepted_turns WHERE event_id=?', (eid,))['state'], 'CANCELLED')
        self.assertEqual(self.r.pool.pids(), [])
        self.assertEqual(self.b1.unloads, 1)
        self.assertEqual(self.b2.unloads, 1)
        self.assertEqual(self.r.store.integrity(True), [])

    def test_normal_final_retains_residents_for_reuse(self):
        self.install_turn(cancelled=False)
        self.wait_idle()
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')
        self.assertEqual(self.r.pool.pids(), [284001, 284002])
        self.assertEqual(self.b1.unloads, 0)
        self.assertEqual(self.b2.unloads, 0)


if __name__ == '__main__':
    unittest.main()
