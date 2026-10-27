"""BP1 train-only QAD token audit; synthetic tokenizer, no model or heldout data."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import bp1_qad_token_budget as B
from scripts import bp1_paired_score as S


class FakeTokenizer:
    def __init__(self, multiplier=1):
        self.multiplier = multiplier
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {"add_generation_prompt": True, "tokenize": False}
        assert len(messages) == 1 and messages[0]["role"] == "user"
        self.calls.append(messages[0]["content"])
        return "<user> " + messages[0]["content"] + " <assistant>"

    def __call__(self, text, **kwargs):
        assert kwargs == {"add_special_tokens": False}
        return {"input_ids": list(range(max(1, len(text.split()) * self.multiplier)))}


def rows():
    out = []
    for i in range(25):
        key = "Code" + str(i)
        prompt = "Question about project " + str(i) + "? " + ("filler " * 220)
        target = json.dumps({"answer": key, "evidence_quote": "The owner is " + key, "uncertainty": ""})
        out.append({"row_id": f"RUN181-{i:02d}", "arm": "offer", "prompt": prompt,
                    "target": target, "answer_keys": [key], "source_sha256": "a"*64})
    return out


class TokenBudgetTests(unittest.TestCase):
    def test_160_truncates_train_but_1024_and_2048_fit_fixture(self):
        data = rows(); tok = FakeTokenizer()
        report = B.audit(data, tok, tokenizer_hashes={"tokenizer.json": "a"*64}, dependency_version="fake")
        self.assertEqual(len(tok.calls), 25)
        self.assertEqual(report["summary"]["160"]["truncated_rows"], 25)
        self.assertEqual(report["summary"]["1024"]["truncated_rows"], 0)
        self.assertEqual(report["summary"]["2048"]["truncated_rows"], 0)
        self.assertTrue(report["window_2048_feasible"])
        self.assertFalse(report["heldout_targets_used"])
        self.assertFalse(report["native_c3_training_executed"])

    def test_window_2048_failure_is_explicit(self):
        report = B.audit(rows(), FakeTokenizer(multiplier=12))
        self.assertFalse(report["window_2048_feasible"])
        self.assertEqual(report["summary"]["2048"]["truncated_rows"], 25)

    def test_target_truncation_detected(self):
        data = rows()
        data[0]["target"] = "answer " * 220
        report = B.audit(data, FakeTokenizer())
        self.assertEqual(report["summary"]["160"]["target_truncated_rows"], 1)
        self.assertFalse(report["rows"][0]["windows"]["160"]["target_fully_preserved"])

    def test_25_row_input_source_hash_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "train_offer.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows()) + "\n")
            loaded, digest = B.load_train(p, pinned=False)
            self.assertEqual(len(loaded), 25)
            self.assertEqual(digest, S.sha(p.read_bytes()))
            with self.assertRaisesRegex(ValueError, "source SHA"):
                B.load_train(p, pinned=True)

    def test_duplicate_row_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data = rows(); data[1]["row_id"] = data[0]["row_id"]
            p = Path(d) / "train.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in data) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate ID"):
                B.load_train(p, pinned=False)

    def test_non_offer_arm_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data = rows(); data[0]["arm"] = "no_offer"
            p = Path(d) / "train.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in data) + "\n")
            with self.assertRaisesRegex(ValueError, "wrong train arm"):
                B.load_train(p, pinned=False)

    def test_bad_target_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data = rows(); data[0]["answer_keys"] = ["wrong"]
            p = Path(d) / "train.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in data) + "\n")
            with self.assertRaisesRegex(ValueError, "answer/key"):
                B.load_train(p, pinned=False)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data = rows(); data[0]["target"] = '{"answer":"x","answer":"y","evidence_quote":"x","uncertainty":""}'
            p = Path(d) / "train.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in data) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                B.load_train(p, pinned=False)


if __name__ == "__main__":
    unittest.main()
