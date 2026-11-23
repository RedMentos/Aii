"""Preregistered real-Store JEF self-outcome source integrity for report metrics."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class JefReportLiveSelfSourceRun11(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self.r.store.event(self.r.session, "synthetic report self source")
        fp.head(self.r, "memory", self.e, "recall")
        self.r.store.message(self.r.session, self.e["event_id"], "assistant",
                             "synthetic final", status="FINAL")
        self.assertEqual(
            jo.after_turn(self.r, self.e, {"memory_ids": ["m1"]},
                          "FINAL", {"coalition": []}), {"memory": "skip"})
        self.r.memory.feedback(self.e["event_id"], "memory", "skip", "record")
        st = self.r.store.state(jo.KEY)[0]
        labels = [x for x in st["labels"] if x["event_id"] == self.e["event_id"]]
        self.assertEqual(len(labels), 1)
        self.self_source_id = labels[0]["source_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def head(self):
        return jo.report(self.r)["heads"]["memory"]

    def assert_historical_but_not_live(self):
        h = self.head()
        self.assertEqual(h["labels"], 1, "historical retained count is audit history")
        self.assertEqual(h["by_value"], {"skip": 1})
        self.assertEqual(h["human_overlap"], 0)
        self.assertEqual(h["live_labels"], 0)
        self.assertIsNone(h["human_agreement"])
        self.assertEqual(self.r.pool.pids(), [])

    def test_live_self_source_still_counts_human_agreement(self):
        h = self.head()
        self.assertEqual(h["labels"], 1)
        self.assertEqual(h["live_labels"], 1)
        self.assertEqual(h["human_overlap"], 1)
        self.assertEqual(h["human_agreement"], 1.0)
        self.assertEqual(self.r.pool.pids(), [])

    def test_revoked_self_source_not_counted_as_live_agreement(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?", (self.self_source_id,))
        self.assert_historical_but_not_live()

    def test_wrong_kind_self_source_not_counted_as_live_agreement(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET kind='HUMAN_DECISION' WHERE id=?",
                       (self.self_source_id,))
        self.assert_historical_but_not_live()

    def test_corrupted_self_source_bytes_not_counted_as_live_agreement(self):
        row = self.r.store.one("SELECT hash FROM sources WHERE id=?",
                               (self.self_source_id,))
        blob = self.r.home / "data/blobs" / row["hash"]
        self.assertTrue(blob.is_file())
        blob.write_bytes(b"corrupt source payload")
        self.assert_historical_but_not_live()


if __name__ == "__main__":
    unittest.main()
