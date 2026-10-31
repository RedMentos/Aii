"""Run84 real-SQLite synthetic post-generation guard tests (NO native model)."""
import json
import sqlite3
import unittest

from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_postgen_shadow as guard
from v13.common import dumps


class Run84PostgenTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    def call(self, callback=None, *, opt=True, callback_opt=True, receipt=None):
        if callback is None:
            callback = self.correct
        return guard.evaluate(
            self.r, self.event, self.offers, self.ids, callback,
            operator_opt_in=opt, callback_opt_in=callback_opt,
            approval_receipt=receipt)

    @staticmethod
    def correct(messages, schema):
        return dumps({"action": json.loads(messages[1]["content"])[
            "typed_jef_action"]})

    def test_valid_real_store_shadow_no_output(self):
        before = (self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"],
            self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages")["n"])
        result = self.call()
        self.assertEqual(result["status"], guard.STATUS, result)
        self.assertEqual(result["parsed_action"], "A")
        self.assertTrue(result["source_rechecked"])
        self.assertTrue(result["callback_invoked"])
        self.assertFalse(result["model_called_by_guard"])
        self.assertFalse(result["native_proof"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["real_tty_approved"])
        self.assertEqual(before, (self.r.store.one(
            "SELECT COUNT(*) AS n FROM actions")["n"],
            self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages")["n"]))

    def test_off_and_tty_reject_before_callback(self):
        def forbidden(*args):
            raise AssertionError("CALLBACK_MUST_NOT_RUN")
        self.assertEqual(self.call(forbidden, opt=False)["status"], "OFF")
        self.assertEqual(self.call(forbidden, opt=1)["status"], "OFF")
        self.assertEqual(self.call(forbidden, callback_opt=False)["status"], "OFF")
        self.assertEqual(self.call(forbidden, receipt={"approved": True})[
            "status"], "REAL_TTY_APPROVAL_UNSUPPORTED")

    def test_wrong_action_is_red_not_source_only_fallback(self):
        result = self.call(lambda m, s: '{"action":"B"}')
        self.assertEqual(result["status"], "FORMATTER_ACTION_MISMATCH_RED")
        self.assertTrue(result["source_rechecked"])
        self.assertNotIn("source_only_fallback_action", result)

    def test_duplicate_key_or_malformed_json_is_red(self):
        for raw in ('{"action":"A","action":"B"}', '{"action":"A","x":0}',
                    'A', '{"action":NaN}', "", '{"action":"C"}'):
            with self.subTest(raw=raw):
                self.assertEqual(self.call(lambda m, s: raw)["status"],
                                 "FORMATTER_JSON_RED")

    def test_prompt_mutation_is_red(self):
        def mutate(messages, schema):
            messages[1]["content"] = "{}"
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_PROMPT_OR_SCHEMA_MUTATED_RED")

    def test_schema_mutation_is_red(self):
        def mutate(messages, schema):
            schema["additionalProperties"] = True
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_PROMPT_OR_SCHEMA_MUTATED_RED")

    def test_newer_user_during_callback_is_red(self):
        def mutate(messages, schema):
            self.r.store.event(self.r.session, "Newer USER: change my request")
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_STORE_MUTATION_RED")

    def test_revoked_f1f5_during_callback_is_red(self):
        def mutate(messages, schema):
            self.r.memory.forget(self.ids[0])
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_STORE_MUTATION_RED")

    def test_same_connection_update_restore_is_red(self):
        def mutate(messages, schema):
            db = self.r.store.db
            packet_id = self.offers["B1_DETAIL"]
            row = db.execute("SELECT payload FROM packets WHERE id=?",
                             (packet_id,)).fetchone()
            original = row[0]
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       ('{}', packet_id))
            db.execute("UPDATE packets SET payload=? WHERE id=?",
                       (original, packet_id))
            db.commit()
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_STORE_MUTATION_RED")

    def test_external_connection_noop_update_is_red(self):
        def mutate(messages, schema):
            db_path = self.r.store.db.execute(
                "PRAGMA database_list").fetchone()[2]
            with sqlite3.connect(db_path) as external:
                external.execute("UPDATE packets SET payload=payload WHERE id=?",
                                 (self.offers["B1_DETAIL"],))
            return '{"action":"A"}'
        self.assertEqual(self.call(mutate)["status"],
                         "CALLBACK_STORE_MUTATION_RED")

    def test_preexisting_stale_user_refuses_callback(self):
        self.r.store.event(self.r.session, "A newer user request")
        result = self.call(lambda *args: self.fail("callback invoked"))
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_RED")
        self.assertFalse(result["callback_invoked"])

    def test_callback_exception_is_red(self):
        def fail(*args):
            raise RuntimeError("synthetic failure")
        result = self.call(fail)
        self.assertEqual(result["status"], "CALLBACK_EXCEPTION_RED")
        self.assertEqual(result["error_type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
