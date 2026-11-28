"""Synthetic, research-only one-step update-effect gate for the A4 cue-delta predictor.

The meta-model is trained on earlier synthetic sessions only. It predicts the
measured effect of a candidate update on the next cue transition, penalized by
regression on a fixed old-pattern replay probe. It never receives future inputs
at decision time. No PCM, user data, persistent model weights or Runtime policy
is changed by this experiment.
"""
from __future__ import annotations

import copy
import json
import math
from statistics import fmean

from a4_temporal_ablation_20261127 import PATTERNS
from v13.audio_temporal_prediction import FEATURE_COUNT, AudioTemporalPredictor, acoustic_feature_vector

RETENTION_WEIGHT = 0.5
LEARNING_RATE = 0.20
RIDGE = 0.01


def _cue(activity, f0, f0_range, energy, voiced_energy, voiced_fraction, confidence, activity_score, prosody):
    return {
        "method": "SYNTHETIC_RAW_EAR_CUE_FIXTURE",
        "frame_ms": 40,
        "hop_ms": 20,
        "activity_hint": activity,
        "frame_count": 50,
        "f0_median_hz": f0,
        "f0_range_hz": f0_range,
        "energy_range_db": energy,
        "voiced_energy_range_db": voiced_energy,
        "voiced_fraction": voiced_fraction,
        "voicing_confidence": confidence,
        "activity_score": activity_score,
        "prosody_change_score": prosody,
    }


def _smooth_sequence(phase: int, drift: float, count: int = 72):
    rows = []
    for i in range(count):
        t = i / max(1, count - 1)
        wave = 0.5 + 0.5 * math.sin((i + phase) * math.pi / 3)
        activity = "VOICED" if (i + phase) % 6 in (1, 2, 3) else "SILENCE"
        voiced = activity == "VOICED"
        rows.append(_cue(
            activity,
            105.0 + 70.0 * drift * t + 5.0 * wave if voiced else None,
            12.0 + 24.0 * drift * t if voiced else None,
            6.0 + 28.0 * drift * t + 3.0 * wave,
            3.0 + 14.0 * drift * t if voiced else None,
            0.48 + 0.35 * drift * t if voiced else 0.0,
            0.55 + 0.35 * drift * t if voiced else 0.0,
            0.40 + 0.45 * drift * t,
            0.08 + 0.65 * drift * t + 0.05 * wave,
        ))
    return tuple(rows)


def _abrupt_sequence(phase: int, split: int, count: int = 72):
    rows = []
    for i in range(count):
        if i < split:
            activity = "VOICED" if (i + phase) % 6 in (1, 2, 3) else "SILENCE"
            voiced = activity == "VOICED"
            rows.append(_cue(
                activity,
                140.0 if voiced else None,
                22.0 if voiced else None,
                16.0 if voiced else 0.0,
                8.0 if voiced else None,
                0.78 if voiced else 0.0,
                0.88 if voiced else 0.0,
                0.78 if voiced else 0.0,
                0.20 if voiced else 0.0,
            ))
        else:
            activity = "IMPULSIVE" if (i + phase) % 3 == 0 else "UNVOICED_NOISE"
            rows.append(_cue(
                activity, None, None,
                72.0 if activity == "IMPULSIVE" else 42.0,
                None, 0.0, 0.0,
                1.0 if activity == "IMPULSIVE" else 0.72,
                1.0 if activity == "IMPULSIVE" else 0.68,
            ))
    return tuple(rows)


def _deltas(sequence):
    features = [acoustic_feature_vector(item) for item in sequence]
    return tuple(
        tuple(abs(features[i][j] - features[i - 1][j]) for j in range(FEATURE_COUNT))
        for i in range(1, len(features))
    )


def _clone(predictor):
    return copy.deepcopy(predictor)


def _aligned_candidate_pair(predictor, delta):
    """Advance candidate and no-update baseline through the same current window."""
    baseline = _clone(predictor)
    candidate = _clone(predictor)
    result = candidate.update(delta, allow_update=True)
    baseline.update(delta, allow_update=False)
    return baseline, candidate, result


def _evaluate(predictor, deltas):
    """Read-only evaluation on a fresh sequence; the checkpoint is not updated."""
    probe = _clone(predictor)
    probe._previous = tuple(deltas[0])
    measured = []
    for delta in deltas[1:]:
        item = probe.update(delta, allow_update=False)
        if item.get("prediction_error_mae") is not None:
            measured.append(item)
    return {
        "observations": len(deltas),
        "measured_windows": len(measured),
        "mean_model_mae": round(fmean(float(x["prediction_error_mae"]) for x in measured), 8) if measured else None,
        "mean_persistence_baseline_mae": round(fmean(float(x["persistence_baseline_mae"]) for x in measured), 8) if measured else None,
        "evaluation_only": all(x.get("update_applied") is False for x in measured),
    }


def _features(delta, result):
    values = (
        float(result.get("prediction_error_mae") or 0.0),
        float(result.get("persistence_baseline_mae") or 0.0),
        float(result.get("excess_prediction_error") or 0.0),
        float(result.get("gradient_l2") or 0.0),
        float(result.get("feature_error_count") or 0) / FEATURE_COUNT,
        fmean(abs(float(x)) for x in delta),
        max(delta) - min(delta),
    )
    if len(values) != 7 or any(not math.isfinite(x) for x in values):
        raise ValueError("update-effect feature vector is invalid")
    return values


def _counterfactual_score(candidate, baseline, next_delta, old_deltas):
    """Delayed training label: next-window gain minus old-pattern replay regression."""
    candidate_next = _clone(candidate).update(next_delta, allow_update=False)
    baseline_next = _clone(baseline).update(next_delta, allow_update=False)
    if candidate_next.get("prediction_error_mae") is None or baseline_next.get("prediction_error_mae") is None:
        return 0.0
    current_gain = float(baseline_next["prediction_error_mae"]) - float(candidate_next["prediction_error_mae"])
    candidate_old = _evaluate(candidate, old_deltas)["mean_model_mae"]
    baseline_old = _evaluate(baseline, old_deltas)["mean_model_mae"]
    retention_cost = float(candidate_old) - float(baseline_old)
    return current_gain - RETENTION_WEIGHT * max(0.0, retention_cost)


def _training_examples(sessions, old_deltas):
    x_rows = []
    y_rows = []
    for _session_id, sequence in sessions:
        deltas = _deltas(sequence)
        predictor = AudioTemporalPredictor(
            learning_rate=LEARNING_RATE,
            warmup_updates=1,
            update_policy="FEATURE_ERROR_GATED",
        )
        for index in range(len(deltas) - 1):
            baseline, candidate, result = _aligned_candidate_pair(
                predictor, deltas[index]
            )
            if result.get("prediction_error_mae") is not None:
                x_rows.append(_features(deltas[index], result))
                y_rows.append(_counterfactual_score(candidate, baseline, deltas[index + 1], old_deltas))
            predictor = candidate
    return x_rows, y_rows


def _solve(matrix, vector):
    a = [list(row) + [float(vector[i])] for i, row in enumerate(matrix)]
    n = len(vector)
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("ridge normal matrix is singular")
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            for j in range(col, n + 1):
                a[row][j] -= factor * a[col][j]
    return [a[i][n] for i in range(n)]


class UpdateEffectPredictor:
    """Tiny normalized ridge model; fit only on earlier synthetic sessions."""

    def __init__(self, ridge=RIDGE):
        self.ridge = float(ridge)
        self.means = []
        self.scales = []
        self.coefficients = []
        self.residual_rmse = 0.0
        self.training_count = 0

    def fit(self, x_rows, y_rows):
        if len(x_rows) < 16 or len(x_rows) != len(y_rows):
            raise ValueError("insufficient or mismatched training examples")
        width = len(x_rows[0])
        self.means = [fmean(row[j] for row in x_rows) for j in range(width)]
        self.scales = []
        for j in range(width):
            variance = fmean((row[j] - self.means[j]) ** 2 for row in x_rows)
            self.scales.append(max(math.sqrt(variance), 1e-6))
        design = [[1.0] + [(row[j] - self.means[j]) / self.scales[j] for j in range(width)] for row in x_rows]
        n = width + 1
        gram = [
            [sum(row[i] * row[j] for row in design) + (self.ridge if i == j and i > 0 else 0.0)
             for j in range(n)]
            for i in range(n)
        ]
        target = [sum(row[i] * float(y) for row, y in zip(design, y_rows)) for i in range(n)]
        self.coefficients = _solve(gram, target)
        residuals = [self.predict(row) - float(y) for row, y in zip(x_rows, y_rows)]
        self.residual_rmse = math.sqrt(fmean(value * value for value in residuals))
        self.training_count = len(x_rows)
        return self

    def predict(self, features):
        if not self.coefficients:
            raise ValueError("predictor is not fitted")
        if len(features) != len(self.means):
            raise ValueError("feature width mismatch")
        values = [1.0] + [
            (float(features[j]) - self.means[j]) / self.scales[j]
            for j in range(len(features))
        ]
        return sum(a * b for a, b in zip(self.coefficients, values))


def _run_policy(policy, adapt_deltas, eval_deltas, old_deltas, meta=None, threshold=0.0):
    update_policy = "FEATURE_ERROR_GATED" if policy in {"FEATURE_ERROR_GATED", "META_GATE"} else "EVERY_FINAL"
    predictor = AudioTemporalPredictor(
        learning_rate=LEARNING_RATE,
        warmup_updates=1,
        update_policy=update_policy,
    )
    initial = predictor.state_dict()
    selected = 0
    candidates = 0
    predicted = []
    selected_true = []
    for index, delta in enumerate(adapt_deltas[:-1]):
        if policy == "META_GATE":
            baseline, candidate, result = _aligned_candidate_pair(
                predictor, delta
            )
            if result.get("update_applied"):
                candidates += 1
            score = meta.predict(_features(delta, result))
            predicted.append(score)
            take = bool(result.get("update_applied") and score > threshold)
            if take:
                selected += 1
                selected_true.append(_counterfactual_score(candidate, baseline, adapt_deltas[index + 1], old_deltas))
                predictor = candidate
            else:
                predictor = baseline
        elif policy == "NO_UPDATE":
            predictor.update(delta, allow_update=False)
        else:
            predictor.update(delta, allow_update=True)

    current = _evaluate(predictor, eval_deltas)
    old_before = _evaluate(
        AudioTemporalPredictor(learning_rate=LEARNING_RATE, warmup_updates=1, update_policy="EVERY_FINAL"),
        old_deltas,
    )
    old_after = _evaluate(predictor, old_deltas)
    old_delta = float(old_after["mean_model_mae"]) - float(old_before["mean_model_mae"])
    final_state = predictor.state_dict()
    parameter_diff = math.sqrt(sum(
        (float(initial["weights"][r][c]) - float(final_state["weights"][r][c])) ** 2
        for r in range(len(initial["weights"]))
        for c in range(len(initial["weights"][r]))
    ))
    return {
        "adapt_observations": len(adapt_deltas),
        "updates": predictor.updates,
        "candidate_updates": candidates,
        "selected_updates": selected,
        "update_fraction": round(predictor.updates / max(1, len(adapt_deltas) - 1), 8),
        "current_eval": current,
        "current_improvement_vs_persistence": round(
            float(current["mean_persistence_baseline_mae"]) - float(current["mean_model_mae"]), 8
        ),
        "old_pattern_before": old_before,
        "old_pattern_after": old_after,
        "old_task_retention_error_delta": round(old_delta, 8),
        "parameter_diff_l2": round(parameter_diff, 8),
        "mean_predicted_effect": round(fmean(predicted), 8) if predicted else None,
        "selected_effect_positive_fraction": (
            round(sum(x > 0 for x in selected_true) / len(selected_true), 8) if selected_true else None
        ),
        "selected_effect_count": len(selected_true),
        "evaluation_only": current["evaluation_only"] and old_after["evaluation_only"],
    }


def run_experiment():
    old_deltas = _deltas(PATTERNS["speech-periodic"])
    training_sessions = (
        ("train-smooth-a", _smooth_sequence(0, 0.55)),
        ("train-smooth-b", _smooth_sequence(2, 0.70)),
        ("train-abrupt-a", _abrupt_sequence(0, 30)),
        ("train-abrupt-b", _abrupt_sequence(2, 38)),
    )
    x_rows, y_rows = _training_examples(training_sessions, old_deltas)
    meta = UpdateEffectPredictor().fit(x_rows, y_rows)
    threshold = max(0.0, 0.25 * meta.residual_rmse)
    test_sessions = {
        "smooth": (_deltas(_smooth_sequence(1, 0.62)), _deltas(_smooth_sequence(3, 0.58))),
        "abrupt": (_deltas(_abrupt_sequence(1, 34)), _deltas(_abrupt_sequence(3, 42))),
    }
    per_regime = {}
    for regime, (adapt, heldout) in test_sessions.items():
        per_regime[regime] = {
            policy: _run_policy(policy, adapt, heldout, old_deltas, meta, threshold)
            for policy in ("EVERY_FINAL", "FEATURE_ERROR_GATED", "META_GATE", "NO_UPDATE")
        }
    return {
        "schema": "v14.a4.update-effect-predictor/2",
        "environment": "SYNTHETIC",
        "synthetic_benchmark": True,
        "device_benchmark": False,
        "input": "deterministic synthetic 13-D RAW EAR cue dictionaries; no PCM, transcript or user data",
        "counterfactual_state_alignment": "CANDIDATE_AND_NO_UPDATE_BASELINE_ADVANCE_THROUGH_SAME_CURRENT_WINDOW",
        "training_sessions": [name for name, _ in training_sessions],
        "heldout_sessions": [
            "heldout-smooth-adapt", "heldout-smooth-eval",
            "heldout-abrupt-adapt", "heldout-abrupt-eval",
        ],
        "training_examples": meta.training_count,
        "training_label_min": round(min(y_rows), 8),
        "training_label_max": round(max(y_rows), 8),
        "training_positive_fraction": round(sum(y > 0 for y in y_rows) / len(y_rows), 8),
        "predictor": {
            "type": "7-feature normalized ridge regression",
            "coefficients": len(meta.coefficients),
            "residual_rmse": round(meta.residual_rmse, 8),
            "abstain_threshold": round(threshold, 8),
            "ridge": RIDGE,
            "retention_weight": RETENTION_WEIGHT,
            "test_labels_used_for_fit": False,
        },
        "per_regime": per_regime,
        "privacy": {
            "raw_audio_persisted": False,
            "feature_windows_persisted": False,
            "training_examples_persisted": False,
        },
        "authority": {
            "runtime_policy_changed": False,
            "weight_persistence": False,
            "learning_authority": False,
            "action_authority": False,
            "truth_authority": False,
        },
        "not_claimed": [
            "real microphone or Android execution",
            "calibrated future-regime probability",
            "production A4 gating or persistent model-weight learning",
            "real old-task replay memory",
            "trained JEPA or cross-organ latent coupling",
            "reduced device energy or latency",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), sort_keys=True, separators=(",", ":"), allow_nan=False))
