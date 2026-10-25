"""Run128: CLI preflight must bind persisted Widget stops before frozen Runtime starts.
Linux/SQLite software only. Does not claim direct Runtime(home) auto-preflight.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from v13.config import initialize
from v13.runtime import Runtime
from v13.store import Store
from v13 import phone_halt as H, standstill as S, prohibitions as P, age as A

APP = Path(__file__).resolve().parents[1]


class PhonePrestartRun128(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def press(self, name):
        (H.control_dir(self.home) / name).touch()

    def test_stillstand_preflight_applies_all_gates_and_owns_only_new_parts(self):
        self.press("STILLSTAND")
        messages = H.prestart(self.home)
        self.assertEqual(len(messages), 1)
        self.assertEqual(H.pending(self.home), [])
        r = Runtime(self.home)
        try:
            self.assertTrue(S.status(r)["on"])
            self.assertTrue(r.paused)
            self.assertTrue(P.report(r.store)["notaus"])
            self.assertTrue(A.controller(r).view()["frozen"])
            self.assertEqual(S.status(r)["set_by_standstill"],
                             {"notaus": True, "queue": True, "age": True})
            self.assertEqual(H.prestart(self.home), [])
            S.release(r)
            self.assertFalse(r.paused)
            self.assertFalse(P.report(r.store)["notaus"])
            self.assertFalse(A.controller(r).view()["frozen"])
        finally:
            r.close()

    def test_human_held_parts_remain_after_release(self):
        r = Runtime(self.home)
        try:
            r.pause()
            P.halt(r.store, True, authority=P.HUMAN)
            A.controller(r).freeze(True)
        finally:
            r.close()
        self.press("STILLSTAND")
        H.prestart(self.home)
        r = Runtime(self.home)
        try:
            self.assertEqual(S.status(r)["set_by_standstill"],
                             {"notaus": False, "queue": False, "age": False})
            S.release(r)
            self.assertTrue(r.paused)
            self.assertTrue(P.report(r.store)["notaus"])
            self.assertTrue(A.controller(r).view()["frozen"])
        finally:
            r.close()

    def test_both_buttons_only_apply_stillstand(self):
        self.press("STILLSTAND")
        self.press("NOTAUS")
        self.assertEqual(len(H.prestart(self.home)), 1)
        self.assertEqual(H.pending(self.home), [])
        r = Runtime(self.home)
        try:
            self.assertTrue(S.status(r)["on"])
            self.assertTrue(P.report(r.store)["notaus"])
        finally:
            r.close()

    def test_notaus_only_does_not_pause_queue_or_freeze_age(self):
        self.press("NOTAUS")
        self.assertEqual(len(H.prestart(self.home)), 1)
        r = Runtime(self.home)
        try:
            self.assertTrue(P.report(r.store)["notaus"])
            self.assertFalse(r.paused)
            self.assertFalse(A.controller(r).view()["frozen"])
        finally:
            r.close()

    def test_invalid_age_state_does_not_consume_request_or_partially_write(self):
        s = Store(self.home)
        try:
            s.set_state(A.STATE_KEY, {"revision": "foreign", "frozen": False})
        finally:
            s.close()
        self.press("STILLSTAND")
        with self.assertRaises((ValueError, RuntimeError)):
            H.prestart(self.home)
        self.assertEqual(H.pending(self.home), ["STILLSTAND"])
        s = Store(self.home)
        try:
            self.assertFalse(s.queue_paused())
            self.assertFalse(P.report(s)["notaus"])
        finally:
            s.close()

    def test_cli_recovered_turn_never_final_before_human_release(self):
        r = Runtime(self.home)
        try:
            r.pause()
            eid = r.submit("Kopiere exakt: must wait for explicit release")
        finally:
            r.close()
        s = Store(self.home)
        try:
            s.set_queue_paused(False)
        finally:
            s.close()
        self.press("STILLSTAND")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP)
        result = subprocess.run([sys.executable, "-m", "v13", "--home", str(self.home),
                                 "ask", "Kopiere exakt: second request"], env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(H.pending(self.home), [])
        s = Store(self.home)
        try:
            self.assertTrue(s.queue_paused())
            self.assertEqual(s.queue_stats()["count"], 1)
            self.assertIsNone(s.one("SELECT status FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL'", (eid,)))
            self.assertTrue(s.state(S.KEY, {})[0].get("on"))
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
