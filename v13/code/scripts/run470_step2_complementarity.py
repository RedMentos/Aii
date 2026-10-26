#!/usr/bin/env python3
"""Run470: source-bound, non-promoting STEP2 within-arm complementarity diagnostic.

The 378-row Run394/397 cohort is exploratory and not the ten-episode scoped
acceptance cohort. No diagnostic result from this module can promote STEP2.
"""
import argparse
import json
import math
from pathlib import Path

ARMS = ("O", "P", "S")
SEEDS = (20, 21, 22)
FIXTURES = ("Alder", "Beacon", "Cypress", "Delta", "Ember", "Fable")
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control",
            "same_policy_dual", "prompt_only_dual")
PRIMARY = "both_exact"
CONTROLS = tuple(v for v in VARIANTS if v != PRIMARY)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def average(values):
    require(bool(values), "EMPTY_COMPARISON")
    return math.fsum(values) / len(values)


def contrast(scores, arm_a, variant_a, arm_b, variant_b):
    by_seed_fixture = {
        str(seed): {fixture: scores[(arm_a, seed)][(fixture, variant_a)] -
                            scores[(arm_b, seed)][(fixture, variant_b)]
                    for fixture in FIXTURES}
        for seed in SEEDS}
    values = [by_seed_fixture[str(seed)][fixture]
              for seed in SEEDS for fixture in FIXTURES]
    return {
        "mean": average(values),
        "pairs": len(values),
        "wins": sum(v > 0 for v in values),
        "ties": sum(v == 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "by_seed": {str(seed): average(list(by_seed_fixture[str(seed)].values()))
                    for seed in SEEDS},
        "by_fixture": {fixture: average([by_seed_fixture[str(seed)][fixture]
                                        for seed in SEEDS]) for fixture in FIXTURES},
        "by_seed_fixture": by_seed_fixture,
    }


def diagnose(scores):
    """Exactly frozen 3x3x6x7 utilities; no statistical or canonical gate claim."""
    expected_keys = {(f, v) for f in FIXTURES for v in VARIANTS}
    require(type(scores) is dict and set(scores) == {(a, s) for a in ARMS for s in SEEDS},
            "FROZEN_NINE_ARM_MATRIX_REQUIRED")
    for key, rows in scores.items():
        require(type(rows) is dict and set(rows) == expected_keys,
                "FROZEN_FIXTURE_VARIANT_MATRIX_REQUIRED:" + str(key))
        for value in rows.values():
            require(type(value) in (float, int) and math.isfinite(value) and
                    0 <= value <= 1, "NONFINITE_OR_INVALID_UTILITY")
    within = {arm: {v: contrast(scores, arm, PRIMARY, arm, v)
                    for v in CONTROLS} for arm in ARMS}
    solo = {arm: contrast(scores, arm, "b1_only", arm, "b2_only")
            for arm in ARMS}
    per_seed_solo_coverage = {
        arm: {str(seed): {
            "b1_wins": sum(solo[arm]["by_seed_fixture"][str(seed)][f] > 0
                           for f in FIXTURES),
            "b2_wins": sum(solo[arm]["by_seed_fixture"][str(seed)][f] < 0
                           for f in FIXTURES)}
            for seed in SEEDS} for arm in ARMS}
    return {
        "run": "Run470",
        "status": "RUN470_FROZEN_COHORT_COMPLEMENTARITY_DIAGNOSTIC_ONLY",
        "rows": 378,
        "within_arm_primary_minus_controls": within,
        "between_arm_primary": {
            "pointer_minus_off": contrast(scores, "P", PRIMARY, "O", PRIMARY),
            "pointer_minus_shared_body": contrast(scores, "P", PRIMARY, "S", PRIMARY)},
        "solo_b1_minus_b2": solo,
        "per_seed_solo_coverage": per_seed_solo_coverage,
        "exploratory_strict_dominance": {
            arm: all(within[arm][v]["mean"] > 0 for v in CONTROLS) and
                 all(per_seed_solo_coverage[arm][str(seed)]["b1_wins"] > 0 and
                     per_seed_solo_coverage[arm][str(seed)]["b2_wins"] > 0
                     for seed in SEEDS)
            for arm in ARMS},
        "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL",
        "b3_status": "FAIL",
        "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0,
        "redmi_measured": False,
        "native_rerun": False,
        "claim_limit": "Run394 six-fixture three-seed exploratory cohort, not ten-episode preregistered STEP2 acceptance; dominance is descriptive, no causal complementarity or whole-system promotion.",
    }


def analyze(export_root, stage9_report):
    """Reverify with Run469, then re-read only SHA-attested files via dirfd."""
    import run469_native378_utility as base
    require(tuple(base.ARMS) == ARMS and tuple(base.SEEDS) == SEEDS and
            tuple(base.FIXTURES) == FIXTURES and tuple(base.VARIANTS) == VARIANTS,
            "FROZEN_RUN469_COHORT_CHANGED")
    prior = base.analyze(export_root, stage9_report)
    require(prior.get("status") == "RUN469_NATIVE378_UTILITY_DESCRIPTIVE_NO_GATE_PROMOTION" and
            prior.get("rows_verified") == 378 and
            prior.get("canonical_gate_pass") is False and
            prior.get("step2_exit") == "UTILITY_FAIL",
            "RUN469_INDEPENDENT_UTILITY_NOT_VERIFIED")
    root = Path(export_root).absolute()
    manifest = json.loads(base.read_pinned(root, base.verified378.gate.MANIFEST,
                                           prior["manifest_sha256"]))
    copied = manifest["copied"]
    progress = json.loads(base.read_pinned(root, "RUN397_PROGRESS.json",
                                           prior["progress_sha256"],
                                           copied["RUN397_PROGRESS.json"]["bytes"]))
    scores = {}
    expected = {(f, v) for f in FIXTURES for v in VARIANTS}
    for arm in ARMS:
        for seed in SEEDS:
            rid = f"{arm}_s{seed}"
            rel = progress["completed"][rid]["attempt"] + f"/tool_{rid}.json"
            member = copied[base.verified378.gate.safe_rel(rel)]
            tool = json.loads(base.read_pinned(root, rel, member["sha256"], member["bytes"]))
            rows = base.validated_rows(tool, expected, rid + ":tool")
            scores[(arm, seed)] = {key: rows[key]["score"]["utility"] for key in expected}
    require(base.aggregate(scores) == {k: prior[k] for k in
            ("arm_mean_utility", "paired_differences", "seeds", "arms",
             "variants", "fixture_ids", "rows")}, "RUN469_MATRIX_CHANGED_AFTER_VERIFICATION")
    result = diagnose(scores)
    result.update(manifest_sha256=prior["manifest_sha256"],
                  progress_sha256=prior["progress_sha256"],
                  independent_receipts=prior["independent_receipts"],
                  evidence_level="SOURCE_ATTESTED_LINUX_NATIVE_ONLY_IF_ACTUAL_EXPORT")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", type=Path, required=True)
    p.add_argument("--stage9-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = analyze(a.export, json.loads(a.stage9_report.read_text()))
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError) as exc:
        result = {"run": "Run470", "status": "RUN470_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                  "redmi_measured": False, "jepa_weight": 0, "native_rerun": False}
        rc = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "rows": result.get("rows", 0),
                      "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}))
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
