"""Run117 real SQLite source-bound C3 postgen SHADOW tests (synthetic C3).

No native inference or human approval; callbacks are controlled test doubles.
"""
import json
import sqlite3
from pathlib import Path
import tempfile
import time
import unittest

from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.common import dumps
from v13.context_os import controller
from v13.jef_b1b2_c3_role_postgen_shadow_candidate import evaluate, PASS
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime


class WrongQuoteBody:
    def __init__(self, role):
        self.role = role
        self.last_metrics = {"status": "FINAL"}

    def generate(self, messages, *args, **kwargs):
        return [json.dumps({"summary": "Option B wins (wrong synthetic guess)",
                            "quotes": ["INVENTED_NON_SOURCE_QUOTE"],
                            "uncertainty": "high", "needs_reentry": True})]


class Runtime(FakeRuntime):
    def _body(self, role):
        return WrongQuoteBody(role)


class PostgenRoleBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name) / "home")
        self.r.cfg.update(OVERRIDES)
        consumer = TopicPartitionOfferConsumer(self.r)
        self.prior = self.r.store.event(
            self.r.session, "Project Kairo. Budget 200 euros. Deadline 5 days. "
            "Local-only requirement: true. These are the binding project rules.")
        for role in ("B1_DETAIL", "B2_GIST"):
            x = consumer.guarded_offer(role, self.prior, 0,
                                       time.monotonic() + 30, operator_opt_in=True)
            self.assertEqual(x["status"], "SHADOW_OFFER_PRODUCED")
        self.current = self.r.store.event(
            self.r.session, "Project Kairo. Apply the earlier project rules. "
            "Option A costs 190 euros, takes 4 days, and is local. "
            "Option B costs 170 euros, takes 7 days, and is local. "
            "Choose the cheapest eligible option and state its remaining budget.")
        self.ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            x = consumer.guarded_offer(role, self.current, 0,
                                       time.monotonic() + 30, operator_opt_in=True)
            self.assertEqual(x["status"], "SHADOW_OFFER_PRODUCED")
            self.ids[role] = x["offer_packet_id"]

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def run_guard(self, generator=lambda _: '{"choice":"A","remaining":10}',
                  **kwargs):
        return evaluate(self.r, self.prior, self.current, self.ids, generator,
                        **({"operator_opt_in": True, "callback_opt_in": True}
                           | kwargs))

    def assert_no_authority(self, result):
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["native_proof"])
        self.assertFalse(result["redmi_measured"])
        self.assertFalse(result["whole_system_complete"])

    def test_off_never_invokes_or_creates_plan(self):
        before = self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"]
        called = []
        r = self.run_guard(lambda _: called.append(True), operator_opt_in=False)
        self.assertEqual(r["status"], "OFF")
        self.assertEqual(called, [])
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")["n"], before)
        self.assert_no_authority(r)

    def test_real_store_wrong_body_correct_exact_formatter(self):
        before_actions = self.r.store.one("SELECT COUNT(*) AS n FROM actions")["n"]
        r = self.run_guard()
        self.assertEqual(r["status"], PASS, r)
        self.assertTrue(r["callback_invoked"])
        self.assertTrue(r["source_rechecked"])
        self.assertTrue(r["formatter_match_shadow"])
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM actions")["n"], before_actions)
        self.assert_no_authority(r)

    def test_candidate_mismatch_refused_without_fallback_output(self):
        for raw in ('{"choice":"B","remaining":30}',
                    '{"choice":"A","remaining":11}',
                    '{"choice":"NONE","remaining":null}'):
            with self.subTest(raw=raw):
                r = self.run_guard(lambda _: raw)
                self.assertEqual(r["status"], "FORMATTER_CANDIDATE_MISMATCH_RED", r)
                self.assertNotIn("parsed_action", r)
                self.assertNotIn("output_sha256", r)
                self.assert_no_authority(r)

    def test_malformed_duplicate_extra_bool_nonfinite_and_oversize_refused(self):
        cases = ('{"choice":"A","choice":"B","remaining":10}',
                 '{"choice":"A","remaining":10,"approved":true}',
                 '{"choice":"A","remaining":true}',
                 '{"choice":"A","remaining":NaN}',
                 '{"choice":"NONE","remaining":10}',
                 '{"choice":"A","remaining":-1}',
                 '{"choice":"A","remaining":10}' + " " * 300,
                 '```json\n{"choice":"A","remaining":10}\n```',
                 '{"choice":"A","remaining":10} trailing')
        for raw in cases:
            with self.subTest(raw=raw[:50]):
                r = self.run_guard(lambda _: raw)
                self.assertEqual(r["status"], "FORMATTER_JSON_RED", r)
                self.assert_no_authority(r)

    def test_callback_mutating_prompt_refused(self):
        def change(messages):
            messages[1]["content"] = "{}"
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(change)
        self.assertEqual(r["status"], "CALLBACK_PROMPT_MUTATED_RED", r)
        self.assert_no_authority(r)

    def test_late_user_correction_refused(self):
        def correction(_):
            self.r.store.event(self.r.session, "Project Kairo. Cancel that request.")
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(correction)
        self.assertIn(r["status"], ("CALLBACK_STORE_CHANGED_RED", "POSTGEN_SOURCE_OR_OFFER_CHANGED_RED"))
        self.assert_no_authority(r)

    def test_late_offer_tamper_refused(self):
        def tamper(_):
            pid = self.ids["B1_DETAIL"]
            row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (pid,))
            data = json.loads(row["payload"])
            data["offer"]["summary"] = "FORGED"
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?", (dumps(data), pid))
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(tamper)
        self.assertEqual(r["status"], "CALLBACK_STORE_CHANGED_RED", r)
        self.assert_no_authority(r)

    def test_late_context_plan_tamper_refused(self):
        def tamper(_):
            row = self.r.store.one("SELECT id,payload FROM packets WHERE kind='ContextPlan' ORDER BY rowid DESC LIMIT 1")
            data = json.loads(row["payload"])
            data["provenance"] = []
            with self.r.store.tx() as db:
                db.execute("UPDATE packets SET payload=? WHERE id=?", (dumps(data), row["id"]))
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(tamper)
        self.assertEqual(r["status"], "CALLBACK_STORE_CHANGED_RED", r)
        self.assert_no_authority(r)

    def test_deleted_source_before_generator_no_callback(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?", (self.prior["source_ref"]["source_id"],))
        called = []
        r = self.run_guard(lambda _: called.append(True))
        self.assertEqual(r["status"], "SOURCE_PREFLIGHT_RED", r)
        self.assertEqual(called, [])
        self.assert_no_authority(r)

    def test_active_context_os_and_approval_refused(self):
        r = self.run_guard(approval_receipt={"approved": True})
        self.assertEqual(r["status"], "REAL_TTY_APPROVAL_UNSUPPORTED_RED")
        controller(self.r).set_mode("ACTIVE", authority="EXPLICIT_HUMAN")
        r = self.run_guard()
        self.assertEqual(r["status"], "SOURCE_PREFLIGHT_RED", r)
        self.assert_no_authority(r)

    def test_external_connection_write_detected(self):
        dbfile = self.r.store.db.execute("PRAGMA database_list").fetchone()[2]
        def external(_):
            with sqlite3.connect(dbfile) as db:
                db.execute("UPDATE packets SET payload=payload || ' ' WHERE id=?",
                           (self.ids["B2_GIST"],))
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(external)
        self.assertEqual(r["status"], "CALLBACK_STORE_CHANGED_RED", r)
        self.assert_no_authority(r)

    def test_external_source_blob_tamper_detected(self):
        source = self.prior["source_ref"]["sha256"]
        blob = Path(self.r.store.home) / "data/blobs" / source
        def tamper(_):
            blob.write_bytes(b"forged content")
            return '{"choice":"A","remaining":10}'
        r = self.run_guard(tamper)
        self.assertEqual(r["status"], "POSTGEN_SOURCE_OR_OFFER_CHANGED_RED", r)
        self.assert_no_authority(r)

    def test_generator_exception_and_invalid_generator(self):
        def fail(_):
            raise RuntimeError("synthetic generator crash")
        self.assertEqual(self.run_guard(fail)["status"], "CALLBACK_EXCEPTION_RED")
        self.assertEqual(self.run_guard(None)["status"], "INVALID_GENERATOR_RED")


if __name__ == "__main__":
    unittest.main()
