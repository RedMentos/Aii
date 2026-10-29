"""Read-only preregistered P0X matched-pair analysis, software only by import.

No model execution, no learning and no Canon gate promotion. This is a
descriptive score-layer analysis; original raw must be independently verified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re

SCHEMA = "v13.p0x.paired_source_analysis.v1"
SEED = 2026102919
BOOTSTRAPS = 5000
N = 150
ARMS = ("b1_only", "b2_only", "both_exact", "shuffled")
CONTRASTS = ("c3_only", "b1_only", "b2_only", "shuffled")
BASELINE_SCORE_SHA = "7c603158c6d821592d5777d46bb4723503f74c063c5c30fcc0f72fe2720b836e"
BASELINE_RAW_SHA = "79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1"
ACTIONS = {"A", "B", "NONE", "UNKNOWN", "UNPARSEABLE"}


def require(ok, reason):
    if not ok:
        raise ValueError("P0X_PAIRED_" + reason + "_RED")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_score_gates(score):
    require(score.get("canonical_gate_pass") is False
            and score.get("step2_status") == "UTILITY_FAIL"
            and score.get("b3_status") == "FAIL"
            and score.get("body_jepa_status") == "UNAVAILABLE"
            and score.get("lp3_status") == "FAIL"
            and score.get("jepa_weight") == 0
            and score.get("redmi_measured") is False
            and score.get("whole_system_complete") is False, "NEGATIVE_GATES")


def parse_details(score, arm):
    details = score.get("details")
    require(type(details) is list, "DETAILS_SHAPE")
    if arm == "c3_only":
        require(len(details) == N, "BASELINE_COUNT")
    else:
        require(len(details) == N * 4, "ARMS_COUNT")
        details = [d for d in details if d.get("arm") == arm]
        require(len(details) == N, "ARM_COUNT")
    result = {}
    counts = {"exact": 0, "wrong_committed": 0, "unknown": 0, "unparseable": 0}
    labels = {label: 0 for label in ACTIONS}
    for d in details:
        require(type(d) is dict and re.fullmatch(r"[0-9a-f]{64}",
                d.get("id_sha256", "")) is not None
                and d["id_sha256"] not in result
                and d.get("oracle") in ("A", "B", "NONE")
                and d.get("parsed") in ACTIONS, "ROW_SHAPE")
        result[d["id_sha256"]] = (d["parsed"], d["oracle"])
        parsed, oracle = result[d["id_sha256"]]
        kind = ("exact" if parsed == oracle else
                "wrong_committed" if parsed in ("A", "B", "NONE") else
                "unknown" if parsed == "UNKNOWN" else "unparseable")
        counts[kind] += 1
        labels[parsed] += 1
    require(len(result) == N and counts == score["per_arm"][arm],
            "SCORE_SUMMARY")
    require(labels == score["output_labels"][arm]
            if arm != "c3_only" else labels == score["output_labels"],
            "LABEL_SUMMARY")
    return result


def mcnemar_exact(wins, losses):
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in
               range(min(wins, losses) + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)


def paired(a, b, rng):
    ids = sorted(a)
    require(set(ids) == set(b) and len(ids) == N, "PAIRED_IDENTITIES")
    diffs = []
    wins = losses = 0
    for id_ in ids:
        new, truth = a[id_]
        old, old_truth = b[id_]
        require(truth == old_truth, "ORACLE_MISMATCH")
        delta = int(new == truth) - int(old == truth)
        diffs.append(delta)
        wins += int(delta == 1)
        losses += int(delta == -1)
    samples = []
    for _ in range(BOOTSTRAPS):
        samples.append(sum(diffs[rng.randrange(N)] for _ in range(N)) / N)
    samples.sort()
    return {"wins": wins, "losses": losses, "ties": N - wins - losses,
            "delta_exact": wins - losses, "paired_gain": (wins - losses) / N,
            "mcnemar_exact_p_two_sided": mcnemar_exact(wins, losses),
            "bootstrap_seed": SEED, "bootstrap_replicates": BOOTSTRAPS,
            "bootstrap_ci_95": [samples[int(.025 * BOOTSTRAPS)],
                                samples[min(BOOTSTRAPS - 1, int(.975 * BOOTSTRAPS))]]}


def holm(p_values):
    ranked = sorted(p_values, key=lambda key: (p_values[key], key))
    adjusted = {}
    prior = 0.0
    for index, key in enumerate(ranked):
        prior = max(prior, min(1.0, (len(ranked) - index) * p_values[key]))
        adjusted[key] = prior
    return adjusted


def analyze(baseline, arms):
    require(baseline.get("schema") == "v13.p0x.c3_150_baseline.v1.score.v1"
            and baseline.get("status") == "P0X_NATIVE_C3_ONLY_HEADROOM_DIAGNOSTIC_NO_GATE"
            and baseline.get("rows") == N and baseline.get("c3_native_calls") == N,
            "BASELINE_SCHEMA")
    require(arms.get("schema") == "v13.p0x.c3_source_arms.v1.score.v1"
            and arms.get("status") == "P0X_NATIVE_SOURCE_ABLATION_DIAGNOSTIC_NO_GATE"
            and arms.get("rows") == N * 4 and arms.get("c3_native_calls") == N * 4,
            "ARMS_SCHEMA")
    validate_score_gates(baseline)
    validate_score_gates(arms)
    base = parse_details(baseline, "c3_only")
    by_arm = {arm: parse_details(arms, arm) for arm in ARMS}
    require(all(set(data) == set(base) for data in by_arm.values()),
            "ARM_IDENTITY_COVERAGE")
    require(all(data[id_][1] == base[id_][1] for data in by_arm.values()
                for id_ in base), "ARM_ORACLE_MATCH")
    rng = random.Random(SEED)
    comparisons = {}
    for arm in CONTRASTS:
        comparisons[arm] = paired(by_arm["both_exact"],
                                  base if arm == "c3_only" else by_arm[arm], rng)
    adjusted = holm({arm: c["mcnemar_exact_p_two_sided"]
                     for arm, c in comparisons.items()})
    for arm, p in adjusted.items():
        comparisons[arm]["holm_adjusted_p"] = p
    return {"schema": SCHEMA,
            "status": "PAIRED_SCORE_DIAGNOSTIC_REQUIRES_INDEPENDENT_RAW_VERIFICATION",
            "rows_per_arm": N, "comparisons": comparisons,
            "wrong_committed": {arm: arms["per_arm"][arm]["wrong_committed"]
                                for arm in ARMS},
            "c3_only_wrong_committed": baseline["per_arm"]["c3_only"]["wrong_committed"],
            "both_exact_count": arms["per_arm"]["both_exact"]["exact"],
            "c3_only_count": baseline["per_arm"]["c3_only"]["exact"],
            "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
            "redmi_measured": False, "whole_system_complete": False,
            "claim_limit": "Read-only paired score analysis; independent original raw verification required; no Canon gate or causal proof"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-score", type=Path, required=True)
    parser.add_argument("--arms-score", type=Path, required=True)
    parser.add_argument("--arms-score-sha256", required=True)
    args = parser.parse_args(argv)
    baseline_bytes = args.baseline_score.read_bytes()
    arms_bytes = args.arms_score.read_bytes()
    require(sha(baseline_bytes) == BASELINE_SCORE_SHA
            and re.fullmatch(r"[0-9a-f]{64}", args.arms_score_sha256) is not None
            and sha(arms_bytes) == args.arms_score_sha256, "EXTERNAL_SCORE_PINS")
    print(json.dumps(analyze(json.loads(baseline_bytes), json.loads(arms_bytes)),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
