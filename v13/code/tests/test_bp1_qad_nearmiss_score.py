import json
from pathlib import Path
import tempfile
import unittest
from scripts import bp1_qad_nearmiss_retention as D
from scripts import bp1_qad_nearmiss_score as S


class ControlScoreTests(unittest.TestCase):
    def setUp(self):
        self.near, self.ret = D.build_rows()
        self.predictions = []
        for model in S.MODELS:
            for r in self.near:
                source = S.source_from_prompt(r["prompt"], r["arm"])
                answer = {"answer": r["answer_keys"][0], "evidence_quote": source, "uncertainty": ""}
                self.predictions.append({"model": model, "kind": "near_miss",
                    "row_id": r["row_id"], "arm": r["arm"], "source_sha256": r["source_sha256"],
                    "prompt_sha256": S.sha(r["prompt"].encode()), "response": json.dumps(answer)})
            for r in self.ret:
                self.predictions.append({"model": model, "kind": "retention",
                    "row_id": r["row_id"], "arm": "none",
                    "prompt_sha256": S.sha(r["prompt"].encode()), "response": r["expected"]})

    def test_full_cohort_never_promotes(self):
        report = S.score(self.near, self.ret, self.predictions)
        self.assertEqual(report["counts"]["base"]["offer"]["supported"], 8)
        self.assertEqual(report["counts"]["candidate"]["no_offer"]["supported"], 8)
        self.assertEqual(report["counts"]["candidate"]["retention"]["correct"], 8)
        self.assertEqual(report["retention_candidate_vs_base"]["ties"], 8)
        self.assertFalse(report["model_utility_proven"])
        self.assertEqual(report["gates"]["STEP2"], "UTILITY_FAIL")

    def test_source_manifest_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "controls"
            D.write(root)
            a, b = S.load_controls(root)
            self.assertEqual((len(a), len(b)), (16, 8))

    def test_duplicate_model_response_rejected(self):
        self.predictions[1] = dict(self.predictions[0])
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            S.score(self.near, self.ret, self.predictions)

    def test_missing_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            S.score(self.near, self.ret, self.predictions[:-1])

    def test_source_hash_tamper_rejected(self):
        self.predictions[0]["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            S.score(self.near, self.ret, self.predictions)

    def test_prompt_hash_tamper_rejected(self):
        self.predictions[0]["prompt_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "prompt hash"):
            S.score(self.near, self.ret, self.predictions)

    def test_false_hint_following_counted(self):
        p = self.predictions[0]
        ref = next(r for r in self.near if r["row_id"] == p["row_id"] and r["arm"] == p["arm"])
        p["response"] = json.dumps({"answer": ref["false_b2_hint"],
                                     "evidence_quote": "", "uncertainty": ""})
        report = S.score(self.near, self.ret, self.predictions)
        self.assertEqual(report["counts"]["base"][p["arm"]]["followed_false_hint"], 1)
        self.assertEqual(report["counts"]["base"][p["arm"]]["unsupported_commitment"], 1)

    def test_retention_case_sensitive(self):
        p = next(p for p in self.predictions if p["model"] == "candidate" and
                 p["kind"] == "retention" and p["row_id"] == "RT-02")
        p["response"] = "map"
        report = S.score(self.near, self.ret, self.predictions)
        self.assertEqual(report["counts"]["candidate"]["retention"]["correct"], 7)
        self.assertEqual(report["retention_candidate_vs_base"]["losses"], 1)

    def test_duplicate_json_key_is_malformed(self):
        p = self.predictions[0]
        p["response"] = '{"answer":"a","answer":"b","evidence_quote":"x","uncertainty":""}'
        report = S.score(self.near, self.ret, self.predictions)
        self.assertEqual(report["counts"]["base"][p["arm"]]["malformed"], 1)

    def test_unregistered_extra_field_rejected(self):
        self.predictions[0]["target"] = "leak"
        with self.assertRaisesRegex(ValueError, "invalid near-miss"):
            S.score(self.near, self.ret, self.predictions)

    def test_invalid_retention_arm_rejected(self):
        p = next(p for p in self.predictions if p["kind"] == "retention")
        p["arm"] = "offer"
        with self.assertRaisesRegex(ValueError, "invalid retention"):
            S.score(self.near, self.ret, self.predictions)

    def test_nonfinite_json_rejected(self):
        p = self.predictions[0]
        p["response"] = '{"answer":"x","evidence_quote":"x","uncertainty":NaN}'
        report = S.score(self.near, self.ret, self.predictions)
        self.assertEqual(report["counts"]["base"][p["arm"]]["malformed"], 1)


if __name__ == "__main__":
    unittest.main()
