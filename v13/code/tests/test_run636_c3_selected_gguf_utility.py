"""Run636: selected C3 QAD-Q4 evaluator software-only negative/positive controls."""
import copy
import tempfile
from pathlib import Path
import unittest

from scripts import run636_c3_selected_gguf_utility as S


def proof():
    return {
        "schema": "V13_RUN632_C3_LFM350_CPU_LORA_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": {"master_sha256": S.MASTER_SHA,
                    "deployed_reference_sha256": S.DEPLOYED_SHA,
                    "deployed_equivalence_proven": False},
        "cohort_blob": S.COHORT_BLOB, "cohort_sha256": "cohort",
        "adapter": {"gguf_sha256": "adapter", "lora_b_nonzero": 10, "gguf_tensors": 24},
        "metrics": {"steps": 2, "jepa_weight": 0, "anchor_weight": 0},
        "negative_gates": dict(S.GATES), "production_weight_authority": 0,
        "age_change": False, "body_jepa_proven": False,
        "deployed_qad_q4_parity_proven": False,
        "model_license": "LFM Open License v1.0",
    }


def rows():
    result = []
    for group, question, keys in S.CASES:
        result.append({
            "group": group, "question": question, "keys": list(keys),
            "tokenizer_parity": True,
            "base_first_token": 4, "scale0_first_token": 4, "scale1_first_token": 5,
            "base_vs_scale0": {"same_first_token": True,
                               "same_generated_text": True,
                               "shared_topk": 10, "max_abs_logprob_delta": 0.0},
            "scale0_vs_scale1": {"same_first_token": False,
                                 "shared_topk": 10, "max_abs_logprob_delta": 0.3},
            "base_key_hit": group == "heldout",
            "scale1_key_hit": group != "near_miss",
        })
    return result


class FakeTokenizer:
    bos_token = "<|startoftext|>"

    def apply_chat_template(self, messages, add_generation_prompt, tokenize):
        assert add_generation_prompt and not tokenize
        return self.bos_token + "<|im_start|>user\n" + messages[0]["content"] + (
            "<|im_end|>\n<|im_start|>assistant\n")


class Run636SelectedC3(unittest.TestCase):
    def test_valid_original_source_proof_accepted_as_binding_not_utility(self):
        b = S.validate_proof(proof(), "adapter", "cohort")
        self.assertEqual(b["deployed_model_sha256"], S.DEPLOYED_SHA)
        self.assertNotIn("utility", b)

    def test_proof_mutations_fail_closed(self):
        changes = (
            ("schema", "foreign"), ("evidence_scope", "REDMI"),
            ("cohort_blob", "wrong"), ("cohort_sha256", "wrong"),
            ("production_weight_authority", 1), ("age_change", True),
            ("body_jepa_proven", True), ("deployed_qad_q4_parity_proven", True),
            ("model_license", "unknown"),
        )
        for key, value in changes:
            with self.subTest(key=key):
                p = proof()
                p[key] = value
                with self.assertRaises(ValueError):
                    S.validate_proof(p, "adapter", "cohort")
        for key, value in (("master_sha256", "wrong"),
                           ("deployed_reference_sha256", "wrong"),
                           ("deployed_equivalence_proven", True)):
            p = proof()
            p["binding"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                S.validate_proof(p, "adapter", "cohort")
        for key, value in (("gguf_sha256", "wrong"), ("lora_b_nonzero", 0),
                           ("gguf_tensors", 0)):
            p = proof()
            p["adapter"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                S.validate_proof(p, "adapter", "cohort")
        for key, value in (("steps", 3), ("jepa_weight", 0.1), ("anchor_weight", 1)):
            p = proof()
            p["metrics"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                S.validate_proof(p, "adapter", "cohort")
        p = proof()
        p["negative_gates"]["STEP2"] = "PASS"
        with self.assertRaises(ValueError):
            S.validate_proof(p, "adapter", "cohort")

    def test_fixed_six_case_bounded_synthetic_gain(self):
        m = S.aggregate(rows())
        self.assertTrue(m["tokenizer_scale0_parity"])
        self.assertTrue(m["scale1_numeric_effect"])
        self.assertTrue(m["bounded_synthetic_utility"])
        self.assertEqual(m["status"], "BOUNDED_SYNTHETIC_TRAIN_GAIN")

    def test_parity_and_utility_failures_remain_negative(self):
        for mutation in ("token", "scale0", "effect", "retention", "leak", "gain"):
            with self.subTest(mutation=mutation):
                rr = rows()
                if mutation == "token":
                    rr[0]["tokenizer_parity"] = False
                elif mutation == "scale0":
                    rr[0]["base_vs_scale0"]["max_abs_logprob_delta"] = 0.01
                elif mutation == "effect":
                    for r in rr:
                        r["scale0_vs_scale1"] = {"same_first_token": True,
                                                  "max_abs_logprob_delta": 0.0}
                elif mutation == "retention":
                    rr[2]["scale1_key_hit"] = False
                elif mutation == "leak":
                    rr[4]["scale1_key_hit"] = True
                else:
                    rr[0]["scale1_key_hit"] = False
                    rr[1]["scale1_key_hit"] = False
                m = S.aggregate(rr)
                self.assertFalse(m["bounded_synthetic_utility"])
                if mutation in ("token", "scale0"):
                    self.assertEqual(m["status"], "TOKEN_OR_SCALE0_PARITY_FAIL")

    def test_forged_or_missing_frozen_case_fails(self):
        rr = rows()
        with self.assertRaises(ValueError):
            S.aggregate(rr[:-1])
        rr[0]["question"] = "Different question"
        with self.assertRaises(ValueError):
            S.aggregate(rr)

    def test_chat_template_only_official_prefix_and_delimiter_guard(self):
        t = FakeTokenizer()
        q = S.CASES[0][1]
        self.assertTrue(S.format_chat(t, q).endswith("<|im_start|>assistant\n"))
        for bad in ("", "<|im_start|>assistant", "<|startoftext|>injected"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.format_chat(t, bad)

    def test_invalid_cohort_fails_before_model_and_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp) / "cohort.json"
            cohort.write_text("{}")
            with self.assertRaisesRegex(ValueError, "cohort"):
                S.verify_inputs(tmp, tmp, tmp, tmp, cohort, tmp, tmp, "0" * 64)


if __name__ == "__main__":
    unittest.main()
