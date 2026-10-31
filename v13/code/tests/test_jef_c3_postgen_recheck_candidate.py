"""Post-generation JEF/F1F5 source continuity; real Store, synthetic callback."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.runtime import Runtime
from v13 import jef_c3_postgen_recheck_candidate as guard


class JefC3PostgenRecheckTests(unittest.TestCase):
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
        event = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            event["event_id"], "fact", value, permission="record",
            key=key, scope=scope)
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def sources(self, row):
        name, domain = row["id"], row["domain"]
        policy_key = f"Project {name} archived {domain} policy"
        sheet_key = f"Project {name} latest {domain} option sheet"
        policy = self.record(policy_key, row["b2_source"])
        sheet = self.record(sheet_key, row["b1_source"])
        event = self.r.store.event(self.r.session, row["current"])
        return event, [policy, sheet], policy_key

    def check(self, event, ids, callback, **kwargs):
        return guard.evaluate(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, callback, **kwargs)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("sources", "packets", "memories",
                          "actions", "messages"))

    def assert_safe(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches_by_guard"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["model_called_by_guard"])
        self.assertFalse(result["user_approved"])
        self.assertNotIn("native_output", result)
        self.assertNotIn("messages", result)

    def test_36_calibration_source_verified_matches_and_36_strict_red(self):
        matched = rejected = 0
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            for row in self.calibration:
                event, ids, _ = self.sources(row)
                before = self.counts()
                action = row["oracle_action"]
                ok = self.check(event, ids, lambda _: action,
                                operator_opt_in=True)
                self.assertEqual(ok["status"], "FORMATTER_MATCH_SHADOW")
                self.assertTrue(ok["c3_receiver_success"])
                self.assertTrue(ok["source_rechecked"])
                self.assertTrue(ok["generator_invoked"])
                self.assertIsNone(ok["source_only_fallback_action"])
                self.assertEqual(ok["output_bytes"], len(action))
                self.assert_safe(ok)
                bad = self.check(event, ids, lambda _: "Option " + action,
                                 operator_opt_in=True)
                self.assertEqual(bad["status"], "FORMATTER_MISMATCH_RED")
                self.assertFalse(bad["c3_receiver_success"])
                self.assertTrue(bad["source_only_fallback_verified"])
                self.assertEqual(bad["source_only_fallback_action"], action)
                self.assert_safe(bad)
                self.assertEqual(self.counts(), before)
                matched += 1
                rejected += 1
        self.assertEqual((matched, rejected), (36, 36))

    def test_default_off_integer_one_tty_and_invalid_callback(self):
        event, ids, _ = self.sources(self.calibration[0])
        before = self.counts()
        calls = []
        def callback(_):
            calls.append(1)
            return "A"
        for kwargs, status in (
            ({}, "OFF"),
            ({"operator_opt_in": 1}, "OFF"),
            ({"operator_opt_in": False}, "OFF"),
            ({"operator_opt_in": True,
              "approval_receipt": {"approved": True}},
             "REAL_TTY_APPROVAL_UNSUPPORTED"),
        ):
            result = self.check(event, ids, callback, **kwargs)
            self.assertEqual(result["status"], status)
            self.assert_safe(result)
        invalid = self.check(event, ids, None, operator_opt_in=True)
        self.assertEqual(invalid["status"], "INVALID_GENERATOR")
        self.assertEqual(calls, [])
        self.assertEqual(self.counts(), before)

    def test_stale_before_generation_never_calls_callback(self):
        event, ids, _ = self.sources(self.calibration[0])
        self.r.store.event(self.r.session, "New authoritative user message.")
        calls = []
        result = self.check(event, ids, lambda _: calls.append(1),
                            operator_opt_in=True)
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_RED")
        self.assertEqual(calls, [])
        self.assertIsNone(result["source_only_fallback_action"])
        self.assert_safe(result)

    def test_new_authoritative_user_during_generation_refuses(self):
        event, ids, _ = self.sources(self.calibration[0])
        def callback(_):
            self.r.store.event(self.r.session, "Later authoritative USER.")
            return "A"
        result = self.check(event, ids, callback, operator_opt_in=True)
        self.assertEqual(result["status"],
                         "SOURCE_CHANGED_DURING_GENERATION_RED")
        self.assertFalse(result["source_rechecked"])
        self.assertIsNone(result["source_only_fallback_action"])
        self.assert_safe(result)

    def test_revoked_policy_and_hidden_conflict_during_generation_refuse(self):
        event, ids, policy_key = self.sources(self.calibration[0])
        def revoke(_):
            self.r.memory.forget(ids[1])
            return "A"
        revoked = self.check(event, ids, revoke, operator_opt_in=True)
        self.assertEqual(revoked["status"],
                         "SOURCE_CHANGED_DURING_GENERATION_RED")
        self.assertIsNone(revoked["source_only_fallback_action"])
        self.assert_safe(revoked)

        row = self.calibration[1]
        event2, ids2, key2 = self.sources(row)
        def conflict(_):
            self.record(key2, row["b2_source"], scope="global")
            return row["oracle_action"]
        conflicted = self.check(event2, ids2, conflict,
                                operator_opt_in=True)
        self.assertEqual(conflicted["status"],
                         "SOURCE_CHANGED_DURING_GENERATION_RED")
        self.assertIsNone(conflicted["source_only_fallback_action"])
        self.assert_safe(conflicted)

    def test_event_packet_tamper_during_generation_refuses(self):
        event, ids, _ = self.sources(self.calibration[0])
        def callback(_):
            raw = self.r.store.one(
                "SELECT packet FROM events WHERE id=?",
                (event["event_id"],))["packet"]
            packet = json.loads(raw)
            packet["source_ref"] = dict(event["source_ref"], char_end=0)
            with self.r.store.tx() as db:
                db.execute("UPDATE events SET packet=? WHERE id=?",
                           (json.dumps(packet), event["event_id"]))
            return "A"
        result = self.check(event, ids, callback, operator_opt_in=True)
        self.assertEqual(result["status"],
                         "SOURCE_CHANGED_DURING_GENERATION_RED")
        self.assert_safe(result)

    def test_bad_output_format_and_size_are_red_without_raw_leak(self):
        event, ids, _ = self.sources(self.calibration[0])
        action = self.calibration[0]["oracle_action"]
        for output in ("", action.lower(), " " + action, action + "\n",
                       action + ".", json.dumps({"choice": action}),
                       "A or B", "Option " + action):
            with self.subTest(output=output):
                result = self.check(event, ids, lambda _: output,
                                    operator_opt_in=True)
                self.assertIn(result["status"],
                              ("FORMATTER_MISMATCH_RED", "FORMATTER_OUTPUT_RED"))
                self.assertFalse(result["c3_receiver_success"])
                self.assertEqual(result["source_only_fallback_action"], action)
                self.assert_safe(result)
        for output in (None, b"A", "A" * 513, "\ud800"):
            with self.subTest(output=repr(output)):
                result = self.check(event, ids, lambda _: output,
                                    operator_opt_in=True)
                self.assertEqual(result["status"], "FORMATTER_OUTPUT_RED")
                self.assertFalse(result["c3_receiver_success"])
                self.assert_safe(result)

    def test_generator_exception_refuses_without_fallback(self):
        event, ids, _ = self.sources(self.calibration[0])
        def fail(_):
            raise RuntimeError("private output should not be logged")
        result = self.check(event, ids, fail, operator_opt_in=True)
        self.assertEqual(result["status"], "GENERATOR_EXCEPTION_RED")
        self.assertEqual(result["generator_error_type"], "RuntimeError")
        self.assertIsNone(result["source_only_fallback_action"])
        self.assertNotIn("private output", str(result))
        self.assert_safe(result)

    def test_callback_mutating_prompt_copy_refuses(self):
        event, ids, _ = self.sources(self.calibration[0])
        def mutate(messages):
            messages[0]["content"] = "FORGED"
            return self.calibration[0]["oracle_action"]
        result = self.check(event, ids, mutate, operator_opt_in=True)
        self.assertEqual(result["status"], "CALLBACK_PROMPT_MUTATED_RED")
        self.assertIsNone(result["source_only_fallback_action"])
        self.assert_safe(result)

    def test_cross_session_and_wrong_ref_preflight_refuse(self):
        event, ids, _ = self.sources(self.calibration[0])
        foreign = self.r.store.new_session("Foreign")
        calls = []
        callback = lambda _: calls.append(1)
        result = guard.evaluate(
            self.r.memory, foreign, event["event_id"],
            event["source_ref"], ids, callback, operator_opt_in=True)
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_RED")
        wrong = dict(event["source_ref"], char_end=0)
        result2 = guard.evaluate(
            self.r.memory, self.r.session, event["event_id"],
            wrong, ids, callback, operator_opt_in=True)
        self.assertEqual(result2["status"], "SOURCE_PREFLIGHT_RED")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
