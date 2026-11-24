#!/usr/bin/env python3
"""Run35 exact-row aligned vs scrambled-slot World-JEPA SHADOW experiment."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import random
import time

import numpy as np

from scripts import z12b_world_jepa as original
from v13.world_jepa_slot_candidate import SlotSharedWorldJEPA
from v13.world_jepa_slot_scramble_candidate import ScrambledSlotWorldJEPA, REVISION

SEEDS = (301, 302, 303)
ARGS = {"train": 4000, "cf": 150, "attr": 300, "steps": 3000}
CLASSES = ("own_only_self", "world_only_world", "both_world", "none_self")
SOURCE_BLOBS = {
    "original_world_jepa_blob": "99a686a131a1bdc89efe0d0cf9610ec54cbd853b",
    "original_collector_blob": "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4",
    "slot_candidate_blob": "67e14e0d03c50c4767b74d5b02a819a95c6cc262",
    "run28_runner_blob": "dbf3af3f8bc61a846eb542c7db3cc034e94f5bd7",
}


def w7(seeds):
    if [s["seed"] for s in seeds] != list(SEEDS):
        raise ValueError("RUN35_SEED_IDENTITY_RED")
    rows = []
    for s in seeds:
        a, b = s["attribution"]["jepa"], s["attribution"]["no_action"]
        if (a["n"] != b["n"] or
                any(type(a["n"][k]) is not int or a["n"][k] < 15
                    for k in ("own_only", "world_only", "both", "none"))):
            raise ValueError("RUN35_W7_CLASS_SUPPORT_RED")
        if any(type(arm[k]) not in (int, float) or
               not math.isfinite(arm[k]) or not 0 <= arm[k] <= 1
               for arm in (a, b) for k in CLASSES):
            raise ValueError("RUN35_W7_NONFINITE_RATE_RED")
        rows.append({
            "seed": s["seed"],
            "both_world_gap": round(a["both_world"] - b["both_world"], 6),
            "none_self_gap": round(a["none_self"] - b["none_self"], 6),
            "four_class_macro_gap": round(
                (sum(a[k] for k in CLASSES) - sum(b[k] for k in CLASSES)) / 4, 6),
            "class_counts": a["n"],
        })
    mean = lambda k: round(float(np.mean([r[k] for r in rows])), 6)
    g = {
        "W7a_both_world_action_gain": mean("both_world_gap") >= .20
            and all(r["both_world_gap"] >= .10 for r in rows),
        "W7b_none_self_action_gain": mean("none_self_gap") >= .05
            and all(r["none_self_gap"] >= 0 for r in rows),
        "W7c_four_class_macro_action_gain": mean("four_class_macro_gap") >= .08
            and all(r["four_class_macro_gap"] >= .04 for r in rows),
    }
    return g, {
        "per_seed": rows,
        "mean_both_world_gap": mean("both_world_gap"),
        "mean_none_self_gap": mean("none_self_gap"),
        "mean_four_class_macro_gap": mean("four_class_macro_gap"),
    }


def original_gates(seeds):
    gates, summary = original.criteria(seeds)
    rho = float(summary["spearman_conf_err_covered"])
    if not math.isfinite(rho):
        gates["W4_confidence_tracks_error"] = False
        summary["spearman_conf_err_covered"] = None
        summary["spearman_undefined_reason"] = "CONSTANT_OR_NONFINITE_CONFIDENCE"
    return {k: bool(v) for k, v in gates.items()}, summary


def evaluate(seed, cls, X, A, X2, fit, val_clean, cf, attr, counts, steps):
    t = time.monotonic()
    model = cls(seed=seed).fit(X, A, X2, steps=steps)
    zero = cls(seed=seed, ensemble=1).fit(X, np.zeros_like(A), X2, steps=steps)
    shuffled = cls(seed=seed, ensemble=1).fit(
        X, A[np.random.default_rng(seed).permutation(len(A))], X2, steps=steps)
    fit_seconds = round(time.monotonic() - t, 1)
    rec = original.cf_eval(model, cf, counts, "own")
    rec0 = original.cf_eval(zero, cf, counts, "zero")
    recs = original.cf_eval(shuffled, cf, counts, "own")
    covered = [r for r in rec if not r["held"]]
    acc = lambda rs: round(float(np.mean([r["ok"] for r in rs])), 4)
    th = original.theta_of(model, val_clean, False)
    th0 = original.theta_of(zero, val_clean, True)
    return {
        "seed": seed,
        "n_train": len(fit), "n_val_clean": len(val_clean),
        "seconds_fit_3_models": fit_seconds,
        "history": model.history[-3:],
        "capacity": {"local_latent_dim": 16, "world_concat_dim": 96,
                     "same_architecture_and_trainable_parameter_count": True,
                     "global_96d_capacity_control_complete": False},
        "cf_retrieval": {
            "jepa_covered": acc(covered),
            "jepa_held_out": acc([r for r in rec if r["held"]]),
            "no_action_covered": acc([r for r in rec0 if not r["held"]]),
            "shuffled_action_covered": acc([r for r in recs if not r["held"]]),
            "ridge_obs_covered_info": original.ridge_cf(fit, cf),
            "n_covered": len(covered), "n_held_out": len(rec) - len(covered),
        },
        "errors": {
            "covered_mean": round(float(np.mean([r["err"] for r in covered])), 4),
            "held_out_mean": round(float(np.mean([r["err"] for r in rec if r["held"]])), 4),
        },
        "confidence": {
            "covered_mean": round(float(np.mean([r["conf"] for r in covered])), 4),
            "held_out_all_uncertain": all(
                r["label"] == "SIMULATION_UNCERTAIN" for r in rec if r["held"]),
            "covered_uncertain_frac": round(float(np.mean([
                r["label"] == "SIMULATION_UNCERTAIN" for r in covered])), 4),
        },
        "_conf_err": [[r["conf"], r["err"]] for r in covered],
        "collapse": model.collapse_stats(X2),
        "attribution": {
            "theta": {k: round(v, 4) for k, v in th.items()},
            "jepa": original.attr_eval(model, attr, th, False),
            "no_action": original.attr_eval(zero, attr, th0, True),
        },
    }


def run(out, work_root, seeds=SEEDS, args=ARGS):
    out, work_root = Path(out), Path(work_root)
    if tuple(seeds) != SEEDS or args != ARGS:
        raise ValueError("RUN35_REGISTERED_COHORT_MUTATION_RED")
    if (platform.system() != "Linux" or
            platform.machine().lower() not in ("x86_64", "amd64")):
        raise ValueError("RUN35_LINUX_REALFILE_ONLY")
    if out.exists() or work_root.exists():
        raise FileExistsError("RUN35_FRESH_PATHS_REQUIRED")
    work_root.mkdir(parents=True)
    result = {
        "schema": "v13.run35.world_jepa_slot_alignment_exact_row.v1",
        "revision": REVISION, "evidence_kind": "LINUX_REALFILE_SHADOW_EXACT_ROWS",
        "registered": True, "seeds": list(SEEDS), "args": dict(ARGS),
        **SOURCE_BLOBS,
        "aligned": [], "scrambled": [], "aligned_gates": None,
        "scrambled_gates": None, "aligned_w7": None, "scrambled_w7": None,
        "locality": None, "status": "INCOMPLETE",
        "exact_same_collected_rows": True, "parameter_count_matched": True,
        "global_96d_capacity_control_complete": False,
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
            nv = len(train) // 10
            fit, val = train[:-nv], train[-nv:]
            val_clean = [r for r in val if not r["world"]]
            X = np.array([r["x"] for r in fit])
            A = np.array([original.onehot(r["a"]) for r in fit])
            X2 = np.array([r["x2"] for r in fit])
            counts = [sum(r["a"] == i for r in fit)
                      for i in range(len(original.ACTIONS))]
            for name, cls in (("aligned", SlotSharedWorldJEPA),
                              ("scrambled", ScrambledSlotWorldJEPA)):
                row = evaluate(seed, cls, X, A, X2, fit, val_clean,
                               cf, attr, counts, ARGS["steps"])
                result[name].append(row)
                (work_root / f"{name}-{seed}-RESULT.json").write_text(
                    json.dumps(row, indent=2, allow_nan=False) + "\n")
        result["aligned_gates"], result["aligned_summary"] = original_gates(result["aligned"])
        result["scrambled_gates"], result["scrambled_summary"] = original_gates(result["scrambled"])
        result["aligned_w7"], result["aligned_w7_summary"] = w7(result["aligned"])
        result["scrambled_w7"], result["scrambled_w7_summary"] = w7(result["scrambled"])
        cf_diffs = [a["cf_retrieval"]["jepa_covered"] -
                    b["cf_retrieval"]["jepa_covered"]
                    for a, b in zip(result["aligned"], result["scrambled"])]
        w7a_diff = (result["aligned_w7_summary"]["mean_both_world_gap"] -
                    result["scrambled_w7_summary"]["mean_both_world_gap"])
        result["locality"] = {
            "per_seed_covered_cf_delta": [round(v, 6) for v in cf_diffs],
            "mean_covered_cf_delta": round(float(np.mean(cf_diffs)), 6),
            "mean_both_world_action_gain_delta": round(w7a_diff, 6),
            "L1_aligned_cf_advantage": float(np.mean(cf_diffs)) >= .10
                and all(v >= .05 for v in cf_diffs),
            "L2_aligned_both_world_gain_advantage": w7a_diff >= .10,
        }
        result["status"] = (
            "SHADOW_CANDIDATE_PASS_NOT_PROMOTED"
            if all(result["aligned_gates"].values()) and
               all(result["aligned_w7"].values())
            else "SHADOW_CANDIDATE_FAIL")
    except Exception as exc:
        result["status"] = "RED"
        result["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        for name in ("aligned", "scrambled"):
            for row in result[name]:
                row.pop("_conf_err", None)
        out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] == "RED":
        raise RuntimeError("RUN35_RED_OR_INCOMPLETE; all original raw retained")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--work-root", type=Path, required=True)
    args = p.parse_args(argv)
    r = run(args.out, args.work_root)
    print(r["status"], r["locality"], r["aligned_gates"], r["aligned_w7"])


if __name__ == "__main__":
    main()
