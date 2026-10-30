"""JEF human receipt integrity: real Store, no native models or optimizer."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class HumanReceiptIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.cfg["learning_mode"] = "SHADOW"
        jo.set_mode(self.r.store, "learn")
        self.e = self.r.store.event(self.r.session, "synthetic human receipt JEF source")
        fp.head(self.r, "skill", self.e, "skill")
        self.d = jo._decision(self.r.store, self.e["event_id"], "skill")
        self.assertIsNotNone(self.d)
        self.assertEqual(jo.after_turn(self.r, self.e,
                         {"skill": {"name": "synthetic_skill"}}, "FINAL",
                         {"coalition": []}), {"skill": "skill"})
        self.assertEqual(len(self.rows()), 1)
        self.r.memory.feedback(self.e["event_id"], "skill", "none", "record")
        self.assertEqual(self.rows(), [], "valid human RECORD must veto self")
        self.feedback = self.r.store.one(
            "SELECT * FROM feedback WHERE event_id=? AND kind='skill' "
            "ORDER BY created DESC LIMIT 1", (self.e["event_id"],))
        self.human = self.r.store.one(
            "SELECT id,payload FROM packets WHERE kind='HumanDecision' AND event_id=? "
            "ORDER BY created DESC LIMIT 1", (self.e["event_id"],))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def rows(self):
        return jo.training_rows(self.r.store, "skill",
                                self.d["context_revision"], set())

    def patch_human(self, key, value):
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET payload=json_set(payload, ?, ?) WHERE id=?",
                      ("$." + key, value, self.human["id"]))

    def assert_no_human_veto(self):
        rows = self.rows()
        self.assertEqual(len(rows), 1, "invalid human receipt cannot veto valid self row")
        self.assertEqual(rows[0][1]["authority"], jo.AUTHORITY)
        self.assertEqual(rows[0][1]["value"], "skill")

    def test_valid_human_record_vetoes_without_learning_permission(self):
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.r.pool.pids(), [])

    def test_tampered_feedback_value_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE feedback SET value='skill' WHERE id=?",
                      (self.feedback["id"],))
        self.assert_no_human_veto()

    def test_tampered_human_packet_value_is_not_human_receipt(self):
        self.patch_human("value", "skill")
        self.assert_no_human_veto()

    def test_tampered_human_packet_permission_is_not_human_receipt(self):
        self.patch_human("learning_permission", "learn")
        self.assert_no_human_veto()

    def test_wrong_source_kind_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET kind='OUTCOME_SELF_LABEL' WHERE id=?",
                      (self.feedback["source_id"],))
        self.assert_no_human_veto()

    def test_wrong_human_source_hash_is_not_human_receipt(self):
        self.patch_human("source_ref.sha256", "0" * 64)
        self.assert_no_human_veto()

    def test_human_packet_event_payload_mismatch_is_not_human_receipt(self):
        self.patch_human("event_id", "evt_forged_other")
        self.assert_no_human_veto()

    def test_deleted_human_source_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (self.feedback["source_id"],))
        self.assert_no_human_veto()

    def test_learning_caller_does_not_veto_on_invalid_receipt(self):
        self.patch_human("value", "skill")
        seen = []
        original = jo.training_rows

        def capture(store, component, revision, human_keys):
            seen.append(set(human_keys))
            return original(store, component, revision, human_keys)

        with patch.object(jo, "training_rows", side_effect=capture), patch.object(
                self.r.guard, "update", return_value="NORMAL"):
            with self.assertRaisesRegex(ValueError, "Je Klasse"):
                self.r.learner.shadow_readout("skill")
        self.assertEqual(seen, [set()],
                         "learning caller must not treat an invalid receipt as human")
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
