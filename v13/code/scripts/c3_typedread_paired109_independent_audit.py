"""Independent read-only audit of paired109 raw report; no native/model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import c3_typedread_paired109_native as cohort
from scripts import listarith_de_operator_shadow as operator
from v13.agi import listarith
from v13.agi import listarith_de_shadow_pipeline as pipeline
from v13.agi import listarith_de_closedworld_candidate as closedworld

MAX_REPORT_BYTES = 2 * 1024 * 1024


class AuditError(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise AuditError(label)


def audit(report_path):
    path = Path(report_path)
    require(path.is_file() and 0 < path.stat().st_size <= MAX_REPORT_BYTES,
            "REPORT_SIZE_OR_TYPE")
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = cohort.frozen_rows()
    require(report.get("schema") == "v13.c3.typedread.paired109.result.v1",
            "REPORT_SCHEMA")
    require(report.get("seed") == 109, "SEED_CHANGED")
    require(report.get("fixture_blob") == cohort.FIXTURE_BLOB,
            "FIXTURE_CHANGED")
    require(report.get("model_sha256") == cohort.original.MODEL_SHA256,
            "MODEL_CHANGED")
    require(report.get("binary_sha256") == cohort.original.BINARY_SHA256,
            "BINARY_CHANGED")
    require(report.get("arm_a_system_sha256") ==
            cohort.sha(listarith.READ_SYSTEM.encode()), "ARM_A_CHANGED")
    require(report.get("arm_b_system_sha256") ==
            cohort.sha(cohort.EXPLICIT_SYSTEM.encode()), "ARM_B_CHANGED")
    require(report.get("learning_mode") == "RECORD_ONLY", "AGE_CHANGED")
    require(report.get("authority") == "SHADOW_ONLY", "AUTHORITY_CHANGED")
    require(type(report.get("jepa_weight")) is int
            and report["jepa_weight"] == 0, "JEPA_CHANGED")
    for field in ("redmi_measured", "live_tool_execution",
                  "external_action_authority", "step2_gate_promoted",
                  "b3_promoted", "body_jepa_available",
                  "whole_system_complete"):
        require(report.get(field) is False, "NEGATIVE_GATE_CHANGED:" + field)
    got_rows = report.get("rows")
    require(isinstance(got_rows, list) and len(got_rows) == 8,
            "ROW_COUNT")
    counts = {"A_exact": 0, "B_exact": 0, "D_exact": 0,
              "A_shadow_correct": 0, "B_shadow_correct": 0,
              "native_admitted": 0}
    diagnostic = {"A_wrong": 0, "B_wrong": 0,
                  "A_abstain": 0, "B_abstain": 0}
    for expected, observed in zip(rows, got_rows):
        require(observed.get("id") == expected["id"], "ROW_ID_CHANGED")
        require(observed.get("source_sha256") ==
                cohort.sha(expected["text"].encode()), "SOURCE_HASH_CHANGED")
        require(observed.get("expected_answer") == expected["expected_answer"],
                "EXPECTED_ANSWER_CHANGED")
        require(observed.get("expected_operation") ==
                expected["expected_operation"], "EXPECTED_OPERATION_CHANGED")
        deterministic = cohort.deterministic_pairs(expected["text"])
        require(observed.get("D_values") == deterministic, "D_BASELINE_CHANGED")
        counts["D_exact"] += int(deterministic == expected["expected_values"])
        arms = observed.get("arms")
        require(isinstance(arms, dict) and set(arms) == {"A", "B"},
                "ARM_SET_CHANGED")
        for arm in ("A", "B"):
            entry = arms[arm]
            receipt = entry.get("receipt")
            require(isinstance(receipt, dict), "RECEIPT_MISSING")
            require(receipt.get("native_attempted") is True, "NATIVE_NOT_ATTEMPTED")
            require(receipt.get("admitted") is True
                    and operator._native_receipt_admissible(receipt),
                    "NATIVE_RECEIPT_UNVERIFIED")
            require(receipt.get("native_final") is True, "NATIVE_NOT_FINAL")
            require(receipt.get("postclose_process_reaped") is True,
                    "NATIVE_NOT_REAPED")
            require(type(receipt.get("native_pid")) is int
                    and receipt["native_pid"] > 0, "NATIVE_PID_INVALID")
            metrics = receipt.get("native_metrics")
            require(isinstance(metrics, dict)
                    and metrics.get("status") == "FINAL"
                    and metrics.get("actual_model") ==
                    "LFM2.5-350M-QAD-Q4_0.gguf", "NATIVE_MODEL_OR_STATUS")
            raw = receipt["raw_output"]
            require(entry.get("raw_sha256") ==
                    hashlib.sha256(raw.encode()).hexdigest(), "RAW_HASH_CHANGED")
            try:
                values = pipeline.parse_typed(raw)
                exact = (sorted((v["name"], v["number"]) for v in values)
                         == sorted((v["name"], v["number"])
                                   for v in expected["expected_values"]))
            except (ValueError, TypeError, KeyError):
                exact = False
            baseline = pipeline.evaluate(expected["text"], raw)
            closed = closedworld.evaluate(expected["text"], raw)
            correct = (closed["status"] == "SHADOW_RESULT"
                       and closed["operation"] == expected["expected_operation"]
                       and closed["value"] == expected["expected_answer"])
            require(entry.get("typed_exact") is exact, "EXACT_CLAIM_CHANGED")
            require(entry.get("baseline") == baseline, "BASELINE_CHANGED")
            require(entry.get("closedworld") == closed, "CLOSEDWORLD_CHANGED")
            require(entry.get("shadow_correct") is correct,
                    "SHADOW_CORRECT_CLAIM_CHANGED")
            counts["native_admitted"] += 1
            counts[arm + "_exact"] += int(exact)
            counts[arm + "_shadow_correct"] += int(correct)
            diagnostic[arm + "_abstain"] += int(closed["status"] == "SHADOW_ABSTAIN")
            diagnostic[arm + "_wrong"] += int(
                closed["status"] == "SHADOW_RESULT" and not correct)
    require(report.get("counts") == counts, "REPORTED_COUNTS_CHANGED")
    return {
        "schema": "v13.c3.typedread.paired109.independent_audit.v1",
        "audit": "STRUCTURAL_PASS", "evidence_level": "LINUX_NATIVE_IF_ORIGINAL_ZIP_VERIFIED",
        "source_report_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "counts": counts, "diagnostic": diagnostic,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.report)
    operator._write_private_new(args.out, result)
    print(json.dumps({"audit": result["audit"], "counts": result["counts"],
                      "diagnostic": result["diagnostic"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
