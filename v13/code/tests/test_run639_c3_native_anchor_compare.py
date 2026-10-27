"""Run639 selected C3 anchored LoRA native comparison: source-only negative controls."""
import unittest
from scripts import run636_c3_selected_gguf_utility as D
from scripts import run639_c3_kl_anchor as S
from scripts import run639_c3_native_anchor_compare as N


def rows():
    out = []
    for group, question, keys in D.CASES:
        out.append({
            "group": group, "question": question, "keys": list(keys),
            "tokenizer_parity": True, "baseline_reproduced": True,
            "unanchored_scale0_parity": True, "anchored_scale0_parity": True,
            "unanchored_effect": {"max_abs_logprob_delta": 0.4},
            "anchored_effect": {"max_abs_logprob_delta": 0.5},
            "unanchored_hit": group in ("train", "near_miss"),
            "anchored_hit": (group == "train" and "color" in question or
                             group == "heldout" and "greeting" in question),
        })
    return out


def baseline():
    return {
        "schema": "V13_RUN638_C3_32STEP_QAD_Q4_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
        "binding": {
            "candidate_adapter_sha256": N.BASELINE_ADAPTER_SHA,
            "deployed_sha256": N.R.DEPLOYED_SHA,
            "master_sha256": N.R.MASTER_SHA,
            "template_sha256": N.TEMPLATE_SHA,
        },
        "metrics": {
            "status": "NO_ANSWER_UTILITY",
            "tokenizer_and_baseline_parity": True,
            "bounded_synthetic_utility": False,
            "groups": {"train": {"candidate_hits": 2},
                       "heldout": {"candidate_hits": 0},
                       "near_miss": {"candidate_hits": 2}},
        },
        "negative_gates": dict(N.GATES),
        "production_weight_authority": 0, "redmi_measured": False,
        "rows": [
            {"group": group, "question": question, "keys": list(keys)}
            for group, question, keys in D.CASES
        ],
    }


def candidate():
    return {
        "schema": "V13_RUN639_C3_ANCHORED_32STEP_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": {
            "master_sha256": N.R.MASTER_SHA,
            "deployed_reference_sha256": N.R.DEPLOYED_SHA,
            "deployed_equivalence_proven": False,
        },
        "cohort_blob": S.COHORT_BLOB, "cohort_sha256": "a" * 64,
        "config": dict(S.CONFIG), "anchor_prompts": list(S.ANCHORS),
        "baseline": dict(S.BASELINE),
        "adapter": {"gguf_sha256": "b" * 64, "lora_b_nonzero": 10, "gguf_tensors": 44},
        "metrics": {"steps": 32, "jepa_weight": 0, "anchor_weight": 1.0},
        "model_license": "LFM Open License v1.0",
        "negative_gates": dict(N.GATES),
        "production_weight_authority": 0,
        "deployed_qad_q4_parity_proven": False,
        "age_change": False, "approval_change": False, "body_jepa_proven": False,
    }


class Run639AnchoredNativeContract(unittest.TestCase):
    def test_strict_bounded_synthetic_acceptance(self):
        m = N.aggregate(rows())
        self.assertEqual(m["status"], "BOUNDED_SYNTHETIC_ANCHORED_GAIN")
        self.assertTrue(m["bounded_synthetic_utility"])
        self.assertEqual(N.GATES["STEP2"], "UTILITY_FAIL")

    def test_missing_or_reordered_case_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            N.aggregate(rows()[:-1])
        r = rows()
        r[0], r[1] = r[1], r[0]
        with self.assertRaisesRegex(ValueError, "order"):
            N.aggregate(r)

    def test_tokenizer_or_scale0_failure_refused(self):
        r = rows()
        r[0]["tokenizer_parity"] = False
        self.assertEqual(N.aggregate(r)["status"], "TOKEN_OR_BASELINE_PARITY_FAIL")
        r = rows()
        r[0]["anchored_scale0_parity"] = False
        self.assertFalse(N.aggregate(r)["tokenizer_and_baseline_parity"])

    def test_baseline_reproduction_failure_refused(self):
        r = rows()
        r[0]["baseline_reproduced"] = False
        self.assertFalse(N.aggregate(r)["bounded_synthetic_utility"])

    def test_train_recall_floor_refused(self):
        r = rows()
        for x in r:
            if x["group"] == "train":
                x["anchored_hit"] = False
        self.assertFalse(N.aggregate(r)["train_minimum"])

    def test_heldout_retention_floor_refused(self):
        r = rows()
        for x in r:
            if x["group"] == "heldout":
                x["anchored_hit"] = False
        self.assertFalse(N.aggregate(r)["heldout_retention_floor"])

    def test_near_miss_leak_refused(self):
        r = rows()
        r[4]["anchored_hit"] = True
        self.assertFalse(N.aggregate(r)["near_miss_nonleak_floor"])

    def test_nonfinite_logprobs_fail_closed(self):
        for value in (None, float("nan"), float("inf"), True):
            r = rows()
            for x in r:
                x["anchored_effect"]["max_abs_logprob_delta"] = value
            self.assertFalse(N.aggregate(r)["both_adapters_numeric_effect"])

    def test_baseline_proof_valid_and_negative_status_bound(self):
        N.validate_baseline(baseline())
        p = baseline()
        p["metrics"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "negative"):
            N.validate_baseline(p)

    def test_baseline_wrong_model_refused(self):
        p = baseline()
        p["binding"]["master_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "binding"):
            N.validate_baseline(p)

    def test_baseline_wrong_rows_refused(self):
        p = baseline()
        p["rows"][0]["question"] = "foreign"
        with self.assertRaisesRegex(ValueError, "case"):
            N.validate_baseline(p)

    def test_candidate_valid_and_no_approval(self):
        p = candidate()
        N.validate_candidate(p, "b" * 64, "a" * 64)
        p["production_weight_authority"] = 1
        with self.assertRaisesRegex(ValueError, "promotion"):
            N.validate_candidate(p, "b" * 64, "a" * 64)

    def test_candidate_anchor_weight_mismatch_refused(self):
        p = candidate()
        p["metrics"]["anchor_weight"] = 0
        with self.assertRaisesRegex(ValueError, "anchor optimizer"):
            N.validate_candidate(p, "b" * 64, "a" * 64)

    def test_candidate_anchor_prompts_mismatch_refused(self):
        p = candidate()
        p["anchor_prompts"][0] = "What is two plus two?"
        with self.assertRaisesRegex(ValueError, "anchors"):
            N.validate_candidate(p, "b" * 64, "a" * 64)

    def test_candidate_adapter_integrity_refused(self):
        with self.assertRaisesRegex(ValueError, "adapter integrity"):
            N.validate_candidate(candidate(), "0" * 64, "a" * 64)


if __name__ == "__main__":
    unittest.main()
