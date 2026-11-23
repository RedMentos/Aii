"""JEF/F1F5 -> C3 typed prompt: real Store, 36-source controls, no native."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13.runtime import Runtime
from v13 import jef_c3_typed_envelope_candidate as bridge


class JefC3TypedEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        rows = cohort.fixtures()
        cohort.validate(rows)
        self.calibration = sorted(
            (x for x in rows if x["partition"] == "calibration"),
            key=lambda x: x["id"])

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

    def setup_sources(self, row, conflict=False):
        name, domain = row["id"], row["domain"]
        policy_key = f"Project {name} archived {domain} policy"
        sheet_key = f"Project {name} latest {domain} option sheet"
        policy = self.record(policy_key, row["b2_source"])
        sheet = self.record(sheet_key, row["b1_source"])
        if conflict:
            self.record(policy_key, row["b2_source"], scope="global")
        event = self.r.store.event(self.r.session, row["current"])
        return event, [policy, sheet]

    def build(self, event, ids, **kwargs):
        return bridge.build_jef_c3_typed_envelope(
            self.r.memory, self.r.session, event["event_id"],
            event["source_ref"], ids, **kwargs)

    def counts(self):
        return tuple(self.r.store.one(
            "SELECT COUNT(*) AS n FROM " + table)["n"]
            for table in ("sources", "packets", "memories", "actions", "messages"))

    def assert_no_authority(self, result):
        self.assertEqual(result["delivery_authority"], 0)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["model_called"])

    def test_36_real_human_source_envelopes_and_exact_formatter(self):
        successes = 0
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            for row in self.calibration:
                event, ids = self.setup_sources(row)
                before = self.counts()
                result = self.build(event, ids, operator_opt_in=True)
                self.assertEqual(result["status"],
                                 "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL")
                self.assertEqual(result["typed_jef_action"], row["oracle_action"])
                self.assertEqual([x["role"] for x in result["messages"]],
                                 ["system", "user"])
                payload = json.loads(result["messages"][1]["content"])
                self.assertEqual(payload["current_source"], row["current"])
                self.assertEqual(payload["policy_source"], row["b2_source"])
                self.assertEqual(payload["sheet_source"], row["b1_source"])
                self.assertEqual(payload["typed_jef_action"], row["oracle_action"])
                self.assertEqual(len(payload["source_ref_sha256"]), 2)
                self.assertEqual(payload["candidate_authority"], 0)
                self.assertNotIn("oracle_action", payload)
                self.assertNotIn("oracle", payload)
                self.assertEqual(self.counts(), before)
                self.assert_no_authority(result)
                accepted = bridge.verify_jef_c3_formatter_output(
                    result, row["oracle_action"])
                self.assertEqual(accepted["status"], "FORMATTER_MATCH_SHADOW")
                self.assertTrue(accepted["formatter_match"])
                self.assert_no_authority(accepted)
                successes += 1
        self.assertEqual(successes, 36)

    def test_stale_user_event_denies_prompt(self):
        event, ids = self.setup_sources(self.calibration[0])
        self.r.store.event(self.r.session, "Later authoritative USER turn.")
        result = self.build(event, ids, operator_opt_in=True)
        self.assertEqual(result["status"], "JEF_CURRENT_SOURCE_RED")
        self.assertNotIn("messages", result)
        self.assert_no_authority(result)

    def test_swapped_and_foreign_source_ids_deny(self):
        event, ids = self.setup_sources(self.calibration[0])
        swapped = self.build(event, ids[::-1], operator_opt_in=True)
        self.assertEqual(swapped["status"], "SOURCE_ORDER_OR_FOREIGN_MEMORY_RED")
        self.assertNotIn("messages", swapped)
        foreign = self.build(event, [ids[0], ids[0]], operator_opt_in=True)
        self.assertEqual(foreign["status"], "INVALID_INPUT")
        self.assertNotIn("messages", foreign)

    def test_revoked_and_hidden_conflicting_source_deny(self):
        event, ids = self.setup_sources(self.calibration[0])
        self.r.memory.forget(ids[1])
        result = self.build(event, ids, operator_opt_in=True)
        self.assertEqual(result["status"], "JEF_CURRENT_SOURCE_RED")
        event2, ids2 = self.setup_sources(self.calibration[1], conflict=True)
        conflict = self.build(event2, ids2, operator_opt_in=True)
        self.assertEqual(conflict["status"], "JEF_CURRENT_SOURCE_RED")
        self.assert_no_authority(conflict)

    def test_forged_approval_and_integer_optin_never_prompt(self):
        event, ids = self.setup_sources(self.calibration[0])
        before = self.counts()
        for kwargs in (
            {}, {"operator_opt_in":1}, {"operator_opt_in":False},
            {"operator_opt_in":True, "approval_receipt":{"approved":True}},
        ):
            with self.subTest(kwargs=kwargs):
                result = self.build(event, ids, **kwargs)
                self.assertIn(result["status"],
                              ("OFF", "REAL_TTY_APPROVAL_UNSUPPORTED"))
                self.assertNotIn("messages", result)
                self.assert_no_authority(result)
        self.assertEqual(self.counts(), before)

    def test_wrong_ref_and_cross_session_deny(self):
        event, ids = self.setup_sources(self.calibration[0])
        ref = dict(event["source_ref"], char_end=0)
        result = bridge.build_jef_c3_typed_envelope(
            self.r.memory, self.r.session, event["event_id"], ref, ids,
            operator_opt_in=True)
        self.assertEqual(result["status"], "JEF_CURRENT_SOURCE_RED")
        foreign = self.r.store.new_session("Foreign")
        result2 = bridge.build_jef_c3_typed_envelope(
            self.r.memory, foreign, event["event_id"], event["source_ref"], ids,
            operator_opt_in=True)
        self.assertEqual(result2["status"], "JEF_CURRENT_SOURCE_RED")

    def test_source_revoked_between_prompt_and_postcheck_denies(self):
        event, ids = self.setup_sources(self.calibration[0])
        original = bridge.decide_current_turn
        calls = [0]
        def mutate(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                self.r.memory.forget(ids[1])
            return original(*args, **kwargs)
        with patch.object(bridge, "decide_current_turn", side_effect=mutate):
            result = self.build(event, ids, operator_opt_in=True)
        self.assertEqual(calls[0], 2)
        self.assertEqual(result["status"], "POST_PROMPT_SOURCE_CHANGED")
        self.assertNotIn("messages", result)

    def test_formatter_wrong_extra_lowercase_json_whitespace_and_forgery_red(self):
        event, ids = self.setup_sources(self.calibration[0])
        env = self.build(event, ids, operator_opt_in=True)
        self.assertEqual(env["status"],
                         "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL")
        answer = env["typed_jef_action"]
        for output in ("", answer.lower() if answer != "NONE" else "none",
                       " " + answer, answer + "\n", answer + ".",
                       json.dumps({"choice":answer}),
                       "A or B", "UNKNOWN", "Choice: " + answer):
            with self.subTest(output=output):
                verdict = bridge.verify_jef_c3_formatter_output(env, output)
                self.assertEqual(verdict["status"], "FORMATTER_MISMATCH_RED")
                self.assertFalse(verdict["formatter_match"])
                self.assert_no_authority(verdict)
        forged = dict(env, messages_sha256="0" * 64)
        self.assertEqual(bridge.verify_jef_c3_formatter_output(
            forged, answer)["status"], "FORMATTER_INPUT_RED")


if __name__ == "__main__":
    unittest.main()
