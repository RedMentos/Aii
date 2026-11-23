"""P0X C3 600-call source-arm independent closed-record verifier."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts import p0x_c3_source_arms as arms
from scripts import p0x_c3_600_native_executor as native

SCHEMA = "v13.p0x.c3_600_independent_verifier.v1"
FINAL = "RECORDED_LINUX_NATIVE_P0X_C3_SOURCE_ABLATIONS_NO_GATE"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def load(root, name):
    raw = (root / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def verify(root, baseline_root):
    root = Path(root)
    base_score = native.baseline_receipt(baseline_root)
    receipt, _ = load(root, "RECEIPT.json")
    raw, raw_sha = load(root, "RAW.json")
    score, score_sha = load(root, "SCORE.json")
    comparison, comparison_sha = load(root, "COMPARISON.json")
    inputs, inputs_sha = load(root, "INPUTS.json")
    answers, answers_sha = load(root, "ANSWERS.json")
    need(receipt.get("schema") == native.SCHEMA
         and receipt.get("status") == FINAL
         and receipt.get("fixture_sha256") == arms.FIXTURE_SHA256
         and receipt.get("baseline_raw_sha256") == native.BASELINE_RAW_SHA256
         and receipt.get("baseline_score_sha256") == native.BASELINE_SCORE_SHA256
         and receipt.get("model_sha256_before") == arms.C3_MODEL_SHA256
         and receipt.get("model_sha256_after") == arms.C3_MODEL_SHA256
         and receipt.get("runner_sha256_before") == arms.RUNNER_SHA256
         and receipt.get("runner_sha256_after") == arms.RUNNER_SHA256
         and receipt.get("seed") == arms.SEED
         and receipt.get("c3_tokens") == arms.TOKENS
         and receipt.get("c3_sampling") == "off"
         and receipt.get("expected_calls") == 600
         and receipt.get("recorded_calls") == 600
         and receipt.get("process_reaped") is True
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False,
         "P0X_ARMS_VERIFY_RECEIPT_RED")
    need(receipt.get("raw_sha256") == raw_sha
         and receipt.get("score_sha256") == score_sha
         and receipt.get("comparison_sha256") == comparison_sha
         and receipt.get("inputs_sha256") == inputs_sha
         and receipt.get("answers_sha256") == answers_sha,
         "P0X_ARMS_VERIFY_HASH_RED")
    plan, key = arms.plan_and_answers()
    need(inputs == plan and answers == key, "P0X_ARMS_VERIFY_INPUTS_RED")
    need(raw.get("status") == FINAL
         and raw.get("fixture_sha256") == arms.FIXTURE_SHA256
         and raw.get("baseline_raw_sha256") == native.BASELINE_RAW_SHA256,
         "P0X_ARMS_VERIFY_RAW_RED")
    need(score == arms.score(raw["rows"], plan, key),
         "P0X_ARMS_VERIFY_SCORE_RED")
    need(comparison == arms.compare_to_baseline(score, base_score),
         "P0X_ARMS_VERIFY_COMPARISON_RED")
    need(score.get("canonical_gate_pass") is False
         and score.get("step2_status") == "UTILITY_FAIL"
         and score.get("b3_status") == "FAIL"
         and score.get("body_jepa_status") == "UNAVAILABLE"
         and score.get("lp3_status") == "FAIL"
         and score.get("jepa_weight") == 0
         and score.get("redmi_measured") is False
         and score.get("whole_system_complete") is False
         and comparison.get("canonical_gate_pass") is False,
         "P0X_ARMS_VERIFY_NEGATIVE_GATES_RED")
    return {"schema": SCHEMA,
            "status": "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE",
            "rows": 600, "raw_sha256": raw_sha, "score_sha256": score_sha,
            "comparison_sha256": comparison_sha,
            "per_arm": score["per_arm"], "comparison": comparison,
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir", required=True, type=Path)
    ap.add_argument("--baseline-evidence-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(verify(args.evidence_dir, args.baseline_evidence_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
