"""Scorer-only controls; native proof requires real C3 runner and actual source store."""
import unittest
from scripts.native_source_consumer_admission import NAMES, fixtures, score


class NativeSourceConsumerScorerTests(unittest.TestCase):
    def test_fresh_deterministic_bilingual_holdout(self):
        a = fixtures()
        self.assertEqual(a, fixtures())
        self.assertEqual(len(a), 8)
        self.assertEqual(len({x["amount"] for x in a}), 8)
        self.assertEqual([x["language"] for x in a], ["en"] * 4 + ["de"] * 4)
        self.assertNotIn("Elyra", {x["project"] for x in a})

    def example(self, correct=8, leaked=False, calls=False):
        p = [{"language": "en" if i < 4 else "de", "exact_amount": i < correct,
              "source_verified": True, "native_status": "FINAL", "actual_model": "native"}
             for i in range(8)]
        n = [{"native_calls": 1 if calls and i == 0 else 0, "status": "CLARIFY",
              "unsupported_amount": leaked and i == 0, "unrelated_source_leak": False}
             for i in range(24)]
        return {"positive": p, "negative": n}

    def test_positive_threshold_and_negative_gate(self):
        self.assertEqual(score(self.example(correct=8))["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_PASS")
        self.assertEqual(score(self.example(correct=7))["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_PASS")
        self.assertEqual(score(self.example(correct=6))["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_FAIL")
        self.assertEqual(score(self.example(leaked=True))["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_FAIL")
        self.assertEqual(score(self.example(calls=True))["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_FAIL")

    def test_nonfinal_native_and_missing_rows_fail(self):
        row = self.example()
        row["positive"][0]["native_status"] = "CANCELLED"
        self.assertEqual(score(row)["status"], "SOURCE_CONSUMER_SCOPED_NATIVE_FAIL")
        self.assertEqual(score(self.example()["positive"] and
                               {"positive": [], "negative": []})["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
