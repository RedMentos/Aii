"""Run117U native runner contracts, exercised with synthetic data only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117u_seed1061_native_three_arm as pilot
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from scripts.run117s_body_complementarity_preflight import build_prompts
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b2_salient_source_excerpt_shadow_candidate import guarded_salient_b2_offer
import time

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json")


def fake_report():
    rows = []
    for row in pilot.fixture(FIXTURE):
        offers = [{"status": "RECORDED", "process_reaped": True,
                   "native_metrics": {"status": "FINAL"}}
                  for _ in range(3)]
        arms = [{"arm": arm, "status": "RECORDED",
                 "native_final": True, "process_reaped": True,
                 "score": {"correct": 1, "parsed": row["oracle"]}}
                for arm in pilot.ARMS]
        rows.append({"id": row["id"], "status": "RECORDED",
                     "closed_store_ok": True, "no_live_output": True,
                     "body_path": "QUOTE_READY", "offers": offers,
                     "arms": arms})
    return {"rows": rows, "native_body_calls": 18, "native_c3_calls": 18,
            "exploratory_body_selection_signal": False}


class Run117UNativeContracts(unittest.TestCase):
    def test_frozen_cohort_and_three_arm_names(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual(pilot.SEED, 1061)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["id"] for r in rows],
                         ["Atlas", "Boreal", "Cinder", "Delta", "Elm", "Flux"])
        self.assertEqual(pilot.ARMS,
                         ("RAW_FULL_SOURCES", "SOURCE_SPANS_ONLY",
                          "BODY_VERIFIED_QUOTES"))
        self.assertEqual(pilot.CONFIG["learning_mode"], "RECORD_ONLY")

    def test_frozen_fixture_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "changed.json"
            p.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_all_three_messages_source_only_real_store_synthetic_body(self):
        row = pilot.fixture(FIXTURE)[0]
        with tempfile.TemporaryDirectory() as d:
            runtime = QuoteRuntime(Path(d) / "home", row)
            try:
                runtime.cfg.update(OVERRIDES | {
                    "b2_quote_select": "pointer",
                    "offer_quote_context_chars": 200})
                prior = runtime.store.event(runtime.session, row["prior"])
                consumer = TopicPartitionOfferConsumer(runtime)
                p = consumer.guarded_offer(
                    "B2_GIST", prior, 0, time.monotonic() + 30,
                    operator_opt_in=True)
                self.assertEqual(p["status"], "SHADOW_OFFER_PRODUCED")
                current = runtime.store.event(runtime.session, row["current"])
                b1 = consumer.guarded_offer(
                    "B1_DETAIL", current, 0, time.monotonic() + 30,
                    operator_opt_in=True)
                b2 = guarded_salient_b2_offer(
                    runtime, current, 0, time.monotonic() + 30,
                    operator_opt_in=True)
                self.assertEqual(b1["status"], "SHADOW_OFFER_PRODUCED")
                self.assertEqual(b2["status"],
                                 "SHADOW_SALIENT_B2_OFFER_PRODUCED")
                controls = pilot._source_messages(runtime, prior, current, row)
                ids = {"B1_DETAIL": b1["offer_packet_id"],
                       "B2_GIST": b2["offer_packet_id"]}
                body, error = pilot._body_messages(runtime, current, ids, row)
                self.assertIsNone(error)
                controls[pilot.ARMS[2]] = body
                for arm, messages in controls.items():
                    self.assertEqual(len(pilot._safe_messages(messages, row, arm)), 64)
                    self.assertNotIn('"oracle"', messages[1]["content"])
                    self.assertNotIn("typed_jef_candidate", messages[1]["content"])
                self.assertEqual(
                    runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"], 0)
            finally:
                runtime.close()

    def test_typed_answer_injection_refused(self):
        row = pilot.fixture(FIXTURE)[0]
        messages = [{"role": "system", "content": pilot.SYSTEM},
                    {"role": "user", "content": json.dumps({
                        "typed_jef_candidate": row["oracle"]})}]
        with self.assertRaisesRegex(ValueError, "LEAK_RED"):
            pilot._safe_messages(messages, row, pilot.ARMS[0])

    def test_full_native_receipt_without_body_gain_is_no_gain(self):
        report = fake_report()
        self.assertEqual(pilot._score_summary(report), pilot.GOOD[1])
        self.assertEqual(report["scores"], {a: 6 for a in pilot.ARMS})
        self.assertFalse(report["exploratory_body_selection_signal"])

    def test_exploratory_signal_never_promotes_gates(self):
        report = fake_report()
        for i, row in enumerate(report["rows"]):
            row["arms"][0]["score"]["correct"] = int(i < 2)
            row["arms"][1]["score"]["correct"] = int(i < 3)
        self.assertEqual(pilot._score_summary(report), pilot.GOOD[0])
        self.assertTrue(report["exploratory_body_selection_signal"])

    def test_missing_body_quote_retains_two_controls_and_red(self):
        report = fake_report()
        row = report["rows"][0]
        row["body_path"] = "BODY_QUOTE_RED"
        row["arms"][2] = {
            "arm": pilot.ARMS[2], "status": "BODY_QUOTE_UNAVAILABLE",
            "native_final": False, "process_reaped": False, "score": None}
        report["native_c3_calls"] = 17
        self.assertEqual(pilot._score_summary(report), pilot.BODY_RED)
        self.assertEqual(report["recorded_by_arm"][pilot.ARMS[0]], 6)
        self.assertEqual(report["recorded_by_arm"][pilot.ARMS[1]], 6)
        self.assertEqual(report["recorded_by_arm"][pilot.ARMS[2]], 5)

    def test_native_model_or_reap_error_never_promotes(self):
        report = fake_report()
        report["rows"][0]["offers"][0]["process_reaped"] = False
        self.assertEqual(pilot._score_summary(report), pilot.STRUCTURAL_RED)


if __name__ == "__main__":
    unittest.main()
