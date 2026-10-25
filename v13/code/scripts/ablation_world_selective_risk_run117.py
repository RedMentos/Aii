"""Run117 fresh-seed, lab-only selective risk of physically valid World Model predictions.

Preregistered before implementation: see docs/proofs/continuation-20261025/world-selective-risk-run117/PREREG.md.
This measures ranking among non-abstained synthetic predictions, not the utility of abstention
or generated answers. No runtime authority, native inference, or V13 gate promotion.
"""
import json
import math
import random
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ablation_world_model_confidence as WMC
from v13 import world_model as WM

SEEDS = tuple(range(200, 220))
QUERIES = 400
TOP_FRACTION = 0.25
MIN_VALID = 40
WIN_THRESHOLD = 16
ARMS = ("confidence", "samples_only", "spread_only", "random")
PREREG = {
    "schema": "V13_WORLD_SELECTIVE_RISK_RUN117_PREREG_V1",
    "seeds": list(SEEDS),
    "transitions_per_seed": 300,
    "queries_per_seed": QUERIES,
    "top_fraction_of_valid": TOP_FRACTION,
    "minimum_valid_per_seed": MIN_VALID,
    "arms": list(ARMS),
    "primary": "mean absolute error against noise-free synthetic truth in top quartile of valid predictions",
    "win_rule": "confidence lower error than each control in >=16/20 seeds AND lower all-seed mean error than each control",
    "claim_limit": "synthetic own transitions only; no abstention-utility or causal/real-answer claim",
}


def _risk(rows, arm, k):
    if not k:
        return None
    # Stable query index tie-break is fixed before seeing the outcomes.
    selected = sorted(rows, key=lambda row: (-row[arm], row["query_index"]))[:k]
    return round(WMC._mean([row["err"] for row in selected]), 8)


def run_seed(seed, query_limit=None):
    if WMC.Q != QUERIES or WMC.N != 300:
        raise RuntimeError("registered synthetic generator parameters changed")
    transitions, queries = WMC.world(seed)
    if len(transitions) != 300 or len(queries) != QUERIES:
        raise RuntimeError("registered synthetic cohort size changed")
    if query_limit is not None:
        # A bounded unit-test seam, not part of the registered full cohort.
        if type(query_limit) is not int or not 0 <= query_limit <= QUERIES:
            raise ValueError("invalid test query limit")
        queries = queries[:query_limit]
    rng = random.Random(seed * 997 + 19)
    rows = []
    abstentions = {}
    with tempfile.TemporaryDirectory() as tmp:
        store, _ = WMC._store(Path(tmp))
        try:
            with mock.patch.object(WM, "transitions", lambda store, limit=WM.MAX_ROWS: transitions):
                fit = WM.fit(store, rng_seed=seed)
            for index, q in enumerate(queries):
                random_score = rng.random()  # Draw even if this query abstains.
                cf = WM.counterfactual(store, q["s"], q["a"])
                scored = WMC._scored_counterfactual(cf)
                if scored is None:
                    reason = cf.get("reason") if type(cf) is dict else None
                    if type(reason) is not str or not reason or len(reason) > 80:
                        reason = "INVALID_SCORING_FIELDS"
                    abstentions[reason] = abstentions.get(reason, 0) + 1
                    continue
                prediction, samples, spread, confidence, label = scored
                error = WMC._mean([abs(pred - truth) for pred, truth in zip(prediction, q["truth"])])
                if not math.isfinite(error):
                    abstentions["NONFINITE_ERROR"] = abstentions.get("NONFINITE_ERROR", 0) + 1
                    continue
                rows.append({
                    "query_index": index, "err": error,
                    "confidence": confidence,
                    "samples_only": 1 - math.exp(-samples / WM.COVER_N),
                    "spread_only": 1 / (1 + spread / WM.SPREAD_REF),
                    "random": random_score,
                })
        finally:
            store.close()
    valid_n = len(rows)
    selected_k = max(1, int(valid_n * TOP_FRACTION)) if valid_n else 0
    result = {
        "seed": seed,
        "fit_status": fit["status"],
        "queries_n": len(queries),
        "valid_n": valid_n,
        "abstained_n": sum(abstentions.values()),
        "abstention_reasons": dict(sorted(abstentions.items())),
        "selected_k": selected_k,
        "eligible": valid_n >= MIN_VALID and fit["status"] == "FITTED",
        "risk": {arm: _risk(rows, arm, selected_k) for arm in ARMS},
        "evidence": "SYNTHETIC_LINUX",
    }
    assert result["valid_n"] + result["abstained_n"] == result["queries_n"]
    return result


def _verdict(per, seeds):
    eligible = [seed for seed in seeds if per[seed]["eligible"]]
    wins = {arm: sum(per[seed]["risk"]["confidence"] < per[seed]["risk"][arm]
                     for seed in eligible) for arm in ARMS[1:]}
    means = {arm: (round(WMC._mean([per[seed]["risk"][arm] for seed in eligible]), 8)
                   if eligible else None) for arm in ARMS}
    complete = tuple(seeds) == SEEDS and len(eligible) == len(SEEDS)
    supported = complete and all(
        wins[arm] >= WIN_THRESHOLD and means["confidence"] < means[arm]
        for arm in ARMS[1:]
    )
    return {
        "verdict": ("INCOMPLETE" if not complete else
                    "SUPPORTED_SYNTHETIC_SELECTIVE" if supported else
                    "NOT_SUPPORTED_SYNTHETIC_SELECTIVE"),
        "eligible_seeds": len(eligible),
        "wins": wins,
        "mean_top_quartile_error": means,
    }


def run_all(seeds=SEEDS):
    per = {seed: run_seed(seed) for seed in seeds}
    return {
        "prereg": PREREG,
        "per_seed": per,
        **_verdict(per, seeds),
        "claim_limit": PREREG["claim_limit"],
        "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                  "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0,
                  "V13": "INCOMPLETE"},
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: ablation_world_selective_risk_run117.py OUTPUT.json")
    result = run_all()
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(result["verdict"], result["wins"], result["mean_top_quartile_error"])
