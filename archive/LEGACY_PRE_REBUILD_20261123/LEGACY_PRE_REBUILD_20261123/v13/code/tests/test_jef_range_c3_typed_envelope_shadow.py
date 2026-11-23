"""Run75 JEF range->C3 typed formatter envelope, real Store no native calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from tests.test_jef_range_policy_shadow import TABLE, texts
from v13 import jef_range_c3_typed_envelope_shadow as bridge
from v13.common import dumps


class TypedRangeEnvelope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = cli.Runtime(Path(self.tmp.name))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prepare(self, row):
        current, policy, sheet = texts(row)
        project, domain = row[:2]
        ids = []
        for key, value in (
            (f"Project {project} archived {domain} policy", policy),
            (f"Project {project} latest {domain} option sheet", sheet),
        ):
            e = self.r.store.event(self.r.session, "Record: " + key)
            mid = self.r.memory.feedback(
                e["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            self.r.memory.candidate(mid, self.r.session)
            ids.append(mid)
        event = self.r.store.event(self.r.session, current)
        return event, ids

    def build(self, event, ids, **kw):
        return bridge.build(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, operator_opt_in=True, **kw)

    def test_six_source_authenticated_formatter_only_envelopes(self):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            for row in TABLE:
                event, ids = self.prepare(row)
                result = self.build(event, ids)
                self.assertEqual(result["status"], bridge.STATUS)
                self.assertEqual(result["typed_jef_action"], row[-1])
                self.assertTrue(result["human_source_lineage_verified"])
                self.assertTrue(result["formatter_only"])
                self.assertFalse(result["independent_reasoning_proven"])
                self.assertFalse(result["model_called"])
                self.assertEqual(result["delivery_authority"], 0)
                self.assertEqual(result["learning_authority"], 0)
                self.assertFalse(result["output_committed"])
                self.assertFalse(result["real_tty_approved"])
                self.assertEqual(result["jepa_weight"], 0)
                self.assertEqual(result["messages_sha256"],
                                 bridge._sha(dumps(result["messages"]).encode()))
                payload = json.loads(result["messages"][1]["content"])
                self.assertEqual(payload["typed_jef_action"], row[-1])
                self.assertTrue(payload["human_source_lineage_verified"])
                self.assertEqual(len(payload["source_ref_sha256"]), 2)
                for text in texts(row):
                    self.assertNotIn(text, dumps(result))
                self.assertEqual(self.r.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"], 0)

    def test_off_and_tty_receipt_refuse_without_reading_sources(self):
        self.assertEqual(bridge.build(None,None,None,None,None)["status"],"OFF")
        self.assertEqual(bridge.build(None,None,None,None,None,
                         operator_opt_in=1)["status"],"OFF")
        self.assertEqual(bridge.build(None,None,None,None,None,
                         operator_opt_in=True,approval_receipt={"ok":True})
                         ["status"],"REAL_TTY_APPROVAL_UNSUPPORTED")

    def test_stale_user_and_revoked_memory_fail_closed(self):
        event, ids = self.prepare(TABLE[0])
        self.r.store.event(self.r.session, "new authoritative USER request")
        self.assertEqual(self.build(event, ids)["status"],
                         "F1F5_RANGE_SOURCE_ADMISSION_RED")
        event, ids = self.prepare(TABLE[1])
        self.r.memory.forget(ids[0])
        self.assertEqual(self.build(event, ids)["status"],
                         "F1F5_RANGE_SOURCE_ADMISSION_RED")

    def test_wrong_memory_and_duplicate_ids_fail_closed(self):
        event, ids = self.prepare(TABLE[2])
        self.assertEqual(self.build(event, ids[::-1])["status"], bridge.STATUS)
        self.assertEqual(self.build(event, [ids[0],ids[0]])["status"],
                         "F1F5_RANGE_SOURCE_ADMISSION_RED")
        self.assertEqual(self.build(event, ["mem_invalid",ids[1]])["status"],
                         "F1F5_RANGE_SOURCE_ADMISSION_RED")


if __name__ == "__main__":
    unittest.main()
