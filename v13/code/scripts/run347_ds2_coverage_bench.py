#!/usr/bin/env python3
"""Run347 frozen disjoint DS2 bounded coverage evaluation, synthetic lab only."""
import argparse
import json
import math
from pathlib import Path
from v13 import sandbox as S

SEEDS = tuple(range(501, 521))
POLICIES = ("lp", "lp_goal", "lp_goal_novelty", "lp_goal_coverage")
STEPS = 1200
NEW_KIND_AT = 500
TARGET = "lp_goal_coverage"
BASELINE = "lp_goal"

def benchmark():
    rows = []
    for seed in SEEDS:
        for policy in POLICIES:
            result = S.run(policy, seed, steps=STEPS, new_kind_at=NEW_KIND_AT)
            if result["new_kind_final_kl"] is None or result["new_kind_interactions"] < 0:
                raise RuntimeError("Frozen new-kind evidence missing")
            rows.append(result)
    fields = ("mean_hunger", "noise_share", "final_kl_learnable",
              "new_kind_final_kl", "new_kind_interactions")
    def mean(policy, field):
        return math.fsum(r[field] for r in rows if r["policy"] == policy) / len(SEEDS)
    means = {p: {field: round(mean(p, field), 6) for field in fields}
             for p in POLICIES}
    def check(field, threshold, direction):
        delta = mean(TARGET, field) - mean(BASELINE, field)
        passed = delta <= threshold if direction == "le" else delta >= threshold
        return {"pass": passed, "paired_mean_delta": round(delta, 6),
                "baseline": BASELINE, "threshold": threshold, "direction": direction}
    checks = {
        "new_kind_kl_improves_by_0p02": check("new_kind_final_kl", -0.02, "le"),
        "new_kind_visits_increase_by_5": check("new_kind_interactions", 5.0, "ge"),
        "hunger_not_worse_by_0p03": check("mean_hunger", 0.03, "le"),
        "noise_not_worse_by_0p05": check("noise_share", 0.05, "le"),
        "learnable_kl_not_worse_by_0p03": check("final_kl_learnable", 0.03, "le"),
    }
    by_seed = {(r["seed"], r["policy"]): r for r in rows}
    improved = sum(by_seed[(seed, TARGET)]["new_kind_final_kl"] <
                   by_seed[(seed, BASELINE)]["new_kind_final_kl"] for seed in SEEDS)
    checks["new_kind_improvement_at_least_14_of_20"] = {
        "pass": improved >= 14, "improved_seeds": improved, "threshold": 14}
    supported = all(c["pass"] for c in checks.values())
    return {"revision": "RUN347_DS2_COVERAGE_FROZEN_V1", "scope": "SYNTHETIC_LAB_ONLY",
            "seeds": list(SEEDS), "steps": STEPS, "new_kind_at": NEW_KIND_AT,
            "policies": list(POLICIES), "target": TARGET, "baseline": BASELINE,
            "rows": rows, "means": means, "checks": checks,
            "decision": "SUPPORTED_LAB_ONLY" if supported else "NOT_SUPPORTED",
            "no_native_or_age_promotion": True}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = benchmark()
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": result["decision"], "means": result["means"],
                      "checks": result["checks"]}, sort_keys=True))
