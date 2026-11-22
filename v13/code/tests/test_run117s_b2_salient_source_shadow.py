"""Run117S seed1061 real SQLite + synthetic Body salient B2 source tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer, _TopicStateView
from v13.b1b2_causal_offer_consumer_candidate import CausalOfferConsumer
from v13.b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from v13.b2_salient_source_excerpt_shadow_candidate import (
    select, guarded_salient_b2_offer,
)

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json")
FIXTURE_SHA = "11d499eeb04d83e3786fe12046207ec3d0fc6684f5220a5fc1943202cd0f31de"


class QuoteBody:
    def __init__(self, role, row, runtime):
        self.role, self.row, self.runtime = role, row, runtime
        self.last_metrics = {"status": "FINAL", "synthetic": True}

    def generate(self, messages, *args, **kwargs):
        self.runtime.calls[self.role] += 1
        query = json.loads(messages[1]["content"])
        if self.role == "B2_GIST" and query.get("quote_choices"):
            ids = [c["id"] for c in query["quote_choices"]
                   if "Binding policy:" in c["text"]]
            quotes = ids[:1]
        else:
            quotes = [self.row["option_span"] if self.role == "B1_DETAIL"
                      else self.row["policy_span"]]
        return [json.dumps({"summary": "Synthetic untrusted observer",
                            "quotes": quotes, "uncertainty": "high",
                            "needs_reentry": True})]


class QuoteRuntime(FakeRuntime):
    def __init__(self, home, row):
        self.row = row
        self.calls = {"B1_DETAIL": 0, "B2_GIST": 0}
        super().__init__(home)

    def _body(self, role):
        return QuoteBody(role, self.row, self)


class SalientSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
        cls.fixture = json.loads(FIXTURE.read_text())
        assert cls.fixture["seed"] == 1061
        assert [r["id"] for r in cls.fixture["rows"]] == [
            "Atlas", "Boreal", "Cinder", "Delta", "Elm", "Flux"]

    def create(self, row):
        tmp = tempfile.TemporaryDirectory()
        runtime = QuoteRuntime(Path(tmp.name) / "home", row)
        runtime.cfg.update(OVERRIDES | {
            "b2_quote_select": "pointer", "offer_quote_context_chars": 200})
        consumer = TopicPartitionOfferConsumer(runtime)
        prior = runtime.store.event(runtime.session, row["prior"])
        x = consumer.guarded_offer("B2_GIST", prior, 0,
                                   time.monotonic() + 30, operator_opt_in=True)
        self.assertEqual(x["status"], "SHADOW_OFFER_PRODUCED", x)
        current = runtime.store.event(runtime.session, row["current"])
        return tmp, runtime, consumer, prior, current

    def prior_context(self, runtime, current):
        from v13.b1b2_causal_context_candidate import _project_scope
        topic = next(iter(_project_scope(runtime.store.read_source(current["source_ref"]))))
        view = _TopicStateView(runtime.store, "B2_GIST", runtime.session,
                               runtime.store.generation_id,
                               runtime.models.revision("B2_GIST"), topic)
        worker = CausalOfferConsumer(runtime)
        worker.s = view
        return worker.body_context("B2_GIST", current)

    def test_all_six_source_bound_policy_and_option_quotes(self):
        for row in self.fixture["rows"]:
            with self.subTest(case=row["id"]):
                tmp, runtime, consumer, prior, current = self.create(row)
                try:
                    original = self.prior_context(runtime, current)
                    self.assertEqual(len(original), 1)
                    selected = select(runtime, current, original,
                                      operator_opt_in=True)
                    self.assertEqual(selected["status"],
                                     "SHADOW_SALIENT_B2_EXCERPT_VERIFIED", selected)
                    self.assertIn(row["policy_span"],
                                  selected["context"][0]["native_context"]["exact_source_excerpt"])
                    self.assertLessEqual(selected["selected_char_count"], 240)
                    self.assertFalse(selected["answer_computed"])
                    self.assertFalse(selected["source_semantic_truth_authority"])
                    b1 = consumer.guarded_offer("B1_DETAIL", current, 0,
                                                time.monotonic() + 30,
                                                operator_opt_in=True)
                    self.assertEqual(b1["status"], "SHADOW_OFFER_PRODUCED")
                    b2 = guarded_salient_b2_offer(
                        runtime, current, 0, time.monotonic() + 30,
                        operator_opt_in=True)
                    self.assertEqual(b2["status"],
                                     "SHADOW_SALIENT_B2_OFFER_PRODUCED", b2)
                    self.assertTrue(b2["model_called"])
                    self.assertIsNone(b2["native_calls"])
                    self.assertFalse(b2["native_model_proven"])
                    env = build_c3_source_envelope(runtime, current,
                        {"B1_DETAIL": b1["offer_packet_id"],
                         "B2_GIST": b2["offer_packet_id"]},
                        operator_opt_in=True)
                    self.assertEqual(env["status"],
                                     "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL", env)
                    obs = json.loads(env["messages"][1]["content"])["body_observations"]
                    self.assertEqual([x["role"] for x in obs],
                                     ["B1_DETAIL", "B2_GIST"])
                    self.assertTrue(any(row["option_span"] in q["text"]
                                        for q in obs[0]["verified_quotes"]))
                    self.assertTrue(any(row["policy_span"] in q["text"]
                                        for q in obs[1]["verified_quotes"]))
                    self.assertTrue(all(x["hypothesis_authority"] ==
                        "MODEL_HYPOTHESIS_NOT_FACT" for x in obs))
                    self.assertFalse(env["output_committed"])
                    self.assertEqual(env["tool_dispatches"], 0)
                    self.assertEqual(env["learning_authority"], 0)
                    self.assertEqual(runtime.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"], 0)
                finally:
                    runtime.close(); tmp.cleanup()

    def test_default_off_does_not_select_or_call_model(self):
        tmp, runtime, _, _, current = self.create(self.fixture["rows"][0])
        try:
            before = dict(runtime.calls)
            r = select(runtime, current, [], operator_opt_in=False)
            self.assertEqual(r["status"], "OFF")
            o = guarded_salient_b2_offer(runtime, current, 0,
                                         time.monotonic() + 30,
                                         operator_opt_in=False)
            self.assertEqual(o["status"], "OFF")
            self.assertEqual(runtime.calls, before)
        finally:
            runtime.close(); tmp.cleanup()

    def test_prior_prefix_misses_policy_but_salient_contains_it(self):
        row = self.fixture["rows"][0]
        tmp, runtime, _, _, current = self.create(row)
        try:
            original = self.prior_context(runtime, current)
            self.assertNotIn(row["policy_span"],
                             original[0]["native_context"]["exact_source_excerpt"])
            selected = select(runtime, current, original,
                              operator_opt_in=True)
            self.assertIn(row["policy_span"],
                          selected["context"][0]["native_context"]["exact_source_excerpt"])
        finally:
            runtime.close(); tmp.cleanup()

    def test_ambiguous_policy_refuses_before_current_body_call(self):
        row = dict(self.fixture["rows"][0])
        row["prior"] += " " + row["policy_span"]
        tmp, runtime, _, _, current = self.create(row)
        try:
            original = self.prior_context(runtime, current)
            result = select(runtime, current, original, operator_opt_in=True)
            self.assertEqual(result["status"],
                             "POLICY_ANCHOR_MISSING_OR_AMBIGUOUS_RED")
            before = runtime.calls["B2_GIST"]
            r = guarded_salient_b2_offer(runtime, current, 0,
                                         time.monotonic() + 30,
                                         operator_opt_in=True)
            self.assertEqual(r["status"], "SALIENT_B2_OFFER_RED", r)
            self.assertEqual(runtime.calls["B2_GIST"], before)
        finally:
            runtime.close(); tmp.cleanup()

    def test_deleted_prior_source_refuses(self):
        row = self.fixture["rows"][0]
        tmp, runtime, _, prior, current = self.create(row)
        try:
            original = self.prior_context(runtime, current)
            with runtime.store.tx() as db:
                db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                           (prior["source_ref"]["source_id"],))
            result = select(runtime, current, original, operator_opt_in=True)
            self.assertNotEqual(result["status"],
                                "SHADOW_SALIENT_B2_EXCERPT_VERIFIED")
            self.assertNotIn("context", result)
        finally:
            runtime.close(); tmp.cleanup()

    def test_late_user_correction_refuses_before_body_model_call(self):
        row = self.fixture["rows"][0]
        tmp, runtime, _, _, current = self.create(row)
        try:
            original = self.prior_context(runtime, current)
            runtime.store.event(runtime.session,
                                "Project Atlas. Cancel the earlier request.")
            result = select(runtime, current, original, operator_opt_in=True)
            self.assertEqual(result["status"],
                             "STALE_OR_FOREIGN_CURRENT_EVENT_RED")
            before = runtime.calls["B2_GIST"]
            r = guarded_salient_b2_offer(runtime, current, 0,
                                         time.monotonic() + 30,
                                         operator_opt_in=True)
            self.assertEqual(r["status"], "CURRENT_USER_SOURCE_RED")
            self.assertEqual(runtime.calls["B2_GIST"], before)
        finally:
            runtime.close(); tmp.cleanup()

    def test_foreign_session_prior_context_refuses(self):
        row = self.fixture["rows"][0]
        tmp, runtime, _, _, current = self.create(row)
        try:
            original = self.prior_context(runtime, current)
            runtime.session = runtime.store.new_session("other")
            result = select(runtime, current, original, operator_opt_in=True)
            self.assertNotEqual(result["status"],
                                "SHADOW_SALIENT_B2_EXCERPT_VERIFIED")
        finally:
            runtime.close(); tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
