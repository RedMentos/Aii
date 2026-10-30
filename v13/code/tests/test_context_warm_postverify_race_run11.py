"""Context OS: injected source-loss race between F5 verification and warm delivery."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13.context_os import ContextOS
from v13.memory import Memory


class ContextWarmPostverifyRaceRun11(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.s = self.r.store
        self.c = ContextOS(self.s, self.r.cfg)
        self.key = "orchard storage phrase"
        e = self.s.event(self.r.session, self.key)
        self.mid = self.r.memory.feedback(
            e["event_id"], "fact", "indigo owl", key=self.key)
        self.assertIsNotNone(self.mid)
        self.c.observe(self.s.event(self.r.session, "synthetic final observation")["event_id"],
                       "C3_LANGUAGE", {}, status="FINAL", memory_ids=[self.mid])
        row = self.s.one(
            "SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id "
            "WHERE m.id=?", (self.mid,))
        self.blob = self.r.home / "data/blobs" / row["hash"]
        self.assertTrue(self.blob.is_file())

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_normal_live_human_source_is_warm_retrievable(self):
        result = self.c.warm(self.key, self.r.session, [])
        self.assertEqual(result["ids"], [self.mid])
        self.assertEqual(result["items"][0]["value"], "indigo owl")
        self.assertFalse(result["applied"])
        self.assertEqual(self.r.pool.pids(), [])

    def test_late_missing_blob_fails_closed_without_delivering_memory(self):
        original = Memory._verified_rows
        removed = []

        def verify_then_lose_blob(memory, rows):
            verified = original(memory, rows)
            self.assertEqual([r["id"] for r in verified], [self.mid])
            self.blob.unlink()
            removed.append(True)
            return verified

        self.c.set_mode("ACTIVE", "EXPLICIT_HUMAN")
        with patch.object(Memory, "_verified_rows", verify_then_lose_blob):
            result = self.c.warm(self.key, self.r.session, [])
        self.assertEqual(removed, [True])
        self.assertEqual(result["ids"], [])
        self.assertEqual(result["items"], [])
        self.assertTrue(result["applied"])
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
