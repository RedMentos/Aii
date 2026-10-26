#!/usr/bin/env python3
"""Run516: fail-closed five-stage Run513 receipts -> frozen Run510 metric.

Source-only aggregation; cannot independently confirm GitHub Actions native work.
"""
import argparse
import hashlib
import json
from pathlib import Path

import run509_b2_rule_quote_prereg as frozen
import run510_b2_quote_metric as metric
import run511_b2_offer_collector as collector
import run513_b2_receipt_postflight as postflight


def require(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def aggregate(stage_dirs):
    require(type(stage_dirs) is list and len(stage_dirs) == 5,
            "EXACT_FIVE_STAGE_DIRS_REQUIRED")
    roots = [Path(p) for p in stage_dirs]
    require(all(p.is_dir() and not p.is_symlink() for p in roots) and
            len({str(p.resolve()) for p in roots}) == 5,
            "STAGE_DIR_MISSING_DUPLICATE_OR_SYMLINK")
    all_rows = []
    bindings = []
    for index, work in enumerate(roots):
        plan = collector.plan(index)
        require(postflight.load_json(work / "RUN511_STAGE_PLAN.json") == plan,
                "STAGE_ORDER_OR_FROZEN_PLAN_DRIFT")
        fresh, rows = postflight.audit(work, index)
        stored = postflight.load_json(work / "RUN513_POSTFLIGHT.json")
        stored_rows = postflight.load_json(
            work / "RUN513_VERIFIED_METRIC_ROWS.json")
        require(stored == fresh and stored_rows == rows,
                "STORED_POSTFLIGHT_OR_METRIC_ROWS_DRIFT")
        require(fresh["stage_id"] == f"p{index:02d}" and
                fresh["source_bound_rows"] == 12 and
                fresh["native_execution_independently_confirmed"] is False and
                fresh["canonical_gate_pass"] is False and
                fresh["step2_exit"] == "UTILITY_FAIL" and
                fresh["b3_l1"] == "FAIL" and
                fresh["jepa_weight"] == 0 and
                fresh["redmi_measured"] is False and
                len(rows) == 12 and
                [[r["fixture"], r["arm"], r["seed"]] for r in rows] ==
                plan["row_keys"], "STAGE_REPORT_COVERAGE_OR_GATE_DRIFT")
        bindings.append({
            "stage_id": f"p{index:02d}",
            "row_keys_sha256": fresh["row_keys_sha256"],
            "raw_observations_sha256": fresh["raw_observations_sha256"],
            "postflight_file_sha256":
                sha((work / "RUN513_POSTFLIGHT.json").read_bytes()),
            "metric_rows_file_sha256":
                sha((work / "RUN513_VERIFIED_METRIC_ROWS.json").read_bytes()),
            "metric_rows_canonical_sha256": sha(canonical(rows)),
        })
        all_rows.extend(rows)
    keys = [(r["fixture"], r["arm"], r["seed"]) for r in all_rows]
    registration = frozen.registration()
    expected = {(f["id"], arm, seed) for f in registration["fixtures"]
                for arm in frozen.ARMS for seed in frozen.SEEDS}
    require(len(keys) == len(set(keys)) == 60 and set(keys) == expected,
            "SIXTY_ROW_EXACT_COVERAGE_REQUIRED")
    scored = metric.score(registration, all_rows)
    require(scored["observations"] == 60 and
            scored["primary_paired_observations"] == 24 and
            scored["native_evidence_verified"] is False and
            scored["canonical_gate_pass"] is False and
            scored["step2_exit"] == "UTILITY_FAIL",
            "FROZEN_RUN510_SCORE_OR_GATE_DRIFT")
    summary = {
        "schema": "V13_RUN516_FIVE_STAGE_B2_QUOTE_AGGREGATE_V1",
        "status": "SOURCE_REF_60_ROW_STRUCTURAL_AGGREGATE_NOT_NATIVE_PROOF",
        "registered_fixture_sha256": frozen.EXPECTED_FIXTURE_SHA256,
        "stages": bindings,
        "stage_count": 5, "observation_count": 60,
        "paired_primary_count": 24,
        "metric_rows_canonical_sha256": sha(canonical(all_rows)),
        "frozen_run510_metric_sha256": sha(canonical(scored)),
        "primary_focus_minus_base_rows":
            scored["primary_focus_minus_base_rows"],
        "preregistered_descriptive_gain_reached":
            scored["preregistered_descriptive_gain_reached"],
        "native_execution_independently_confirmed": False,
        "false_prior_rule_assertions_in_summaries_evaluated": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "claim_limit": "Only structural source-ref receipts plus literal quote metric. Confirm original native Actions and model hashes separately; no STEP2/JEPA/Redmi promotion.",
    }
    return summary, all_rows, scored


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir", type=Path, action="append", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    require(args.output_dir.is_dir() and not args.output_dir.is_symlink(),
            "OUTPUT_DIR_REQUIRED")
    paths = [args.output_dir / name for name in
             ("RUN516_AGGREGATED_ROWS.json", "RUN516_RUN510_METRIC.json",
              "RUN516_AGGREGATE_REPORT.json")]
    require(not any(x.exists() or x.is_symlink() for x in paths),
            "REFUSE_OVERWRITE_OR_PARTIAL_OUTPUT")
    summary, rows, scored = aggregate(args.stage_dir)
    for path, value in zip(paths, (rows, scored, summary)):
        postflight.write_exclusive(path, value)
    print(json.dumps({"status": summary["status"], "observations": 60,
                      "native_execution_independently_confirmed": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
