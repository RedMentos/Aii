#!/usr/bin/env python3
"""Run505: source-only first future 42-row STEP2 batch; native only opt-in.

Run505 CI must use --plan and mocked tests only. A separate preregistered
native run and owner check are mandatory before anyone uses --execute.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import run500_step2_stage_map as stages
import run502_step2_batch as original_batch
import run504_remaining980_schedule as schedule

BATCH_ID = "FUTURE_001"
STAGE_IDS = ("A_s31_p00", "A_s31_p01", "A_s31_p02")
FIXTURE_PAIRS = (("Vesper", "Willow"), ("Xenia", "Yarrow"),
                 ("Crescent", "Asteria"))
EXPECTED_ROWS = 42
run_child = original_batch.run_child
append_progress = original_batch.append_progress
require = original_batch.require
digest = original_batch.digest


def load_exact(path, expected, why):
    path = Path(path)
    require(path.is_file(), why)
    require(json.loads(path.read_text(encoding="utf-8")) == expected, why)


def plan(work):
    work = Path(work)
    full = stages.registration()
    future = schedule.registration()
    load_exact(work / "RUN500_STAGE_MAP.json", full, "FROZEN_STAGE_MAP_REQUIRED")
    load_exact(work / "RUN504_SCHEDULE.json", future, "FROZEN_FUTURE_SCHEDULE_REQUIRED")
    require(future["full_stage_map_sha256"] == schedule.digest(full),
            "SCHEDULE_MAP_HASH_DRIFT")
    batch = next((b for b in future["batches"] if b["id"] == BATCH_ID), None)
    require(type(batch) is dict and
            batch["stage_ids"] == list(STAGE_IDS) and
            batch["fixture_pairs"] == [list(pair) for pair in FIXTURE_PAIRS] and
            batch["expected_rows"] == EXPECTED_ROWS and
            batch["native_executed"] is False, "FUTURE_001_DRIFT")
    selected = [stages.choose(full, sid) for sid in STAGE_IDS]
    require([s["fixture_ids"] for s in selected] ==
            [list(pair) for pair in FIXTURE_PAIRS], "FROZEN_STAGE_PAIR_DRIFT")
    keys = [tuple(k) for stage in selected for k in stage["row_keys"]]
    require(len(keys) == len(set(keys)) == EXPECTED_ROWS and
            not set(STAGE_IDS).intersection(future["reserved_stage_ids"]) and
            batch["row_keys_sha256"] ==
            schedule.digest([list(key) for key in keys]),
            "FUTURE_001_ROW_COVERAGE_DRIFT")
    return {
        "schema": "V13_RUN505_FUTURE001_42_ROW_BATCH_V1",
        "status": "SOURCE_ONLY_NO_NATIVE",
        "batch_id": BATCH_ID,
        "source_schedule_sha256": schedule.digest(future),
        "full_stage_map_sha256": schedule.digest(full),
        "stage_ids": list(STAGE_IDS),
        "fixture_pairs": [list(pair) for pair in FIXTURE_PAIRS],
        "arm": "A", "seed": 31, "expected_rows": EXPECTED_ROWS,
        "row_keys_sha256": batch["row_keys_sha256"],
        "model_sha256_expected_not_retrieved":
            full["model_sha256_expected_not_retrieved"],
        "runner_sha256_expected_not_retrieved":
            full["runner_sha256_expected_not_retrieved"],
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }


def execute(work, installed_home):
    work = Path(work)
    expected = plan(work)
    load_exact(work / "RUN505_BATCH_PLAN.json", expected,
               "RUN505_BATCH_PLAN_NOT_FROZEN")
    installed_home = Path(installed_home)
    require(installed_home.is_dir(), "INSTALLED_HOME_REQUIRED")
    logs = work / "run505-raw"
    progress = work / "RUN505_BATCH_PROGRESS.jsonl"
    result_path = work / "RUN505_BATCH_RESULT.json"
    preflight_path = work / "RUN505_INSTALLED_PREFLIGHT.json"
    require(not any(path.exists() or path.is_symlink() for path in
                    (logs, progress, result_path, preflight_path)),
            "REFUSE_BATCH_RERUN_OR_PARTIAL")
    for stage_id in STAGE_IDS:
        path = work / ("stage_" + stage_id)
        require(not path.exists() and not path.is_symlink(),
                "REFUSE_EXISTING_STAGE_DIR")
    # Real SHA-pinned model, runner and library bytes are mandatory here.
    import run496_heldout10_native_pilot as pilot
    installed = pilot.verify_installed(installed_home)
    logs.mkdir(parents=True, exist_ok=False)
    stages.write_new(preflight_path, installed)
    receipts = []
    for stage_id in STAGE_IDS:
        append_progress(progress, {"stage_id": stage_id, "state": "STARTED",
                                   "time_ns": time.time_ns()})
        log_path = logs / (stage_id + ".log")
        command = [sys.executable, str(Path(stages.__file__).resolve()),
                   "--work", str(work), "--installed-home", str(installed_home),
                   "--stage-id", stage_id, "--execute"]
        rc = run_child(command, log_path)
        receipt = work / ("stage_" + stage_id) / "RUN500_STAGE_RESULT.json"
        if rc == 0:
            if not receipt.is_file() or receipt.is_symlink():
                rc = 99
            else:
                try:
                    data = json.loads(receipt.read_text(encoding="utf-8"))
                    require(data["status"] == "STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY" and
                            data["stage_id"] == stage_id and
                            data["rows_verified"] == 14 and
                            data["native_execution_performed"] is True and
                            data["canonical_gate_pass"] is False and
                            data["step2_exit"] == "UTILITY_FAIL" and
                            data["b3_l1"] == "FAIL" and
                            data["body_jepa"] == "UNAVAILABLE" and
                            data["jepa_weight"] == 0 and
                            data["redmi_measured"] is False,
                            "INVALID_STAGE_RECEIPT")
                except (ValueError, KeyError, TypeError):
                    rc = 98
        sha = digest(receipt.read_bytes()) if receipt.is_file() and not receipt.is_symlink() else None
        append_progress(progress, {"stage_id": stage_id, "state": "FINISHED",
                                   "rc": rc, "receipt_sha256": sha,
                                   "time_ns": time.time_ns()})
        if rc != 0:
            raise RuntimeError(f"RUN505_STOPPED_AT_{stage_id}_RC_{rc}")
        receipts.append({"stage_id": stage_id, "receipt_sha256": sha,
                         "rows_verified": 14})
    result = {
        "status": "RUN505_42_ROWS_STRUCTURALLY_VERIFIED_ONLY",
        "batch_id": BATCH_ID,
        "stage_ids": list(STAGE_IDS), "stage_receipts": receipts,
        "rows_verified": EXPECTED_ROWS,
        "native_execution_performed": True,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
    }
    stages.write_new(result_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--installed-home", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(args.plan != args.execute, "EXACTLY_ONE_MODE_REQUIRED")
    if args.plan:
        require(args.installed_home is None, "PLAN_FORBIDS_INSTALLED_HOME")
        value = plan(args.work)
        stages.write_new(args.work / "RUN505_BATCH_PLAN.json", value)
        print(json.dumps({"status": value["status"],
                          "batch_id": BATCH_ID, "rows": EXPECTED_ROWS,
                          "native_executed": False}, sort_keys=True))
        return
    require(args.installed_home is not None, "EXECUTION_NEEDS_INSTALLED_HOME")
    print(json.dumps(execute(args.work, args.installed_home), sort_keys=True))


if __name__ == "__main__":
    main()
