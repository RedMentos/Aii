#!/usr/bin/env python3
"""Run384: offline AG9 answer-field confidence vs actual native correctness.

Descriptive only. No calibration fitting, AG9 writes, threshold selection,
model, network, native execution, or production abstention activation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from v13.agi.generality import calibration
from v13.agi.metacog import MIN_SUPPORT

THRESHOLDS = (0.25, 0.50, 0.75, 0.90)
SCHEMA = "run384-field-only-selective-risk-v1"


def checked_row(row):
    if not isinstance(row, dict):
        raise ValueError("native row must be an object")
    if row.get("status") != "FINAL" or row.get("can_train_body") is not False:
        raise ValueError("native row is not a nontraining FINAL result")
    for name in ("correct_exact", "field_supported"):
        if type(row.get(name)) is not bool:
            raise ValueError("invalid native " + name)
    c = row.get("confidence")
    if type(c) not in (int, float) or not math.isfinite(c) or not 0 <= c <= 1:
        raise ValueError("invalid native confidence")
    arm = row.get("arm")
    if not isinstance(arm, str) or not arm or len(arm) > 64:
        raise ValueError("invalid arm")
    answer = row.get("answer")
    if not isinstance(answer, str):
        raise ValueError("invalid answer")
    empty = not bool(answer.strip())
    if empty and row["correct_exact"]:
        raise ValueError("empty answer cannot be exact correct")
    wrong_nonempty = not empty and not row["correct_exact"]
    if "empty" in row and row["empty"] is not empty:
        raise ValueError("empty flag conflicts with answer")
    if "wrong_nonempty" in row and row["wrong_nonempty"] is not wrong_nonempty:
        raise ValueError("wrong_nonempty conflicts with answer")
    if row["field_supported"] and row.get("confidence_source") not in (
        "field_min_prob", "field_mean_prob"
    ):
        raise ValueError("unsupported confidence source for field")
    return {
        "arm": arm, "confidence": float(c),
        "correct": row["correct_exact"], "field_supported": row["field_supported"],
        "empty": empty, "wrong_nonempty": wrong_nonempty,
    }


def audit_report(report, source_sha256):
    if not isinstance(report, dict) or report.get("evidence_level") != "LINUX_NATIVE_C3_ONLY":
        raise ValueError("expected actual Linux-native C3 report")
    rows = report.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("native report has no rows")
    validated = [checked_row(row) for row in rows]
    arms = sorted({row["arm"] for row in validated})
    results = {}
    for arm in arms:
        rr = [row for row in validated if row["arm"] == arm]
        field = [row for row in rr if row["field_supported"]]
        pairs = [(row["confidence"], int(row["correct"])) for row in field]
        selective = {}
        for threshold in THRESHOLDS:
            accepted = [
                row for row in rr
                if row["field_supported"] and not row["empty"] and row["confidence"] >= threshold
            ]
            accepted_correct = sum(row["correct"] for row in accepted)
            accepted_wrong = len(accepted) - accepted_correct
            selective[f"{threshold:.2f}"] = {
                "accepted": len(accepted),
                "coverage": round(len(accepted) / len(rr), 6),
                "accepted_correct": accepted_correct,
                "accepted_wrong": accepted_wrong,
                "selective_risk": (
                    round(accepted_wrong / len(accepted), 6) if accepted else None
                ),
                "rejected_correct": sum(row["correct"] for row in rr) - accepted_correct,
            }
        results[arm] = {
            "n": len(rr),
            "correct": sum(row["correct"] for row in rr),
            "empty": sum(row["empty"] for row in rr),
            "wrong_nonempty": sum(row["wrong_nonempty"] for row in rr),
            "field_supported": len(field),
            "fallback_or_unsupported": len(rr) - len(field),
            "field_only_calibration": calibration(pairs),
            "calibration_status": (
                "UNDERPOWERED" if len(field) < MIN_SUPPORT
                else "DESCRIPTIVE_ONLY_NOT_HELDOUT"
            ),
            "selective": selective,
        }
    return {
        "source_revision": report.get("revision"),
        "source_sha256": source_sha256,
        "source_evidence_level": report["evidence_level"],
        "arms": results,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", action="append", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    reports = []
    for name in args.report:
        raw = Path(name).read_bytes()
        reports.append(audit_report(json.loads(raw), hashlib.sha256(raw).hexdigest()))
    out = {
        "schema": SCHEMA,
        "thresholds": list(THRESHOLDS),
        "ag9_min_support": MIN_SUPPORT,
        "reports": reports,
        "claim_limit": (
            "Descriptive tiny Linux-native diagnostics; field-only confidence, "
            "no calibration fit or selected abstention threshold, no heldout promotion."
        ),
        "production_abstention_modified": False,
    }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "arms": [{k: {"n": v["n"], "field_supported": v["field_supported"],
                      "calibration_status": v["calibration_status"]}
                  for k, v in r["arms"].items()} for r in reports],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
