"""Run117Q read-only original-native attribution counterexample tests.

Synthetic one-row structures test the auditor; original Run116 ZIP is audited
separately, not fabricated by these unit tests.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117q_native_attribution_readonly as audit


def arm(name, oracle, sources, output, tokens):
    user = {"sources": copy.deepcopy(sources)}
    if name != audit.ARMS[0]:
        user.update(typed_jef_candidate=oracle,
                    typed_candidate_authority=0,
                    typed_candidate_origin=
                    "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL")
    system = "You are C3."
    if name != audit.ARMS[0]:
        system += " Copy typed_jef_candidate.choice and remaining exactly."
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)}]
    sha = hashlib.sha256(json.dumps(messages, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"arm": name, "messages": messages, "messages_sha256": sha,
            "native_final": True, "process_reaped": True, "status": "RECORDED",
            "native_metrics": {"status": "FINAL", "prompt_tokens": tokens},
            "output": json.dumps(output), "score": {"correct": int(output == oracle)}}


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {"id": "Synthetic", "prior": "prior user source",
                        "current": "current user source",
                        "oracle": {"choice": "B", "remaining": 60}}
        sources = [{"text": self.fixture["prior"]},
                   {"text": self.fixture["current"]}]
        self.row = {"id": "Synthetic", "arms": [
            arm(audit.ARMS[0], self.fixture["oracle"], sources,
                {"choice": "A", "remaining": 100}, 500),
            arm(audit.ARMS[1], self.fixture["oracle"], sources,
                self.fixture["oracle"], 700),
            arm(audit.ARMS[2], self.fixture["oracle"], sources,
                self.fixture["oracle"], 1500)]}

    def summarize(self, row=None, fixture=None):
        return audit.summarize([row or self.row], [fixture or self.fixture])

    def test_paired_formatter_copy_is_not_reasoning_or_body_gain(self):
        r = self.summarize()
        self.assertEqual(r["scores"], dict(zip(audit.ARMS, (0, 1, 1))))
        self.assertEqual(r["paired_raw_to_typed_improved"], 1)
        self.assertEqual(r["paired_typed_to_body_improved"], 0)
        self.assertTrue(r["typed_candidate_is_deterministic_oracle_in_user_prompt"])
        self.assertFalse(r["c3_reasoning_gain_proven"])
        self.assertFalse(r["b1b2_complementarity_proven"])
        self.assertFalse(r["step2_promoted"])

    def test_wrong_typed_answer_in_prompt_refused(self):
        row = copy.deepcopy(self.row)
        data = json.loads(row["arms"][1]["messages"][1]["content"])
        data["typed_jef_candidate"] = {"choice": "A", "remaining": 100}
        row["arms"][1]["messages"][1]["content"] = json.dumps(data)
        with self.assertRaises(ValueError):
            self.summarize(row)

    def test_raw_arm_answer_leak_refused(self):
        row = copy.deepcopy(self.row)
        data = json.loads(row["arms"][0]["messages"][1]["content"])
        data["typed_jef_candidate"] = self.fixture["oracle"]
        row["arms"][0]["messages"][1]["content"] = json.dumps(data)
        with self.assertRaises(ValueError):
            self.summarize(row)

    def test_score_or_output_tamper_refused(self):
        row = copy.deepcopy(self.row)
        row["arms"][0]["score"]["correct"] = 1
        with self.assertRaisesRegex(ValueError, "ORIGINAL_SCORE_MISMATCH_RED"):
            self.summarize(row)
        row = copy.deepcopy(self.row)
        row["arms"][1]["output"] = '{"choice":"B","remaining":60,"approved":true}'
        with self.assertRaisesRegex(ValueError, "C3_OUTPUT_SCHEMA_RED"):
            self.summarize(row)

    def test_source_drift_and_prompt_hash_tamper_refused(self):
        row = copy.deepcopy(self.row)
        row["arms"][2]["messages"][1]["content"] = '{}'
        with self.assertRaisesRegex(ValueError, "PROMPT_HASH_RED"):
            self.summarize(row)
        row = copy.deepcopy(self.row)
        for a in row["arms"]:
            data = json.loads(a["messages"][1]["content"])
            data["sources"][1]["text"] = "forged current"
            a["messages"][1]["content"] = json.dumps(data)
            a["messages_sha256"] = hashlib.sha256(json.dumps(a["messages"],
                sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "EXACT_USER_SOURCE_RED"):
            self.summarize(row)

    def test_native_receipt_and_cohort_order_refused(self):
        row = copy.deepcopy(self.row)
        row["arms"][0]["process_reaped"] = False
        with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_OR_ROLE_RED"):
            self.summarize(row)
        with self.assertRaisesRegex(ValueError, "COHORT_ORDER_RED"):
            self.summarize(fixture=dict(self.fixture, id="Other"))

    def test_outer_artifact_wrong_sha_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "not-the-original.zip"
            p.write_bytes(b"not the original native artifact")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_OUTER_SHA_RED"):
                audit.audit(p)


if __name__ == "__main__":
    unittest.main()
