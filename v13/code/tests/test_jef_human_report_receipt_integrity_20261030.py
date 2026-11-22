"""JEF human-agreement report must use exact live receipt bytes and event."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class HumanReportReceiptIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.e = self.r.store.event(self.r.session, "synthetic report human receipt")
        fp.head(self.r, "memory", self.e, "recall")
        self.r.store.message(self.r.session, self.e["event_id"], "assistant",
                             "synthetic final", status="FINAL")
        self.assertEqual(jo.after_turn(self.r, self.e, {"memory_ids": ["m1"]},
                                       "FINAL", {"coalition": []}),
                         {"memory": "skip"})
        self.r.memory.feedback(self.e["event_id"], "memory", "skip", "record")
        self.feedback = self.r.store.one(
            "SELECT * FROM feedback WHERE event_id=? AND kind='memory' "
            "ORDER BY created DESC LIMIT 1", (self.e["event_id"],))
        self.human = self.r.store.one(
            "SELECT id FROM packets WHERE kind='HumanDecision' AND event_id=? "
            "ORDER BY created DESC LIMIT 1", (self.e["event_id"],))
        self.assertEqual(self.head()["human_overlap"], 1)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def head(self):
        return jo.report(self.r)["heads"]["memory"]

    def test_live_human_receipt_counts(self):
        self.assertEqual(self.head()["human_overlap"], 1)
        self.assertEqual(self.head()["human_agreement"], 1.0)

    def test_forged_human_event_payload_not_counted(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload=json_set(payload,'$.event_id',?) "
                      "WHERE id=?", ("evt_wrong", self.human["id"]))
        self.assertEqual(self.head()["human_overlap"], 0)
        self.assertIsNone(self.head()["human_agreement"])

    def test_corrupted_source_blob_not_counted(self):
        src = self.r.store.one("SELECT hash FROM sources WHERE id=?",
                               (self.feedback["source_id"],))
        blob = self.r.home / "data/blobs" / src["hash"]
        self.assertTrue(blob.is_file())
        blob.write_bytes(b"corrupted but same DB metadata")
        self.assertEqual(self.head()["human_overlap"], 0)
        self.assertIsNone(self.head()["human_agreement"])
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
