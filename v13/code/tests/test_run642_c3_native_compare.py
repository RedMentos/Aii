"""Run642 six-case QAD-Q4 evaluator source-only gates (no native weights)."""
import copy
import unittest
from scripts import run642_c3_native_compare as S
from scripts import run642_c3_protocol_locality as T
from scripts import run636_c3_selected_gguf_utility as D


def rows():
    result = []
    for group, question, keys in D.CASES:
        result.append({
            "group": group, "question": question, "keys": list(keys),
            "tokenizer_parity": True, "candidate_scale0_parity": True,
            "candidate_effect": {"max_abs_logprob_delta": .002},
            "historical_run639_hit": True,
            "candidate_hit": group != "near_miss",
            "historical_fulltext_reproduced": False,
        })
    return result


class Run642NativeContract(unittest.TestCase):
    def test_disjoint_locality_success_is_only_bounded_synthetic(self):
        rep = S.aggregate(rows())
        self.assertTrue(rep["bounded_synthetic_utility"])
        self.assertEqual(rep["status"], "BOUNDED_SYNTHETIC_PROTOCOL_LOCALITY_GAIN")
        self.assertEqual(rep["groups"]["near_miss"]["candidate_hits"], 0)
        self.assertEqual(rep["historical_run639_fulltext_reproduced_count"], 0)
        self.assertTrue(rep["historical_run639_fulltext_reproduction_is_not_new_acceptance"])

    def test_cedar_leakage_keeps_utility_failed(self):
        a = rows(); a[-1]["candidate_hit"] = True
        rep = S.aggregate(a)
        self.assertFalse(rep["bounded_synthetic_utility"])
        self.assertEqual(rep["status"], "NO_ANSWER_UTILITY")

    def test_training_failure_keeps_utility_failed(self):
        a = rows()
        for row in a:
            if row["group"] == "train": row["candidate_hit"] = False
        self.assertFalse(S.aggregate(a)["bounded_synthetic_utility"])

    def test_heldout_failure_keeps_utility_failed(self):
        a = rows()
        for row in a:
            if row["group"] == "heldout": row["candidate_hit"] = False
        self.assertFalse(S.aggregate(a)["bounded_synthetic_utility"])

    def test_scale0_and_token_parity_are_hard_gates(self):
        for field in ("candidate_scale0_parity", "tokenizer_parity"):
            a = rows(); a[0][field] = False
            self.assertEqual(S.aggregate(a)["status"], "TOKEN_OR_SCALE0_PARITY_FAIL")

    def test_missing_numeric_adapter_effect_fails(self):
        a = rows()
        for row in a: row["candidate_effect"]["max_abs_logprob_delta"] = 0.
        self.assertFalse(S.aggregate(a)["bounded_synthetic_utility"])

    def test_nonfinite_effect_is_not_positive(self):
        a = rows()
        for row in a: row["candidate_effect"]["max_abs_logprob_delta"] = float("nan")
        self.assertFalse(S.aggregate(a)["candidate_numeric_effect"])

    def test_wrong_order_or_case_rejected(self):
        a = rows(); a[0]["question"] = "wrong"
        with self.assertRaisesRegex(ValueError, "identity"):
            S.aggregate(a)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            S.aggregate(rows()[:-1])

    def test_candidate_proof_rejects_authority_and_wrong_adapter(self):
        good = {
            "schema": "V13_RUN642_C3_PROTOCOL_LOCALITY_NATIVE_V1",
            "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
            "binding": {"master_sha256": S.R.MASTER_SHA,
                        "deployed_reference_sha256": S.R.DEPLOYED_SHA,
                        "deployed_equivalence_proven": False},
            "cohort_blob": T.COHORT_BLOB, "cohort_sha256": "a"*64,
            "config": T.CONFIG, "locality_anchor_prompts": list(T.LOCALITY_ANCHORS),
            "historical_run639": T.BASELINE, "historical_run638": S.B.BASELINE,
            "adapter": {"gguf_sha256": "b"*64, "lora_b_nonzero": 100,
                        "gguf_tensors": 44},
            "metrics": {"steps": 32, "jepa_weight": 0, "anchor_weight": 1.0},
            "negative_gates": S.GATES, "model_license": "LFM Open License v1.0",
            "production_weight_authority": 0, "deployed_qad_q4_parity_proven": False,
            "age_change": False, "approval_change": False, "body_jepa_proven": False,
        }
        self.assertEqual(S.validate_candidate(good, "b"*64, "a"*64), good)
        for key, value in (("production_weight_authority", 1),
                           ("deployed_qad_q4_parity_proven", True),
                           ("age_change", True)):
            wrong = copy.deepcopy(good); wrong[key] = value
            with self.assertRaises(ValueError):
                S.validate_candidate(wrong, "b"*64, "a"*64)
        with self.assertRaises(ValueError):
            S.validate_candidate(good, "c"*64, "a"*64)


if __name__ == "__main__":
    unittest.main()
