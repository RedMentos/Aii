"""P0X C3-only baseline independent closed-record verifier, not native attestation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts import p0x_c3_150_baseline as p0x

SCHEMA = "v13.p0x.c3_150_independent_verifier.v1"
FINAL = "RECORDED_LINUX_NATIVE_P0X_C3_ONLY_BASELINE_NO_GATE"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def load(root, name):
    raw = (root / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def verify(root):
    root = Path(root)
    receipt, _ = load(root, "RECEIPT.json")
    raw, raw_sha = load(root, "RAW.json")
    score, score_sha = load(root, "SCORE.json")
    inputs, inputs_sha = load(root, "INPUTS.json")
    answers, answers_sha = load(root, "ANSWERS.json")
    need(receipt.get("schema") == "v13.p0x.c3_150_native_baseline.v1"
         and receipt.get("status") == FINAL
         and receipt.get("fixture_sha256") == p0x.FIXTURE_SHA256
         and receipt.get("model_sha256_before") == p0x.C3_MODEL_SHA256
         and receipt.get("model_sha256_after") == p0x.C3_MODEL_SHA256
         and receipt.get("runner_sha256_before") == p0x.RUNNER_SHA256
         and receipt.get("runner_sha256_after") == p0x.RUNNER_SHA256
         and receipt.get("seed") == p0x.SEED
         and receipt.get("c3_tokens") == p0x.TOKENS
         and receipt.get("c3_sampling") == "off"
         and receipt.get("expected_calls") == 150
         and receipt.get("recorded_calls") == 150
         and receipt.get("process_reaped") is True
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False,
         "P0X_BASELINE_VERIFY_RECEIPT_RED")
    need(receipt.get("raw_sha256") == raw_sha
         and receipt.get("score_sha256") == score_sha
         and receipt.get("inputs_sha256") == inputs_sha
         and receipt.get("answers_sha256") == answers_sha,
         "P0X_BASELINE_VERIFY_HASH_RED")
    plan, key = p0x.plan_and_answers()
    need(inputs == plan and answers == key, "P0X_BASELINE_VERIFY_INPUTS_RED")
    need(raw.get("status") == FINAL
         and raw.get("fixture_sha256") == p0x.FIXTURE_SHA256,
         "P0X_BASELINE_VERIFY_RAW_RED")
    need(score == p0x.score(raw["rows"], plan, key),
         "P0X_BASELINE_VERIFY_SCORE_RED")
    need(score.get("canonical_gate_pass") is False
         and score.get("step2_status") == "UTILITY_FAIL"
         and score.get("b3_status") == "FAIL"
         and score.get("body_jepa_status") == "UNAVAILABLE"
         and score.get("lp3_status") == "FAIL"
         and score.get("jepa_weight") == 0
         and score.get("redmi_measured") is False
         and score.get("whole_system_complete") is False,
         "P0X_BASELINE_VERIFY_NEGATIVE_GATES_RED")
    return {"schema": SCHEMA,
            "status": "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE",
            "rows": 150, "raw_sha256": raw_sha, "score_sha256": score_sha,
            "per_arm": score["per_arm"], "output_labels": score["output_labels"],
            "oracle_headroom": score["oracle_headroom"],
            "headroom_sufficient": score["headroom_sufficient"],
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(verify(args.evidence_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
