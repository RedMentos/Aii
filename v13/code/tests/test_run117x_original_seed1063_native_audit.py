"""Run117X read-only original seed1063 native auditor synthetic tamper tests."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117x_original_seed1063_native_audit as audit
from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117w_c3_arithmetic_native import _prompts
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.common import dumps

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117W_C3_ARITHMETIC_SEED1063.json")


def recorded_arm(row, name, messages):
    output = dumps(row["oracle"])
    return {"arm": name, "status": "RECORDED",
            "native_final": True, "process_reaped": True,
            "native_metrics": {"status": "FINAL",
                               "actual_model": audit.C3_FILE},
            "messages": messages,
            "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
            "output": output, "score": score(output, row["oracle"])}


class OriginalSeed1063AuditTests(unittest.TestCase):
    def setUp(self):
        self.row = audit.fixture(FIXTURE)[0]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = QuoteRuntime(Path(self.tmp.name) / "home", self.row)
        self.addCleanup(self.runtime.close)
        prior = self.runtime.store.event(
            self.runtime.session, self.row["prior"])
        current = self.runtime.store.event(
            self.runtime.session, self.row["current"])
        self.prompts = _prompts(self.runtime, prior, current, self.row)

    def test_all_three_source_role_prompts_and_original_score(self):
        for name, messages in self.prompts.items():
            with self.subTest(arm=name):
                self.assertTrue(audit._arm(
                    recorded_arm(self.row, name, messages), self.row))

    def test_wrong_model_or_missing_reap_refused(self):
        name = audit.ARMS[0]
        item = recorded_arm(self.row, name, self.prompts[name])
        item["native_metrics"]["actual_model"] = "fake.gguf"
        with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_RED"):
            audit._arm(item, self.row)
        item = recorded_arm(self.row, name, self.prompts[name])
        item["process_reaped"] = False
        with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_RED"):
            audit._arm(item, self.row)

    def test_typed_answer_in_source_only_arm_refused(self):
        name = audit.ARMS[0]
        item = recorded_arm(self.row, name, self.prompts[name])
        payload = json.loads(item["messages"][1]["content"])
        payload["typed_jef_candidate"] = self.row["oracle"]
        item["messages"][1]["content"] = dumps(payload)
        item["messages_sha256"] = sha256(
            dumps(item["messages"]).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "TYPED_JEF_LEAK"):
            audit._arm(item, self.row)

    def test_wrong_policy_source_ref_refused(self):
        name = audit.ARMS[1]
        item = recorded_arm(self.row, name, self.prompts[name])
        payload = json.loads(item["messages"][1]["content"])
        payload["policy"]["source_ref"]["sha256"] = "0" * 64
        item["messages"][1]["content"] = dumps(payload)
        item["messages_sha256"] = sha256(
            dumps(item["messages"]).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "SOURCE_REF_BYTES_RED"):
            audit._arm(item, self.row)

    def test_forged_native_score_refused(self):
        name = audit.ARMS[2]
        item = recorded_arm(self.row, name, self.prompts[name])
        item["score"]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "ORIGINAL_OUTPUT_SCORE_RED"):
            audit._arm(item, self.row)

    def test_original_outer_sha_tamper_refused_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            p.write_bytes(b"not a zip")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_OUTER_SHA_RED"):
                audit.audit(p, "0" * 64, FIXTURE)

    def test_original_gate_promotion_refused(self):
        report = {"schema": "v13.run117w.c3_arithmetic_native.v1",
                  "seed": 1063, "fixture_sha256": audit.FIXTURE_SHA,
                  "native_c3": True, "typed_candidate_precomputed": True,
                  "native_body_calls": 0, "native_jef_calls": 0,
                  "native_c2_calls": 0, "age0": "RECORD_ONLY",
                  "step2_exit": "EVIDENCE_NOT_PASSING", "b3": "NO_PROMOTION",
                  "body_jepa": "UNAVAILABLE", "jepa_weight": 1,
                  "redmi_measured": False, "whole_system_complete": False,
                  "output_committed": False, "tool_dispatches": 0,
                  "learning_authority": 0, "delivery_authority": 0,
                  "status": audit.RED}
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES_RED"):
            audit._report(report, audit.fixture(FIXTURE))


if __name__ == "__main__":
    unittest.main()
