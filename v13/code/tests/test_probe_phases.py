"""Synthetic native-probe regression: do not conflate slow B1/B2 offer with text generation."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

from v13.common import Limits
from v13 import verification


class FakeStore:
    def __init__(self):
        self.metadata = {"last_session": "human-session"}

    def meta(self, key, default=None):
        return self.metadata.get(key, default)

    def set_meta(self, key, value):
        self.metadata[key] = value

    def new_session(self, title):
        return "probe-session"

    def event(self, session, text):
        return {"event_id": "evt-probe", "source_ref": {"source_id": "s1"}}


class FakeRunner:
    def __init__(self, role):
        self.role = role
        self.last_metrics = {}

    def generate(self, messages, cancel, deadline, tokens):
        self.last_metrics = {"role": self.role, "generated_tokens": 2,
                             "stage_durations_s": {"load_s": .25}}
        return iter(["yes"])


class FakePool:
    def __init__(self):
        self.loaded = None

    def get(self, role):
        self.loaded = FakeRunner(role)
        return self.loaded

    def unload(self):
        return {"process_reaped": True}


class ProbeStageTests(unittest.TestCase):
    def test_text_generation_success_but_second_offer_budget_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "exports").mkdir()
            r = SimpleNamespace()
            r.home = home
            r.store = FakeStore()
            r.cfg = {"deadline_seconds": 90, "observer_seconds": 35}
            r.session = "human-session"
            r.pool = FakePool()
            r.cancel_event = threading.Event()
            r.revisions = lambda: {}
            def offer(role, event, version, deadline):
                r.pool.loaded.last_metrics = {
                    "status": "DEADLINE",
                    "stage_durations_s": {"load_s": 1., "template_s": .2}}
                raise Limits("Zeitbudget erreicht")
            r.cognition = SimpleNamespace(percept=lambda event: None, offer=offer)
            r.needle = SimpleNamespace(
                embed=lambda *args: [1., 2.],
                control=lambda *args: {},
                last_metrics={},
                unload=lambda: None)
            with mock.patch.object(verification, "prompt", return_value="synthetic"), \
                 mock.patch.object(verification, "device", return_value={"android": False}):
                result = verification.probe(r)
            self.assertEqual(result["status"], "SMOKE_PARTIAL")
            self.assertEqual(r.session, "human-session")
            for role in ("B1_DETAIL", "B2_GIST"):
                x = result["roles"][role]
                self.assertFalse(x["ok"])
                self.assertTrue(x["native_generation_ok"])
                self.assertEqual(x["failure_stage"], "structured_offer")
                self.assertIn("stage_durations_s", x["failure_runner_metrics"])
            self.assertTrue(result["roles"]["C3_LANGUAGE"]["ok"])


if __name__ == "__main__":
    unittest.main()
