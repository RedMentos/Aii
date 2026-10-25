"""Run124: pending phone stop requests must bind before Runtime's coordinator starts.

Linux software/SQLite only; tests a recovered queued turn, stop provenance and
human-only release. No native models, no Android/Redmi claims.
"""
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.store import Store
from v13 import phone_halt as H, standstill as S, prohibitions as P, age as A


class PreworkerPhoneHaltRun124(unittest.TestCase):
    def test_preexisting_stillstand_blocks_recovered_turn_before_worker(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            r=Runtime(home)
            try:
                r.pause()
                eid=r.submit("Kopiere exakt: must wait for explicit release")
                self.assertEqual(r.store.queue_stats()["count"],1)
            finally:r.close()
            s=Store(home)
            try:s.set_queue_paused(False)  # simulate previously unpaused persisted queue
            finally:s.close()
            (H.control_dir(home)/"STILLSTAND").touch()
            r=Runtime(home)
            try:
                self.assertTrue(S.status(r)["on"],"stop must apply in Runtime.__init__ before worker")
                self.assertTrue(r.paused)
                self.assertEqual(H.pending(home),[])
                self.assertEqual(r.store.queue_stats()["count"],1)
                self.assertFalse(r.store.one(
                    "SELECT status FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL'",(eid,)))
                end=time.monotonic()+2.
                while not S.status(r)["confirmed_still"] and time.monotonic()<end:time.sleep(.02)
                self.assertTrue(S.status(r)["confirmed_still"])
                S.release(r)  # only a human-originated local operator can do this
                end=time.monotonic()+4.
                row=None
                while time.monotonic()<end:
                    row=r.store.one("SELECT status,text FROM messages WHERE event_id=? AND role='assistant'",(eid,))
                    if row and row["status"]=="FINAL":break
                    time.sleep(.02)
                self.assertIsNotNone(row)
                self.assertEqual(row["status"],"FINAL")
                self.assertEqual(row["text"],"must wait for explicit release")
                self.assertEqual(H.pending(home),[])
            finally:r.close()

    def test_notaus_pending_applies_before_runtime_returns(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            (H.control_dir(home)/"NOTAUS").touch()
            r=Runtime(home)
            try:
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertEqual(H.pending(home),[])
            finally:r.close()

    def test_preexisting_human_stop_parts_survive_widget_release(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            r=Runtime(home)
            try:
                r.pause()
                P.halt(r.store,True,authority=P.HUMAN)
                A.controller(r).freeze(True)
            finally:r.close()
            (H.control_dir(home)/"STILLSTAND").touch()
            r=Runtime(home)
            try:
                self.assertTrue(S.status(r)["on"])
                self.assertEqual(S.status(r)["set_by_standstill"],
                                 {"notaus":False,"queue":False,"age":False})
                S.release(r)
                self.assertTrue(r.paused)
                self.assertTrue(P.report(r.store)["notaus"])
                self.assertTrue(A.controller(r).view()["frozen"])
            finally:r.close()


if __name__=="__main__":
    unittest.main()
