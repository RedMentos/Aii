"""Run638 selected C3 2-vs-32-step native comparison: source-only gates."""
import copy
import unittest
from scripts import run636_c3_selected_gguf_utility as D
from scripts import run638_c3_dose_response as S
from scripts import run638_c3_native_compare as N
from scripts import run631_c3_chat_native as C


def synthetic_rows():
    rows = []
    for group, question, keys in D.CASES:
        rows.append({
            "group": group, "question": question, "keys": list(keys),
            "tokenizer_parity": True, "original_baseline_reproduced": True,
            "two_step_scale0_parity": True, "thirtytwo_scale0_parity": True,
            "two_step_effect": {"max_abs_logprob_delta": 0.4},
            "thirtytwo_effect": {"max_abs_logprob_delta": 0.5},
            "two_step_hit": group == "heldout",
            "thirtytwo_hit": group in ("train", "heldout"),
        })
    return rows


def original_proof():
    return {
        "schema": "V13_RUN636_SELECTED_C3_QAD_Q4_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
        "binding": {
            "adapter_sha256": N.ORIGINAL_ADAPTER_SHA,
            "deployed_model_sha256": N.R.DEPLOYED_SHA,
            "master_sha256": N.R.MASTER_SHA,
            "template_sha256": N.TEMPLATE_SHA,
        },
        "metrics": {
            "status": "NO_ANSWER_UTILITY",
            "tokenizer_scale0_parity": True,
            "bounded_synthetic_utility": False,
            "groups": {"train": {"candidate_hits": 0}},
        },
        "negative_gates": dict(N.GATES),
        "production_weight_authority": 0, "redmi_measured": False,
        "rows": [
            {"group": group, "question": question, "keys": list(keys)}
            for group, question, keys in D.CASES
        ],
    }


def candidate_proof():
    return {
        "schema": "V13_RUN638_C3_32STEP_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": {
            "master_sha256": N.R.MASTER_SHA,
            "deployed_reference_sha256": N.R.DEPLOYED_SHA,
            "deployed_equivalence_proven": False,
        },
        "cohort_blob": S.COHORT_BLOB, "cohort_sha256": "a" * 64,
        "config": dict(S.CONFIG), "baseline": dict(S.BASELINE),
        "adapter": {"gguf_sha256": "b" * 64, "lora_b_nonzero": 10, "gguf_tensors": 44},
        "metrics": {"steps": 32, "jepa_weight": 0, "anchor_weight": 0},
        "model_license": "LFM Open License v1.0",
        "negative_gates": dict(N.GATES),
        "production_weight_authority": 0,
        "deployed_qad_q4_parity_proven": False,
        "age_change": False, "approval_change": False, "body_jepa_proven": False,
    }


class Run638NativeCompareContracts(unittest.TestCase):
    def test_positive_is_only_bounded_synthetic_not_system_promotion(self):
        m = N.aggregate(synthetic_rows())
        self.assertEqual(m["status"], "BOUNDED_SYNTHETIC_32STEP_GAIN")
        self.assertTrue(m["bounded_synthetic_utility"])
        self.assertEqual(N.GATES["STEP2"], "UTILITY_FAIL")

    def test_missing_row_refused(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            N.aggregate(synthetic_rows()[:-1])

    def test_reordered_row_refused(self):
        rows = synthetic_rows()
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaisesRegex(ValueError, "order"):
            N.aggregate(rows)

    def test_tokenizer_parity_failure_refused(self):
        rows = synthetic_rows()
        rows[0]["tokenizer_parity"] = False
        self.assertEqual(N.aggregate(rows)["status"], "TOKEN_OR_BASELINE_PARITY_FAIL")

    def test_original_baseline_nonreproducible_refused(self):
        rows = synthetic_rows()
        rows[0]["original_baseline_reproduced"] = False
        self.assertFalse(N.aggregate(rows)["bounded_synthetic_utility"])

    def test_scale0_nonidentity_refused(self):
        rows = synthetic_rows()
        rows[0]["thirtytwo_scale0_parity"] = False
        self.assertFalse(N.aggregate(rows)["tokenizer_and_baseline_parity"])

    def test_heldout_regression_refused(self):
        rows = synthetic_rows()
        rows[2]["thirtytwo_hit"] = False
        rows[3]["thirtytwo_hit"] = False
        self.assertFalse(N.aggregate(rows)["heldout_nonregression"])

    def test_near_miss_leak_refused(self):
        rows = synthetic_rows()
        rows[4]["thirtytwo_hit"] = True
        self.assertFalse(N.aggregate(rows)["near_miss_nonleak"])

    def test_no_train_gain_refused(self):
        rows = synthetic_rows()
        rows[0]["thirtytwo_hit"] = False
        rows[1]["thirtytwo_hit"] = False
        self.assertEqual(N.aggregate(rows)["status"], "NO_ANSWER_UTILITY")

    def test_no_numeric_effect_refused(self):
        rows = synthetic_rows()
        for r in rows:
            r["thirtytwo_effect"]["max_abs_logprob_delta"] = 0
        self.assertFalse(N.aggregate(rows)["both_adapters_numeric_effect"])

    def test_missing_or_nonfinite_logprob_effect_fails_closed(self):
        for value in (None, float("nan"), float("inf")):
            rows = synthetic_rows()
            for row in rows:
                row["thirtytwo_effect"]["max_abs_logprob_delta"] = value
            self.assertFalse(N.aggregate(rows)["both_adapters_numeric_effect"])

    def test_original_proof_valid_and_negative_status_bound(self):
        N.validate_original(original_proof())
        p = original_proof()
        p["metrics"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "negative"):
            N.validate_original(p)

    def test_original_proof_wrong_model_refused(self):
        p = original_proof()
        p["binding"]["master_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "binding"):
            N.validate_original(p)

    def test_original_proof_wrong_case_refused(self):
        p = original_proof()
        p["rows"][0]["question"] = "foreign question"
        with self.assertRaisesRegex(ValueError, "case"):
            N.validate_original(p)

    def test_candidate_proof_valid_and_no_approval(self):
        p = candidate_proof()
        N.validate_candidate(p, "b" * 64, "a" * 64)
        p["production_weight_authority"] = 1
        with self.assertRaisesRegex(ValueError, "promotion"):
            N.validate_candidate(p, "b" * 64, "a" * 64)

    def test_candidate_proof_wrong_steps_refused(self):
        p = candidate_proof()
        p["metrics"]["steps"] = 31
        with self.assertRaisesRegex(ValueError, "steps"):
            N.validate_candidate(p, "b" * 64, "a" * 64)

    def test_candidate_proof_wrong_adapter_refused(self):
        with self.assertRaisesRegex(ValueError, "integrity"):
            N.validate_candidate(candidate_proof(), "0" * 64, "a" * 64)

    def test_original_exact_key_scoring_is_preserved_not_retroactively_changed(self):
        # Known limitation: exact digit 4 does not count the word 'four'.
        self.assertFalse(C.hit("Two plus two equals four.", ("4",)))
        self.assertTrue(C.hit("Hello!", ("hello",)))


if __name__ == "__main__":
    unittest.main()
