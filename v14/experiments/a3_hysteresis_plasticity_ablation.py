"""Source-disjoint synthetic ablation for A3 persistence-relative hysteresis.

This experiment does not use camera frames, real user data, model weights or
Android hardware. Thresholds are selected on seeds 0..19 and evaluated on
held-out seeds 20..39. It compares temporal gating with matched-update and
matched-average-learning-rate controls; all predictors remain ephemeral.
Run from repository root with PYTHONPATH=v13/code:
    python v14/experiments/a3_hysteresis_plasticity_ablation.py
"""
from __future__ import annotations

import json
import random
from statistics import fmean

from v13.vision_temporal_prediction import A3TemporalPredictor

BASE_LR = 0.30
OPEN_RATIO = 0.10
CLOSE_RATIO = 0.05
TRAIN_SEEDS = range(20)
HOLDOUT_SEEDS = range(20, 40)


def make_stream(seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    patterns = []
    for _ in range(3):
        first = [0.0] * 16
        second = [0.0] * 16
        first[rng.randrange(0, 8)] = rng.uniform(0.35, 0.90)
        second[rng.randrange(8, 16)] = rng.uniform(0.35, 0.90)
        patterns.append((first, second))
    zero = [0.0] * 16
    return (
        [zero] * 200
        + [patterns[0][i % 2] for i in range(100)]
        + [zero] * 400
        + [patterns[1][i % 2] for i in range(100)]
        + [zero] * 400
        + [patterns[2][i % 2] for i in range(100)]
        + [zero] * 400
        + [patterns[0][i % 2] for i in range(100)]
    )


class PeriodicMatchedUpdates(A3TemporalPredictor):
    """Control with a fixed 7/8 update schedule, independent of prediction error."""

    def __init__(self) -> None:
        super().__init__(learning_rate=BASE_LR, warmup_updates=4, update_policy="ERROR_HYSTERESIS")

    def _update_hysteresis_gate(self, model_error: float, baseline_error: float):
        opened = (self._observations % 8) != 7
        if opened != self._gate_open:
            self._gate_transitions += 1
        self._gate_open = opened
        return opened, 0.0


def run_one(seed: int, policy: str, *, matched_lr: float | None = None) -> dict:
    stream = make_stream(seed)
    if policy == "ALWAYS":
        predictor = A3TemporalPredictor(learning_rate=BASE_LR, warmup_updates=4)
    elif policy == "ERROR_GATED":
        predictor = A3TemporalPredictor(
            learning_rate=BASE_LR, warmup_updates=4, update_policy="ERROR_GATED",
        )
    elif policy == "ERROR_HYSTERESIS":
        predictor = A3TemporalPredictor(
            learning_rate=BASE_LR, warmup_updates=4,
            update_policy="ERROR_HYSTERESIS",
            gate_open_ratio=OPEN_RATIO, gate_close_ratio=CLOSE_RATIO,
        )
    elif policy == "PERIODIC_MATCHED_UPDATES":
        predictor = PeriodicMatchedUpdates()
    elif policy == "MATCHED_AVERAGE_LR":
        if matched_lr is None:
            raise ValueError("matched_lr is required for the average-rate control")
        predictor = A3TemporalPredictor(learning_rate=matched_lr, warmup_updates=4)
    else:
        raise ValueError("unknown policy")

    errors = []
    old_pattern_errors = []
    for index, sample in enumerate(stream):
        result = predictor.update(sample)
        if result["status"] == "SHADOW_MEASURED":
            errors.append(result["prediction_error_mae"])
            if index >= len(stream) - 100:
                old_pattern_errors.append(result["prediction_error_mae"])
    return {
        "updates": predictor._updates,
        "observations": predictor._observations,
        "update_fraction": predictor._updates / predictor._observations,
        "mean_mae": fmean(errors),
        "old_pattern_mae": fmean(old_pattern_errors),
        "gate_transitions": predictor._gate_transitions,
    }


def _aggregate(rows: list[dict]) -> dict:
    return {
        "updates": round(fmean(row["updates"] for row in rows), 2),
        "update_fraction": round(fmean(row["update_fraction"] for row in rows), 6),
        "mean_mae": round(fmean(row["mean_mae"] for row in rows), 8),
        "old_pattern_mae": round(fmean(row["old_pattern_mae"] for row in rows), 8),
        "gate_transitions": round(fmean(row["gate_transitions"] for row in rows), 2),
    }


def run_experiment() -> dict:
    train_always = [run_one(seed, "ALWAYS") for seed in TRAIN_SEEDS]
    train_hysteresis = [run_one(seed, "ERROR_HYSTERESIS") for seed in TRAIN_SEEDS]
    matched_fraction = fmean(row["update_fraction"] for row in train_hysteresis)
    matched_lr = BASE_LR * matched_fraction

    holdout = {
        policy: [run_one(seed, policy, matched_lr=matched_lr) for seed in HOLDOUT_SEEDS]
        for policy in (
            "ALWAYS", "ERROR_GATED", "ERROR_HYSTERESIS",
            "PERIODIC_MATCHED_UPDATES", "MATCHED_AVERAGE_LR",
        )
    }
    return {
        "schema": "v14.a3-hysteresis-plasticity-ablation/1",
        "status": "SYNTHETIC_DIAGNOSTIC_ONLY",
        "data": "generated 16-tile vectors; no image, user or device data",
        "train_seeds": "0..19",
        "heldout_seeds": "20..39",
        "observations_per_stream": 1799,
        "base_learning_rate": BASE_LR,
        "gate_open_ratio": OPEN_RATIO,
        "gate_close_ratio": CLOSE_RATIO,
        "matched_average_learning_rate": round(matched_lr, 8),
        "periodic_control": "7 updates per 8 observations",
        "train": {
            "ALWAYS": _aggregate(train_always),
            "ERROR_HYSTERESIS": _aggregate(train_hysteresis),
        },
        "heldout": {policy: _aggregate(rows) for policy, rows in holdout.items()},
        "authority": "SHADOW_ONLY",
        "weights_persisted": False,
        "truth_authority": 0,
        "learning_authority": False,
        "action_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2, sort_keys=True))
