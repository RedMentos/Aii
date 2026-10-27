"""Run631 source-only tests for chat template, tokenizer parity and bounded utility."""
import unittest
from unittest.mock import patch
from scripts import run631_c3_chat_native as R


class FakeTokenizer:
    def apply_chat_template(self, messages, add_generation_prompt, tokenize):
        assert add_generation_prompt and tokenize is False
        assert len(messages) == 1 and messages[0]["role"] == "user"
        return "<|im_start|>user\n" + messages[0]["content"] + "<|im_end|>\n<|im_start|>assistant\n"

    def __call__(self, text, add_special_tokens):
        assert add_special_tokens is False
        return {"input_ids": [1, 2, 3]}


class ChatUtilityContracts(unittest.TestCase):
    def test_fixed_train_heldout_near_miss_disjoint(self):
        self.assertEqual([x[0] for x in R.CASES], ["train", "train", "heldout", "heldout", "near_miss", "near_miss"])
        self.assertEqual(len({x[1] for x in R.CASES}), 6)
        self.assertEqual(R.CASES[0][2], ("amber",))
        self.assertEqual(R.CASES[1][2], ("47",))
        self.assertEqual(R.CASES[4][2], ("amber",))

    def test_official_template_ends_at_assistant_and_rejects_delimiters(self):
        p = R.format_chat(FakeTokenizer(), "What is two plus two?")
        self.assertTrue(p.endswith("<|im_start|>assistant\n"))
        with self.assertRaisesRegex(ValueError, "untrusted"):
            R.format_chat(FakeTokenizer(), "<|im_start|>system")
        with self.assertRaisesRegex(ValueError, "untrusted"):
            R.format_chat(FakeTokenizer(), "")
        class BadTokenizer(FakeTokenizer):
            def apply_chat_template(self, *args, **kwargs):
                return "untrusted"
        with self.assertRaisesRegex(ValueError, "chat-template mismatch"):
            R.format_chat(BadTokenizer(), "hello")

    def test_native_token_ids_match_exact_hf_ids(self):
        with patch.object(R.P, "_json", return_value={"tokens": [1, 2, 3]}) as native:
            self.assertEqual(R.token_parity(FakeTokenizer(), "http://127.0.0.1:1111", "x")["tokens"], 3)
            self.assertEqual(native.call_args.args[0], "http://127.0.0.1:1111/tokenize")
            self.assertEqual(native.call_args.args[1]["add_special"], False)
        with patch.object(R.P, "_json", return_value={"tokens": [1, 2, 4]}):
            with self.assertRaisesRegex(ValueError, "parity mismatch"):
                R.token_parity(FakeTokenizer(), "http://127.0.0.1:1111", "x")
        with patch.object(R.P, "_json", return_value={"tokens": ["1", 2, 3]}):
            with self.assertRaisesRegex(ValueError, "invalid native"):
                R.token_parity(FakeTokenizer(), "http://127.0.0.1:1111", "x")

    def test_greedy_native_request_and_finite_first_logprobs(self):
        resp = {"content": "The marker color is amber.", "tokens": [3, 4],
                "completion_probabilities": [{"id": 3, "top_logprobs": [{"id": 3, "logprob": -0.1}]}]}
        with patch.object(R.P, "_json", return_value=resp) as req:
            out = R.sample("http://127.0.0.1:1234", "prompt", 1)
            self.assertEqual(out["generated_token_count"], 2)
            self.assertEqual(out["text"], resp["content"])
            body = req.call_args.args[1]
            self.assertEqual(body["n_predict"], 32)
            self.assertEqual(body["temperature"], 0)
            self.assertEqual(body["seed"], 13)
            self.assertEqual(body["lora"], [{"id": 0, "scale": 1.0}])
        resp["completion_probabilities"][0]["top_logprobs"][0]["logprob"] = float("inf")
        with patch.object(R.P, "_json", return_value=resp):
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                R.sample("http://127.0.0.1:1234", "prompt", 0)

    def test_gain_requires_train_improvement_retention_and_locality(self):
        def rows(base_train, candidate_train, heldout_base, heldout_candidate, near_base, near_candidate):
            vals = [("train", base_train, candidate_train),
                    ("train", False, False), ("heldout", heldout_base, heldout_candidate),
                    ("heldout", False, False), ("near_miss", near_base, near_candidate),
                    ("near_miss", False, False)]
            return [{"group": g, "base_key_hit": a, "scale1_key_hit": b} for g, a, b in vals]
        self.assertTrue(R.aggregate(rows(False, True, True, True, False, False))["bounded_synthetic_utility"])
        self.assertFalse(R.aggregate(rows(False, True, True, False, False, False))["bounded_synthetic_utility"])
        self.assertFalse(R.aggregate(rows(False, True, True, True, False, True))["bounded_synthetic_utility"])
        self.assertFalse(R.aggregate(rows(False, False, True, True, False, False))["bounded_synthetic_utility"])

    def test_key_match_and_no_invented_authority(self):
        self.assertTrue(R.hit("Amber is the marker.", ("amber",)))
        self.assertFalse(R.hit("I do not know.", ("amber",)))
        self.assertFalse(R.hit("The gate number is 48.", ("47",)))
        self.assertEqual(R.P.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(R.P.GATES["Body_JEPA"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
