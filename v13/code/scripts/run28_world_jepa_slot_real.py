#!/usr/bin/env python3
"""Run28 registered real-file slot-shared World-JEPA SHADOW experiment.

Original Z12b collection, counterfactuals, attribution and criteria are reused
without changes. No production runtime integration, phone claim or age promotion.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import shutil
import time

import numpy as np

from scripts import z12b_world_jepa as original
from v13.world_jepa_slot_candidate import SlotSharedWorldJEPA, REVISION

REGISTERED = {"seeds": [101, 102, 103], "train": 4000,
              "cf": 150, "attr": 300, "steps": 3000}
ORIGINAL_MODEL_BLOB = "99a686a131a1bdc89efe0d0cf9610ec54cbd853b"
ORIGINAL_EXPERIMENT_BLOB = "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4"


def run_seed(seed, args, work_root):
    work = work_root / ("seed-" + str(seed))
    work.mkdir()
    rng = random.Random(seed)
    held = set(rng.sample(range(original.NOOP), 4))
    t = time.monotonic()
    train = original.collect_train(work, seed, args.train, held)
    cf = original.collect_cf(work, seed, args.cf, held)
    attr = original.collect_attr(work, seed, args.attr, held)
    collect_s = time.monotonic() - t
    nv = len(train) // 10
    fit, val = train[:-nv], train[-nv:]
    val_clean = [r for r in val if not r["world"]]
    X = np.array([r["x"] for r in fit])
    A = np.array([original.onehot(r["a"]) for r in fit])
    X2 = np.array([r["x2"] for r in fit])
    counts = [sum(r["a"] == i for r in fit) for i in range(len(original.ACTIONS))]
    perm = np.random.default_rng(seed).permutation(len(A))
    t = time.monotonic()
    m = SlotSharedWorldJEPA(seed=seed).fit(X, A, X2, steps=args.steps)
    m0 = SlotSharedWorldJEPA(seed=seed, ensemble=1).fit(
        X, np.zeros_like(A), X2, steps=args.steps)
    ms = SlotSharedWorldJEPA(seed=seed, ensemble=1).fit(
        X, A[perm], X2, steps=args.steps)
    fit_s = time.monotonic() - t
    rec = original.cf_eval(m, cf, counts, "own")
    rec0 = original.cf_eval(m0, cf, counts, "zero")
    recs = original.cf_eval(ms, cf, counts, "own")
    cov = lambda rs: [r for r in rs if not r["held"]]
    acc = lambda rs: round(float(np.mean([r["ok"] for r in rs])), 4)
    covered = cov(rec)
    th, th0 = original.theta_of(m, val_clean, False), original.theta_of(m0, val_clean, True)
    return {
        "seed": seed, "held_out_actions": [list(original.ACTIONS[i]) for i in sorted(held)],
        "n_train": len(fit), "n_val_clean": len(val_clean),
        "world_touched_train_frac": round(float(np.mean([r["world"] for r in train])), 4),
        "seconds_collect": round(collect_s, 1),
        "seconds_fit_3_models": round(fit_s, 1),
        "history": m.history[-3:],
        "capacity": {"local_latent_dim": 16, "world_concat_dim": 96,
                     "original_z12b_world_latent_dim": 16,
                     "matched_capacity_control_complete": False},
        "cf_retrieval": {
            "jepa_covered": acc(covered),
            "jepa_held_out": acc([r for r in rec if r["held"]]),
            "no_action_covered": acc(cov(rec0)),
            "shuffled_action_covered": acc(cov(recs)),
            "ridge_obs_covered_info": original.ridge_cf(fit, cf),
            "n_covered": len(covered),
            "n_held_out": len(rec) - len(covered),
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
        "collapse": m.collapse_stats(X2),
        "attribution": {
            "theta": {k: round(v, 4) for k, v in th.items()},
            "jepa": original.attr_eval(m, attr, th, False),
            "no_action": original.attr_eval(m0, attr, th0, True),
        },
    }


def run(args):
    seeds = [int(s) for s in args.seeds.split(",")]
    if (args.registered and
            (seeds != REGISTERED["seeds"] or
             any(getattr(args, key) != REGISTERED[key]
                 for key in ("train", "cf", "attr", "steps")))):
        raise ValueError("RUN28_REGISTERED_COHORT_MUTATION_RED")
    if (not seeds or len(set(seeds)) != len(seeds)
            or any(seed < 0 or seed > 2**31-1 for seed in seeds)
            or args.train < 100 or args.cf < 1 or args.attr < 1 or args.steps < 1):
        raise ValueError("RUN28_INVALID_EXPERIMENT")
    if args.work_root.exists() or args.out.exists():
        raise FileExistsError("RUN28_FRESH_WORK_AND_RESULT_REQUIRED")
    args.work_root.mkdir(parents=True)
    result = {
        "schema": "v13.run28.slot_shared_world_jepa.v1",
        "revision": REVISION,
        "evidence_kind": "REAL_FILE_ACTIONS_CLOUD_SHADOW" if args.registered else "SMOKE_ONLY",
        "original_world_jepa_blob": ORIGINAL_MODEL_BLOB,
        "original_z12b_experiment_blob": ORIGINAL_EXPERIMENT_BLOB,
        "registered": args.registered,
        "args": {"seeds": seeds, "train": args.train, "cf": args.cf,
                 "attr": args.attr, "steps": args.steps},
        "seeds": [], "summary": None, "criteria": None,
        "status": "INCOMPLETE",
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa_authority": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "capacity_confounded": True,
    }
    try:
        for seed in seeds:
            s = run_seed(seed, args, args.work_root)
            result["seeds"].append(s)
            # Durable per-seed checkpoint before another long seed.
            (args.work_root / ("seed-" + str(seed) + "-RESULT.json")).write_text(
                json.dumps(s, indent=2, allow_nan=False) + "\n")
        if args.registered:
            criteria, summary = original.criteria(result["seeds"])
            # A nonfinite statistic is a measured failure, not a success or
            # JSON NaN; preserve seed raw and mark the overall verdict RED.
            if not all(math.isfinite(float(v)) for v in (
                    summary["spearman_conf_err_covered"],
                    *summary["pooled_cf"].values())):
                raise ValueError("RUN28_NONFINITE_EVALUATION_RED")
            result["criteria"] = criteria
            result["summary"] = summary
            result["status"] = ("SHADOW_CANDIDATE_PASS_NOT_PROMOTED"
                                if all(criteria.values()) else "SHADOW_CANDIDATE_FAIL")
        else:
            result["status"] = "SMOKE_ONLY_NOT_EVIDENCE"
    except Exception as exc:
        result["status"] = "RED"
        result["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        for s in result["seeds"]:
            s.pop("_conf_err", None)
        args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] == "RED":
        raise RuntimeError("RUN28_RED_OR_INCOMPLETE; original work and per-seed raw retained")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--work-root", type=Path, required=True)
    p.add_argument("--registered", action="store_true")
    p.add_argument("--seeds", default="101,102,103")
    p.add_argument("--train", type=int, default=4000)
    p.add_argument("--cf", type=int, default=150)
    p.add_argument("--attr", type=int, default=300)
    p.add_argument("--steps", type=int, default=3000)
    args = p.parse_args(argv)
    r = run(args)
    print(r["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
