"""Run348 RED-first: durable release consent and crash-safe standstill ownership.

Real Runtime/SQLite, no model/native execution. A failed release must never
turn protections off before durable consent; retries require a human command.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import standstill as S
from v13 import prohibitions as P


class ReleaseRecoveryRun348(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_first_release_cas_failure_preserves_all_guards(self):
        S.engage(self.r)
        original = self.r.store.set_state
        def fail_first(key, value, *args, **kwargs):
            if key == S.KEY:
                raise ValueError("injected STANDSTILL CAS failure")
            return original(key, value, *args, **kwargs)
        with patch.object(self.r.store, "set_state", side_effect=fail_first):
            with self.assertRaisesRegex(ValueError, "injected STANDSTILL"):
                S.release(self.r)
        state = S.status(self.r)
        self.assertTrue(state["on"])
        self.assertTrue(state["all_parts_on"])
        self.assertTrue(self.r.paused and self.r.store.queue_paused())

    def test_guard_failure_persists_retry_marker_without_resuming(self):
        S.engage(self.r)
        original = P.halt
        def fail_clear(store, on=True, **kwargs):
            if on is False:
                raise OSError("injected NOTAUS clear failure")
            return original(store, on, **kwargs)
        with patch.object(P, "halt", side_effect=fail_clear):
            with self.assertRaisesRegex(OSError, "injected NOTAUS"):
                S.release(self.r)
        state = S.status(self.r)
        self.assertFalse(state["on"])
        self.assertEqual(state["release_pending"], {"notaus": True, "queue": True, "age": True})
        self.assertTrue(self.r.paused and self.r.store.queue_paused())
        self.assertTrue(P.report(self.r.store)["notaus"])
        S.release(self.r)  # second explicit human command
        self.assertFalse(any(S.parts(self.r).values()))
        self.assertFalse(S.status(self.r)["release_pending"])

    def test_restart_does_not_auto_resume_pending_release(self):
        S.engage(self.r)
        with patch.object(P, "halt", side_effect=OSError("interrupted release")):
            with self.assertRaises(OSError):
                S.release(self.r)
        self.r.close()
        self.r = Runtime(self.home)
        self.assertTrue(self.r.paused and self.r.store.queue_paused())
        self.assertTrue(S.status(self.r)["release_pending"])
        self.assertTrue(P.report(self.r.store)["notaus"])
        S.release(self.r)
        self.assertFalse(self.r.paused)
        self.assertFalse(S.status(self.r)["release_pending"])

    def test_reengage_during_pending_preserves_original_ownership(self):
        P.halt(self.r.store, True, authority=P.HUMAN)  # user guard predates standstill
        S.engage(self.r)
        with patch.object(self.r, "resume", side_effect=RuntimeError("interrupted resume")):
            with self.assertRaisesRegex(RuntimeError, "interrupted resume"):
                S.release(self.r)
        self.assertTrue(self.r.paused and self.r.store.queue_paused())
        self.assertTrue(S.status(self.r)["release_pending"])
        S.engage(self.r)
        owned = S.status(self.r)["set_by_standstill"]
        self.assertEqual(owned, {"notaus": False, "queue": True, "age": True})
        S.release(self.r)
        self.assertFalse(self.r.paused)
        self.assertFalse(S.parts(self.r)["age"])
        self.assertTrue(P.report(self.r.store)["notaus"])


    def test_second_cas_failure_reports_already_resumed_queue_truthfully(self):
        S.engage(self.r)
        original = self.r.store.set_state
        count = 0
        def fail_second(key, value, *args, **kwargs):
            nonlocal count
            if key == S.KEY:
                count += 1
                if count == 2:
                    raise ValueError("injected final release CAS failure")
            return original(key, value, *args, **kwargs)
        with patch.object(self.r.store, "set_state", side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, "final release CAS"):
                S.release(self.r)
        state = S.status(self.r)
        self.assertFalse(state["on"])
        self.assertTrue(state["release_pending"])
        self.assertFalse(self.r.paused)  # release was explicitly authorized
        self.assertIn("bereits fortgesetzt", S.text(state))
        S.release(self.r)
        self.assertFalse(S.status(self.r)["release_pending"])


if __name__ == "__main__":
    unittest.main()
