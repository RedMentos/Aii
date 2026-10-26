#!/usr/bin/env python3
"""Run504: source-only partition of the unexecuted frozen Run491 STEP2 stages.

No model, native runner, runtime, or learning rights are touched. The five
C_s31 stages are reserved (Run503 p02-p04 still require native postflight).
"""
import argparse
import hashlib
import json
from pathlib import Path

import run491_step2_heldout10 as frozen
import run500_step2_stage_map as stage_map

RESERVED_IDS = tuple(f"C_s31_p{i:02d}" for i in range(5))
BATCH_SIZE = 3
EXPECTED_REMAINING_STAGES = 70
EXPECTED_REMAINING_ROWS = 980
EXPECTED_BATCHES = 24
ORIGINAL_FIXTURE_SHA256 = "c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63"


def require(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def registration():
    full = stage_map.registration()
    source = frozen.registration()
    require(full["original_fixture_sha256"] == ORIGINAL_FIXTURE_SHA256 and
            source["fixture_sha256"] == ORIGINAL_FIXTURE_SHA256,
            "ORIGINAL_FIXTURE_DRIFT")
    require(full["stage_count"] == 75 and full["expected_native_rows"] == 1050 and
            full["arms"] == list(frozen.ARMS) and
            full["seeds"] == list(frozen.SEEDS) and
            full["variants"] == list(frozen.VARIANTS),
            "FROZEN_FULL_MAP_DRIFT")
    require(full["model_sha256_expected_not_retrieved"] == frozen.MODEL_SHA256 and
            full["runner_sha256_expected_not_retrieved"] == frozen.RUNNER_SHA256,
            "FROZEN_MODEL_RUNNER_DRIFT")
    stages = full["stages"]
    expected_ids = [f"{arm}_s{seed}_p{index:02d}"
                    for arm in frozen.ARMS for seed in frozen.SEEDS
                    for index in range(5)]
    require([s["id"] for s in stages] == expected_ids,
            "FROZEN_STAGE_ORDER_DRIFT")
    original_fixtures = [f["id"] for f in source["fixtures"]]
    expected_keys = {(arm, seed, fid, variant)
                     for arm in frozen.ARMS for seed in frozen.SEEDS
                     for fid in original_fixtures for variant in frozen.VARIANTS}
    all_keys = []
    for stage in stages:
        pair_index = stage["pair_index"]
        expected_pair = original_fixtures[pair_index * 2:pair_index * 2 + 2]
        expected_stage_keys = [[stage["arm"], stage["seed"], fid, variant]
                               for fid in expected_pair for variant in frozen.VARIANTS]
        require(type(pair_index) is int and 0 <= pair_index < 5 and
                stage["fixture_ids"] == expected_pair and
                stage["expected_rows"] == 14 and
                stage["row_keys"] == expected_stage_keys and
                stage["row_keys_sha256"] == digest(expected_stage_keys),
                "FROZEN_STAGE_CONTENT_DRIFT")
        all_keys.extend(tuple(key) for key in stage["row_keys"])
    require(len(all_keys) == len(set(all_keys)) == 1050 and
            set(all_keys) == expected_keys and
            full["row_keys_sha256"] == digest([list(key) for key in all_keys]),
            "FROZEN_FULL_ROW_COVERAGE_DRIFT")

    reserved = [s for s in stages if s["id"] in RESERVED_IDS]
    future = [s for s in stages if s["id"] not in RESERVED_IDS]
    require([s["id"] for s in reserved] == list(RESERVED_IDS) and
            len(future) == EXPECTED_REMAINING_STAGES, "RESERVED_STAGE_DRIFT")
    reserved_keys = {tuple(k) for s in reserved for k in s["row_keys"]}
    future_keys = [tuple(k) for s in future for k in s["row_keys"]]
    require(len(reserved_keys) == 70 and
            len(future_keys) == len(set(future_keys)) == EXPECTED_REMAINING_ROWS and
            not reserved_keys.intersection(future_keys) and
            reserved_keys.union(future_keys) == expected_keys,
            "FUTURE_COVERAGE_OR_OVERLAP")
    batches = []
    for offset in range(0, len(future), BATCH_SIZE):
        selected = future[offset:offset + BATCH_SIZE]
        keys = [k for stage in selected for k in stage["row_keys"]]
        batches.append({
            "id": f"FUTURE_{len(batches)+1:03d}",
            "stage_ids": [s["id"] for s in selected],
            "fixture_pairs": [s["fixture_ids"] for s in selected],
            "expected_rows": len(keys),
            "row_keys_sha256": digest(keys),
            "native_executed": False,
        })
    require(len(batches) == EXPECTED_BATCHES and
            [b["expected_rows"] for b in batches] == [42] * 23 + [14] and
            [sid for b in batches for sid in b["stage_ids"]] ==
            [s["id"] for s in future], "FUTURE_BATCH_PARTITION_DRIFT")
    return {
        "schema": "V13_RUN504_FROZEN_REMAINING980_SCHEDULE_V1",
        "status": "SOURCE_ONLY_NO_NATIVE",
        "original_fixture_sha256": ORIGINAL_FIXTURE_SHA256,
        "full_stage_map_sha256": digest(full),
        "full_stage_count": 75, "full_row_count": 1050,
        "reserved_stage_ids": list(RESERVED_IDS),
        "reserved_planned_rows": 70,
        "reserved_p02_p04_native_verification_pending": True,
        "remaining_stage_count": EXPECTED_REMAINING_STAGES,
        "remaining_planned_rows": EXPECTED_REMAINING_ROWS,
        "remaining_row_keys_sha256": digest([list(k) for k in future_keys]),
        "batches": batches, "batch_count": len(batches),
        "model_sha256_expected_not_retrieved": dict(frozen.MODEL_SHA256),
        "runner_sha256_expected_not_retrieved": frozen.RUNNER_SHA256,
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
        "claim_limit": "Schedule only; 980 rows not executed; Run503 p02-p04 still pending."
    }


def write_exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    value = registration()
    write_exclusive(args.output, value)
    print(json.dumps({"status": value["status"],
                      "batches": value["batch_count"],
                      "remaining_stages": value["remaining_stage_count"],
                      "remaining_planned_rows": value["remaining_planned_rows"],
                      "native_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
