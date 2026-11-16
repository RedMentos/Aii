"""Synthetic QA only; no Android proof."""
import unittest
from scripts.qa_android_e2e_gate import evaluate

def row(i):
    return dict(turn_id=str(i), release_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", device_receipt={"verified": True, "issue_url": "private-receipt"},
                status="FINAL", correct=True, total_ms=100, ttft_ms=30, native_prefill_ms=10,
                pss_kib=500, c3_tokens=5, b1_attempted=1, b1_delivered=1,
                b1_consumed=1, b2_attempted=1, b2_delivered=1, b2_consumed=1,
                c4_consumed=2, category=["greeting","arithmetic","ambiguity","memory",
                "source","deep","followup","correction"][i % 8])

class AndroidGateTests(unittest.TestCase):
    def test_synthetic_complete(self):
        self.assertEqual(evaluate([row(i) for i in range(20)], "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["gate"], "PASS")

    def test_wrong_answer_blocks(self):
        rows = [row(i) for i in range(20)]
        rows[1]["correct"] = False
        self.assertEqual(evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["gate"], "BLOCKED")

    def test_attempts_without_delivery_block(self):
        rows = [row(i) for i in range(20)]
        for r in rows:
            r["b1_delivered"] = r["b1_consumed"] = 0
            r["c4_consumed"] = 1
        self.assertIn("B1_B2_NOT_BOTH_CONSUMED", evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["problems"])

    def test_unverified_device_blocks(self):
        rows = [row(i) for i in range(20)]
        rows[0]["device_receipt"] = None
        self.assertEqual(evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["gate"], "BLOCKED")

    def test_nonfinite_latency_blocks(self):
        for bad in (float("nan"), float("inf"), -float("inf")):
            rows = [row(i) for i in range(20)]
            rows[0]["total_ms"] = bad
            self.assertEqual(evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["gate"], "BLOCKED")

    def test_no_c4_consumption_blocks(self):
        rows = [row(i) for i in range(20)]
        for r in rows:
            r["c4_consumed"] = 0
        self.assertIn("C4_NEVER_CONSUMED", evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["problems"])

    def test_never_claim_device_proof(self):
        result = evaluate([row(i) for i in range(20)], "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertFalse(result["release_ready"])
        self.assertEqual(result["evidence"], "SYNTHETIC_SCHEMA_ONLY_NOT_DEVICE_VERIFIED")

    def test_deep_turn_requires_both_body_contributions(self):
        rows = [row(i) for i in range(20)]
        rows[5]["b1_delivered"] = rows[5]["b1_consumed"] = 0
        rows[5]["c4_consumed"] = 1
        self.assertIn("TURN_6_MISSING_DEEP_ORGAN_COOPERATION", evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["problems"])

    def test_non_object_turn_blocks_without_crash(self):
        rows = [row(i) for i in range(20)]
        rows[0] = None
        self.assertIn("TURN_1_NOT_OBJECT", evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")["problems"])

    def test_malformed_receipt_rows_fail_closed_without_crash(self):
        for malformed in (None, [], {"turn_id": "partial"}, dict(row(0), turn_id=[]),
                          dict(row(0), category=[])):
            rows = [row(i) for i in range(20)]
            rows[0] = malformed
            result = evaluate(rows, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            self.assertEqual(result["gate"], "BLOCKED")
            self.assertFalse(result["release_ready"])

    def test_short_release_sha_blocks(self):
        self.assertIn("INVALID_EXPECTED_RELEASE_SHA", evaluate([row(i) for i in range(20)], "abcdef0")["problems"])

    def test_sha_mismatch_blocks(self):
        self.assertEqual(evaluate([row(i) for i in range(20)], "different")["gate"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
