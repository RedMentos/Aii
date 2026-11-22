"""Run117CW real SQLite callback source recheck, synthetic callbacks only."""
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_jef_range_policy_shadow import TABLE, texts
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13 import jef_c3_source_callback_shadow_candidate as C


class C3LiveCallbackSourceBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = FakeRuntime(self.home)
        row = ("RunCW",) + TABLE[0][1:]
        current, policy, sheet = texts(row)
        self.ids = []
        for key, value in (
            ("Project RunCW archived harbor drones policy", policy),
            ("Project RunCW latest harbor drones option sheet", sheet),
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

    def invoke(self, callback, **kwargs):
        return C.invoke(
            self.r.memory, self.r.session,
            self.event["event_id"], self.event["source_ref"],
            self.ids, callback, operator_opt_in=True, **kwargs)

    def test_live_source_callback_valid_shadow_without_delivery(self):
        calls = []
        def fake(messages, schema):
            calls.append((messages, schema))
            return '{"action":"A"}'
        result = self.invoke(fake)
        self.assertEqual(result["status"], C.READY, result)
        self.assertEqual(result["shadow_action"], "A")
        self.assertEqual(result["model_callback_invocations"], 1)
        self.assertTrue(result["source_rechecked"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["independent_reasoning_proven"])
        self.assertEqual(result["step2"], "UTILITY_FAIL")
        self.assertEqual(result["b3"], "NO_PROMOTION")
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(len(calls), 1)
        messages, schema = calls[0]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertEqual(schema, C.SCHEMA)
        payload = json.loads(messages[1]["content"])
        self.assertNotIn("oracle", payload)
        self.assertNotIn("suggested_action", payload)
        self.assertNotIn("typed_jef_action", payload)
        self.assertFalse(payload["typed_jef_action_visible"])

    def test_callback_revoke_policy_discard_output(self):
        ref = self.r.memory.candidate(self.ids[0], self.r.session)["source_ref"]
        def revoke(messages, schema):
            with self.r.store.tx() as db:
                db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                           (ref["source_id"],))
            return '{"action":"A"}'
        result = self.invoke(revoke)
        self.assertEqual(result["status"], "SOURCE_OR_CALLBACK_MUTATION_RED")
        self.assertNotIn("shadow_action", result)
        self.assertNotIn("raw_output_sha256", result)
        self.assertFalse(result["source_rechecked"])

    def test_newer_user_during_generation_discard_output(self):
        def supersede(messages, schema):
            self.r.store.event(self.r.session, "Project RunCW newer request")
            return '{"action":"B"}'
        result = self.invoke(supersede)
        self.assertEqual(result["status"], "SOURCE_OR_CALLBACK_MUTATION_RED")
        self.assertNotIn("shadow_action", result)

    def test_callback_prompt_mutation_and_side_effects_fail_closed(self):
        def mutate_prompt(messages, schema):
            messages[1]["content"] = "{}"
            return '{"action":"A"}'
        self.assertEqual(self.invoke(mutate_prompt)["status"],
                         "SOURCE_OR_CALLBACK_MUTATION_RED")
        def side_effect(messages, schema):
            self.r.store.log("synthetic-callback", self.event["event_id"],
                             {"untrusted": True})
            return '{"action":"A"}'
        self.assertEqual(self.invoke(side_effect)["status"],
                         "SOURCE_OR_CALLBACK_MUTATION_RED")

    def test_callback_exception_does_not_expose_partial(self):
        def broken(messages, schema):
            raise RuntimeError("PRIVATE_OUTPUT_DO_NOT_ECHO")
        result = self.invoke(broken)
        self.assertEqual(result["status"], "MODEL_CALLBACK_ERROR_RED")
        self.assertEqual(result["callback_error_type"], "RuntimeError")
        self.assertNotIn("PRIVATE_OUTPUT_DO_NOT_ECHO", str(result))
        self.assertNotIn("shadow_action", result)

    def test_strict_output_decoder_rejects_forged_or_malformed(self):
        invalid = [
            "", "A", "Here is A", '{"action":"A","action":"B"}',
            '{"action":"A","extra":1}', '{"action":"UNKNOWN"}',
            '{"action":1}', '{"action":"A","x":NaN}',
            '{"action":"A"}' + " " * 1024,
        ]
        for raw in invalid:
            with self.subTest(raw=raw[:30]):
                self.assertIsNone(C.decode(raw))
        self.assertEqual(C.decode('{"action":"NONE"}'), "NONE")
        for raw in invalid:
            result = self.invoke(lambda m, s, raw=raw: raw)
            self.assertEqual(result["status"], "MODEL_OUTPUT_INVALID_RED")
            self.assertNotIn("shadow_action", result)

    def test_off_and_fake_tty_never_call_callback(self):
        calls = []
        def fake(messages, schema):
            calls.append(True)
            return '{"action":"A"}'
        r = C.invoke(self.r.memory, self.r.session, self.event["event_id"],
                     self.event["source_ref"], self.ids, fake)
        self.assertEqual(r["status"], "OFF")
        r = self.invoke(fake, approval_receipt={"approved": True})
        self.assertEqual(r["status"], "REAL_TTY_APPROVAL_UNSUPPORTED")
        self.assertEqual(calls, [])

    def test_revoked_before_invocation_never_call_callback(self):
        self.r.memory.forget(self.ids[0])
        calls = []
        r = self.invoke(lambda m, s: calls.append(1))
        self.assertEqual(r["status"], "SOURCE_ADMISSION_RED")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
