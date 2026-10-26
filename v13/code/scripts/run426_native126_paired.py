#!/usr/bin/env python3
"""Run426: paired O/P/S seed20 diagnostics from independently verified actual native receipts.

Read-only; never launches models or changes frozen Run394/397. Only 126/378
rows exist. No STEP2, B3, Body-JEPA, jepa_weight, Age or Redmi promotion.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import run394_step2_fresh as r394
import run397_step2_resume as r397
import run419_verify_stage3_native as r419
from run396_step2_pilot_audit import validated_rows

ARMS = ("O", "P", "S")
SEED = 20
VARIANTS = tuple(r397.VARIANTS)
FIXTURES = tuple(f["id"] for f in r394.FIXTURES)
EXPECTED = {(fixture, variant) for fixture in FIXTURES for variant in VARIANTS}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _mean(xs):
    require(bool(xs), "EMPTY_UTILITY_GROUP")
    return sum(xs) / len(xs)


def aggregate(by_arm):
    """Pure paired math with complete, finite, same-task source keys."""
    require(type(by_arm) is dict and set(by_arm) == set(ARMS),
            "ARM_SET_MISMATCH")
    for arm in ARMS:
        values = by_arm[arm]
        require(type(values) is dict and set(values) == EXPECTED,
                "PAIRED_TASK_COVERAGE_MISMATCH:" + arm)
        require(all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                    for x in values.values()),
                "NONFINITE_OR_OUT_OF_RANGE_UTILITY:" + arm)
    means = {arm: {variant: _mean([by_arm[arm][(f, variant)] for f in FIXTURES])
                   for variant in VARIANTS} for arm in ARMS}
    paired = {}
    for label, a, b in (("pointer_minus_off", "P", "O"),
                        ("pointer_minus_shared_body", "P", "S")):
        paired[label] = {}
        for variant in VARIANTS:
            values = {f: by_arm[a][(f, variant)] - by_arm[b][(f, variant)]
                      for f in FIXTURES}
            paired[label][variant] = {
                "paired_count": len(values),
                "mean": _mean(list(values.values())),
                "by_fixture": values,
                "positive": sum(x > 0 for x in values.values()),
                "negative": sum(x < 0 for x in values.values()),
                "ties": sum(x == 0 for x in values.values()),
            }
    return {"arm_mean_utility": means, "paired_differences": paired,
            "same_task_pairs_per_comparison": len(EXPECTED),
            "seed_count": 1, "seed": SEED}


def analyze(work, stage3_report):
    root = Path(work).absolute()
    verified = r419.verify(root, stage3_report)
    require(verified["status"] == "RUN419_NATIVE_126_INDEPENDENTLY_VERIFIED",
            "NATIVE126_RECEIPTS_NOT_VERIFIED")
    progress = json.loads((root / "RUN397_PROGRESS.json").read_text())
    by_arm = {}
    source = {}
    for arm in ARMS:
        rid = f"{arm}_s{SEED}"
        info = progress["completed"][rid]
        attempt = root / info["attempt"]
        report_path = attempt / f"tool_{rid}.json"
        tool = json.loads(report_path.read_text())
        rows = validated_rows(tool, EXPECTED, "run426:" + rid)
        values = {}
        for key, row in rows.items():
            score = row.get("score")
            require(type(score) is dict, "MISSING_UTILITY_SCORE:" + rid)
            utility = score.get("utility")
            require(type(utility) in (int, float) and math.isfinite(utility)
                    and 0 <= utility <= 1, "UTILITY_INVALID:" + rid)
            require(row.get("oracle_visible_to_native") is False,
                    "ORACLE_LEAK:" + rid)
            values[key] = utility
        by_arm[arm] = values
        source[rid] = {
            "tool_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "receipt": verified["receipt_sha256"][rid],
            "rows": len(rows),
        }
    result = aggregate(by_arm)
    return {"run": "Run426", "status": "SEED20_PAIRED_DIAGNOSTIC_NATIVE126",
            "evidence_level": "ACTUAL_LINUX_NATIVE_RUN418_INDEPENDENT_RUN425",
            "source": source, "verified_rows": 126,
            "verified_manifest_sha256": verified["manifest_sha256"],
            "verified_progress_sha256": verified["progress_sha256"],
            **result, "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "native_execution_performed": False,
            "claim_limit": "Seed20 only, 126/378 preregistered rows; no cross-seed inference or STEP2/B3/Body-JEPA/Age promotion."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--stage3-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        report = analyze(a.work, json.loads(a.stage3_report.read_text()))
        code = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        report = {"run": "Run426", "status": "SEED20_DIAGNOSTIC_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "native_execution_performed": False, "redmi_measured": False,
                  "jepa_weight": 0}
        code = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    summary = {"status": report["status"],
               "rows": report.get("verified_rows", 0),
               "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
    if code == 0:
        summary["arm_mean_utility"] = report["arm_mean_utility"]
        summary["paired_by_variant"] = {
            label: {variant: {"mean": row["mean"], "positive": row["positive"],
                              "negative": row["negative"], "ties": row["ties"]}
                    for variant, row in variants.items()}
            for label, variants in report["paired_differences"].items()}
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
