#!/usr/bin/env python3
"""Run502: three frozen Run500 stages, serialized, no implicit retry.

Plan mode is source-only. Execute mode requires pinned installed native bytes
and creates fresh stage directories, raw logs and append-only progress.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import run500_step2_stage_map as stages

BATCH_IDS = ("C_s31_p02", "C_s31_p03", "C_s31_p04")
BATCH_FIXTURES = (("Crescent", "Asteria"), ("Boreal", "Cascade"),
                  ("Drift", "Eon"))
EXPECTED_ROWS = 42


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def plan(work):
    work = Path(work)
    manifest = work / "RUN500_STAGE_MAP.json"
    require(manifest.is_file(), "RUN500_STAGE_MAP_REQUIRED")
    raw = manifest.read_bytes()
    reg = json.loads(raw)
    require(reg == stages.registration(), "RUN500_STAGE_MAP_DRIFT")
    selected = [stages.choose(reg, stage_id) for stage_id in BATCH_IDS]
    require([tuple(s["fixture_ids"]) for s in selected] == list(BATCH_FIXTURES),
            "BATCH_FIXTURE_DRIFT")
    keys = [tuple(key) for stage in selected for key in stage["row_keys"]]
    require(len(keys) == len(set(keys)) == EXPECTED_ROWS,
            "BATCH_COVERAGE_OR_DUPLICATE")
    require(not any(key[2] in ("Vesper", "Willow", "Xenia", "Yarrow")
                    for key in keys), "BATCH_OVERLAPS_PRIOR_STAGES")
    return {
        "schema": "V13_RUN502_C_S31_THREE_STAGE_BATCH_V1",
        "status": "SOURCE_ONLY_NO_NATIVE",
        "source_map_sha256": digest(raw),
        "stage_ids": list(BATCH_IDS),
        "fixture_pairs": [list(pair) for pair in BATCH_FIXTURES],
        "arm": "C", "seed": 31,
        "expected_rows": EXPECTED_ROWS,
        "row_keys_sha256": digest(canonical([list(key) for key in keys])),
        "model_sha256_expected_not_retrieved": reg["model_sha256_expected_not_retrieved"],
        "runner_sha256_expected_not_retrieved": reg["runner_sha256_expected_not_retrieved"],
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }


def append_progress(path, value):
    data = canonical(value) + b"\n"
    with open(path, "ab", buffering=0) as stream:
        stream.write(data)
        os.fsync(stream.fileno())


def run_child(command, log_path, timeout_s=3600):
    """One process group at a time; terminate descendants on timeout."""
    with open(log_path, "xb") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            return proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            return 124


def execute(work, installed_home):
    work = Path(work)
    frozen = plan(work)
    path = work / "RUN502_BATCH_PLAN.json"
    require(path.is_file() and json.loads(path.read_text()) == frozen,
            "BATCH_PLAN_NOT_FROZEN")
    require(Path(installed_home).is_dir(), "INSTALLED_HOME_REQUIRED")
    logs = work / "run502-raw"
    progress = work / "RUN502_BATCH_PROGRESS.jsonl"
    result_path = work / "RUN502_BATCH_RESULT.json"
    require(not logs.exists() and not progress.exists() and
            not result_path.exists(), "REFUSE_BATCH_RERUN_OR_PARTIAL")
    for stage_id in BATCH_IDS:
        require(not (work / ("stage_" + stage_id)).exists(),
                "REFUSE_EXISTING_STAGE_DIR")
    # Reuse Run498 strict symlink-aware actual model/runner/library preflight.
    import run496_heldout10_native_pilot as pilot
    preflight = pilot.verify_installed(installed_home)
    logs.mkdir(parents=True, exist_ok=False)
    stages.write_new(work / "RUN502_INSTALLED_PREFLIGHT.json", preflight)
    receipts = []
    for stage_id in BATCH_IDS:
        append_progress(progress, {"stage_id": stage_id, "state": "STARTED",
                                   "time_ns": time.time_ns()})
        log = logs / (stage_id + ".log")
        command = [sys.executable, str(Path(stages.__file__).resolve()),
                   "--work", str(work), "--installed-home", str(installed_home),
                   "--stage-id", stage_id, "--execute"]
        rc = run_child(command, log)
        receipt = work / ("stage_" + stage_id) / "RUN500_STAGE_RESULT.json"
        if rc == 0 and not receipt.is_file():
            rc = 99
        sha = digest(receipt.read_bytes()) if receipt.is_file() else None
        append_progress(progress, {"stage_id": stage_id, "state": "FINISHED",
                                   "rc": rc, "receipt_sha256": sha,
                                   "time_ns": time.time_ns()})
        if rc != 0:
            raise RuntimeError(f"BATCH_STOPPED_AT_{stage_id}_RC_{rc}")
        data = json.loads(receipt.read_text())
        require(data["status"] == "STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY" and
                data["stage_id"] == stage_id and data["rows_verified"] == 14 and
                data["canonical_gate_pass"] is False,
                "STAGE_RECEIPT_INVALID")
        receipts.append({"stage_id": stage_id, "receipt_sha256": sha,
                         "rows_verified": 14})
    result = {
        "status": "RUN502_THREE_STAGES_42_ROWS_STRUCTURALLY_VERIFIED_ONLY",
        "stage_ids": list(BATCH_IDS), "stage_receipts": receipts,
        "rows_verified": EXPECTED_ROWS,
        "native_execution_performed": True,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
    }
    stages.write_new(result_path, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--plan", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    require(args.plan != args.execute, "EXACTLY_ONE_MODE_REQUIRED")
    if args.plan:
        require(args.installed_home is None, "PLAN_MUST_NOT_USE_INSTALLED_HOME")
        result = plan(args.work)
        stages.write_new(args.work / "RUN502_BATCH_PLAN.json", result)
        print(json.dumps({"status": result["status"],
                          "stage_ids": result["stage_ids"],
                          "rows": EXPECTED_ROWS, "native_executed": False}))
        return
    require(args.installed_home is not None, "EXECUTION_NEEDS_INSTALLED_HOME")
    print(json.dumps(execute(args.work, args.installed_home), sort_keys=True))


if __name__ == "__main__":
    main()
