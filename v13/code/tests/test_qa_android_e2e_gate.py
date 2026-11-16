"""Synthetic QA only; no Android proof."""
import unittest
from scripts.qa_android_e2e_gate import evaluate

def row(i):
    return dict(turn_id=str(i), release_sha="abc", device_receipt={"verified": True, "issue_url": "private-receipt"},
                status="FINAL", correct=True, total_ms=100, ttft_ms=30, native_prefill_ms=10,
                pss_kib=500, c3_tokens=5, b1_attempted=1, b1_delivered=1,
                b1_consumed=1, b2_attempted=1, b2_delivered=1, b2_consumed=1,
                c4_consumed=2, category=["greeting","arithmetic","ambiguity","memory",
                "source","deep","followup","correction"][i % 8])

class AndroidGateTests(unittest.TestCase):
    def test_synthetic_complete(self):
        self.assertEqual(evaluate([row(i) for i in range(20)], "abc")["gate"], "PASS")

    def test_wrong_answer_blocks(self):
        rows = [row(i) for i in range(20)]
        rows[1]["correct"] = False
        self.assertEqual(evaluate(rows, "abc")["gate"], "BLOCKED")

    def test_attempts_without_delivery_block(self):
        rows = [row(i) for i in range(20)]
        for r in rows:
            r["b1_delivered"] = r["b1_consumed"] = 0
            r["c4_consumed"] = 1
        self.assertIn("B1_B2_NOT_BOTH_CONSUMED", evaluate(rows, "abc")["problems"])

    def test_unverified_device_blocks(self):
        rows = [row(i) for i in range(20)]
        rows[0]["device_receipt"] = None
        self.assertEqual(evaluate(rows, "abc")["gate"], "BLOCKED")

    def test_sha_mismatch_blocks(self):
        self.assertEqual(evaluate([row(i) for i in range(20)], "different")["gate"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
