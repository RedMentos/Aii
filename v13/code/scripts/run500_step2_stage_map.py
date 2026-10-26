#!/usr/bin/env python3
"""Run500: source-bound 75-stage plan and isolated runner for frozen Run491 STEP2.

Default source-only mode never invokes native weights. Native execution requires
an exact preregistered map, pinned installed bytes and a fresh stage directory.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path

import run491_step2_heldout10 as frozen
import run496_heldout10_native_pilot as pilot

GROUP_SIZE = 2
STAGES_PER_ARM_SEED = 5
EXPECTED_STAGES = 75
EXPECTED_ROWS = 1050
STAGE_ROWS = 14


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def registration():
    original = frozen.registration()
    require(original["fixture_sha256"] == frozen.FIXTURE_SHA256 and
            len(original["fixtures"]) == 10, "FROZEN_FIXTURE_DRIFT")
    require(tuple(original["arms"]) == ("A", "B", "C", "D", "E") and
            tuple(original["seeds"]) == (31, 32, 33) and
            tuple(original["variants"]) == frozen.VARIANTS, "FROZEN_COHORT_DRIFT")
    stages = []
    all_keys = []
    for arm in frozen.ARMS:
        for seed in frozen.SEEDS:
            for index in range(STAGES_PER_ARM_SEED):
                fixtures = original["fixtures"][index * GROUP_SIZE:(index + 1) * GROUP_SIZE]
                require(len(fixtures) == GROUP_SIZE, "STAGE_FIXTURE_COUNT")
                ids = [f["id"] for f in fixtures]
                keys = [[arm, seed, fid, variant] for fid in ids for variant in frozen.VARIANTS]
                require(len(keys) == STAGE_ROWS, "STAGE_ROW_COUNT")
                stages.append({
                    "id": f"{arm}_s{seed}_p{index:02d}",
                    "arm": arm, "seed": seed, "pair_index": index,
                    "fixture_ids": ids, "fixture_sha256": digest(fixtures),
                    "expected_rows": STAGE_ROWS,
                    "row_keys": keys, "row_keys_sha256": digest(keys),
                })
                all_keys.extend(keys)
    expected = {(arm, seed, f["id"], v) for arm in frozen.ARMS
                for seed in frozen.SEEDS for f in original["fixtures"]
                for v in frozen.VARIANTS}
    require(len(stages) == EXPECTED_STAGES and len(all_keys) == EXPECTED_ROWS and
            len({tuple(k) for k in all_keys}) == EXPECTED_ROWS and
            {tuple(k) for k in all_keys} == expected, "FULL_COHORT_COVERAGE")
    return {
        "schema": "V13_RUN500_FROZEN_1050_STAGE_MAP_V1",
        "status": "SOURCE_ONLY_NO_NATIVE",
        "original_fixture_sha256": frozen.FIXTURE_SHA256,
        "arms": list(frozen.ARMS), "seeds": list(frozen.SEEDS),
        "variants": list(frozen.VARIANTS),
        "model_sha256_expected_not_retrieved": dict(frozen.MODEL_SHA256),
        "runner_sha256_expected_not_retrieved": frozen.RUNNER_SHA256,
        "stages": stages, "stage_count": EXPECTED_STAGES,
        "expected_native_rows": EXPECTED_ROWS,
        "row_keys_sha256": digest(all_keys),
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }


def choose(reg, stage_id):
    require(type(stage_id) is str and
            stage_id in {s["id"] for s in reg["stages"]}, "UNKNOWN_STAGE_ID")
    return next(s for s in reg["stages"] if s["id"] == stage_id)


@contextmanager
def scoped_stage(stage, full=None):
    """Temporarily rebind only original harness globals, restoring on failure."""
    import step2_z2_timescale as z2
    import step2_z2b_seeds as z2b
    full = full or frozen.registration()
    require(full["fixture_sha256"] == frozen.FIXTURE_SHA256, "FROZEN_FIXTURE_DRIFT")
    selected = [f for f in full["fixtures"] if f["id"] in stage["fixture_ids"]]
    require([f["id"] for f in selected] == stage["fixture_ids"] and
            digest(selected) == stage["fixture_sha256"], "STAGE_FIXTURE_DRIFT")
    require(set(z2.ARMS) == set(frozen.ARMS), "ORIGINAL_ARM_DRIFT")
    saved_fixtures = z2.FIXTURES
    saved_arms = dict(z2b.ARMS)
    saved_seeds = z2b.SEEDS
    try:
        z2.FIXTURES = selected
        z2b.ARMS.clear()
        z2b.ARMS.update({arm: {"base": arm, "query": False} for arm in frozen.ARMS})
        z2b.SEEDS = frozen.SEEDS
        yield z2b
    finally:
        z2.FIXTURES = saved_fixtures
        z2b.ARMS.clear()
        z2b.ARMS.update(saved_arms)
        z2b.SEEDS = saved_seeds


def verify_stage(stage, tool, summary):
    """Structural proof only; no semantic or canonical STEP2 promotion."""
    require(type(tool) is dict and type(summary) is dict, "STAGE_REPORT_SCHEMA")
    require(tool.get("installed_artifacts_unchanged") is True, "STAGE_INSTALLED_DRIFT")
    rows = tool.get("rows")
    require(type(rows) is list and len(rows) == STAGE_ROWS, "STAGE_ROWS_INCOMPLETE")
    required = {(fid, v) for fid in stage["fixture_ids"] for v in frozen.VARIANTS}
    observed = {(r.get("fixture"), r.get("variant")) for r in rows if type(r) is dict}
    require(len(observed) == STAGE_ROWS and observed == required, "STAGE_COVERAGE_INVALID")
    for row in rows:
        score = row.get("score")
        require(row.get("status") == "RECORDED" and
                row.get("oracle_visible_to_native") is False and
                type(score) is dict and
                type(score.get("utility")) in (int, float) and
                math.isfinite(score["utility"]) and
                0 <= score["utility"] <= 1, "STAGE_ROW_INVALID")
    require(summary.get("run") == f"{stage['arm']}_s{stage['seed']}" and
            summary.get("arm") == stage["arm"] and
            summary.get("seed") == stage["seed"], "STAGE_SUMMARY_IDENTITY")
    require(summary.get("tool_status") != "STRUCTURAL_FAIL" and
            summary.get("step2_status") != "DIAGNOSTIC_INCOMPLETE", "STAGE_STRUCTURAL_FAIL")
    counts = summary.get("tool_summary")
    require(type(counts) is dict and set(counts) == set(frozen.VARIANTS) and
            all(type(v) is dict and v.get("wrong_committed") == 0
                for v in counts.values()), "STAGE_WRONG_COMMITTED")
    return {"status": "STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY",
            "stage_id": stage["id"], "rows_verified": STAGE_ROWS,
            "native_execution_performed": True,
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--stage-id")
    parser.add_argument("--installed-home", type=Path)
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(args.fixture_only != args.execute, "EXACTLY_ONE_MODE_REQUIRED")
    reg = registration()
    manifest = args.work / "RUN500_STAGE_MAP.json"
    if args.fixture_only:
        require(args.stage_id is None and args.installed_home is None,
                "FIXTURE_ONLY_MUST_NOT_USE_NATIVE_ARGUMENTS")
        write_new(manifest, reg)
        print(json.dumps({"status": reg["status"], "stages": EXPECTED_STAGES,
                          "rows": EXPECTED_ROWS, "native_executed": False}))
        return
    require(args.installed_home is not None and args.stage_id is not None,
            "EXECUTION_NEEDS_INSTALLED_HOME_AND_STAGE")
    require(manifest.is_file() and json.loads(manifest.read_text()) == reg,
            "STAGE_MAP_NOT_FROZEN")
    stage = choose(reg, args.stage_id)
    stage_dir = args.work / ("stage_" + stage["id"])
    require(not stage_dir.exists(), "REFUSE_STAGE_OVERWRITE_OR_PARTIAL_RERUN")
    preflight = pilot.verify_installed(args.installed_home)
    stage_dir.mkdir(parents=True, exist_ok=False)
    write_new(stage_dir / "RUN500_STAGE_PREREG.json", stage)
    write_new(stage_dir / "RUN500_INSTALLED_PREFLIGHT.json", preflight)
    with scoped_stage(stage) as z2b:
        summary = z2b.run_one(args.installed_home, stage_dir,
                              stage["arm"], stage["seed"])
    name = f"{stage['arm']}_s{stage['seed']}"
    tool_path = stage_dir / ("tool_" + name + ".json")
    summary_path = stage_dir / ("summary_" + name + ".json")
    tool = json.loads(tool_path.read_text())
    result = verify_stage(stage, tool, summary)
    result["tool_sha256"] = hashlib.sha256(tool_path.read_bytes()).hexdigest()
    result["summary_sha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    write_new(stage_dir / "RUN500_STAGE_RESULT.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
