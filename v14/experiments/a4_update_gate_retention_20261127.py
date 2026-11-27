"""Synthetic ablation of optional memorized-error gating for the A4 cue-delta learner.

The experiment reuses the production AudioTemporalPredictor. It does not ingest PCM,
persist feature windows, enable a Runtime policy, or claim phone/energy measurements.
The continuous-regression gate is an adaptation, not the paper's classification rule.
"""
from __future__ import annotations

import json
import math
from statistics import fmean

from a4_temporal_ablation_20261127 import PATTERNS
from v13.audio_temporal_prediction import (
    AudioTemporalPredictor,
    acoustic_feature_vector,
)

POLICIES = ("EVERY_FINAL", "MEMORIZED_ERROR", "NO_UPDATE")
LEARNING_RATE = 0.20
MISTAKE_MEMORY_CAPACITY = 64
REPEATS = 4


def _deltas(sequence: tuple[dict, ...]) -> tuple[tuple[float, ...], ...]:
    features = [acoustic_feature_vector(item) for item in sequence]
    return tuple(
        tuple(abs(features[index][col] - features[index - 1][col]) for col in range(len(features[index])))
        for index in range(1, len(features))
    )


def _train(predictor: AudioTemporalPredictor, deltas, *, repeats: int, allow_update: bool = True) -> list[dict]:
    results = []
    for _ in range(repeats):
        for delta in deltas:
            results.append(predictor.update(delta, allow_update=allow_update))
    return results


def _state_diff_l2(before: dict, after: dict) -> float:
    return math.sqrt(sum(
        (float(before["weights"][row][col]) - float(after["weights"][row][col])) ** 2
        for row in range(len(before["weights"]))
        for col in range(len(before["weights"][row]))
    ))


def _evaluate(predictor: AudioTemporalPredictor, deltas) -> dict:
    """Evaluate a numeric checkpoint without changing weights or gate memory."""
    probe = AudioTemporalPredictor(
        learning_rate=predictor.learning_rate,
        warmup_updates=predictor.warmup_updates,
        max_gradient_norm=predictor.max_gradient_norm,
        max_abs_weight=predictor.max_abs_weight,
        update_policy=predictor.update_policy,
        mistake_memory_capacity=predictor.mistake_memory_capacity,
    )
    probe.load_state_dict(predictor.state_dict())
    results = [probe.update(delta, allow_update=False) for delta in deltas]
    measured = [item for item in results if item.get("prediction_error_mae") is not None]
    return {
        "observations": len(deltas),
        "measured_windows": len(measured),
        "mean_model_mae": round(fmean(float(item["prediction_error_mae"]) for item in measured), 8) if measured else None,
        "mean_persistence_baseline_mae": round(fmean(float(item["persistence_baseline_mae"]) for item in measured), 8) if measured else None,
        "update_count": probe.updates,
        "evaluation_only": all(item.get("update_reason") in {"WARMUP_BASELINE", "EVALUATION_ONLY"} for item in results),
        "gate_memory_entries_after_restart": len(probe._mistake_keys),
    }


def _summarize_policy(sequence: tuple[dict, ...], policy: str) -> dict:
    deltas = _deltas(sequence)
    predictor_policy = "EVERY_FINAL" if policy == "NO_UPDATE" else policy
    predictor = AudioTemporalPredictor(
        learning_rate=LEARNING_RATE,
        warmup_updates=1,
        update_policy=predictor_policy,
        mistake_memory_capacity=MISTAKE_MEMORY_CAPACITY,
    )
    initial_state = predictor.state_dict()
    results = _train(predictor, deltas, repeats=REPEATS, allow_update=policy != "NO_UPDATE")
    measured = [item for item in results if item.get("prediction_error_mae") is not None]
    updates = sum(item.get("update_applied") is True for item in results)
    return {
        "observations": len(results),
        "updates": updates,
        "update_fraction": round(updates / max(1, len(results)), 8),
        "mean_model_mae": round(fmean(float(item["prediction_error_mae"]) for item in measured), 8) if measured else None,
        "mean_persistence_baseline_mae": round(fmean(float(item["persistence_baseline_mae"]) for item in measured), 8) if measured else None,
        "mean_improvement_mae": round(fmean(float(item["improvement_mae"]) for item in measured), 8) if measured else None,
        "gradient_updates": sum(float(item.get("weight_delta_l2") or 0.0) > 0.0 for item in results),
        "gradient_l2_sum": round(sum(float(item.get("gradient_l2") or 0.0) for item in results), 8),
        "total_weight_delta_l2": round(sum(float(item.get("weight_delta_l2") or 0.0) for item in results), 8),
        "parameter_diff_l2_from_initial": round(_state_diff_l2(initial_state, predictor.state_dict()), 8),
        "max_weight_delta_l2": round(max((float(item.get("weight_delta_l2") or 0.0) for item in results), default=0.0), 8),
        "max_mistake_memory_entries": max((int(item.get("mistake_memory_entries") or 0) for item in results), default=0),
        "final_parameter_l2": round(predictor._parameter_l2(), 8),
        "state_dict_fields": sorted(predictor.state_dict()),
    }


def _retention_restart_ablation(policy: str) -> dict:
    old_deltas = _deltas(PATTERNS["speech-periodic"])
    new_deltas = _deltas(PATTERNS["non-speech-impulse"])
    predictor_policy = "EVERY_FINAL" if policy == "NO_UPDATE" else policy
    predictor = AudioTemporalPredictor(
        learning_rate=LEARNING_RATE,
        warmup_updates=1,
        update_policy=predictor_policy,
        mistake_memory_capacity=MISTAKE_MEMORY_CAPACITY,
    )
    allow_update = policy != "NO_UPDATE"
    _train(predictor, old_deltas, repeats=REPEATS, allow_update=allow_update)
    old_before = _evaluate(predictor, old_deltas)
    gate_entries_before_new = len(predictor._mistake_keys)

    _train(predictor, new_deltas, repeats=REPEATS, allow_update=allow_update)
    old_after = _evaluate(predictor, old_deltas)
    retention_delta = (
        round(old_after["mean_model_mae"] - old_before["mean_model_mae"], 8)
        if old_after["mean_model_mae"] is not None and old_before["mean_model_mae"] is not None
        else None
    )

    checkpoint = predictor.state_dict()
    restored = AudioTemporalPredictor(
        learning_rate=LEARNING_RATE,
        warmup_updates=1,
        update_policy=predictor_policy,
        mistake_memory_capacity=MISTAKE_MEMORY_CAPACITY,
    )
    restored.load_state_dict(checkpoint)
    old_after_restart = _evaluate(restored, old_deltas)
    return {
        "old_pattern_before_new_task": old_before,
        "old_pattern_after_new_task": old_after,
        "retention_error_delta": retention_delta,
        "numeric_weights_equal_after_restart": restored.state_dict() == checkpoint,
        "old_pattern_after_restart": old_after_restart,
        "restart_prediction_error_equal": (
            old_after_restart["mean_model_mae"] == old_after["mean_model_mae"]
        ),
        "gate_memory_entries_before_restart": gate_entries_before_new,
        "gate_memory_entries_after_restart": len(restored._mistake_keys),
        "gate_memory_persisted": False,
        "raw_audio_or_feature_windows_persisted": False,
    }


def run_experiment() -> dict:
    per_source = {
        source: {
            policy: _summarize_policy(sequence, policy)
            for policy in POLICIES
        }
        for source, sequence in PATTERNS.items()
    }
    retention = {
        policy: _retention_restart_ablation(policy)
        for policy in POLICIES
    }
    return {
        "schema": "v14.a4.error-gated-plasticity/1",
        "environment": "SYNTHETIC",
        "synthetic_benchmark": True,
        "device_benchmark": False,
        "input": "deterministic acoustic cue dictionaries; no PCM, transcript, speaker identity or user data",
        "update_policy_default": "EVERY_FINAL",
        "experimental_policy": "MEMORIZED_ERROR",
        "negative_control": "NO_UPDATE uses allow_update=False for every FINAL cue delta; it is an experiment-only control, not a production policy",
        "gate_definition": "update when model MAE exceeds persistence MAE, or when the same quantized previous/target-delta transition fingerprint was previously mistaken in this process-local stream",
        "memory_scope": "bounded process-local fingerprints; reset on stream/consent reset and restart; not a privacy/anonymisation guarantee",
        "memory_capacity": MISTAKE_MEMORY_CAPACITY,
        "repeats": REPEATS,
        "per_source": per_source,
        "retention_restart": retention,
        "not_claimed": [
            "paper-exact classification mistake gating",
            "real audio, microphone or Android execution",
            "reduced forward-pass or device energy cost",
            "calibrated event probability or semantic audio understanding",
            "B1/B2/C3 master-weight learning",
            "trained JEPA or cross-organ latent coupling",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), sort_keys=True, separators=(",", ":"), allow_nan=False))
