"""Synthetic contract tests, NOT Redmi native tests."""
import unittest
from phone_acceptance import evaluate

def fixture():
    categories = ["greeting", "arithmetic", "reasoning", "ambiguity", "memory", "source", "deep"]
    return {"installed_sha": "abcdef0123456789", "turns": [dict(category=categories[i % 7], status="FINAL", correct=True, total_ms=1000+i*10, ttft_ms=100, source_bound=True, b1_delivered=True, b2_delivered=True, c4_consumed=True) for i in range(20)]}

class AcceptanceTests(unittest.TestCase):
    def test_synthetic_contract(self):
        self.assertEqual(evaluate(fixture())["gate"], "PASS")
        self.assertIn("NOT_DEVICE", evaluate(fixture())["proof"])
    def test_incorrect_answer(self):
        r=fixture(); r["turns"][1]["correct"]=False
        self.assertEqual(evaluate(r)["gate"], "BLOCKED")
    def test_missing_offer(self):
        r=fixture(); r["turns"][5]["b2_delivered"]=False
        self.assertIn("TURN_5_NO_CROSS_ORGAN_PROOF", evaluate(r)["failures"])
    def test_missing_sha(self):
        r=fixture(); r.pop("installed_sha")
        self.assertIn("UNVERIFIED_INSTALLED_SHA", evaluate(r)["failures"])
    def test_timing(self):
        r=fixture(); r["turns"][0]["ttft_ms"]=2000
        self.assertIn("TURN_0_TTFT_AFTER_TOTAL", evaluate(r)["failures"])
    def test_short_cohort(self):
        r=fixture(); r["turns"]=r["turns"][:10]
        self.assertIn("INSUFFICIENT_TURNS", evaluate(r)["failures"])

if __name__ == "__main__":
    unittest.main()
