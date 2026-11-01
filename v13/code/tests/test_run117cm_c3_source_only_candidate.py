"""Run117CM real-Store source-only C3 envelope, no native model or output."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_run52_b1b2_cross_turn import FakeRuntime
from tests.test_jef_range_policy_shadow import TABLE, texts
from v13 import jef_c3_source_only_shadow_candidate as C


class C3SourceOnlyCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = FakeRuntime(Path(self.tmp.name))
        row = ("Harbor",) + TABLE[0][1:]
        current, policy, sheet = texts(row)
        self.ids = []
        for key, value in (
            ("Project Harbor archived harbor drones policy", policy),
            ("Project Harbor latest harbor drones option sheet", sheet),
        ):
            e = self.r.store.event(self.r.session, "Record: " + key)
            mid = self.r.memory.feedback(
                e["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            self.r.memory.candidate(mid, self.r.session)
            self.ids.append(mid)
        self.event = self.r.store.event(self.r.session, current)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def build(self, ids=None, opt=True, receipt=None, session=None):
        return C.build(
            self.r.memory, self.r.session if session is None else session,
            self.event["event_id"], self.event["source_ref"],
            self.ids if ids is None else ids,
            operator_opt_in=opt, approval_receipt=receipt)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("packets", "actions", "messages"))

    def test_source_only_prompt_is_deterministic_and_oracle_hidden(self):
        before = self.counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            first = self.build()
            second = self.build(ids=self.ids[::-1])
        self.assertEqual(first["status"], C.STATUS, first)
        self.assertEqual(first["messages_sha256"], second["messages_sha256"])
        self.assertEqual(self.counts(), before)
        self.assertFalse(first["oracle_action_visible"])
        self.assertFalse(first["independent_reasoning_proven"])
        self.assertFalse(first["model_called"])
        self.assertFalse(first["output_committed"])
        self.assertEqual(first["delivery_authority"], 0)
        self.assertEqual(first["learning_authority"], 0)
        self.assertEqual(first["tool_dispatches"], 0)
        self.assertNotIn("suggested_action", first)
        self.assertNotIn("typed_jef_action", first)
        payload = json.loads(first["messages"][1]["content"])
        self.assertFalse(payload["typed_jef_action_visible"])
        self.assertNotIn("typed_jef_action", payload)
        self.assertNotIn("expected_action", payload)
        self.assertEqual([m["role"] for m in first["messages"]],
                         ["system", "user"])
        self.assertIn("Project Harbor", payload["policy"]["text"])
        self.assertIn("Project Harbor", payload["sheet"]["text"])
        self.assertIn("Project Harbor", payload["current"]["text"])

    def test_off_invalid_opt_in_and_fake_approval(self):
        self.assertEqual(self.build(opt=False)["status"], "OFF")
        self.assertEqual(self.build(opt=1)["status"], "OFF")
        self.assertEqual(self.build(receipt={"approved": True})["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(self.build(ids=[self.ids[0], self.ids[0]])["status"],
                         "INVALID_SOURCE_INPUT")

    def test_forgotten_policy_and_foreign_session_fail_closed(self):
        self.assertNotEqual(self.build(session="foreign")["status"], C.STATUS)
        self.r.memory.forget(self.ids[0])
        self.assertEqual(self.build()["status"], "HUMAN_SOURCE_ADMISSION_RED")

    def test_stale_current_user_fails_closed(self):
        self.r.store.event(self.r.session, "Project Harbor newer correction")
        self.assertEqual(self.build()["status"], "HUMAN_SOURCE_ADMISSION_RED")

    def test_source_revocation_during_composition_fails_closed(self):
        original = C.admit
        called = [0]
        source = self.r.memory.candidate(self.ids[0], self.r.session)["source_ref"]

        def injected(*args, **kwargs):
            result = original(*args, **kwargs)
            called[0] += 1
            if called[0] == 1:
                with self.r.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (source["source_id"],))
            return result

        with patch.object(C, "admit", side_effect=injected):
            result = self.build()
        self.assertNotEqual(result["status"], C.STATUS)
        self.assertFalse(result["model_called"])
        self.assertEqual(result["delivery_authority"], 0)

    def test_payload_cap_fails_closed_without_model(self):
        with patch.object(C, "MAX_PAYLOAD_BYTES", 10):
            self.assertEqual(self.build()["status"],
                             "SOURCE_ONLY_PAYLOAD_TOO_LARGE_RED")


if __name__ == "__main__":
    unittest.main()
