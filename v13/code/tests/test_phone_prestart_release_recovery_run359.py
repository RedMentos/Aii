"""Run359: a STOP widget re-engaging an interrupted standstill release must retain original ownership.

SQLite/Runtime software-only; no model, phone or learning utility claim.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import phone_halt as H, standstill as S, prohibitions as P, age as A
from v13.store import Store


class PrestartReleaseRecoveryRun359(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def press(self):
        (H.control_dir(self.home) / "STILLSTAND").touch()

    def test_widget_reengage_retains_pending_queue_ownership_after_interrupted_release(self):
        r = Runtime(self.home)
        try:
            # This guard was explicitly held by the user BEFORE standstill.
            P.halt(r.store, True, authority=P.HUMAN)
            S.engage(r)
            with patch.object(r, "resume", side_effect=RuntimeError("injected interrupted resume")):
                with self.assertRaisesRegex(RuntimeError, "interrupted resume"):
                    S.release(r)
            self.assertEqual(S.status(r)["release_pending"],
                             {"notaus": False, "queue": True, "age": True})
            self.assertTrue(r.paused)
        finally:
            r.close()

        self.press()
        self.assertEqual(len(H.prestart(self.home)), 1)
        self.assertEqual(H.pending(self.home), [])
        r = Runtime(self.home)
        try:
            state = S.status(r)
            self.assertTrue(state["on"] and state["all_parts_on"])
            self.assertEqual(state["set_by_standstill"],
                             {"notaus": False, "queue": True, "age": True})
            self.assertEqual(state["release_pending"], {})
            S.release(r)
            self.assertFalse(r.paused)
            self.assertFalse(A.controller(r).view()["frozen"])
            self.assertTrue(P.report(r.store)["notaus"], "user's pre-existing halt must survive")
        finally:
            r.close()

    def test_malformed_pending_release_refuses_prestart_without_consuming_button(self):
        r = Runtime(self.home)
        try:
            S.engage(r)
            r.store.set_state(S.KEY, {"revision": S.REVISION, "on": False, "since": None,
                                      "set": {}, "release_pending": {"queue": "yes"}})
        finally:
            r.close()
        self.press()
        with self.assertRaisesRegex(ValueError, "Stillstand"):
            H.prestart(self.home)
        self.assertEqual(H.pending(self.home), ["STILLSTAND"])
        s = Store(self.home)
        try:
            self.assertEqual(s.state(S.KEY, {})[0]["release_pending"], {"queue": "yes"})
            self.assertTrue(s.queue_paused())
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
