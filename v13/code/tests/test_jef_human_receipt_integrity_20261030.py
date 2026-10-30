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

    def receipt_valid(self):
        feedback = self.r.store.one("SELECT * FROM feedback WHERE id=?",
                                    (self.feedback["id"],))
        human = json.loads(self.r.store.one(
            "SELECT payload FROM packets WHERE id=?",
            (self.human["id"],))["payload"])
        return jo._valid_human_receipt(self.r.store, feedback, human, self.d)

    def assert_suspect_blocks_self_but_is_not_valid_human(self):
        self.assertFalse(self.receipt_valid(),
                         "corrupt receipt cannot enter explicit-human optimizer")
        self.assertEqual(self.rows(), [],
                         "active suspect human feedback must conservatively veto self")

    def test_valid_human_record_vetoes_without_learning_permission(self):
        self.assertTrue(self.receipt_valid())
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.r.pool.pids(), [])

    def test_tampered_feedback_value_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE feedback SET value='skill' WHERE id=?",
                      (self.feedback["id"],))
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_tampered_human_packet_value_is_not_human_receipt(self):
        self.patch_human("value", "skill")
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_tampered_human_packet_permission_is_not_human_receipt(self):
        self.patch_human("learning_permission", "learn")
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_wrong_source_kind_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET kind='OUTCOME_SELF_LABEL' WHERE id=?",
                      (self.feedback["source_id"],))
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_wrong_human_source_hash_is_not_human_receipt(self):
        self.patch_human("source_ref.sha256", "0" * 64)
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_human_packet_event_payload_mismatch_is_not_human_receipt(self):
        self.patch_human("event_id", "evt_forged_other")
        self.assert_suspect_blocks_self_but_is_not_valid_human()

    def test_deleted_human_source_is_not_human_receipt(self):
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (self.feedback["source_id"],))
        self.assertFalse(self.receipt_valid())
        self.assertEqual(len(self.rows()), 1,
                         "explicit revocation removes the active human veto")

    def test_learning_caller_does_not_veto_on_invalid_receipt(self):
        self.patch_human("value", "skill")
        seen = []
        admitted_self = []
        original = jo.training_rows

        def capture(store, component, revision, human_keys):
            seen.append(set(human_keys))
            result = original(store, component, revision, human_keys)
            admitted_self.extend(result)
            return result

        with patch.object(jo, "training_rows", side_effect=capture), patch.object(
                self.r.guard, "update", return_value="NORMAL"):
            with self.assertRaisesRegex(ValueError, "Je Klasse"):
                self.r.learner.shadow_readout("skill")
        self.assertEqual(seen, [set()],
                         "invalid receipt cannot enter human training set")
        self.assertEqual(admitted_self, [],
                         "suspect active human record must still veto self learning")
        self.assertEqual(self.r.pool.pids(), [])


if __name__ == "__main__":
    unittest.main()
