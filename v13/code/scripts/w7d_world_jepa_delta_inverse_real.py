#!/usr/bin/env python3
"""W7D disjoint two-arm delta-inverse World-JEPA real-file SHADOW."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import random

import numpy as np

from scripts import z12b_world_jepa as original
from scripts.run35_world_jepa_slot_alignment_real import evaluate, original_gates
from v13.world_jepa_action_balanced_fullslot_candidate import (
    BalancedFullSlotWorldJEPA,
)
from v13.world_jepa_delta_balanced_candidate import (
    DeltaBalancedFullSlotWorldJEPA, REVISION,
)

SEEDS = (701, 702, 703)
ARGS = {"train": 4000, "cf": 150, "attr": 900, "steps": 3000}
CLASSES = ("own_only_self", "world_only_world", "both_world", "none_self")
ARMS = (("balanced_slot", BalancedFullSlotWorldJEPA),
        ("delta_slot", DeltaBalancedFullSlotWorldJEPA))
FROZEN = {
    "world_jepa_blob": "99a686a131a1bdc89efe0d0cf9610ec54cbd853b",
    "original_collector_blob": "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4",
    "two_slot_blob": "67e14e0d03c50c4767b74d5b02a819a95c6cc262",
    "six_slot_blob": "51bc5260cde8db3bc6cf7924a7a089a5cdfe5fd0",
    "run35_evaluator_blob": "219bf7233cb91c746c89a60f9b7789dc3b5ca9ef",
    "balanced_slot_blob": "c65467f1f000c187f46542270dfc53ee569824a1",
    "delta_core_blob": "ed5d4b4f3324fc757c2a62944a82023c54b71fd0",
    "delta_balanced_blob": "8d0102d9ecc1e8aaa8bb073c0975480448e369ed",
}


FROZEN_PATHS = {
    "world_jepa_blob": "v13/world_jepa.py",
    "original_collector_blob": "scripts/z12b_world_jepa.py",
    "two_slot_blob": "v13/world_jepa_slot_candidate.py",
    "six_slot_blob": "v13/world_jepa_fullslot_candidate.py",
    "run35_evaluator_blob": "scripts/run35_world_jepa_slot_alignment_real.py",
    "balanced_slot_blob": "v13/world_jepa_action_balanced_fullslot_candidate.py",
    "delta_core_blob": "v13/world_jepa_delta_inverse_candidate.py",
    "delta_balanced_blob": "v13/world_jepa_delta_balanced_candidate.py",
}


def assert_frozen_sources(root=None):
    """Git-blob SHA-1 pin; do not silently train on changed code."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    for key, path in FROZEN_PATHS.items():
        raw = (root / path).read_bytes()
        blob = hashlib.sha1(
            ("blob " + str(len(raw)) + "\0").encode("ascii") + raw
        ).hexdigest()
        if blob != FROZEN[key]:
            raise ValueError("W7D_SOURCE_PIN_RED:" + key)


def attribution_support(rows):
    """Same class/support partition as original z12b_world_jepa.attr_eval."""
    counts = {"own_only": 0, "world_only": 0, "both": 0, "none": 0}
    for row in rows:
        if row["ambiguous"]:
            continue
        own = row["a"] != original.NOOP
        world = row["world_changed"]
        key = ("both" if world else "own_only") if own else (
            "world_only" if world else "none")
        counts[key] += 1
    return counts


def w7(rows):
    if [row["seed"] for row in rows] != list(SEEDS):
        raise ValueError("W7D_W7_SEED_IDENTITY")
    per_seed = []
    for row in rows:
        a, b = row["attribution"]["jepa"], row["attribution"]["no_action"]
        if a["n"] != b["n"] or any(type(a["n"][key]) is not int or a["n"][key] < 15
                                     for key in ("own_only", "world_only", "both", "none")):
            raise ValueError("W7D_W7_SUPPORT")
        if any(type(arm[key]) not in (int, float) or not math.isfinite(arm[key])
               or not 0 <= arm[key] <= 1 for arm in (a, b)
               for key in CLASSES + ("balanced",)):
            raise ValueError("W7D_W7_NUMERIC")
        per_seed.append({
            "seed": row["seed"],
            "both_world_gap": round(a["both_world"] - b["both_world"], 6),
            "none_self_gap": round(a["none_self"] - b["none_self"], 6),
            "four_class_macro_gap": round(
                sum(a[key] - b[key] for key in CLASSES) / 4, 6),
            "balanced_gap": round(a["balanced"] - b["balanced"], 6),
            "class_counts": dict(a["n"]),
        })
    mean = lambda key: round(float(np.mean([r[key] for r in per_seed])), 6)
    gates = {
        "W7a_both_world_action_gain": mean("both_world_gap") >= .20
            and all(r["both_world_gap"] >= .10 for r in per_seed),
        "W7b_none_self_action_gain": mean("none_self_gap") >= .05
            and all(r["none_self_gap"] >= 0 for r in per_seed),
        "W7c_four_class_macro_action_gain": mean("four_class_macro_gap") >= .08
            and all(r["four_class_macro_gap"] >= .04 for r in per_seed),
    }
    return gates, {"per_seed": per_seed, "mean_both_world_gap": mean("both_world_gap"),
                   "mean_none_self_gap": mean("none_self_gap"),
                   "mean_four_class_macro_gap": mean("four_class_macro_gap"),
                   "mean_balanced_gap": mean("balanced_gap")}


def delta_exploratory(result):
    """Prospective D1/D2/D3; never overrides original W1-W7."""
    baseline, delta = result["balanced_slot"], result["delta_slot"]
    if ([row["seed"] for row in baseline] != list(SEEDS)
            or [row["seed"] for row in delta] != list(SEEDS)):
        raise ValueError("W7D_EXPLORATORY_SEEDS")
    d1 = []
    for a, b in zip(delta, baseline):
        margin_a = (a["attribution"]["jepa"]["balanced"]
                    - a["attribution"]["no_action"]["balanced"])
        margin_b = (b["attribution"]["jepa"]["balanced"]
                    - b["attribution"]["no_action"]["balanced"])
        d1.append(round(margin_a-margin_b, 6))
    b_w7 = result["balanced_slot_w7_summary"]["per_seed"]
    d_w7 = result["delta_slot_w7_summary"]["per_seed"]
    d2 = [round(a["none_self_gap"]-b["none_self_gap"], 6)
          for a, b in zip(d_w7, b_w7)]
    rho_b = [r["spearman_conf_err_covered"]
             for r in result["balanced_slot_summary"]["per_seed"]] if False else None
    # Original summary is pooled, so use pooled W4 delta only; do not invent
    # per-seed rho from absent original per-seed raw rank receipts.
    rb = result["balanced_slot_summary"]["spearman_conf_err_covered"]
    rd = result["delta_slot_summary"]["spearman_conf_err_covered"]
    rho_delta = round(rd-rb, 6) if rb is not None and rd is not None else None
    return {
        "per_seed_w6_margin_delta": d1,
        "mean_w6_margin_delta": round(float(np.mean(d1)), 6),
        "D1_w6_margin_improvement": float(np.mean(d1)) >= .05
            and all(v >= -.02 for v in d1),
        "per_seed_w7b_none_gap_delta": d2,
        "mean_w7b_none_gap_delta": round(float(np.mean(d2)), 6),
        "D2_w7b_none_improvement": float(np.mean(d2)) >= .05
            and all(v >= -.02 for v in d2),
        "pooled_w4_rho_delta": rho_delta,
        "D3_pooled_w4_rho_improvement": rho_delta is not None
            and rho_delta <= -.05,
        "D3_per_seed_rho_unmeasured": True,
    }


def run(out, work_root, seeds=SEEDS, args=ARGS):
    out, work_root = Path(out), Path(work_root)
    if tuple(seeds) != SEEDS or args != ARGS:
        raise ValueError("W7D_COHORT_MUTATION")
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("W7D_LINUX_REALFILE_ONLY")
    assert_frozen_sources()
    if out.exists() or work_root.exists():
        raise FileExistsError("W7D_FRESH_PATHS_REQUIRED")
    work_root.mkdir(parents=True)
    result = {
        "schema": "v13.w7d.world_jepa_delta_inverse_exact_row.v1",
        "revision": REVISION,
        "evidence_kind": "LINUX_REALFILE_WORLD_JEPA_SHADOW_EXACT_ROWS",
        "registered": True, "seeds": list(SEEDS), "args": dict(ARGS),
        **FROZEN,
        "balanced_slot": [], "delta_slot": [],
        "status": "INCOMPLETE",
        "same_collected_rows": True, "same_core_parameter_count": True,
        "same_optimizer_steps": True, "same_training_example_count": True,
        "attribution_support_preflight": [],
        "global_96d_capacity_control_complete": False,
        "affected_slot_copies": 5,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "world_jepa_authority": "SHADOW",
        "redmi_measured": False, "whole_system_complete": False,
    }
    try:
        for seed in SEEDS:
            work = work_root / ("seed-" + str(seed))
            work.mkdir()
            held = set(random.Random(seed).sample(range(original.NOOP), 4))
            train = original.collect_train(work, seed, ARGS["train"], held)
            cf = original.collect_cf(work, seed, ARGS["cf"], held)
            attr = original.collect_attr(work, seed, ARGS["attr"], held)
            support = attribution_support(attr)
            result["attribution_support_preflight"].append(
                {"seed": seed, "counts": support})
            if any(n < 15 for n in support.values()):
                raise ValueError("W7D_W7_SUPPORT")

            nv = len(train) // 10
            fit, val = train[:-nv], train[-nv:]
            val_clean = [r for r in val if not r["world"]]
            X = np.array([r["x"] for r in fit])
            A = np.array([original.onehot(r["a"]) for r in fit])
            X2 = np.array([r["x2"] for r in fit])
            counts = [sum(r["a"] == i for r in fit)
                      for i in range(len(original.ACTIONS))]
            for name, cls in ARMS:
                row = evaluate(seed, cls, X, A, X2, fit, val_clean,
                               cf, attr, counts, ARGS["steps"])
                result[name].append(row)
                (work_root / f"{name}-{seed}-RESULT.json").write_text(
                    json.dumps(row, indent=2, allow_nan=False) + "\n")
        for name, _ in ARMS:
            result[name + "_gates"], result[name + "_summary"] = original_gates(result[name])
            result[name + "_w7"], result[name + "_w7_summary"] = w7(result[name])
        result["exploratory"] = delta_exploratory(result)
        result["status"] = (
            "SHADOW_CANDIDATE_PASS_NOT_PROMOTED"
            if all(result["delta_slot_gates"].values())
            and all(result["delta_slot_w7"].values())
            else "SHADOW_CANDIDATE_FAIL")
    except Exception as exc:
        result["status"] = "RED"
        result["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        for name, _ in ARMS:
            for row in result[name]:
                row.pop("_conf_err", None)
        out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] == "RED":
        raise RuntimeError("W7D_RED_OR_INCOMPLETE; original raw preserved")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--work-root", required=True, type=Path)
    args = p.parse_args()
    r = run(args.out, args.work_root)
    print(r["status"], r["delta_slot_gates"],
          r["delta_slot_w7"], r["exploratory"])


if __name__ == "__main__":
    main()
