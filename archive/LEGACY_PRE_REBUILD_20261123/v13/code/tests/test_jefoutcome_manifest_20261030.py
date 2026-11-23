"""WP-U1 lifecycle: update provenance is exact typed source_ids, never JSON substring."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.common import uid
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import jefoutcome as jo


class LifecycleManifestIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        e = self.r.store.event(self.r.session, "Synthetic provenance attribution")
        self.eid = e["event_id"]
        self.r.memory.feedback(self.eid, "fact", "synthetic feedback value")
        self.sid = self.r.store.one(
            "SELECT source_id FROM feedback WHERE event_id=?",
            (self.eid,))["source_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def insert(self, manifest, status="PENDING_APPROVAL"):
        mid = uid("upd")
        text = manifest if isinstance(manifest, str) else json.dumps(manifest)
        with self.r.store.tx() as c:
            c.execute("INSERT INTO updates VALUES (?,?,?,?,?,?,?)",
                      (mid, self.r.store.generation_id, status, None,
                       None, text, time.time()))
        return mid

    def lifecycle(self):
        return jo.lifecycle(self.r, self.eid)

    def test_unrelated_text_and_longer_ids_do_not_invent_update_stages(self):
        ids = [
            self.insert({"source_ids": [], "note": f"unrelated mention {self.sid}"}),
            self.insert({"source_ids": [self.sid + "-foreign"]},
                        status="APPROVED"),
            self.insert({"source_ids": self.sid}, status="ROLLED_BACK"),
        ]
        result = self.lifecycle()
        self.assertEqual(result["updates"], [])
        for stage in ("L4_UPDATE_PROPOSAL", "L5_SHADOW_LEARN",
                      "L7_VALIDATE", "L9_PROMOTE", "L11_REOPEN"):
            self.assertFalse(result["reached"][stage], stage)
        self.assertTrue(all(mid not in str(result) for mid in ids))
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_only_exact_typed_source_id_links_update(self):
        foreign = self.insert({"source_ids": [self.sid + "_shadow"],
                               "comment": self.sid}, status="REJECTED")
        matched = self.insert({"source_ids": [self.sid]}, status="PENDING_APPROVAL")
        result = self.lifecycle()
        self.assertEqual(result["updates"],
                         [{"id": matched, "status": "PENDING_APPROVAL"}])
        self.assertTrue(result["reached"]["L4_UPDATE_PROPOSAL"])
        self.assertTrue(result["reached"]["L5_SHADOW_LEARN"])
        self.assertTrue(result["reached"]["L7_VALIDATE"])
        self.assertFalse(result["reached"]["L9_PROMOTE"])
        self.assertFalse(result["reached"]["L11_REOPEN"])
        self.assertNotIn(foreign, str(result))
        self.assertEqual(json.loads(Operator(self.r).run(
            f":fastpolicy lifecycle {self.eid}"))["updates"],
            result["updates"])

    def test_malformed_manifest_is_unlinked_and_restart_stays_exact(self):
        self.insert('{"source_ids": [bad] /* ' + self.sid + ' */',
                    status="EVALUATED_FAIL")
        self.assertEqual(self.lifecycle()["updates"], [])
        matched = self.insert({"source_ids": [self.sid]}, status="EVALUATED_FAIL")
        self.assertEqual(self.lifecycle()["updates"],
                         [{"id": matched, "status": "EVALUATED_FAIL"}])
        self.assertTrue(self.lifecycle()["reached"]["L11_REOPEN"])
        session = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.r.session, session)
        self.assertEqual(self.lifecycle()["updates"],
                         [{"id": matched, "status": "EVALUATED_FAIL"}])
        other = Operator(self.r).run(":new")
        self.assertNotEqual(other, session)
        with self.assertRaisesRegex(ValueError, "CURRENT_SESSION_EVENT_REQUIRED"):
            self.lifecycle()
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
