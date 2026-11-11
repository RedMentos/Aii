"""Synthetic opt-in route smoke: real Store, Cognition and PerceptPacket."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from v13.config import initialize
from v13.store import Store
from v13.cognition import Cognition
from v13.percept_runtime_route_candidate import run_percept_route


class NoStudent:
    def student_percept(self, text):
        return None


class PerceptRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.runtime = SimpleNamespace(
            store=self.store, home=self.home,
            cfg={"segment_mode": "percept"}, learner=NoStudent())
        self.runtime.cognition = Cognition(self.runtime)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def event(self, text):
        return {
            "event_id": "synthetic-event-001",
            "brain_generation_id": "synthetic-generation-001",
            "source_ref": self.store.source(text),
        }

    def test_real_a5_packet_and_two_source_exact_views(self):
        text = "Alpha 123.\nBeta € and 🚀!\n\n" * 25
        result = run_percept_route(self.runtime, self.event(text),
                                   width_detail=16, width_gist=42)
        self.assertEqual(result["percept_packet"]["modality"], "text")
        self.assertEqual(result["a3_mode"], "UNAVAILABLE")
        self.assertFalse(result["teacher_truth_authority"])
        self.assertFalse(result["body_inference_executed"])
        for key in ("b1_detail_source_view", "b2_gist_source_view"):
            self.assertEqual(
                "".join(self.store.read_source(x["source_ref"])
                        for x in result[key]), text)
        self.assertEqual(
            self.store.one("SELECT kind FROM packets WHERE id=?",
                           (result["percept_packet_id"],))["kind"],
            "PerceptPacket")

    def test_nonzero_span_fails_closed_before_packet(self):
        event = self.event("PREFIX Alpha Beta. SUFFIX")
        text = self.store.read_source(event["source_ref"])
        event["source_ref"] = dict(
            event["source_ref"],
            char_start=text.index("Alpha"),
            char_end=text.index(" SUFFIX"))
        with self.assertRaisesRegex(ValueError, "nonzero A5 span"):
            run_percept_route(self.runtime, event, width_detail=3, width_gist=6)
        self.assertIsNone(self.store.one(
            "SELECT id FROM packets WHERE kind='PerceptPacket' LIMIT 1"))

    def test_zero_start_shortened_span_remains_source_exact(self):
        event = self.event("Alpha Beta. SUFFIX")
        event["source_ref"] = dict(event["source_ref"], char_end=11)
        result = run_percept_route(self.runtime, event, width_detail=3,
                                   width_gist=6)
        for key in ("b1_detail_source_view", "b2_gist_source_view"):
            self.assertEqual("".join(
                self.store.read_source(x["source_ref"]) for x in result[key]),
                "Alpha Beta.")

    def test_invalid_view_width_fails_before_a5_persistence(self):
        for width_detail, width_gist in (
                (0, 6), (3, 0), (-1, 6), (3, -1),
                (True, 6), (3, False), (1.5, 6), (3, "6")):
            with self.subTest(detail=width_detail, gist=width_gist):
                event = self.event("Alpha Beta.")
                with self.assertRaisesRegex(ValueError, "B source-view width"):
                    run_percept_route(self.runtime, event,
                                     width_detail=width_detail,
                                     width_gist=width_gist)
                self.assertIsNone(self.store.one(
                    "SELECT id FROM packets WHERE kind='PerceptPacket' LIMIT 1"))

    def test_bad_source_fails_without_packet(self):
        event = self.event("hello")
        event["source_ref"] = dict(event["source_ref"], sha256="0"*64)
        with self.assertRaises(ValueError):
            run_percept_route(self.runtime, event)
        self.assertIsNone(self.store.one(
            "SELECT id FROM packets WHERE kind='PerceptPacket' LIMIT 1"))


if __name__ == "__main__":
    unittest.main()
