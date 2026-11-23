"""Run117AE: replay immutable original native C3 outputs, no new inference."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import zipfile

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_span_c3_postgen_shadow_candidate import evaluate, PASS
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json")
FIXTURE_SHA = "cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d"
ORIGINAL = Path(os.environ.get("V13_RUN117Z_ORIGINAL_ZIP",
                               "/mnt/data/run117z-original-native.zip"))
ORIGINAL_SHA = "65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a"


class OriginalNativeReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
        assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == ORIGINAL_SHA
        cls.rows = json.loads(FIXTURE.read_text())["rows"]
        with zipfile.ZipFile(ORIGINAL) as z:
            assert z.testzip() is None
            cls.report = json.loads(z.read("NATIVE_CASE/report.json"))
        assert cls.report["native_c3_calls"] == 12
        assert cls.report["native_body_calls"] == 0
        assert cls.report["native_jef_calls"] == 0
        assert cls.report["native_c2_calls"] == 0
        assert [r["id"] for r in cls.report["rows"]] == [
            r["id"] for r in cls.rows]

    def make(self, row):
        temp = tempfile.TemporaryDirectory()
        runtime = QuoteRuntime(Path(temp.name) / "home", row)
        runtime.cfg.update(OVERRIDES)
        prior = runtime.store.event(runtime.session, row["prior"])
        current = runtime.store.event(runtime.session, row["current"])
        consumer = TopicPartitionOfferConsumer(runtime)
        ids = {}
        for role in ("B1_DETAIL", "B2_GIST"):
            offer = consumer.guarded_offer(
                role, current, 0, time.monotonic() + 30,
                operator_opt_in=True)
            self.assertEqual(offer["status"], "SHADOW_OFFER_PRODUCED")
            ids[role] = offer["offer_packet_id"]
        return temp, runtime, prior, current, ids

    def typed_output(self, native_row):
        arms = native_row["arms"]
        self.assertEqual(set(a["arm"] for a in arms),
                         {"RAW_EXACT_SOURCE", "REAL_STORE_JEF_TYPED"})
        for arm in arms:
            self.assertEqual(arm["status"], "RECORDED")
            self.assertTrue(arm["native_final"])
            self.assertTrue(arm["process_reaped"])
        return next(a["output"] for a in arms
                    if a["arm"] == "REAL_STORE_JEF_TYPED")

    def test_all_six_recorded_original_native_outputs_replay(self):
        self.assertEqual(len(self.rows), 6)
        for row, native_row in zip(self.rows, self.report["rows"]):
            with self.subTest(project=row["id"]):
                self.assertEqual(native_row["id"], row["id"])
                self.assertEqual(native_row["typed_jef_candidate"],
                                 row["oracle"])
                output = self.typed_output(native_row)
                temp, runtime, prior, current, ids = self.make(row)
                try:
                    calls = dict(runtime.calls)
                    result = evaluate(
                        runtime, prior, current, ids,
                        lambda _: output,
                        operator_opt_in=True, callback_opt_in=True)
                    self.assertEqual(result["status"], PASS, result)
                    self.assertEqual(runtime.calls, calls)
                    self.assertEqual(result["output_sha256"],
                                     hashlib.sha256(output.encode()).hexdigest())
                    self.assertTrue(result["source_rechecked"])
                    self.assertFalse(result["native_proof"])
                    self.assertFalse(result["body_model_quote_verified"])
                    self.assertFalse(result["output_committed"])
                    self.assertEqual(result["tool_dispatches"], 0)
                    self.assertEqual(result["delivery_authority"], 0)
                    self.assertEqual(result["learning_authority"], 0)
                    self.assertEqual(result["jepa_weight"], 0)
                    self.assertFalse(result["whole_system_complete"])
                    self.assertEqual(runtime.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"], 0)
                finally:
                    runtime.close()
                    temp.cleanup()

    def test_wrong_recorded_output_refused(self):
        row = self.rows[0]
        temp, runtime, prior, current, ids = self.make(row)
        try:
            result = evaluate(
                runtime, prior, current, ids,
                lambda _: '{"choice":"B","remaining":50}',
                operator_opt_in=True, callback_opt_in=True)
            self.assertEqual(result["status"],
                             "FORMATTER_CANDIDATE_MISMATCH_RED")
            self.assertNotIn("output_sha256", result)
        finally:
            runtime.close()
            temp.cleanup()

    def test_original_zip_byte_tamper_detected(self):
        data = ORIGINAL.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), ORIGINAL_SHA)
        tampered = bytearray(data)
        tampered[len(tampered)//2] ^= 1
        self.assertNotEqual(hashlib.sha256(tampered).hexdigest(),
                            ORIGINAL_SHA)

    def test_late_user_correction_refused_on_original_output(self):
        row, native_row = self.rows[0], self.report["rows"][0]
        output = self.typed_output(native_row)
        temp, runtime, prior, current, ids = self.make(row)
        try:
            def late(_):
                runtime.store.event(runtime.session,
                                    "Project Helix correction: cancel request.")
                return output
            result = evaluate(
                runtime, prior, current, ids, late,
                operator_opt_in=True, callback_opt_in=True)
            self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
            self.assertFalse(result["output_committed"])
        finally:
            runtime.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
