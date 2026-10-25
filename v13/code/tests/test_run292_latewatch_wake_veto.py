"""Run292 RED-first: approved learned wake=none must suppress late body offers."""
import unittest
from unittest.mock import patch

from v13 import latewatch


class FakeStore:
    def __init__(self, mode="shadow"):
        self.mode = mode
        self.logs = []

    def state(self, key):
        self.logs.append(("state", key))
        return {"mode": self.mode, "log": [], "counts": {}}, 1

    def log(self, *args):
        self.logs.append(args)


class FakeCognition:
    def __init__(self):
        self.calls = []

    def offer(self, role, event, version, deadline, peer, valid_until):
        self.calls.append(role)
        return {"packet_id": "fake-offer", "offer": {}, "role": role}


class FakeRunner:
    role = "C3_LANGUAGE"


class FakeRuntime:
    def __init__(self, mode="shadow"):
        self.store = FakeStore(mode)
        self.cognition = FakeCognition()
        self.cfg = {"observer_mode": "background", "observer_seconds": 1.0,
                    "c3_decode_mode": "server"}


class Run292LatewatchWakeVeto(unittest.TestCase):
    def invoke(self, runtime, meta):
        return latewatch.start(
            runtime, {"event_id": "evt_software", "source_ref": {}}, 0,
            [], 1000.0, meta, FakeRunner(), eligible=True)

    def test_learned_none_never_starts_body_even_when_resident(self):
        runtime = FakeRuntime()
        meta = {"wake_decision": {"learned": True, "action": "none"}}
        with patch.object(latewatch, "residency", return_value=None) as residency:
            watcher = self.invoke(runtime, meta)
            if watcher.thread is not None:
                watcher.thread.join(timeout=1)
            self.assertIsNone(watcher.thread, "learned none must not launch a late B1/B2 thread")
            self.assertEqual(watcher.status, "LEARNED_WAKE_NONE")
            self.assertEqual(meta["late_watch"]["status"], "LEARNED_WAKE_NONE")
            self.assertEqual(runtime.cognition.calls, [])
            residency.assert_not_called()

    def test_unlearned_none_keeps_original_latewatch_residency_policy(self):
        runtime = FakeRuntime()
        with patch.object(latewatch, "residency", return_value="NO_RESIDENCY") as residency:
            watcher = self.invoke(runtime, {"wake_decision": {"learned": False, "action": "none"}})
            self.assertEqual(watcher.status, "NO_RESIDENCY")
            residency.assert_called_once()

    def test_learned_detail_does_not_veto_latewatch(self):
        runtime = FakeRuntime()
        with patch.object(latewatch, "residency", return_value="NO_RESIDENCY") as residency:
            watcher = self.invoke(runtime, {"wake_decision": {"learned": True, "action": "detail"}})
            self.assertEqual(watcher.status, "NO_RESIDENCY")
            residency.assert_called_once()

    def test_explicit_off_remains_off(self):
        runtime = FakeRuntime("off")
        with patch.object(latewatch, "residency", side_effect=AssertionError("must not run")):
            watcher = self.invoke(runtime, {"wake_decision": {"learned": True, "action": "none"}})
            self.assertEqual(watcher.status, "OFF")
            self.assertIsNone(watcher.thread)


if __name__ == "__main__":
    unittest.main()
