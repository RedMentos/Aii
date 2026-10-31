#!/usr/bin/env python3
"""Read-only stdlib W7S raw report replay; never trains or promotes."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

SEEDS = (601, 602, 603)
ARGS = {"train": 4000, "cf": 150, "attr": 900, "steps": 3000}
ARMS = ("two_slot", "six_slot", "balanced_slot")
CLASSES = ("own_only", "world_only", "both", "none")
METRICS = ("own_only_self", "world_only_world", "both_world",
           "none_self", "balanced")
PINS = {
    "world_jepa_blob": "99a686a131a1bdc89efe0d0cf9610ec54cbd853b",
    "original_collector_blob": "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4",
    "two_slot_blob": "67e14e0d03c50c4767b74d5b02a819a95c6cc262",
    "six_slot_blob": "51bc5260cde8db3bc6cf7924a7a089a5cdfe5fd0",
    "run35_evaluator_blob": "219bf7233cb91c746c89a60f9b7789dc3b5ca9ef",
}
GATES = ("W7a_both_world_action_gain",
         "W7b_none_self_action_gain",
         "W7c_four_class_macro_action_gain")
MAX_JSON = 8 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError("W7S_REPLAY_" + reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def nonfinite(_):
    raise ValueError("W7S_REPLAY_NONFINITE_JSON")


def load(path):
    with Path(path).open("rb") as file:
        raw = file.read(MAX_JSON + 1)
    require(0 < len(raw) <= MAX_JSON, "INPUT_SIZE")
    return json.loads(raw.decode("utf-8", "strict"),
                      object_pairs_hook=unique, parse_constant=nonfinite)


def number(x):
    return type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1


def mean6(rows, key):
    return round(sum(row[key] for row in rows) / len(rows), 6)


def replay_w7(rows):
    require([r["seed"] for r in rows] == list(SEEDS), "SEED_ORDER")
    per_seed = []
    for row in rows:
        a, b = row["attribution"]["jepa"], row["attribution"]["no_action"]
        require(type(a["n"]) is dict and type(b["n"]) is dict
                and set(a["n"]) == set(CLASSES)
                and a["n"] == b["n"], "SUPPORT_IDENTITY")
        require(all(type(a["n"][key]) is int and a["n"][key] >= 15
                    for key in CLASSES), "SUPPORT_FLOOR")
        require(all(number(side[key]) for side in (a, b)
                    for key in METRICS), "NUMERIC_RANGE")
        per_seed.append({
            "seed": row["seed"],
            "both_world_gap": round(a["both_world"] - b["both_world"], 6),
            "none_self_gap": round(a["none_self"] - b["none_self"], 6),
            "four_class_macro_gap": round(
                sum(a[key] - b[key] for key in (
                    "own_only_self", "world_only_world", "both_world",
                    "none_self")) / 4, 6),
            "balanced_gap": round(a["balanced"] - b["balanced"], 6),
            "class_counts": dict(a["n"]),
        })
    gates = {
        GATES[0]: mean6(per_seed, "both_world_gap") >= .20
            and all(r["both_world_gap"] >= .10 for r in per_seed),
        GATES[1]: mean6(per_seed, "none_self_gap") >= .05
            and all(r["none_self_gap"] >= 0 for r in per_seed),
        GATES[2]: mean6(per_seed, "four_class_macro_gap") >= .08
            and all(r["four_class_macro_gap"] >= .04 for r in per_seed),
    }
    summary = {
        "per_seed": per_seed,
        "mean_both_world_gap": mean6(per_seed, "both_world_gap"),
        "mean_none_self_gap": mean6(per_seed, "none_self_gap"),
        "mean_four_class_macro_gap": mean6(per_seed, "four_class_macro_gap"),
        "mean_balanced_gap": mean6(per_seed, "balanced_gap"),
    }
    return gates, summary


def verify(result_path, work_root):
    r = load(result_path)
    require(type(r) is dict, "RESULT_TYPE")
    require(r.get("schema") == "v13.w7s.world_jepa_disjoint_support_exact_row.v1",
            "SCHEMA")
    require(r.get("seeds") == list(SEEDS) and r.get("args") == ARGS
            and r.get("registered") is True, "REGISTERED_COHORT")
    require(all(r.get(k) == v for k, v in PINS.items()), "FROZEN_PINS")
    require(r.get("evidence_kind") ==
            "LINUX_REALFILE_WORLD_JEPA_SHADOW_EXACT_ROWS", "EVIDENCE_KIND")
    require(r.get("age0") == "RECORD_ONLY"
            and r.get("step2") == "UTILITY_FAIL"
            and r.get("b3") == "NO_PROMOTION"
            and r.get("body_jepa") == "UNAVAILABLE"
            and r.get("jepa_weight") == 0
            and r.get("world_jepa_authority") == "SHADOW"
            and r.get("redmi_measured") is False
            and r.get("whole_system_complete") is False, "NEGATIVE_GATES")
    require(r.get("same_collected_rows") is True
            and r.get("same_core_parameter_count") is True
            and r.get("same_optimizer_steps") is True
            and r.get("same_training_example_count") is False
            and r.get("global_96d_capacity_control_complete") is False
            and r.get("affected_slot_copies") == 5, "ARM_COMPARABILITY")
    if r.get("status") in ("RED", "INCOMPLETE"):
        return {"status": "ORIGINAL_RED_OR_INCOMPLETE",
                "original_status": r["status"], "w7_verified": False,
                "native_proof": False, "promotion": False}
    require(r.get("status") in (
        "SHADOW_CANDIDATE_FAIL", "SHADOW_CANDIDATE_PASS_NOT_PROMOTED"),
        "STATUS")
    support = r.get("attribution_support_preflight")
    require(type(support) is list and len(support) == 3
            and [s["seed"] for s in support] == list(SEEDS), "PREFIT_SUPPORT")
    for s in support:
        require(type(s["counts"]) is dict
                and set(s["counts"]) == set(CLASSES)
                and all(type(v) is int and v >= 15
                        for v in s["counts"].values()), "PREFIT_FLOOR")
    root = Path(work_root)
    summaries = {}
    for arm in ARMS:
        rows = r.get(arm)
        require(type(rows) is list and len(rows) == 3, "ARM_ROWS")
        require([row["seed"] for row in rows] == list(SEEDS), "ARM_SEEDS")
        for i, row in enumerate(rows):
            require(row["capacity"]["world_concat_dim"] == 96
                    and row["capacity"]["local_latent_dim"] == 16,
                    "CAPACITY")
            for side in ("jepa", "no_action"):
                require(row["attribution"][side]["n"] ==
                        support[i]["counts"], "PREFIT_POSTFIT_SUPPORT")
            original = load(root / f"{arm}-{SEEDS[i]}-RESULT.json")
            require(type(original) is dict, "ROW_FILE_TYPE")
            original.pop("_conf_err", None)
            require(original == row, "ROW_FILE_MISMATCH")
        gates, summary = replay_w7(rows)
        require(r.get(arm + "_w7") == gates, "W7_GATES")
        require(r.get(arm + "_w7_summary") == summary, "W7_SUMMARY")
        recorded = r.get(arm + "_gates")
        require(type(recorded) is dict and len(recorded) == 6
                and all(type(v) is bool for v in recorded.values()),
                "W1_W6_STRUCTURE")
        summaries[arm] = summary
    b = summaries["balanced_slot"]["per_seed"]
    u = summaries["six_slot"]["per_seed"]
    d1 = [round(x["balanced_gap"] - y["balanced_gap"], 6)
          for x, y in zip(b, u)]
    d3 = [round(x["four_class_macro_gap"] - y["four_class_macro_gap"], 6)
          for x, y in zip(b, u)]
    avg = lambda vals: sum(vals) / len(vals)
    expected = {
        "per_seed_balanced_gap_delta": d1,
        "mean_balanced_gap_delta": round(avg(d1), 6),
        "H1_balanced_gap_improvement": avg(d1) >= .05
            and all(v >= -.01 for v in d1),
        "H2_covered_cf_and_controls": all(
            row["cf_retrieval"]["jepa_covered"] >= .80
            for row in r["balanced_slot"])
            and r["balanced_slot_gates"]["W2_controls_fail"],
        "per_seed_w7c_delta": d3,
        "mean_w7c_delta": round(avg(d3), 6),
        "H3_w7c_improvement": avg(d3) >= .03
            and all(v >= -.01 for v in d3),
    }
    require(r.get("exploratory") == expected, "EXPLORATORY_REPLAY")
    expected_status = (
        "SHADOW_CANDIDATE_PASS_NOT_PROMOTED"
        if all(r["balanced_slot_gates"].values())
        and all(r["balanced_slot_w7"].values())
        else "SHADOW_CANDIDATE_FAIL")
    require(r["status"] == expected_status, "VERDICT")
    return {"status": "W7S_W7_SUPPORT_REPLAY_VERIFIED_SHADOW",
            "original_status": r["status"], "w7_verified": True,
            "native_proof": False, "promotion": False,
            "seeds": list(SEEDS), "rows": 9}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.result, args.work_root)
    except Exception as exc:
        report = {"status": "W7S_INDEPENDENT_REPLAY_RED",
                  "reason": type(exc).__name__ + ":" + str(exc)[:120],
                  "native_proof": False, "promotion": False}
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    raise SystemExit(0 if report["status"] ==
                     "W7S_W7_SUPPORT_REPLAY_VERIFIED_SHADOW" else 1)


if __name__ == "__main__":
    main()
