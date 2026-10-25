#!/usr/bin/env python3
"""Run346 frozen DS2 paired lab benchmark. Not native, not an Age/AG5 grant."""
import argparse
import json
import math
from pathlib import Path
from v13 import sandbox as S

SEEDS = tuple(range(401, 421))
POLICIES = ("lp", "lp_goal", "lp_goal_novelty", "efe")
STEPS = 1200
NEW_KIND_AT = 500
CRITERIA = {
    "hunger_improves_over_lp_by_0p03": ("mean_hunger", "lp", -0.03),
    "noise_not_worse_than_lp_by_0p03": ("noise_share", "lp", 0.03),
    "learnable_kl_not_worse_than_lp_by_0p05": ("final_kl_learnable", "lp", 0.05),
    "new_kind_kl_improves_over_lp_goal_by_0p05": ("new_kind_final_kl", "lp_goal", -0.05),
}

def benchmark():
    rows = []
    for seed in SEEDS:
        by_policy = {p: S.run(p, seed, steps=STEPS, new_kind_at=NEW_KIND_AT)
                     for p in POLICIES}
        for p, result in by_policy.items():
            if result["new_kind_final_kl"] is None:
                raise RuntimeError("New kind absent in frozen cohort")
            if result["new_kind_interactions"] < 0:
                raise RuntimeError("Negative observed interactions")
            rows.append(result)
    def mean(p, field):
        return math.fsum(r[field] for r in rows if r["policy"] == p) / len(SEEDS)
    means = {p: {field: round(mean(p, field), 6)
                 for field in ("mean_hunger", "noise_share", "final_kl_learnable",
                               "new_kind_final_kl", "new_kind_interactions")}
             for p in POLICIES}
    target = "lp_goal_novelty"
    checks = {}
    for name, (field, baseline, threshold) in CRITERIA.items():
        delta = mean(target, field) - mean(baseline, field)
        checks[name] = {"pass": delta <= threshold, "paired_mean_delta": round(delta, 6),
                        "baseline": baseline, "threshold": threshold}
    by_seed = {(r["seed"], r["policy"]): r for r in rows}
    improved = sum(by_seed[(seed, target)]["new_kind_final_kl"] <
                   by_seed[(seed, "lp_goal")]["new_kind_final_kl"] for seed in SEEDS)
    checks["new_kind_improvement_at_least_14_of_20"] = {
        "pass": improved >= 14, "improved_seeds": improved, "threshold": 14}
    supported = all(c["pass"] for c in checks.values())
    return {"revision": "RUN346_DS2_FROZEN_V1", "scope": "SYNTHETIC_LAB_ONLY",
            "seeds": list(SEEDS), "steps": STEPS, "new_kind_at": NEW_KIND_AT,
            "policies": list(POLICIES), "rows": rows, "means": means,
            "checks": checks, "decision": "SUPPORTED_LAB_ONLY" if supported else "NOT_SUPPORTED",
            "no_native_or_age_promotion": True}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = benchmark()
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": result["decision"], "means": result["means"],
                      "checks": result["checks"]}, sort_keys=True))
