"""HB1b independent read-only closed native record verifier (not native attestation)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_followup as hb1b

SCHEMA = "v13.hb1b.independent_native_verifier.v1"
FINAL = "RECORDED_LINUX_NATIVE_C3_FORMAT_DIAGNOSTIC_NO_GATE"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def load(root, name):
    raw = (root / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def verify(root, parent_root):
    root = Path(root)
    receipt, _ = load(root, "RECEIPT.json")
    raw, raw_sha = load(root, "RAW.json")
    score, score_sha = load(root, "SCORE.json")
    inputs, input_sha = load(root, "INPUTS.json")
    need(receipt.get("schema") == "v13.hb1b.c3_format_native_execution.v1"
         and receipt.get("status") == FINAL
         and receipt.get("parent_raw_sha256") == hb1b.PARENT_RAW_SHA256
         and receipt.get("parent_score_sha256") == hb1b.PARENT_SCORE_SHA256
         and receipt.get("fixture_sha256") == hb1.FIXTURE
         and receipt.get("model_sha256_before") == hb1b.C3_MODEL_SHA256
         and receipt.get("model_sha256_after") == hb1b.C3_MODEL_SHA256
         and receipt.get("runner_sha256_before") == hb1b.RUNNER_SHA256
         and receipt.get("runner_sha256_after") == hb1b.RUNNER_SHA256
         and receipt.get("seed") == hb1b.SEED
         and receipt.get("c3_tokens") == hb1b.TOKENS
         and receipt.get("c3_sampling") == "off"
         and receipt.get("expected_calls") == 24
         and receipt.get("recorded_calls") == 24
         and receipt.get("process_reaped") is True
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False,
         "HB1B_VERIFY_RECEIPT_RED")
    need(receipt.get("raw_sha256") == raw_sha
         and receipt.get("score_sha256") == score_sha
         and receipt.get("inputs_sha256") == input_sha,
         "HB1B_VERIFY_HASH_RED")
    plan = hb1b.build(parent_root)
    need(inputs == plan, "HB1B_VERIFY_INPUTS_RED")
    need(raw.get("status") == FINAL
         and raw.get("parent_raw_sha256") == hb1b.PARENT_RAW_SHA256,
         "HB1B_VERIFY_RAW_RED")
    need(score == hb1b.score(raw["rows"], plan), "HB1B_VERIFY_SCORE_RED")
    need(score.get("canonical_gate_pass") is False
         and score.get("step2_status") == "UTILITY_FAIL"
         and score.get("b3_status") == "FAIL"
         and score.get("body_jepa_status") == "UNAVAILABLE"
         and score.get("lp3_status") == "FAIL"
         and score.get("jepa_weight") == 0
         and score.get("redmi_measured") is False
         and score.get("whole_system_complete") is False,
         "HB1B_VERIFY_NEGATIVE_GATES_RED")
    return {"schema": SCHEMA,
            "status": "CLOSED_RECORD_CONSISTENT_NO_NATIVE_ATTESTATION_NO_GATE",
            "rows": 24, "parent_raw_sha256": hb1b.PARENT_RAW_SHA256,
            "raw_sha256": raw_sha, "score_sha256": score_sha,
            "per_arm": score["per_arm"], "output_labels": score["output_labels"],
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--parent-evidence-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.evidence_dir, args.parent_evidence_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
