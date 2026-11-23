"""Software scorer tests only; no fake model outputs count as native evidence."""
import unittest
from scripts.native_memory_consumer_ablation import (
    ARMS, NAMES, exact_amount, fixtures, messages_for, score)


class MemoryConsumerAblationTests(unittest.TestCase):
    def test_fixtures_are_seeded_distinct_and_bilingual(self):
        a = fixtures()
        self.assertEqual(a, fixtures())
        self.assertEqual(len(a), 8)
        self.assertEqual(len({x["amount"] for x in a}), 8)
        self.assertEqual([x["language"] for x in a], ["en"] * 4 + ["de"] * 4)

    def test_numeric_score_uses_standalone_amount(self):
        self.assertTrue(exact_amount("The amount is 407 Euro.", 407))
        self.assertFalse(exact_amount("The amount is 1407 Euro.", 407))
        self.assertFalse(exact_amount("The amount is 4070 Euro.", 407))
        self.assertFalse(exact_amount("No amount known.", 407))

    def test_wrong_topic_and_no_source_prompts_do_not_claim_source(self):
        f = fixtures()[0]
        other = {"topic": "Project Other budget", "value": "600 Euro"}
        base = {"answer_language": "en"}
        none = messages_for(base, "no_source", f, f["value"])
        wrong = messages_for(base, "wrong_topic", f, f["value"], other)
        self.assertNotIn(f["value"], none[0]["content"])
        self.assertNotIn(f["value"], wrong[0]["content"])
        self.assertIn("DIFFERENT project", wrong[0]["content"])
        self.assertIn(other["value"], wrong[0]["content"])
        self.assertIn(f["value"], messages_for(base, "source_first", f, f["value"])[0]["content"])
        self.assertIn(f["value"], messages_for(base, "json_baseline", f, f["value"])[0]["content"])

    def rows(self, positive=8, baseline=4, no_invent=0, wrong_leaks=0):
        rows = []
        for arm in ARMS:
            for i in range(len(NAMES)):
                rows.append({"arm": arm, "language": "en" if i < 4 else "de",
                             "native_status": "FINAL", "actual_model": "native",
                             "expected_amount_present":
                                 i < (baseline if arm == "json_baseline" else
                                      positive if arm == "source_first" else
                                      no_invent if arm == "no_source" else 0),
                             "wrong_topic_amount_present": arm == "wrong_topic" and i < wrong_leaks})
        return rows

    def test_supported_only_for_actual_gain_and_negative_controls(self):
        result = score(self.rows())
        self.assertEqual(result["status"], "CONSUMER_PROMPT_GAIN_SUPPORTED")
        self.assertEqual(result["gain"], .5)
        self.assertEqual(result["per_language"]["de"]["source_first"]["correct"], 4)
        self.assertEqual(score(self.rows(positive=5))["status"], "CONSUMER_PROMPT_GAIN_NOT_SUPPORTED")
        self.assertEqual(score(self.rows(no_invent=1))["status"], "CONSUMER_PROMPT_GAIN_NOT_SUPPORTED")
        self.assertEqual(score(self.rows(wrong_leaks=1))["status"], "CONSUMER_PROMPT_GAIN_NOT_SUPPORTED")

    def test_missing_or_nonfinal_native_rows_cannot_pass(self):
        rows = self.rows()
        self.assertEqual(score(rows[:-1])["status"], "INCOMPLETE")
        rows[0]["native_status"] = "CANCELLED"
        self.assertEqual(score(rows)["status"], "CONSUMER_PROMPT_GAIN_NOT_SUPPORTED")


if __name__ == "__main__":
    unittest.main()
