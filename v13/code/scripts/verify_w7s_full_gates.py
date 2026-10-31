#!/usr/bin/env python3
"""Independent read-only W1-W6 replay from retained raw confidence pairs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from scripts import verify_w7s_world_jepa_report as base

CF_KEYS = ("jepa_covered", "jepa_held_out", "no_action_covered",
           "shuffled_action_covered", "ridge_obs_covered_info")
ATTR_KEYS = ("own_only_self", "world_only_world", "none_self", "balanced")
W1_W6 = (
    "W1_cf_retrieval_covered", "W2_controls_fail", "W3_no_collapse",
    "W4_confidence_tracks_error", "W5_attribution_jepa",
    "W6_no_action_attribution_worse",
)


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def replay_arm(rows):
    base.require(len(rows) == 3
                 and [r["seed"] for r in rows] == list(base.SEEDS),
                 "W1_W6_ROW_IDENTITY")
    for row in rows:
        cf = row["cf_retrieval"]
        base.require(all(finite(cf[k]) and 0 <= cf[k] <= 1
                         for k in CF_KEYS), "W1_W6_CF_NUMERIC")
        base.require(finite(row["collapse"]["effective_rank"])
                     and finite(row["collapse"]["min_std"]),
                     "W1_W6_COLLAPSE_NUMERIC")
        base.require(type(row["confidence"]["held_out_all_uncertain"])
                     is bool, "W1_W6_UNCERTAINTY_TYPE")
        for side in ("jepa", "no_action"):
            base.require(all(base.number(row["attribution"][side][key])
                             for key in ATTR_KEYS), "W1_W6_ATTR_NUMERIC")
        pairs = row.get("_conf_err")
        base.require(type(pairs) is list and len(pairs) > 0
                     and all(type(pair) is list and len(pair) == 2
                             and all(finite(v) for v in pair)
                             and 0 <= pair[0] <= 1 and pair[1] >= 0
                             for pair in pairs), "W1_W6_RAW_CONF_ERR")

    def pooled(key):
        return float(np.mean([row["cf_retrieval"][key] for row in rows]))

    def attribution(key):
        return float(np.mean([
            row["attribution"]["jepa"][key] for row in rows]))

    no_action = float(np.mean([
        row["attribution"]["no_action"]["balanced"] for row in rows]))
    ce = [pair for row in rows for pair in row["_conf_err"]]
    a = np.asarray([pair[0] for pair in ce], dtype=np.float64)
    b = np.asarray([pair[1] for pair in ce], dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        rank_a = np.argsort(np.argsort(a))
        rank_b = np.argsort(np.argsort(b))
        rho = float(np.corrcoef(rank_a, rank_b)[0, 1])
    rho_valid = math.isfinite(rho)
    gates = {
        W1_W6[0]: pooled("jepa_covered") >= .80
            and all(row["cf_retrieval"]["jepa_covered"] >= .70
                    for row in rows),
        W1_W6[1]: pooled("no_action_covered") <= .40
            and pooled("shuffled_action_covered") <= .40
            and pooled("jepa_covered") -
                max(pooled("no_action_covered"),
                    pooled("shuffled_action_covered")) >= .30,
        W1_W6[2]: all(row["collapse"]["effective_rank"] >= 4
                       and row["collapse"]["min_std"] >= .05
                       for row in rows),
        W1_W6[3]: rho_valid and rho <= -.30
            and all(row["confidence"]["held_out_all_uncertain"]
                    for row in rows),
        W1_W6[4]: attribution("own_only_self") >= .90
            and attribution("world_only_world") >= .90
            and attribution("none_self") >= .80,
        W1_W6[5]: no_action <= attribution("balanced") - .20,
    }
    summary = {
        "pooled_cf": {key: round(pooled(key), 4) for key in CF_KEYS},
        "spearman_conf_err_covered": round(rho, 4) if rho_valid else None,
        "attribution_jepa": {
            key: round(attribution(key), 4) for key in ATTR_KEYS},
        "attribution_no_action_balanced": round(no_action, 4),
    }
    if not rho_valid:
        summary["spearman_undefined_reason"] = (
            "CONSTANT_OR_NONFINITE_CONFIDENCE")
    return gates, summary


def verify(result_path, work_root):
    w7 = base.verify(result_path, work_root)
    if w7["status"] == "ORIGINAL_RED_OR_INCOMPLETE":
        return {"status": "ORIGINAL_RED_OR_INCOMPLETE",
                "original_status": w7["original_status"],
                "w1_w6_verified": False, "native_proof": False,
                "promotion": False}
    base.require(w7["status"] == "W7S_W7_SUPPORT_REPLAY_VERIFIED_SHADOW",
                 "W7_PRECONDITION")
    result = base.load(result_path)
    for arm in base.ARMS:
        rows = [base.load(Path(work_root) /
                          f"{arm}-{seed}-RESULT.json")
                for seed in base.SEEDS]
        gates, summary = replay_arm(rows)
        base.require(result[arm + "_gates"] == gates, "W1_W6_GATES")
        base.require(result[arm + "_summary"] == summary, "W1_W6_SUMMARY")
    return {"status": "W7S_W1_W7_FULL_RAW_REPLAY_VERIFIED_SHADOW",
            "original_status": result["status"], "w1_w6_verified": True,
            "w7_verified": True, "native_proof": False,
            "promotion": False, "seeds": list(base.SEEDS), "rows": 9}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(args.result, args.work_root)
    except Exception as exc:
        report = {"status": "W7S_W1_W6_REPLAY_RED",
                  "reason": type(exc).__name__ + ":" + str(exc)[:120],
                  "native_proof": False, "promotion": False}
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    raise SystemExit(0 if report["status"] ==
                     "W7S_W1_W7_FULL_RAW_REPLAY_VERIFIED_SHADOW" else 1)


if __name__ == "__main__":
    main()
