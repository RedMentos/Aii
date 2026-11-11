"""Candidate regression: A5 source views and packet survive a Store restart.

Software-only; does not assert Android or teacher/student inference.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest

from v13.config import initialize
from v13.store import Store
from v13.cognition import Cognition
from v13.percept_runtime_route_candidate import run_percept_route


class NoStudent:
    def student_percept(self, text):
        return None


class PerceptRestartTests(unittest.TestCase):
    def test_packet_and_b1b2_source_views_survive_store_restart(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            initialize(home)
            store = Store(home)
            text = ("Alpha 123.\nBeta € and 🚀!\n" * 13) + "final"
            try:
                event = {
                    "event_id": "synthetic-restart-event-001",
                    "brain_generation_id": "synthetic-restart-generation-001",
                    "source_ref": store.source(text),
                }
                runtime = SimpleNamespace(
                    store=store, home=home,
                    cfg={"segment_mode": "percept"}, learner=NoStudent())
                runtime.cognition = Cognition(runtime)
                route = run_percept_route(runtime, event,
                                         width_detail=17, width_gist=43)
                packet_id = route["percept_packet_id"]
                packet_before = route["percept_packet"]
                views = [route["b1_detail_source_view"],
                         route["b2_gist_source_view"]]
                self.assertFalse(route["runtime_activated"])
                self.assertFalse(route["a3_available"])
            finally:
                store.close()

            reopened = Store(home)
            try:
                row = reopened.one(
                    "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
                    (packet_id,))
                self.assertIsNotNone(row)
                self.assertEqual(json.loads(row["payload"]), packet_before)
                for view in views:
                    reconstructed = "".join(
                        reopened.read_source(item["source_ref"]) for item in view)
                    self.assertEqual(reconstructed, text)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
