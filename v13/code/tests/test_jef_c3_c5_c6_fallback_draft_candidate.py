"""JEF source-only fallback to real SQLite C5/F3 DRAFT, C6 read-only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.runtime import Runtime
from v13 import jef_c3_c5_c6_fallback_draft_candidate as bridge


class JefC3C5C6FallbackDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        rows = cohort.fixtures()
        cohort.validate(rows)
        self.calibration = sorted(
            (r for r in rows if r["partition"] == "calibration"),
            key=lambda r: r["id"])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def record(self, key, value, scope="session"):
        e = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            e["event_id"], "fact", value, permission="record",
            key=key, scope=scope)
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def sources(self, row):
        name, domain = row["id"], row["domain"]
        policy_key = f"Project {name} archived {domain} policy"
        sheet_key = f"Project {name} latest {domain} option sheet"
        ids = [self.record(policy_key, row["b2_source"]),
               self.record(sheet_key, row["b1_source"])]
        event = self.r.store.event(self.r.session, row["current"])
        return event, ids, policy_key

    def stage(self, event, ids, callback, **kwargs):
        return bridge.stage(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, callback, **kwargs)

    def preflight(self, event, ids, staged, **kwargs):
        return bridge.preflight(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, staged, **kwargs)

    def count(self, table, event):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table + " WHERE event_id=?",
            (event["event_id"],))["n"]

    def assert_safe(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["c3_receiver_success"])
        self.assertFalse(result["real_tty_approved"])
        self.assertNotIn("native_output", result)

    def assert_staged(self, event, ids, result, action, origin):
        self.assertEqual(result["status"], bridge.STAGED)
        self.assertEqual(result["source_action"], action)
        self.assertEqual(result["draft_origin"], origin)
        self.assertTrue(result["shadow_draft_may_exist"])
        self.assertEqual(self.count("messages", event), 1)
        self.assertEqual(self.count("actions", event), 1)
        row = self.r.store.one(
            "SELECT role,text,status,metadata FROM messages WHERE id=?",
            (result["draft_message_id"],))
        self.assertEqual((row["role"], row["text"], row["status"]),
                         ("assistant", action, "DRAFT"))
        meta = json.loads(row["metadata"])
        self.assertEqual(meta["origin"], origin)
        self.assertNotIn("native_output", meta)
        self.assertNotIn("delivery_authority", meta)
        self.assert_safe(result)
        c6 = self.preflight(event, ids, result, operator_opt_in=True)
        self.assertEqual(c6["status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assertTrue(c6["preflight_only"])
        self.assertTrue(c6["source_rechecked"])
        self.assertTrue(c6["c5_binding_verified"])
        self.assert_safe(c6)

    def test_36_exact_and_36_source_only_fallback_staged(self):
        exact = fallback = 0
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            for row in self.calibration:
                event, ids, _ = self.sources(row)
                action = row["oracle_action"]
                exact_result = self.stage(
                    event, ids, lambda _: action,
                    operator_opt_in=True, callback_opt_in=True)
                self.assert_staged(
                    event, ids, exact_result, action, "MODEL_EXACT_SHADOW")
                self.assertFalse(exact_result["source_only_fallback"])
                self.assertEqual(exact_result["model_formatter_status"],
                                 "FORMATTER_MATCH_SHADOW")
                exact += 1

                event2 = self.r.store.event(self.r.session, row["current"])
                fallback_result = self.stage(
                    event2, ids, lambda _: "Option " + action,
                    operator_opt_in=True, callback_opt_in=True)
                self.assert_staged(
                    event2, ids, fallback_result, action,
                    "SOURCE_ONLY_FALLBACK_C3_RED")
                self.assertTrue(fallback_result["source_only_fallback"])
                self.assertEqual(fallback_result["model_formatter_status"],
                                 "FORMATTER_MISMATCH_RED")
                fallback += 1
        self.assertEqual((exact, fallback), (36, 36))

    def test_default_off_integer_one_tty_and_invalid_callback(self):
        event, ids, _ = self.sources(self.calibration[0])
        calls = []
        callback = lambda _: calls.append(1)
        for kwargs, expected in (
            ({}, "OFF"),
            ({"operator_opt_in": 1, "callback_opt_in": True}, "OFF"),
            ({"operator_opt_in": True, "callback_opt_in": 1}, "OFF"),
            ({"operator_opt_in": True, "callback_opt_in": True,
              "approval_receipt": {"approved": True}},
             "REAL_TTY_APPROVAL_UNSUPPORTED"),
        ):
            result = self.stage(event, ids, callback, **kwargs)
            self.assertEqual(result["status"], expected)
            self.assert_safe(result)
        invalid = self.stage(event, ids, None,
                             operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(invalid["status"], "INVALID_CALLBACK")
        self.assertEqual(calls, [])
        self.assertEqual(self.count("messages", event), 0)

    def test_duplicate_output_prevents_callback(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        first = self.stage(event, ids, lambda _: row["oracle_action"],
                           operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(first["status"], bridge.STAGED)
        calls = []
        second = self.stage(event, ids, lambda _: calls.append(1),
                            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(second["status"], "EXISTING_OUTPUT_OR_ACTION_RED")
        self.assertFalse(second["callback_invoked"])
        self.assertEqual(calls, [])
        self.assertEqual(self.count("messages", event), 1)
        self.assertEqual(self.count("actions", event), 1)

    def test_stale_user_and_revoked_source_during_callback_never_stage(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        def newer(_):
            self.r.store.event(self.r.session, "New USER supersedes.")
            return row["oracle_action"]
        stale = self.stage(event, ids, newer,
                           operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(stale["status"], "JEF_C3_GENERATION_RED")
        self.assertEqual(self.count("messages", event), 0)
        self.assert_safe(stale)

        event2, ids2, _ = self.sources(self.calibration[1])
        def revoke(_):
            self.r.memory.forget(ids2[1])
            return self.calibration[1]["oracle_action"]
        revoked = self.stage(event2, ids2, revoke,
                             operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(revoked["status"], "JEF_C3_GENERATION_RED")
        self.assertEqual(self.count("messages", event2), 0)
        self.assert_safe(revoked)

    def test_callback_exception_and_oversized_no_draft(self):
        event, ids, _ = self.sources(self.calibration[0])
        def fail(_):
            raise ValueError("not for logs")
        for callback in (fail, lambda _: "A" * 513):
            result = self.stage(event, ids, callback,
                                operator_opt_in=True, callback_opt_in=True)
            self.assertEqual(result["status"], "JEF_C3_GENERATION_RED")
            self.assertEqual(self.count("messages", event), 0)
            self.assertEqual(self.count("actions", event), 0)
            self.assert_safe(result)

    def test_source_conflict_during_callback_refuses_draft(self):
        row = self.calibration[0]
        event, ids, key = self.sources(row)
        def conflict(_):
            self.record(key, row["b2_source"], scope="global")
            return row["oracle_action"]
        result = self.stage(event, ids, conflict,
                            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "JEF_C3_GENERATION_RED")
        self.assertEqual(self.count("messages", event), 0)
        self.assert_safe(result)

    def test_stale_user_or_revoked_sheet_after_draft_denies_c6(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        staged = self.stage(event, ids, lambda _: row["oracle_action"],
                            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(staged["status"], bridge.STAGED)
        self.r.store.event(self.r.session, "New authoritative user event.")
        stale = self.preflight(event, ids, staged, operator_opt_in=True)
        self.assertNotEqual(stale["status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assert_safe(stale)

        row2 = self.calibration[1]
        event2, ids2, _ = self.sources(row2)
        staged2 = self.stage(event2, ids2, lambda _: row2["oracle_action"],
                             operator_opt_in=True, callback_opt_in=True)
        self.r.memory.forget(ids2[1])
        revoked = self.preflight(event2, ids2, staged2, operator_opt_in=True)
        self.assertNotEqual(revoked["status"], "NEEDS_REAL_TTY_APPROVAL")
        self.assert_safe(revoked)

    def test_draft_text_and_metadata_tamper_deny_c6(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        staged = self.stage(event, ids, lambda _: row["oracle_action"],
                            operator_opt_in=True, callback_opt_in=True)
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET text=? WHERE id=?",
                       ("FORGED", staged["draft_message_id"]))
        red = self.preflight(event, ids, staged, operator_opt_in=True)
        self.assertEqual(red["status"], "DRAFT_BINDING_RED")
        self.assert_safe(red)
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET text=?,metadata=? WHERE id=?",
                       (row["oracle_action"], '{"shadow":true}',
                        staged["draft_message_id"]))
        red2 = self.preflight(event, ids, staged, operator_opt_in=True)
        self.assertEqual(red2["status"], "DRAFT_METADATA_OR_SOURCE_RED")
        self.assert_safe(red2)

    def test_c5_action_corollary_and_intent_tamper_deny_c6(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        staged = self.stage(event, ids, lambda _: row["oracle_action"],
                            operator_opt_in=True, callback_opt_in=True)
        with self.r.store.tx() as db:
            db.execute("UPDATE actions SET expected=? WHERE id=?",
                       ('{"type":"FORGED"}', staged["c5_action_id"]))
        self.assertEqual(
            self.preflight(event, ids, staged, operator_opt_in=True)["status"],
            "C5_F3_BINDING_RED")

        event2, ids2, _ = self.sources(self.calibration[1])
        staged2 = self.stage(event2, ids2,
                             lambda _: self.calibration[1]["oracle_action"],
                             operator_opt_in=True, callback_opt_in=True)
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? "
                       "WHERE kind='CorollaryCopy' AND event_id=?",
                       ('{"self_caused":false}', event2["event_id"]))
        self.assertEqual(
            self.preflight(event2, ids2, staged2, operator_opt_in=True)["status"],
            "C5_F3_BINDING_RED")

        event3, ids3, _ = self.sources(self.calibration[2])
        staged3 = self.stage(event3, ids3,
                             lambda _: self.calibration[2]["oracle_action"],
                             operator_opt_in=True, callback_opt_in=True)
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? "
                       "WHERE kind='ActionIntent' AND event_id=?",
                       ('{"action_type":"FORGED"}', event3["event_id"]))
        self.assertEqual(
            self.preflight(event3, ids3, staged3, operator_opt_in=True)["status"],
            "C5_F3_BINDING_RED")

    def test_forged_stage_prompt_or_tty_receipt_refuses_c6(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        staged = self.stage(event, ids, lambda _: row["oracle_action"],
                            operator_opt_in=True, callback_opt_in=True)
        forged = dict(staged, prompt_sha256="0" * 64)
        self.assertEqual(
            self.preflight(event, ids, forged, operator_opt_in=True)["status"],
            "SOURCE_PROMPT_CHANGED_AFTER_DRAFT")
        tty = self.preflight(
            event, ids, staged, operator_opt_in=True,
            approval_receipt={"approved": True})
        self.assertEqual(tty["status"], "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assert_safe(tty)

    def test_cross_session_and_wrong_ref_do_not_stage(self):
        row = self.calibration[0]
        event, ids, _ = self.sources(row)
        foreign = self.r.store.new_session("Foreign")
        callback = lambda _: row["oracle_action"]
        result = bridge.stage(
            self.r.memory, foreign, event["event_id"],
            event["source_ref"], ids, callback,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "JEF_C3_GENERATION_RED")
        wrong = dict(event["source_ref"], char_end=0)
        result2 = bridge.stage(
            self.r.memory, self.r.session, event["event_id"],
            wrong, ids, callback,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result2["status"], "JEF_C3_GENERATION_RED")
        self.assertEqual(self.count("messages", event), 0)


if __name__ == "__main__":
    unittest.main()
