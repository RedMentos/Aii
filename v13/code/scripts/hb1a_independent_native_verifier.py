"""Independent read-only HB1a closed native evidence verifier.

Never calls models, repairs raw, promotes Canon gates or accepts mock proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts import hb0_split_information_cohort as hb0
from scripts import hb1a_two_body_native_pilot as hb1

SCHEMA = "v13.hb1a.independent_native_verifier.v1"
FINAL = "RECORDED_LINUX_NATIVE_THREE_ORGAN_DIAGNOSTIC_NO_GATE"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(root, name):
    raw = (root / name).read_bytes()
    return json.loads(raw), digest(raw)


def verify(root, expected_fixture_sha=hb1.FIXTURE):
    root = Path(root)
    need(expected_fixture_sha == hb1.FIXTURE, "HB1A_VERIFY_EXTERNAL_FIXTURE_RED")
    receipt, _ = load(root, "RECEIPT.json")
    raw, raw_hash = load(root, "RAW.json")
    score, score_hash = load(root, "SCORE.json")
    body_inputs, body_hash = load(root, "BODY_INPUTS.json")
    c3_inputs, c3_hash = load(root, "C3_INPUTS.json")
    need(receipt.get("schema") == "v13.hb1a.native_execution.v1"
         and receipt.get("status") == FINAL
         and receipt.get("fixture_sha256") == expected_fixture_sha
         and receipt.get("model_sha256_before") == hb1.MODEL_SHAS
         and receipt.get("model_sha256_after") == hb1.MODEL_SHAS
         and type(receipt.get("runner_sha256_before")) is str
         and len(receipt["runner_sha256_before"]) == 64
         and receipt.get("runner_sha256_after") == receipt["runner_sha256_before"]
         and receipt.get("process_reaped") is True
         and receipt.get("body_recorded") == 24
         and receipt.get("c3_recorded") == 30
         and receipt.get("seed") == hb1.SEED
         and receipt.get("body_tokens") == hb1.BODY_TOKENS
         and receipt.get("c3_tokens") == hb1.C3_TOKENS
         and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False,
         "HB1A_VERIFY_RECEIPT_RED")
    need(receipt.get("raw_sha256") == raw_hash
         and receipt.get("score_sha256") == score_hash
         and receipt.get("body_inputs_sha256") == body_hash
         and receipt.get("c3_inputs_sha256") == c3_hash,
         "HB1A_VERIFY_HASH_RED")
    rows = hb0.fixtures()
    need(hb0._sha(rows) == expected_fixture_sha, "HB1A_VERIFY_COHORT_DRIFT_RED")
    need(body_inputs == hb1.body_plan(rows, expected_fixture_sha),
         "HB1A_VERIFY_BODY_INPUTS_RED")
    need(raw.get("status") == FINAL
         and raw.get("fixture_sha256") == expected_fixture_sha,
         "HB1A_VERIFY_RAW_IDENTITY_RED")
    need(c3_inputs == hb1.receiver_plan(rows, expected_fixture_sha, raw["body_rows"]),
         "HB1A_VERIFY_C3_INPUTS_RED")
    need(score == hb1.score(raw["body_rows"], raw["c3_rows"], rows, expected_fixture_sha),
         "HB1A_VERIFY_SCORE_DRIFT_RED")
    need(score.get("canonical_gate_pass") is False
         and score.get("step2_status") == "UTILITY_FAIL"
         and score.get("b3_status") == "FAIL"
         and score.get("jepa_weight") == 0
         and score.get("redmi_measured") is False
         and score.get("whole_system_complete") is False,
         "HB1A_VERIFY_NEGATIVE_GATES_RED")
    return {"schema": SCHEMA, "status": "VERIFIED_LINUX_NATIVE_DIAGNOSTIC_ONLY_NO_GATE",
            "body_rows": 24, "c3_rows": 30, "fixture_sha256": expected_fixture_sha,
            "raw_sha256": raw_hash, "score_sha256": score_hash,
            "per_arm": score["per_arm"], "canonical_gate_pass": False,
            "step2_status": "UTILITY_FAIL", "b3_status": "FAIL",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--fixture-sha256", default=hb1.FIXTURE)
    args = p.parse_args(argv)
    print(json.dumps(verify(args.evidence_dir, args.fixture_sha256), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
