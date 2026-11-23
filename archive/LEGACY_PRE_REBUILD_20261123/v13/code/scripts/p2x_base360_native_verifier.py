#!/usr/bin/env python3
"""Independent P2X frozen base360 raw/score/receipt replay verifier (no model calls)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts import p2x_native_receiver_eval_scorer as scorer
from scripts import hb1b_c3_format_native_executor as native

SCHEMA = "v13.p2x.base360_native.v1"
SUCCESS = "P2X_C3_BASE360_NATIVE_DIAGNOSTIC_NO_GATE"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify(evidence, validation_dir):
    root = Path(evidence)
    need(root.is_dir() and not root.is_symlink(),
         "P2X_BASE360_VERIFY_ROOT_RED")
    paths = {name: root / name for name in
             ("RECEIPT.json", "RAW.json", "SCORE.json",
              "INPUTS.json", "ANSWERS.json")}
    need(all(p.is_file() and not p.is_symlink() for p in paths.values()),
         "P2X_BASE360_VERIFY_MISSING_OR_SYMLINK_RED")
    receipt = json.loads(paths["RECEIPT.json"].read_bytes())
    need(receipt.get("schema") == SCHEMA
         and receipt.get("status") == SUCCESS
         and receipt.get("evidence_kind") == "LINUX_NATIVE_QAD_C3_P2X_BASE_ONLY"
         and receipt.get("fixture_sha256") == scorer.FIXTURE_SHA
         and receipt.get("validation_inputs_sha256") == scorer.INPUT_SHA
         and receipt.get("validation_answers_sha256") == scorer.ANSWER_SHA
         and receipt.get("model_sha256_before") == scorer.MODEL_SHA
         and receipt.get("model_sha256_after") == scorer.MODEL_SHA
         and receipt.get("runtime_sha256_before") == scorer.RUNTIME_SHA
         and receipt.get("runtime_sha256_after") == scorer.RUNTIME_SHA
         and receipt.get("runner_binary_sha256_before") == native.hb1b.RUNNER_SHA256
         and receipt.get("runner_binary_sha256_after") == native.hb1b.RUNNER_SHA256
         and receipt.get("adapter_sha256") is None
         and receipt.get("seed") == scorer.SEED
         and receipt.get("c3_sampling") == "off"
         and type(receipt.get("expected_calls")) is int
         and receipt["expected_calls"] == 360
         and type(receipt.get("recorded_calls")) is int
         and receipt["recorded_calls"] == 360
         and receipt.get("process_reaped") is True
         and receipt.get("weight_updates") is False
         and type(receipt.get("jepa_weight")) is int
         and receipt["jepa_weight"] == 0
         and receipt.get("redmi_measured") is False
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("whole_system_complete") is False,
         "P2X_BASE360_VERIFY_RECEIPT_OR_GATE_RED")
    for name, key in (("RAW.json", "raw_sha256"),
                      ("SCORE.json", "score_sha256"),
                      ("INPUTS.json", "inputs_sha256"),
                      ("ANSWERS.json", "answers_sha256")):
        need(receipt.get(key) == native.file_sha(paths[name]),
             "P2X_BASE360_VERIFY_HASH_RED:" + name)
    plan, answers = scorer.load_validation(validation_dir)
    need(paths["INPUTS.json"].read_bytes() ==
         scorer.canonical(plan).decode("utf-8").encode("utf-8")
         and paths["ANSWERS.json"].read_bytes() == scorer.canonical(answers),
         "P2X_BASE360_VERIFY_FROZEN_PLAN_RED")
    records = json.loads(paths["RAW.json"].read_bytes())
    need(type(records) is list and len(records) == 360
         and all(type(r) is dict and r.get("adapter_sha256") is None
                 and r.get("runtime_sha256") == scorer.RUNTIME_SHA
                 for r in records),
         "P2X_BASE360_VERIFY_RAW_COVERAGE_RED")
    calculated = scorer.score(records, plan, answers, adapter_sha256=None)
    scorer._validate_score_snapshot(calculated)
    need(paths["SCORE.json"].read_bytes() == scorer.canonical(calculated),
         "P2X_BASE360_VERIFY_SCORE_REPLAY_RED")
    return {
        "schema": "v13.p2x.base360_native.verify.v1",
        "status": "VERIFIED_BASE_ONLY_LINUX_NATIVE_NO_GATE",
        "rows": 360,
        "per_arm": calculated["per_arm"],
        "raw_sha256": receipt["raw_sha256"],
        "score_sha256": receipt["score_sha256"],
        "model_sha256": scorer.MODEL_SHA,
        "runtime_sha256": scorer.RUNTIME_SHA,
        "adapter_sha256": None,
        "native_calls": 360,
        "redmi_measured": False,
        "step2_status": "UTILITY_FAIL",
        "jepa_weight": 0,
        "whole_system_complete": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-dir", required=True)
    p.add_argument("--validation-dir", required=True)
    args = p.parse_args(argv)
    result = verify(args.evidence_dir, args.validation_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
