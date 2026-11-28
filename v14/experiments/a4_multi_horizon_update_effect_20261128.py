"""Research-only multi-horizon A4 update-effect and residual-calibration ablation.

The gate sees only current-window features. Delayed labels are measured over
multiple future windows and independent replay anchors. Synthetic inputs only;
no Runtime policy, persistent weights, PCM, transcript or device state changes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from statistics import fmean

from v13.audio_temporal_prediction import (
    FEATURE_COUNT,
    AudioTemporalPredictor,
    acoustic_feature_vector,
)

HORIZONS = (1, 3, 8)
RETENTION_WEIGHT = 0.5
LEARNING_RATE = 0.20
RIDGE = 0.01


def _cue(activity, f0, f0_range, energy, voiced_energy, voiced_fraction,
         confidence, activity_score, prosody):
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


def _smooth_sequence(phase, drift, count=84):
    rows = []
    for i in range(count):
        t = i / max(1, count - 1)
        wave = 0.5 + 0.5 * math.sin((i + phase) * math.pi / 3)
        activity = "VOICED" if (i + phase) % 6 in (1, 2, 3) else "SILENCE"
        voiced = activity == "VOICED"
        rows.append(_cue(
            activity,
            105 + 70 * drift * t + 5 * wave if voiced else None,
            12 + 24 * drift * t if voiced else None,
            6 + 28 * drift * t + 3 * wave,
            3 + 14 * drift * t if voiced else None,
            0.48 + 0.35 * drift * t if voiced else 0,
            0.55 + 0.35 * drift * t if voiced else 0,
            0.40 + 0.45 * drift * t,
            0.08 + 0.65 * drift * t + 0.05 * wave,
        ))
    return tuple(rows)


def _abrupt_sequence(phase, split, count=84):
    rows = []
    for i in range(count):
        if i < split:
            activity = "VOICED" if (i + phase) % 6 in (1, 2, 3) else "SILENCE"
            voiced = activity == "VOICED"
            rows.append(_cue(
                activity,
                140 if voiced else None,
                22 if voiced else None,
                16 if voiced else 0,
                8 if voiced else None,
                0.78 if voiced else 0,
                0.88 if voiced else 0,
                0.78 if voiced else 0,
                0.20 if voiced else 0,
            ))
        else:
            activity = "IMPULSIVE" if (i + phase) % 3 == 0 else "UNVOICED_NOISE"
            rows.append(_cue(
                activity, None, None,
                72 if activity == "IMPULSIVE" else 42,
                None, 0, 0,
                1 if activity == "IMPULSIVE" else 0.72,
                1 if activity == "IMPULSIVE" else 0.68,
            ))
    return tuple(rows)


def _abrupt_to_smooth_sequence(phase, split=24, count=96):
    noisy = []
    for i in range(split):
        activity = "IMPULSIVE" if (i + phase) % 3 == 0 else "UNVOICED_NOISE"
        noisy.append(_cue(
            activity, None, None,
            72 if activity == "IMPULSIVE" else 42,
            None, 0, 0,
            1 if activity == "IMPULSIVE" else 0.72,
            1 if activity == "IMPULSIVE" else 0.68,
        ))
    smooth = _smooth_sequence(phase + 5, 0.58, count=count - split)
    return tuple(noisy) + smooth


def _deltas(sequence):
    features = [acoustic_feature_vector(item) for item in sequence]
    return tuple(
        tuple(abs(features[i][j] - features[i - 1][j])
              for j in range(FEATURE_COUNT))
        for i in range(1, len(features))
    )


def _clone(predictor):
    return copy.deepcopy(predictor)


def _features(delta, result):
    values = (
        float(result.get("prediction_error_mae") or 0),
        float(result.get("persistence_baseline_mae") or 0),
        float(result.get("excess_prediction_error") or 0),
        float(result.get("gradient_l2") or 0),
        float(result.get("feature_error_count") or 0) / FEATURE_COUNT,
        fmean(abs(float(x)) for x in delta),
        max(delta) - min(delta),
    )
    if len(values) != 7 or any(not math.isfinite(x) for x in values):
        raise ValueError("feature vector invalid")
    return values


def _solve(matrix, vector):
    n = len(vector)
    a = [list(matrix[i]) + [float(vector[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular ridge system")
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [value / scale for value in a[col]]
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if factor:
                a[row] = [
                    a[row][j] - factor * a[col][j]
                    for j in range(n + 1)
                ]
    return [a[i][-1] for i in range(n)]


class RidgeHead:
    """Small normalized ridge head for one delayed outcome horizon."""

    def __init__(self):
        self.means = []
        self.scales = []
        self.coefficients = []
        self.residual_rmse = 0.0
        self.training_count = 0

    def fit(self, x_rows, y_rows):
        if len(x_rows) < 16 or len(x_rows) != len(y_rows):
            raise ValueError("insufficient examples")
        width = len(x_rows[0])
        self.means = [
            fmean(row[j] for row in x_rows)
            for j in range(width)
        ]
        self.scales = [
            max(
                math.sqrt(fmean(
                    (row[j] - self.means[j]) ** 2 for row in x_rows
                )),
                1e-6,
            )
            for j in range(width)
        ]
        design = [
            [1.0] + [
                (row[j] - self.means[j]) / self.scales[j]
                for j in range(width)
            ]
            for row in x_rows
        ]
        n = width + 1
        gram = [
            [
                sum(row[i] * row[j] for row in design)
                + (RIDGE if i == j and i > 0 else 0.0)
                for j in range(n)
            ]
            for i in range(n)
        ]
        target = [
            sum(row[i] * float(y) for row, y in zip(design, y_rows))
            for i in range(n)
        ]
        self.coefficients = _solve(gram, target)
        residuals = [
            self.predict(row) - float(y)
            for row, y in zip(x_rows, y_rows)
        ]
        self.residual_rmse = math.sqrt(fmean(
            value * value for value in residuals
        ))
        self.training_count = len(x_rows)
        return self

    def predict(self, features):
        if not self.coefficients or len(features) != len(self.means):
            raise ValueError("unfitted head or feature mismatch")
        values = [1.0] + [
            (float(features[j]) - self.means[j]) / self.scales[j]
            for j in range(len(features))
        ]
        return sum(
            a * b for a, b in zip(self.coefficients, values)
        )


def _future_mae(predictor, future):
    probe = _clone(predictor)
    errors = []
    for delta in future:
        item = probe.update(delta, allow_update=False)
        if item.get("update_applied") is not False:
            raise RuntimeError("future evaluation unexpectedly updated weights")
        if item.get("prediction_error_mae") is not None:
            errors.append(float(item["prediction_error_mae"]))
    if not errors:
        raise ValueError("future horizon has no measured windows")
    return fmean(errors)


def _anchor_mae(predictor, anchor):
    probe = _clone(predictor)
    probe._previous = tuple(anchor[0])
    errors = []
    for delta in anchor[1:]:
        item = probe.update(delta, allow_update=False)
        if item.get("update_applied") is not False:
            raise RuntimeError("replay evaluation unexpectedly updated weights")
        if item.get("prediction_error_mae") is not None:
            errors.append(float(item["prediction_error_mae"]))
    if not errors:
        raise ValueError("replay anchor has no measured windows")
    return fmean(errors)


def _worst_retention_cost(candidate, baseline, anchors):
    costs = [
        _anchor_mae(candidate, anchor) - _anchor_mae(baseline, anchor)
        for anchor in anchors.values()
    ]
    return max(0.0, max(costs))


def _horizon_effect(candidate, baseline, future, anchors, *, retention_cost=None):
    gain = _future_mae(baseline, future) - _future_mae(candidate, future)
    if retention_cost is None:
        retention_cost = _worst_retention_cost(candidate, baseline, anchors)
    return gain - RETENTION_WEIGHT * retention_cost


def _aligned_candidate_pair(predictor, delta):
    """Compare one update against no-update after the same current observation."""
    baseline = _clone(predictor)
    candidate = _clone(predictor)
    result = candidate.update(delta, allow_update=True)
    baseline.update(delta, allow_update=False)
    return baseline, candidate, result


def _training_examples(sessions, replay_anchors):
    x_by = {h: [] for h in HORIZONS}
    y_by = {h: [] for h in HORIZONS}
    for _session, sequence in sessions:
        deltas = _deltas(sequence)
        predictor = AudioTemporalPredictor(
            learning_rate=LEARNING_RATE,
            warmup_updates=1,
            update_policy="FEATURE_ERROR_GATED",
        )
        for index in range(len(deltas) - max(HORIZONS)):
            baseline, candidate, result = _aligned_candidate_pair(
                predictor, deltas[index]
            )
            if (
                result.get("prediction_error_mae") is not None
                and result.get("update_applied")
            ):
                row = _features(deltas[index], result)
                retention_cost = _worst_retention_cost(
                    candidate, baseline, replay_anchors
                )
                for horizon in HORIZONS:
                    future = deltas[index + 1:index + 1 + horizon]
                    if len(future) == horizon:
                        x_by[horizon].append(row)
                        y_by[horizon].append(_horizon_effect(
                            candidate, baseline, future, replay_anchors,
                            retention_cost=retention_cost,
                        ))
            predictor = candidate
    return x_by, y_by


def _quantile(values, q):
    if not values or not 0.0 < q < 1.0:
        raise ValueError("quantile requires values and q in (0, 1)")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("quantile values must be finite")
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def _calibrate_threshold(head, x_rows, y_rows, *, quantile=0.90):
    """Compare a residual margin with a negative-score threshold on disjoint sessions."""
    if len(x_rows) < 16 or len(x_rows) != len(y_rows):
        raise ValueError("insufficient disjoint calibration examples")
    scores = [head.predict(row) for row in x_rows]
    targets = [float(target) for target in y_rows]
    residuals = [abs(score - target) for score, target in zip(scores, targets)]
    margin = max(0.0, _quantile(residuals, quantile))
    negative_scores = [score for score, target in zip(scores, targets) if target <= 0.0]
    positive_scores = [score for score, target in zip(scores, targets) if target > 0.0]
    if len(negative_scores) < 8 or len(positive_scores) < 1:
        raise ValueError("calibration requires negative and positive delayed outcomes")
    negative_threshold = _quantile(negative_scores, quantile)
    negative_false_positive = sum(score > negative_threshold for score in negative_scores)
    negative_true_positive = sum(score > negative_threshold for score in positive_scores)
    residual_false_positive = sum(score > margin for score, target in zip(scores, targets) if target <= 0.0)
    residual_true_positive = sum(score > margin for score, target in zip(scores, targets) if target > 0.0)
    return margin, negative_threshold, {
        "examples": len(scores),
        "positive_examples": len(positive_scores),
        "negative_examples": len(negative_scores),
        "residual_mae": round(fmean(residuals), 8),
        "residual_rmse": round(math.sqrt(fmean(value * value for value in residuals)), 8),
        "residual_p90": round(margin, 8),
        "coverage_at_residual_p90": round(
            sum(value <= margin for value in residuals) / len(residuals), 8
        ),
        "false_positive_rate_at_margin": round(
            residual_false_positive / len(negative_scores), 8
        ),
        "positive_recall_at_margin": round(
            residual_true_positive / len(positive_scores), 8
        ),
        "negative_score_q90": round(negative_threshold, 8),
        "false_positive_rate_at_negative_score_q90": round(
            negative_false_positive / len(negative_scores), 8
        ),
        "positive_recall_at_negative_score_q90": round(
            negative_true_positive / len(positive_scores), 8
        ),
        "residual_threshold_source": "DISJOINT_CALIBRATION_ABSOLUTE_RESIDUAL_P90",
        "negative_threshold_source": "DISJOINT_CALIBRATION_NEGATIVE_SCORE_Q90",
        "probability_calibration": False,
    }


def _select_multi_horizon(scores, thresholds):
    if len(scores) != len(thresholds) or not scores:
        return False
    return (
        fmean(scores) > fmean(thresholds)
        and all(
            score >= -threshold
            for score, threshold in zip(scores, thresholds)
        )
    )


def _select_negative_score_gate(scores, thresholds):
    """Require positive mean effect and exceed each disjoint negative-score cutoff."""
    if len(scores) != len(thresholds) or not scores:
        return False
    return fmean(scores) > 0.0 and all(
        score > threshold for score, threshold in zip(scores, thresholds)
    )


def _evaluate(predictor, deltas):
    probe = _clone(predictor)
    probe._previous = tuple(deltas[0])
    errors = []
    baselines = []
    evaluation_only = True
    for delta in deltas[1:]:
        item = probe.update(delta, allow_update=False)
        evaluation_only = evaluation_only and item.get("update_applied") is False
        if item.get("prediction_error_mae") is not None:
            errors.append(float(item["prediction_error_mae"]))
            baselines.append(float(item["persistence_baseline_mae"]))
    return {
        "mean_model_mae": fmean(errors),
        "mean_persistence_baseline_mae": fmean(baselines),
        "evaluation_only": evaluation_only,
    }


def _run_policy(policy, adapt, heldout, anchors, heads, thresholds, negative_thresholds):
    base_policy = (
        "EVERY_FINAL" if policy == "EVERY_FINAL" else "FEATURE_ERROR_GATED"
    )
    predictor = AudioTemporalPredictor(
        learning_rate=LEARNING_RATE,
        warmup_updates=1,
        update_policy=base_policy,
    )
    initial = predictor.state_dict()
    candidate_count = 0
    selected_count = 0
    predicted = {h: [] for h in HORIZONS}
    actual = {h: [] for h in HORIZONS}
    selected_flags = {h: [] for h in HORIZONS}

    for index, delta in enumerate(adapt[:-max(HORIZONS)]):
        if policy == "NO_UPDATE":
            predictor.update(delta, allow_update=False)
            continue
        if policy in ("EVERY_FINAL", "FEATURE_ERROR_GATED"):
            predictor.update(delta, allow_update=True)
            continue

        baseline, candidate, result = _aligned_candidate_pair(
            predictor, delta
        )
        if not result.get("update_applied"):
            predictor = baseline
            continue

        candidate_count += 1
        row = _features(delta, result)
        scores = {h: heads[h].predict(row) for h in HORIZONS}
        retention_cost = _worst_retention_cost(candidate, baseline, anchors)
        for horizon in HORIZONS:
            predicted[horizon].append(scores[horizon])
            future = adapt[index + 1:index + 1 + horizon]
            actual[horizon].append(_horizon_effect(
                candidate, baseline, future, anchors,
                retention_cost=retention_cost,
            ))

        if policy == "ONE_STEP_META_GATE":
            take = scores[1] > thresholds[1]
        elif policy == "MULTI_HORIZON_NEGATIVE_SCORE_GATE":
            take = _select_negative_score_gate(
                [scores[h] for h in HORIZONS],
                [negative_thresholds[h] for h in HORIZONS],
            )
        else:
            take = _select_multi_horizon(
                [scores[h] for h in HORIZONS],
                [thresholds[h] for h in HORIZONS],
            )
        if take:
            selected_count += 1
            predictor = candidate
        else:
            predictor = baseline
        for horizon in HORIZONS:
            selected_flags[horizon].append(bool(take))

    current = _evaluate(predictor, heldout)
    anchor_before = {
        name: _anchor_mae(
            AudioTemporalPredictor(
                learning_rate=LEARNING_RATE,
                warmup_updates=1,
                update_policy="EVERY_FINAL",
            ),
            anchor,
        )
        for name, anchor in anchors.items()
    }
    anchor_after = {
        name: _anchor_mae(predictor, anchor)
        for name, anchor in anchors.items()
    }
    retention = {
        name: round(anchor_after[name] - anchor_before[name], 8)
        for name in anchors
    }
    final = predictor.state_dict()
    delta_l2 = math.sqrt(sum(
        (final["weights"][i][j] - initial["weights"][i][j]) ** 2
        for i in range(len(final["weights"]))
        for j in range(len(final["weights"][i]))
    ))

    horizon_metrics = {}
    for horizon in HORIZONS:
        values = actual[horizon]
        flags = selected_flags[horizon]
        positive = sum(value > 0 for value in values)
        chosen = sum(flags)
        true_positive = sum(
            flag and value > 0 for flag, value in zip(flags, values)
        )
        false_positive_regret = sum(
            -value for flag, value in zip(flags, values)
            if flag and value < 0
        )
        missed_positive_regret = sum(
            value for flag, value in zip(flags, values)
            if not flag and value > 0
        )
        horizon_metrics[str(horizon)] = {
            "mean_predicted_effect": (
                round(fmean(predicted[horizon]), 8)
                if predicted[horizon] else None
            ),
            "mean_actual_candidate_effect": (
                round(fmean(values), 8) if values else None
            ),
            "candidate_positive_fraction": (
                round(positive / len(values), 8) if values else None
            ),
            "selected_positive_precision": (
                round(true_positive / chosen, 8) if chosen else None
            ),
            "selected_positive_recall": (
                round(true_positive / positive, 8) if positive else None
            ),
            "counterfactual_regret": round(
                false_positive_regret + missed_positive_regret, 8
            ),
            "false_positive_regret": round(false_positive_regret, 8),
            "missed_positive_regret": round(missed_positive_regret, 8),
            "candidate_count": len(values),
            "selected_count": chosen,
        }

    return {
        "adapt_observations": len(adapt),
        "updates": predictor.updates,
        "candidate_updates": candidate_count,
        "selected_updates": selected_count,
        "abstention_fraction": (
            round(1 - selected_count / candidate_count, 8)
            if candidate_count else 1.0
        ),
        "update_fraction": round(
            predictor.updates / max(1, len(adapt) - 1), 8
        ),
        "current_eval": current,
        "current_improvement_vs_persistence": round(
            current["mean_persistence_baseline_mae"]
            - current["mean_model_mae"],
            8,
        ),
        "retention_error_delta_by_anchor": retention,
        "worst_old_task_retention_error_delta": round(
            max(retention.values()), 8
        ),
        "parameter_diff_l2": round(delta_l2, 8),
        "horizon_metrics": horizon_metrics,
        "evaluation_only": current["evaluation_only"],
    }


def _digest(deltas):
    return hashlib.sha256(
        json.dumps(deltas, separators=(",", ":")).encode()
    ).hexdigest()


def run_experiment():
    training_replay_anchors = {
        "train-periodic": _deltas(_smooth_sequence(7, 0.35, 84)),
        "train-noise": _deltas(_abrupt_sequence(6, 28, 84)),
        "train-transition": _deltas(_abrupt_to_smooth_sequence(4, 26, 96)),
    }
    calibration_replay_anchors = {
        "calibration-periodic": _deltas(_smooth_sequence(11, 0.47, 84)),
        "calibration-noise": _deltas(_abrupt_sequence(7, 33, 84)),
    }
    heldout_replay_anchors = {
        "heldout-periodic": _deltas(_smooth_sequence(9, 0.92, 84)),
        "heldout-noise": _deltas(_abrupt_sequence(5, 28, 84)),
    }
    training_sessions = (
        ("train-smooth-a", _smooth_sequence(0, 0.55)),
        ("train-smooth-b", _smooth_sequence(2, 0.70)),
        ("train-abrupt-a", _abrupt_sequence(0, 30)),
        ("train-abrupt-b", _abrupt_sequence(2, 38)),
        ("train-abrupt-to-smooth-a", _abrupt_to_smooth_sequence(0, 24)),
        ("train-abrupt-to-smooth-b", _abrupt_to_smooth_sequence(2, 30)),
    )
    calibration_sessions = (
        ("calibration-smooth-a", _smooth_sequence(5, 0.63)),
        ("calibration-abrupt-a", _abrupt_sequence(4, 32)),
        ("calibration-abrupt-to-smooth-a", _abrupt_to_smooth_sequence(3, 27)),
    )
    x_by, y_by = _training_examples(training_sessions, training_replay_anchors)
    calibration_x_by, calibration_y_by = _training_examples(
        calibration_sessions, calibration_replay_anchors
    )
    heads = {
        horizon: RidgeHead().fit(x_by[horizon], y_by[horizon])
        for horizon in HORIZONS
    }
    thresholds = {}
    negative_score_thresholds = {}
    calibration = {}
    for horizon in HORIZONS:
        (
            thresholds[horizon],
            negative_score_thresholds[horizon],
            calibration[str(horizon)],
        ) = _calibrate_threshold(
            heads[horizon], calibration_x_by[horizon], calibration_y_by[horizon]
        )
        calibration[str(horizon)]["legacy_train_rmse_margin"] = round(
            0.25 * heads[horizon].residual_rmse, 8
        )
    test_sessions = {
        "smooth": (
            _deltas(_smooth_sequence(1, 0.62)),
            _deltas(_smooth_sequence(3, 0.58)),
        ),
        "abrupt": (
            _deltas(_abrupt_sequence(1, 34)),
            _deltas(_abrupt_sequence(3, 42)),
        ),
        "abrupt_to_smooth": (
            _deltas(_abrupt_to_smooth_sequence(1, 28)),
            _deltas(_smooth_sequence(4, 0.50)),
        ),
    }
    per_regime = {}
    for regime, (adapt, heldout) in test_sessions.items():
        per_regime[regime] = {}
        for policy in (
            "EVERY_FINAL",
            "FEATURE_ERROR_GATED",
            "ONE_STEP_META_GATE",
            "MULTI_HORIZON_META_GATE",
            "MULTI_HORIZON_NEGATIVE_SCORE_GATE",
            "NO_UPDATE",
        ):
            per_regime[regime][policy] = _run_policy(
                policy, adapt, heldout, heldout_replay_anchors, heads,
                thresholds, negative_score_thresholds,
            )
        no_update = per_regime[regime]["NO_UPDATE"]
        for result in per_regime[regime].values():
            utility_delta = (
                result["current_improvement_vs_persistence"]
                - no_update["current_improvement_vs_persistence"]
            )
            retention_delta = (
                result["worst_old_task_retention_error_delta"]
                - no_update["worst_old_task_retention_error_delta"]
            )
            result["current_utility_delta_vs_no_update"] = round(
                utility_delta, 8
            )
            result["worst_retention_delta_vs_no_update"] = round(
                retention_delta, 8
            )
            result["synthetic_reference_verdict"] = (
                "PASS"
                if utility_delta > 1e-4 and retention_delta <= 1e-4
                else (
                    "REGRESSION"
                    if utility_delta < -1e-4 or retention_delta > 1e-3
                    else "NO_IMPROVEMENT"
                )
            )

    return {
        "schema": "v14.a4.multi-horizon-update-effect/1",
        "environment": "SYNTHETIC",
        "synthetic_benchmark": True,
        "device_benchmark": False,
        "horizons": list(HORIZONS),
        "training_sessions": [name for name, _ in training_sessions],
        "calibration_sessions": [name for name, _ in calibration_sessions],
        "heldout_sessions": [
            "heldout-smooth",
            "heldout-abrupt",
            "heldout-abrupt-to-smooth",
        ],
        "training_replay_anchors": {
            name: {"sha256": _digest(anchor)}
            for name, anchor in training_replay_anchors.items()
        },
        "calibration_replay_anchors": {
            name: {"sha256": _digest(anchor)}
            for name, anchor in calibration_replay_anchors.items()
        },
        "heldout_replay_anchors": {
            name: {"sha256": _digest(anchor)}
            for name, anchor in heldout_replay_anchors.items()
        },
        "training_anchor_shared_with_test": False,
        "training_anchor_shared_with_calibration": False,
        "calibration_anchor_shared_with_test": False,
        "training_examples_by_horizon": {
            str(horizon): len(x_by[horizon]) for horizon in HORIZONS
        },
        "calibration_examples_by_horizon": {
            str(horizon): len(calibration_x_by[horizon]) for horizon in HORIZONS
        },
        "test_labels_used_for_fit": False,
        "heldout_labels_used_for_calibration": False,
        "calibration_labels_used_for_thresholds": True,
        "calibration_labels_used_at_decision": False,
        "future_labels_used_at_decision": False,
        "reference_checkpoint": "SYNTHETIC_NO_UPDATE_BASELINE_NOT_DEPLOYED_C0",
        "deployed_checkpoint_available": False,
        "replay_anchor_policy": (
            "TRAIN_ON_WORST_OF_THREE_DISJOINT_ANCHORS; "
            "CALIBRATE_ON_SEPARATE_TWO_ANCHORS; "
            "EVALUATE_WORST_OF_TWO_HELDOUT_ANCHORS"
        ),
        "decision_threshold_policy": (
            "COMPARE_DISJOINT_CALIBRATION_ABSOLUTE_RESIDUAL_P90_MARGIN "
            "WITH_NEGATIVE_SCORE_Q90_CUTOFF; "
            "EMPIRICAL_THRESHOLDS_NOT_PROBABILITIES"
        ),
        "calibration": calibration,
        "predictors": {
            str(horizon): {
                "coefficients": len(heads[horizon].coefficients),
                "residual_rmse": round(heads[horizon].residual_rmse, 8),
                "legacy_train_rmse_margin": round(
                    0.25 * heads[horizon].residual_rmse, 8
                ),
                "abstain_threshold": round(thresholds[horizon], 8),
                "calibrated_abstain_margin": round(thresholds[horizon], 8),
                "negative_score_q90_threshold": round(
                    negative_score_thresholds[horizon], 8
                ),
                "positive_training_fraction": round(
                    sum(y > 0 for y in y_by[horizon]) / len(y_by[horizon]),
                    8,
                ),
            }
            for horizon in HORIZONS
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
            "production A4 gating",
            "real replay memory",
            "trained JEPA or cross-organ latent coupling",
            "reduced device energy or latency",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(
        run_experiment(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ))
