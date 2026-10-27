"""Run644 native evaluator source-only six-case vs four-negative separation."""
import copy
import unittest
from scripts import run644_c3_native_compare as S
from scripts import run644_c3_contrastive as T
from scripts import run636_c3_selected_gguf_utility as D


def rows():
    return [
        {"group": group, "question": question, "keys": list(keys),
         "tokenizer_parity": True, "candidate_scale0_parity": True,
         "candidate_effect": {"max_abs_logprob_delta": .001},
         "historical_run642_hit": True,
         "historical_run642_reproduced": False,
         "candidate_hit": group != "near_miss"}
        for group, question, keys in D.CASES
    ]


def negatives():
    return [{"question": r["prompt"], "target": r["target"],
             "candidate_hit": True} for r in T.CONTRASTIVE]


class Run644NativeContract(unittest.TestCase):
    def test_six_case_acceptance_separate_from_four_negative_rows(self):
        m = S.aggregate(rows(), negatives())
        self.assertTrue(m["bounded_synthetic_utility"])
        self.assertEqual(m["groups"]["near_miss"]["candidate_hits"], 0)
        self.assertEqual(m["contrastive_train_hits"], 4)
        self.assertEqual(m["contrastive_train_denominator"], 4)
        self.assertTrue(m["contrastive_train_is_not_six_case_acceptance"])
        self.assertEqual(m["historical_run642_fulltext_reproduced_count"], 0)

    def test_cedar_leak_still_fails_even_when_negatives_learn(self):
        a = rows(); a[-1]["candidate_hit"] = True
        self.assertEqual(S.aggregate(a, negatives())["status"], "NO_ANSWER_UTILITY")

    def test_negative_train_miss_does_not_redefine_six_case_gate(self):
        n = negatives()
        for row in n: row["candidate_hit"] = False
        m = S.aggregate(rows(), n)
        self.assertTrue(m["bounded_synthetic_utility"])
        self.assertEqual(m["contrastive_train_hits"], 0)

    def test_wrong_or_missing_negative_diagnostics_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing contrastive"):
            S.aggregate(rows(), negatives()[:-1])
        n = negatives(); n[0]["question"] = "Cedar"
        with self.assertRaisesRegex(ValueError, "identity"):
            S.aggregate(rows(), n)

    def test_tokenizer_scale0_and_numeric_are_hard_gates(self):
        for field in ("tokenizer_parity", "candidate_scale0_parity"):
            a = rows(); a[0][field] = False
            self.assertEqual(S.aggregate(a, negatives())["status"], "TOKEN_OR_SCALE0_PARITY_FAIL")
        a = rows()
        for row in a: row["candidate_effect"]["max_abs_logprob_delta"] = 0.
        self.assertFalse(S.aggregate(a, negatives())["bounded_synthetic_utility"])

    def test_incomplete_six_case_denominator_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            S.aggregate(rows()[:-1], negatives())

    def test_candidate_proof_fails_on_authority_or_wrong_contrastive(self):
        good = {
            "schema": "V13_RUN644_C3_DISJOINT_CONTRASTIVE_NATIVE_V1",
            "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
            "binding": {"master_sha256": S.R.MASTER_SHA,
                        "deployed_reference_sha256": S.R.DEPLOYED_SHA,
                        "deployed_equivalence_proven": False},
            "cohort_blob": T.COHORT_BLOB, "cohort_sha256": "a"*64,
            "config": T.CONFIG, "locality_anchor_prompts": list(S.B.LOCALITY_ANCHORS),
            "contrastive_rows": list(T.CONTRASTIVE),
            "historical_run642": T.BASELINE, "historical_run639": S.B.BASELINE,
            "historical_run638": S.H.BASELINE,
            "adapter": {"gguf_sha256": "b"*64, "lora_b_nonzero": 100, "gguf_tensors": 44},
            "metrics": {"steps": 32, "jepa_weight": 0, "anchor_weight": 1.0},
            "negative_gates": S.GATES, "model_license": "LFM Open License v1.0",
            "production_weight_authority": 0, "deployed_qad_q4_parity_proven": False,
            "age_change": False, "approval_change": False, "body_jepa_proven": False,
        }
        self.assertEqual(S.validate_candidate(good, "b"*64, "a"*64), good)
        for field, value in (("production_weight_authority", 1),
                             ("age_change", True),
                             ("deployed_qad_q4_parity_proven", True)):
            wrong = copy.deepcopy(good); wrong[field] = value
            with self.assertRaises(ValueError):
                S.validate_candidate(wrong, "b"*64, "a"*64)
        wrong = copy.deepcopy(good); wrong["contrastive_rows"][0]["target"] = "violet"
        with self.assertRaises(ValueError):
            S.validate_candidate(wrong, "b"*64, "a"*64)


if __name__ == "__main__":
    unittest.main()
