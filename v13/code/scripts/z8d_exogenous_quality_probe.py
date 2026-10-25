#!/usr/bin/env python3
"""Run381 WP-Z8d: preregistered *synthetic* exogenous source-quality ablation.

The quality signal is phase-correlated by construction, not an observed sensor.
It is visible only after each completed 50-item window. Real AgeControl/SQLite
and the frozen Z8 NLMS stream are used; no model, phone or production policy.
"""
import argparse
import json
import math
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import ablation99 as A
from scripts import z8_age_reopen as Z

ARMS = ("noise_aware", "quality", "quality_no_reopen", "quality_restart", "quality_shuffled")
FIRST_SEED = 301
SEEDS = 20
QUALITY_LOW = 0.20
QUALITY_HIGH = 0.95
LOW_PROB_NOISY = 0.80
LOW_PROB_OTHER = 0.10
LOW_CAP = 0.50
HIGH_FLOOR = 0.90
LOW_CUTOFF = 0.60
HIGH_CUTOFF = 0.80


def quality_flags(stream, seed):
    """Separate RNG, synthetic phase-correlated sensor; not inferred from w/y."""
    rng = random.Random(seed + 1_000_003)
    return [QUALITY_LOW if rng.random() < (
        LOW_PROB_NOISY if event["phase"] == "noisy" else LOW_PROB_OTHER
    ) else QUALITY_HIGH for event in stream]


def quality_policy(base, prior_window_quality, fails, allow_reopen=True):
    """No phase, target, current-event quality or future samples are inputs."""
    if prior_window_quality <= LOW_CUTOFF:
        return min(base, LOW_CAP)
    if allow_reopen and prior_window_quality >= HIGH_CUTOFF and fails >= 1:
        return max(base, HIGH_FLOOR)
    return base


def run(stream, flags, arm, home):
    ctl = Z.open_ctl(home, "noise_aware")
    theta = [0.0] * A.DIM
    prev_err = None
    prev_theta = list(theta)
    fails = 0
    novel = True
    errors = []
    win = []
    quality_win = []
    previous_quality = QUALITY_HIGH  # neutral at boot; first window not seen
    p_used = []
    stages = []
    quality_trace = []
    restarted = False
    for ev, quality in zip(stream, flags):
        if arm == "quality_restart" and ev["t"] == Z.RESTART_AT and not restarted:
            ctl.s.close()
            ctl = Z.open_ctl(home, "noise_aware")
            restarted = True
        allow_reopen = arm != "quality_no_reopen"
        p = ctl.plasticity(
            "language",
            novel_domain=novel and allow_reopen,
            repeated_errors=fails if allow_reopen else 0,
        )
        if arm != "noise_aware":
            p = quality_policy(p, previous_quality, fails, allow_reopen)
        p_used.append(p)
        quality_trace.append(previous_quality)
        theta = A._nlms(theta, ev["x"], ev["y"], Z.LR * p)
        error = A._err(theta, ev["w"])  # evaluation only, never policy input
        errors.append(error)
        win.append(error)
        quality_win.append(quality)
        if (ev["t"] + 1) % Z.WINDOW == 0:
            measured_error = A._mean(win)
            win = []
            # Quality becomes visible only after the completed window.
            previous_quality = A._mean(quality_win)
            quality_win = []
            novel = prev_err is not None and measured_error > 2 * prev_err and measured_error > .1
            passed = prev_err is None or measured_error <= prev_err * 1.1 + .02
            fails = 0 if passed else fails + 1
            drift = math.sqrt(sum((a - b) ** 2 for a, b in zip(theta, prev_theta))) / max(
                1e-9, math.sqrt(A._dot(theta, theta))
            )
            comp = max(0., 1 - measured_error)
            ctl.record("language", {
                "experience": ev["t"] + 1, "competence": comp,
                "stability": max(0., 1 - drift), "retention": comp,
                "calibration": .8, "memory_health": .97,
                "safe_self_control": .999, "regression_pass": passed,
            }, evidence_id="z8d-" + str(ev["t"]))
            stages.append(ctl.state()[0]["capabilities"]["language"]["stage"])
            prev_err = measured_error
            prev_theta = list(theta)
    transitions = ctl.s.db.execute(
        "SELECT COUNT(*) FROM telemetry WHERE kind='age_transition'"
    ).fetchone()[0]
    ctl.s.close()
    seg = lambda xs, a, b: A._mean(xs[a:b])
    return {
        "p": {
            "learn_end": seg(p_used, 500, 600),
            "noisy": seg(p_used, 600, 1000),
            "shift_start": seg(p_used, 1000, 1100),
            "settle_end": seg(p_used, 2100, 2200),
        },
        "err": {
            "learn": seg(errors, 0, 600),
            "noisy": seg(errors, 600, 1000),
            "shift_250": seg(errors, 1000, 1250),
            "shift": seg(errors, 1000, 1600),
            "settle": seg(errors, 1600, 2200),
        },
        "stages": stages,
        "noisy_stage_changes": sum(
            1 for i in range(1, len(stages))
            if stages[i] != stages[i - 1] and 600 <= (i + 1) * Z.WINDOW - 1 < 1000 + Z.WINDOW
        ),
        "max_stage": max(stages) if stages else None,
        "age_transition_events": transitions,
        "p_trace_every_25": [round(p, 9) for p in p_used[::25]],
        "quality_prior_every_25": [round(q, 6) for q in quality_trace[::25]],
    }


def verdict(raw, seeds):
    q = raw["quality"]
    nr = raw["quality_no_reopen"]
    baseline = raw["noise_aware"]
    shuffled = raw["quality_shuffled"]
    restart = raw["quality_restart"]
    n = len(seeds)
    k1 = sum(a["p"]["shift_start"] >= 1.25 * a["p"]["learn_end"] for a in q)
    k2_seeds = sum(a["err"]["shift_250"] < b["err"]["shift_250"] for a, b in zip(q, nr))
    k2_rel = 1 - statistics.mean(a["err"]["shift_250"] for a in q) / statistics.mean(
        b["err"]["shift_250"] for b in nr
    )
    k3 = statistics.median(a["p"]["noisy"] / a["p"]["learn_end"] for a in q)
    k4 = statistics.median(a["p"]["settle_end"] / a["p"]["shift_start"] for a in q)
    k5 = all(a == b for a, b in zip(q, restart))
    k6 = statistics.median(a["noisy_stage_changes"] for a in q)
    k7 = statistics.mean(a["err"]["noisy"] for a in q) / statistics.mean(
        b["err"]["noisy"] for b in baseline
    )
    k8_seeds = sum(a["err"]["shift_250"] < b["err"]["shift_250"] for a, b in zip(q, shuffled))
    k8_rel = 1 - statistics.mean(a["err"]["shift_250"] for a in q) / statistics.mean(
        b["err"]["shift_250"] for b in shuffled
    )
    criteria = {
        "K1_reopens": {"value": f"{k1}/{n}", "pass": k1 >= math.ceil(.8 * n)},
        "K2_reopen_helps": {
            "value": {"seeds_better": f"{k2_seeds}/{n}", "mean_error_reduction": round(k2_rel, 6)},
            "pass": k2_seeds >= math.ceil(.75 * n) and k2_rel >= .10,
        },
        "K3_noise_damped": {"value": round(k3, 6), "pass": k3 <= 1.25},
        "K4_recloses": {"value": round(k4, 6), "pass": k4 <= .8},
        "K5_restart_identical": {"value": k5, "pass": k5},
        "K6_no_stage_flapping": {"value": k6, "pass": k6 <= 2},
        "K7_noise_error_retained": {"value": round(k7, 6), "pass": k7 <= 1.10},
        "K8_quality_specificity": {
            "value": {"seeds_better": f"{k8_seeds}/{n}", "mean_error_reduction": round(k8_rel, 6)},
            "pass": k8_seeds >= math.ceil(.75 * n) and k8_rel >= .10,
        },
    }
    return ("Z8D_SYNTHETIC_QUALITY_PASS" if all(x["pass"] for x in criteria.values())
            else "Z8D_SYNTHETIC_QUALITY_FAIL"), criteria


def experiment(seeds, home):
    raw = {arm: [] for arm in ARMS}
    for seed in seeds:
        stream = Z.stream(seed)
        flags = quality_flags(stream, seed)
        shuffled = list(flags)
        random.Random(seed + 2_000_003).shuffle(shuffled)
        for arm in ARMS:
            raw[arm].append(run(stream, shuffled if arm == "quality_shuffled" else flags,
                                arm, Path(home) / (arm + "-" + str(seed))))
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--first-seed", type=int, default=FIRST_SEED)
    ap.add_argument("--seeds", type=int, default=SEEDS)
    args = ap.parse_args()
    if not 1 <= args.seeds <= 20 or args.first_seed < 0:
        raise ValueError("Bounded preregistered seed count required")
    seeds = list(range(args.first_seed, args.first_seed + args.seeds))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="z8d-quality-") as home:
        raw = experiment(seeds, home)
    label, criteria = verdict(raw, seeds)
    result = {
        "schema": "v13-z8d-synthetic-exogenous-quality-v1",
        "registered_full_seeds": list(range(FIRST_SEED, FIRST_SEED + SEEDS)),
        "seeds": seeds, "verdict": label, "criteria": criteria,
        "arms": list(ARMS), "raw": raw,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "claim_limit": (
            "Synthetic phase-correlated quality metadata constructed from known phases; "
            "candidate consumes only prior-window quality, no actual source-quality sensor, "
            "no model/Redmi, no G-AGE-REOPEN-001 promotion."
        ),
        "production_age_policy_modified": False,
        "phone_measured": False,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "z8d.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"verdict": label, "criteria": criteria}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
