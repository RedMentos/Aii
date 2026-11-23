"""Run117AD model-free, real SQLite persisted Body/JEF/ContextOS C3 postgen."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_span_c3_postgen_shadow_candidate import evaluate, PASS
from v13.common import dumps
from v13.context_os import controller

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json")
FIXTURE_SHA = "cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d"


class PostgenBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
        cls.rows = json.loads(FIXTURE.read_text())["rows"]

    def setUp(self):
        self.make(self.rows[0])

    def make(self, row):
        self.tmp = tempfile.TemporaryDirectory()
        self.row = row
        self.r = QuoteRuntime(Path(self.tmp.name) / "home", row)
        self.r.cfg.update(OVERRIDES)
        self.prior = self.r.store.event(self.r.session, row["prior"])
        self.current = self.r.store.event(self.r.session, row["current"])
        consumer = TopicPartitionOfferConsumer(self.r)
        self.ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            offer = consumer.guarded_offer(
                role, self.current, 0, time.monotonic() + 30,
                operator_opt_in=True)
            assert offer["status"] == "SHADOW_OFFER_PRODUCED", offer
            self.ids[role] = offer["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def call(self, callback=None, **kw):
        if callback is None:
            candidate = self.row["oracle"]
            callback = lambda _: dumps(candidate)
        flags = {"operator_opt_in": True, "callback_opt_in": True}
        flags.update(kw)
        return evaluate(self.r, self.prior, self.current, self.ids,
                        callback, **flags)

    def assert_safe(self, result):
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["body_model_quote_verified"])
        self.assertFalse(result["body_hypotheses_are_facts"])
        self.assertEqual(result["age0"], "RECORD_ONLY")
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["whole_system_complete"])

    def test_six_rows_real_store_synthetic_callback(self):
        for index, row in enumerate(self.rows):
            with self.subTest(row=row["id"]):
                if index:
                    self.tearDown()
                    self.make(row)
                prior_calls = dict(self.r.calls)
                result = self.call()
                self.assertEqual(result["status"], PASS, result)
                self.assertTrue(result["source_rechecked"])
                self.assertTrue(result["formatter_match_shadow"])
                self.assertEqual(self.r.calls, prior_calls)
                self.assertEqual(result["offer_packet_ids"], self.ids)
                self.assertEqual(result["source_refs"],
                                 [self.prior["source_ref"],
                                  self.current["source_ref"]])
                self.assertEqual(result["output_sha256"],
                                 hashlib.sha256(
                                     dumps(row["oracle"]).encode()).hexdigest())
                self.assertIsNotNone(self.r.store.one(
                    "SELECT id FROM packets WHERE id=? AND kind='ContextPlan'",
                    (result["context_plan_packet_id"],)))
                self.assertEqual(self.r.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"], 0)
                self.assert_safe(result)

    def test_off_does_not_write_plan_or_call(self):
        called = []
        before = self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"]
        for kw in ({"operator_opt_in": False},
                   {"callback_opt_in": False}):
            result = self.call(lambda _: called.append(1), **kw)
            self.assertEqual(result["status"], "OFF")
            self.assert_safe(result)
        self.assertEqual(called, [])
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"],
            before)

    def test_active_contextos_refuses_callback(self):
        controller(self.r).set_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        called = []
        result = self.call(lambda _: called.append(1))
        self.assertEqual(result["status"], "BRIDGE_PREFLIGHT_RED")
        self.assertEqual(called, [])
        self.assert_safe(result)

    def test_stale_correction_refuses_callback(self):
        self.r.store.event(self.r.session, "Project Helix correction: cancel options.")
        called = []
        result = self.call(lambda _: called.append(1))
        self.assertEqual(result["status"], "BRIDGE_PREFLIGHT_RED")
        self.assertEqual(called, [])

    def test_deleted_source_refuses_callback(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior["source_ref"]["source_id"],))
        called = []
        result = self.call(lambda _: called.append(1))
        self.assertEqual(result["status"], "BRIDGE_PREFLIGHT_RED")
        self.assertEqual(called, [])

    def test_swapped_offer_ids_refused(self):
        self.ids = {"B1_DETAIL": self.ids["B2_GIST"],
                    "B2_GIST": self.ids["B1_DETAIL"]}
        called = []
        result = self.call(lambda _: called.append(1))
        self.assertEqual(result["status"], "BRIDGE_PREFLIGHT_RED")
        self.assertEqual(called, [])

    def test_callback_prompt_mutation(self):
        def change(messages):
            messages[1]["content"] = "{}"
            return dumps(self.row["oracle"])
        result = self.call(change)
        self.assertEqual(result["status"], "CALLBACK_PROMPT_MUTATED_RED")
        self.assert_safe(result)

    def test_callback_late_user_correction(self):
        def change(_):
            self.r.store.event(
                self.r.session, "Project Helix correction: cancel old request.")
            return dumps(self.row["oracle"])
        result = self.call(change)
        self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
        self.assert_safe(result)

    def test_callback_offer_mutation(self):
        def change(_):
            row = self.r.store.one(
                "SELECT payload FROM packets WHERE id=?",
                (self.ids["B1_DETAIL"],))
            data = json.loads(row["payload"])
            data["offer"]["summary"] = "FORGED"
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?",
                           (dumps(data), self.ids["B1_DETAIL"]))
            return dumps(self.row["oracle"])
        result = self.call(change)
        self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
        self.assert_safe(result)

    def test_callback_context_plan_mutation(self):
        def change(messages):
            # The callback sees only the prompt, not authority. Locate the
            # stored ContextPlan ID embedded in the user-role data.
            pid = json.loads(messages[1]["content"])["context_plan_packet_id"]
            row = self.r.store.one(
                "SELECT payload FROM packets WHERE id=?", (pid,))
            plan = json.loads(row["payload"])
            plan["provenance"] = []
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?",
                           (dumps(plan), pid))
            return dumps(self.row["oracle"])
        result = self.call(change)
        self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
        self.assert_safe(result)

    def test_callback_offer_id_dict_mutation(self):
        def change(_):
            self.ids["B1_DETAIL"] = self.ids["B2_GIST"]
            return dumps(self.row["oracle"])
        result = self.call(change)
        self.assertEqual(result["status"], "CALLBACK_OFFER_IDS_MUTATED_RED")
        self.assert_safe(result)

    def test_mismatched_candidate(self):
        raw = '{"choice":"B","remaining":50}'
        result = self.call(lambda _: raw)
        self.assertEqual(result["status"], "FORMATTER_CANDIDATE_MISMATCH_RED")
        self.assertNotIn("output_sha256", result)
        self.assert_safe(result)

    def test_malformed_duplicate_bool_nonfinite_extra_oversize(self):
        bad = ('{"choice":"A","choice":"B","remaining":50}',
               '{"choice":"A","remaining":true}',
               '{"choice":"A","remaining":NaN}',
               '{"choice":"A","remaining":50,"approved":true}',
               '{"choice":"A","remaining":-1}',
               '{"choice":"A","remaining":50}' + ' ' * 300,
               'BACKTICKS: {"choice":"A","remaining":50}',
               '{"choice":"A","remaining":null}')
        for raw in bad:
            with self.subTest(raw=raw[:35]):
                result = self.call(lambda _: raw)
                self.assertEqual(result["status"], "FORMATTER_JSON_RED", result)
                self.assert_safe(result)

    def test_callback_exception_and_approval_refused(self):
        def bad(_):
            raise RuntimeError("synthetic failure")
        result = self.call(bad)
        self.assertEqual(result["status"], "CALLBACK_EXCEPTION_RED")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assert_safe(result)
        called = []
        result = self.call(lambda _: called.append(1),
                           approval_receipt={"approved": True})
        self.assertEqual(result["status"],
                         "REAL_TTY_APPROVAL_UNSUPPORTED_RED")
        self.assertEqual(called, [])

    def test_invalid_generator_and_offer_ids(self):
        self.assertEqual(self.call(callback="not a callable")["status"],
                         "INVALID_GENERATOR_RED")
        self.ids["extra"] = "forged"
        result = self.call()
        self.assertEqual(result["status"], "OFFER_ID_SHAPE_RED")
        self.assert_safe(result)


if __name__ == "__main__":
    unittest.main()
