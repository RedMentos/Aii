#!/usr/bin/env python3
"""Run393: exploratory paired STEP2 source-access/utility analysis, no native inference."""
import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "bench-results/step2-z2c-b2-rule-20261021"
ARMS = ("CQ", "CQA", "CQP")
SEEDS = (17, 18, 19)
B2_VARIANTS = ("b2_only", "both_none", "both_exact", "both_control")
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control", "same_policy_dual", "prompt_only_dual")
MODES = {"CQ": "off", "CQA": "anchor", "CQP": "pointer"}
BOOT_SEED = 20261026


def finite_utility(x):
    return type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1


def validate_summary(j, arm, seed, fixtures):
    if not isinstance(j, dict) or j.get("arm") != arm or j.get("seed") != seed or j.get("run") != f"{arm}_s{seed}":
        raise ValueError("arm/seed/run mismatch")
    z = j.get("z2c")
    if not isinstance(z, dict) or z.get("b2_quote_select") != MODES[arm]:
        raise ValueError("quote mode mismatch")
    if j.get("tool_status") == "STRUCTURAL_FAIL" or j.get("step2_status") == "DIAGNOSTIC_INCOMPLETE":
        raise ValueError("incomplete native source report")
    if type(z.get("b2_wrong_rule_rows")) is not int or type(z.get("wrong_committed_tool")) is not int:
        raise ValueError("untyped safety counts")
    if z["b2_wrong_rule_rows"] < 0 or z["wrong_committed_tool"] < 0:
        raise ValueError("negative safety counts")
    rows = z.get("b2_rule_rows")
    utility = j.get("episode_utility_tool")
    if not isinstance(rows, dict) or not isinstance(utility, dict):
        raise ValueError("missing rows/utility")
    expected_rows = {f["id"] + ":" + v for f in fixtures if f["type"] in ("RULE", "SPLIT") for v in B2_VARIANTS}
    expected_utility = {f["id"] + ":" + v for f in fixtures for v in VARIANTS}
    if set(rows) != expected_rows or set(utility) != expected_utility:
        raise ValueError("missing/extra fixture or variant rows")
    for key, entry in rows.items():
        if not isinstance(entry, dict) or type(entry.get("rules")) is not bool or type(entry.get("wrong_rule")) is not bool:
            raise ValueError("invalid B2 rule access: " + key)
    for key, value in utility.items():
        if not finite_utility(value):
            raise ValueError("invalid utility: " + key)
    return j


def load_reports(folder=INPUT, fixtures=None):
    if fixtures is None:
        from step2_z2_timescale import FIXTURES
        fixtures = FIXTURES
    folder = Path(folder)
    reports = {}
    hashes = {}
    for arm in ARMS:
        for seed in SEEDS:
            name = f"summary_{arm}_s{seed}.json"
            raw = (folder / name).read_bytes()
            j = json.loads(raw)
            reports[(arm, seed)] = validate_summary(j, arm, seed, fixtures)
            hashes[name] = hashlib.sha256(raw).hexdigest()
    return reports, hashes


def ci_cluster_fixture(per_fixture, samples=4000, seed=BOOT_SEED):
    """One value per fixture; resample fixture clusters, never individual seed rows."""
    vals = list(per_fixture.values())
    if not vals:
        return {"mean": None, "ci95": None, "fixtures": 0}
    if not all(type(x) in (int, float) and math.isfinite(x) for x in vals):
        raise ValueError("nonfinite paired fixture difference")
    mean = sum(vals) / len(vals)
    rng = random.Random(seed)
    n = len(vals)
    draws = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return {"mean": mean, "ci95": [draws[int(.025 * samples)], draws[min(samples - 1, int(.975 * samples))]],
            "fixtures": n, "bootstrap_seed": seed, "bootstrap_samples": samples}


def paired_delta(reports, arm_a, variant_a, arm_b, variant_b, fixtures):
    per = {}
    for f in fixtures:
        key = f["id"]
        per[key] = sum(
            reports[(arm_a, seed)]["episode_utility_tool"][key + ":" + variant_a] -
            reports[(arm_b, seed)]["episode_utility_tool"][key + ":" + variant_b]
            for seed in SEEDS
        ) / len(SEEDS)
    return ci_cluster_fixture(per)


def analyze(reports, hashes, fixtures):
    # Revalidate before any derived analysis; never treat a missing row as zero.
    for arm in ARMS:
        for seed in SEEDS:
            validate_summary(reports[(arm, seed)], arm, seed, fixtures)
    records = {}
    for arm in ("CQA", "CQP"):
        by = defaultdict(list)
        for seed in SEEDS:
            control = reports[("CQ", seed)]
            treatment = reports[(arm, seed)]
            for f in fixtures:
                if f["type"] not in ("RULE", "SPLIT"):
                    continue
                for variant in B2_VARIANTS:
                    key = f["id"] + ":" + variant
                    before = control["z2c"]["b2_rule_rows"][key]["rules"]
                    after = treatment["z2c"]["b2_rule_rows"][key]["rules"]
                    transition = {(False, True): "gained", (True, False): "lost",
                                  (True, True): "always", (False, False): "never"}[(before, after)]
                    delta = treatment["episode_utility_tool"][key] - control["episode_utility_tool"][key]
                    by[(variant, f["type"], transition)].append(delta)
                    by[(variant, "ALL", transition)].append(delta)
                    by[("ALL", "ALL", transition)].append(delta)
        records[arm] = {"|".join(k): {"n_paired_rows": len(v), "mean_utility_delta": sum(v) / len(v)}
                        for k, v in sorted(by.items())}
    paired = {}
    for arm in ("CQA", "CQP"):
        paired[arm] = {
            "both_exact_minus_CQ_both_exact": paired_delta(reports, arm, "both_exact", "CQ", "both_exact", fixtures),
            "both_exact_minus_same_arm_b1_only": paired_delta(reports, arm, "both_exact", arm, "b1_only", fixtures),
            "both_exact_minus_same_arm_b2_only": paired_delta(reports, arm, "both_exact", arm, "b2_only", fixtures),
            "both_exact_minus_same_arm_shared_body": paired_delta(reports, arm, "both_exact", arm, "same_policy_dual", fixtures),
        }
    safety = {arm: {
        "wrong_rule_rows": sum(reports[(arm, s)]["z2c"]["b2_wrong_rule_rows"] for s in SEEDS),
        "wrong_committed_tool": sum(reports[(arm, s)]["z2c"]["wrong_committed_tool"] for s in SEEDS),
    } for arm in ARMS}
    from step2_z2_timescale import __file__ as fixture_source
    sources = {"script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "fixture_script": hashlib.sha256(Path(fixture_source).read_bytes()).hexdigest(),
               "input_summary_sha256": hashes}
    return {
        "run": "Run393", "status": "EXPLORATORY_RECORDED",
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "native_rerun": False, "redmi_measured": False,
        "source": sources, "fixtures": len(fixtures), "seeds": list(SEEDS),
        "access_transition_associations": records,
        "paired_fixture_cluster_bootstrap": paired, "safety": safety,
        "claim_limit": "Posthoc association on original Z2c native outputs, not a new causal intervention or heldout STEP2 gate. "
                       "Changed access and changed C3 prompt/quote policy are confounded; only fresh registered episodes and "
                       "shared-body controls can test generalization.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, default=INPUT)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    from step2_z2_timescale import FIXTURES
    reports, hashes = load_reports(args.input_dir, FIXTURES)
    out = analyze(reports, hashes, FIXTURES)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": out["status"], "rows_per_arm": 3 * sum(f["type"] in ("RULE", "SPLIT") for f in FIXTURES) * len(B2_VARIANTS),
                      "paired": out["paired_fixture_cluster_bootstrap"],
                      "safety": out["safety"], "canonical_gate_pass": False}, sort_keys=True))


if __name__ == "__main__":
    main()
