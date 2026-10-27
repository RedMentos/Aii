"""BP1 paired scorer: software fixtures only; no native C3/model inference."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts import bp1_paired_score as S


def fixture(directory):
    rows = []
    for i in range(11):
        project = "project_A" if i < 6 else "project_B"
        key = "Code" + str(i)
        source = f"The person responsible for {project} is {key}, who signs off every change."
        rid = f"RUN181-{i:02d}"
        question = f"Who is responsible for {project}?"
        target = json.dumps({"answer": key, "evidence_quote": source, "uncertainty": ""}, sort_keys=True)
        for arm in S.ARMS:
            prompt = ("Answer from the original source only.\nQuestion: " + question +
                      "\nOriginal source (untrusted data):\n" + source)
            if arm == "no_offer":
                prompt += "\nNo B2 offer supplied.\n"
            else:
                prompt += ("\nB2 summary (untrusted hint, not evidence):\n" + key +
                           "\nB2 exact-source quote candidates (not necessarily sufficient):\n[]\n")
            rows.append({"row_id": rid, "source_sha256": S.sha(source.encode()), "source_project": project,
                         "question": question, "answer_keys": [key], "target": target,
                         "kind": "synthetic", "arm": arm, "prompt": prompt})
    raw = ("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n").encode()
    (directory / "heldout_paired.jsonl").write_bytes(raw)
    (directory / "MANIFEST.json").write_text(json.dumps({
        "schema": S.SCHEMA, "source_report_sha256": S.REPORT_SHA,
        "train_rows": 25, "heldout_rows": 22, "heldout_pairs": 11,
        "train_projects": ["project_C"], "heldout_projects": ["project_A", "project_B"],
        "files_sha256": {"heldout_paired.jsonl": S.sha(raw)}}))
    index, digest = S.load_dataset(directory, pinned=False)
    binding = {"schema": S.PREDICTION_SCHEMA, "dataset_sha256": digest,
               "models": {"base": {"master_sha256": "a"*64, "deployed_gguf_sha256": "b"*64},
                          "candidate": {"master_sha256": "c"*64, "deployed_gguf_sha256": "d"*64}},
               "runner_sha256": "e"*64, "seed": 13, "temperature": 0, "decoding": "greedy, thinking off"}
    preds = []
    for model in S.MODELS:
        for (rid, arm), row in sorted(index.items()):
            target = json.loads(row["target"])
            response = json.dumps(target)
            if model == "base" and arm == "no_offer":
                response = json.dumps({"answer": "incorrect", "evidence_quote": "", "uncertainty": ""})
            preds.append({"model": model, "row_id": rid, "arm": arm,
                          "source_sha256": row["source_sha256"],
                          "prompt_sha256": S.sha(row["prompt"].encode()),
                          "response": response})
    return index, digest, binding, preds


class PairedScorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.index, self.digest, self.binding, self.pred = fixture(self.dir)

    def test_positive_paired_scoring_is_not_native_proof(self):
        result = S.evaluate(self.index, self.digest, self.binding, self.pred)
        self.assertEqual(result["counts"]["base"]["no_offer"]["supported"], 0)
        self.assertEqual(result["counts"]["base"]["offer"]["supported"], 11)
        self.assertEqual(result["counts"]["candidate"]["no_offer"]["supported"], 11)
        self.assertEqual(result["offer_vs_no_offer"]["base"], {"wins": 11, "losses": 0, "ties": 0})
        self.assertEqual(result["candidate_vs_base"]["no_offer"]["wins"], 11)
        self.assertFalse(result["native_execution_verified_by_scorer"])
        self.assertFalse(result["model_utility_proven"])
        self.assertEqual(result["gates"]["jepa_weight"], 0)

    def test_invalid_quote_fails_closed(self):
        ref = self.index[("RUN181-00", "offer")]
        ans = ref["answer_keys"][0]
        result = S.score_one(json.dumps({"answer": ans, "evidence_quote": "invented " + ans,
                                         "uncertainty": ""}), ref["source"], ans)
        self.assertTrue(result["parsed"])
        self.assertFalse(result["quote_valid"])
        self.assertTrue(result["unsupported_commitment"])

    def test_unsupported_answer_and_key_substring(self):
        ref = self.index[("RUN181-00", "offer")]
        ans = ref["answer_keys"][0]
        raw = json.dumps({"answer": "My answer is " + ans, "evidence_quote": ref["source"], "uncertainty": ""})
        self.assertFalse(S.score_one(raw, ref["source"], ans)["supported"])

    def test_duplicate_keys_and_fenced_json_not_accepted(self):
        ref = self.index[("RUN181-00", "offer")]
        ans = ref["answer_keys"][0]
        raw = '{"answer":"' + ans + '","answer":"other","evidence_quote":"' + ref["source"] + '","uncertainty":""}'
        self.assertFalse(S.score_one(raw, ref["source"], ans)["parsed"])
        self.assertFalse(S.score_one("```json\n{}\n```", ref["source"], ans)["parsed"])

    def test_valid_abstention_not_unsupported_commitment(self):
        ref = self.index[("RUN181-00", "offer")]
        r = S.score_one('{"answer":"","evidence_quote":"","uncertainty":"unknown"}',
                        ref["source"], ref["answer_keys"][0])
        self.assertTrue(r["abstained"])
        self.assertFalse(r["unsupported_commitment"])

    def test_swapped_prompt_binding_rejected(self):
        row = next(p for p in self.pred if p["model"] == "candidate" and p["arm"] == "offer")
        other = self.index[(row["row_id"], "no_offer")]
        row["prompt_sha256"] = S.sha(other["prompt"].encode())
        with self.assertRaisesRegex(ValueError, "prompt binding"):
            S.evaluate(self.index, self.digest, self.binding, self.pred)

    def test_wrong_source_binding_rejected(self):
        self.pred[0]["source_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "source/prompt binding"):
            S.evaluate(self.index, self.digest, self.binding, self.pred)

    def test_missing_and_duplicate_predictions_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete predictions"):
            S.evaluate(self.index, self.digest, self.binding, self.pred[:-1])
        dup = list(self.pred)
        dup[-1] = dict(dup[0])
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            S.evaluate(self.index, self.digest, self.binding, dup)

    def test_model_binding_must_be_distinct_and_greedy(self):
        self.binding["models"]["candidate"]["deployed_gguf_sha256"] = "b"*64
        with self.assertRaisesRegex(ValueError, "identical"):
            S.evaluate(self.index, self.digest, self.binding, self.pred)
        self.binding["models"]["candidate"]["deployed_gguf_sha256"] = "d"*64
        self.binding["temperature"] = 0.5
        with self.assertRaisesRegex(ValueError, "non-greedy"):
            S.evaluate(self.index, self.digest, self.binding, self.pred)

    def test_manifest_and_source_tamper_rejected(self):
        path = self.dir / "heldout_paired.jsonl"
        original = path.read_bytes()
        path.write_bytes(original.replace(b"Code0", b"Xode0", 1))
        with self.assertRaisesRegex(ValueError, "heldout SHA"):
            S.load_dataset(self.dir, pinned=False)
        path.write_bytes(original)
        manifest = json.loads((self.dir / "MANIFEST.json").read_text())
        manifest["heldout_projects"] = ["project_A", "project_C"]
        (self.dir / "MANIFEST.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "split mismatch"):
            S.load_dataset(self.dir, pinned=False)

    def test_real_dataset_hash_pin_blocks_fixture(self):
        with self.assertRaisesRegex(ValueError, "heldout dataset SHA"):
            S.load_dataset(self.dir, pinned=True)

    def test_jsonl_duplicate_keys_and_nonfinite_rejected(self):
        path = self.dir / "bad.jsonl"
        path.write_text('{"model":"base","model":"candidate"}\n')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            S.read_jsonl(path)
        path.write_text('{"bad":NaN}\n')
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            S.read_jsonl(path)

    def test_empty_or_ambiguous_source_delimiter_rejected(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            S.source_from_prompt("no source", "offer")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            S.source_from_prompt(S.SOURCE_MARKER + "a" + S.ENDS["offer"] +
                                 S.SOURCE_MARKER + "b", "offer")

    def test_exclusive_write_preserves_original(self):
        path = self.dir / "SCORES.json"
        S.exclusive(path, b"original")
        with self.assertRaises(FileExistsError):
            S.exclusive(path, b"overwrite")
        self.assertEqual(path.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
