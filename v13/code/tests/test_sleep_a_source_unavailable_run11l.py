"""Sleep A must not retire corrupt live source or abort unrelated replay."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13.memory import Memory
from v13.sleep import SleepCycle


class SleepASourceUnavailableRun11L(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, self.cfg)
        self.cycle = SleepCycle(self.store, self.cfg, self.memory, home=self.home)
        self.event = self._correct("Projekt Sonnenwind Budget?", "120 Euro")

    def _correct(self, question, value):
        event = self.store.event(self.session, question)
        self.memory.feedback(event["event_id"], "fact", value)
        return event

    def _probe(self):
        return self.cycle._probe({"event_id": self.event["event_id"]})

    def _blob(self, event):
        return self.home / "data/blobs" / event["source_ref"]["sha256"]

    def assert_source_fail(self, outcome, errors, detail, ref):
        self.assertEqual(outcome, "FAIL")
        self.assertIn("EVENT_SOURCE_UNAVAILABLE", errors)
        self.assertIn("source_integrity", detail["affected_paths"])
        self.assertIn(ref, detail["source_refs"])
        self.assertTrue(any(c["probe"] == "EVENT_SOURCE" and not c["pass"]
                            for c in detail["checks"]))

    def test_healthy_exact_source_retention_still_passes(self):
        outcome, errors, detail = self._probe()
        self.assertEqual(outcome, "PASS", (outcome, errors, detail))
        self.assertEqual(errors, [])

    def test_explicit_source_tombstone_still_retires(self):
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.event["source_ref"]["source_id"],))
        outcome, reason, detail = self._probe()
        self.assertEqual((outcome, reason), ("RETIRE", "SOURCE_DELETED"))
        self.assertEqual(detail, {})

    def test_missing_live_source_blob_is_failure_not_exception(self):
        self._blob(self.event).unlink()
        self.assert_source_fail(*self._probe(), self.event["source_ref"])

    def test_corrupted_live_source_blob_is_failure_not_retirement(self):
        self._blob(self.event).write_bytes(b"tampered event source")
        self.assert_source_fail(*self._probe(), self.event["source_ref"])

    def test_one_missing_source_does_not_abort_other_replay(self):
        second = self._correct("Projekt Mondlicht Budget?", "250 Euro")
        self._blob(self.event).unlink()
        before = self.store.rows("SELECT * FROM memories ORDER BY id")
        st, _ = self.cycle.queue.load()
        self.cycle.queue.sync(st, self.cycle.policy())
        report = self.cycle.sleep_a(st, self.cycle.policy(), 2,
                                    stage_candidates=False)
        self.assertEqual(report["status"], "DONE")
        self.assertEqual(report["selected"], 2)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(before, self.store.rows("SELECT * FROM memories ORDER BY id"))
        self.assertEqual(self.cycle._probe({"event_id": second["event_id"]})[0],
                         "PASS")


if __name__ == "__main__":
    unittest.main()
