import json
import unittest
from scripts import bp1_qad_v2_raw_audit as A
from scripts import bp1_qad_v2_rescore as R


class IndependentRescoreTests(unittest.TestCase):
    def setUp(self):
        self.refs = []
        self.predictions = []
        for i in range(11):
            source = f"Project {i}. The deadline is March 3. Previous deadline December 12 is superseded."
            for arm in ("no_offer", "offer"):
                prompt = "Question?\n" + R.MARKER + source + R.END[arm]
                if arm == "offer":
                    prompt += "B2 exact-source quote candidates (not necessarily sufficient):\nMarch 3\n"
                ref = {"row_id": f"RUN181-{i:02}", "arm": arm,
                       "prompt": prompt, "source_sha256": A.sha(source.encode()),
                       "answer_keys": ["March 3"]}
                self.refs.append(ref)
                for model in ("base", "candidate"):
                    supported = model == "candidate" or (arm == "offer" and i < 2)
                    response = {"answer": "March 3" if supported else "December 12",
                                "evidence_quote": "The deadline is March 3." if supported else "Previous deadline December 12 is superseded.",
                                "uncertainty": ""}
                    self.predictions.append({"model": model, "row_id": ref["row_id"], "arm": arm,
                                             "response": json.dumps(response)})

    def test_counts_and_paired_wins(self):
        result = R.rescore(self.refs, self.predictions)
        self.assertEqual(result["counts"]["base"]["no_offer"]["supported"], 0)
        self.assertEqual(result["counts"]["base"]["offer"]["supported"], 2)
        self.assertEqual(result["counts"]["candidate"]["no_offer"]["supported"], 11)
        self.assertEqual(result["counts"]["candidate"]["offer"]["supported"], 11)
        self.assertEqual(result["candidate_vs_base"]["no_offer"]["wins"], 11)
        self.assertEqual(result["candidate_vs_base"]["offer"]["wins"], 9)
        self.assertEqual(result["offer_vs_no_offer"]["base"]["wins"], 2)

    def test_false_answer_is_unsupported(self):
        r = R.score_one(json.dumps({"answer": "December 12",
                  "evidence_quote": "Previous deadline December 12 is superseded.", "uncertainty": ""}),
                  "Previous deadline December 12 is superseded.", "March 3")
        self.assertTrue(r["unsupported_commitment"])
        self.assertFalse(r["supported"])

    def test_invalid_quote(self):
        r = R.score_one(json.dumps({"answer": "March 3",
                  "evidence_quote": "Not in source", "uncertainty": ""}),
                  "The deadline is March 3.", "March 3")
        self.assertFalse(r["quote_valid"])
        self.assertFalse(r["supported"])

    def test_duplicate_json_keys_rejected(self):
        r = R.score_one('{"answer":"March 3","answer":"March 3","evidence_quote":"March 3","uncertainty":""}',
                        "March 3", "March 3")
        self.assertFalse(r["parsed"])

    def test_source_hash_tamper(self):
        self.refs[0]["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "source text hash"):
            R.rescore(self.refs, self.predictions)

    def test_duplicate_model_arm(self):
        self.predictions[1] = dict(self.predictions[0])
        with self.assertRaisesRegex(ValueError, "duplicate/unknown"):
            R.rescore(self.refs, self.predictions)

    def test_ambiguous_source_boundary(self):
        with self.assertRaisesRegex(ValueError, "ambiguous source"):
            R.extract_source("not a valid source", "no_offer")

    def test_nonfinite_json(self):
        self.assertFalse(R.score_one('{"answer":"March 3","evidence_quote":"March 3","uncertainty":NaN}',
                                     "March 3", "March 3")["parsed"])


if __name__ == "__main__":
    unittest.main()
