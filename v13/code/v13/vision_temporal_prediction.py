"""Tiny session-local online predictor for A3 tile-change patterns.

This is an ephemeral shadow learner, not a visual encoder or semantic motion
model. It predicts the next 16-tile A3 cosine-delta vector from the previous
vector, reports pre-update error against a persistence baseline, then applies
one bounded LMS update. State must remain inside the existing consent-scoped
TemporalVisualEvidence stream and be erased on reset/revocation.
"""
from __future__ import annotations

import math


TILE_COUNT = 16
INPUT_COUNT = TILE_COUNT  # 16 previous tile deltas
METHOD = "A3_TILE_DELTA_ONLINE_LMS_V1"


class A3TemporalPredictorError(ValueError):
    """Malformed input or invalid predictor configuration."""


class A3TemporalPredictor:
    """Bounded online linear next-change predictor with ephemeral weights."""

    def __init__(self, *, learning_rate: float = 0.25,
                 warmup_updates: int = 4, max_gradient_norm: float = 1.0,
                 max_abs_weight: float = 2.0) -> None:
        if (type(learning_rate) not in (int, float)
                or not math.isfinite(float(learning_rate))
                or not 0.0 < float(learning_rate) <= 1.0):
            raise ValueError("learning_rate must be finite in (0,1]")
        if type(warmup_updates) is not int or not 1 <= warmup_updates <= 128:
            raise ValueError("warmup_updates must be an integer in [1,128]")
        if (type(max_gradient_norm) not in (int, float)
                or not math.isfinite(float(max_gradient_norm))
                or not 0.0 < float(max_gradient_norm) <= 10.0):
            raise ValueError("max_gradient_norm must be finite in (0,10]")
        if (type(max_abs_weight) not in (int, float)
                or not math.isfinite(float(max_abs_weight))
                or not 0.0 < float(max_abs_weight) <= 10.0):
            raise ValueError("max_abs_weight must be finite in (0,10]")
        self.learning_rate = float(learning_rate)
        self.warmup_updates = warmup_updates
        self.max_gradient_norm = float(max_gradient_norm)
        self.max_abs_weight = float(max_abs_weight)
        self._weights = [[0.0] * TILE_COUNT for _ in range(INPUT_COUNT)]
        self._previous = None
        self._updates = 0

    def reset(self) -> None:
        """Erase the session-local predictor and all learned numeric state."""
        self._weights = [[0.0] * TILE_COUNT for _ in range(INPUT_COUNT)]
        self._previous = None
        self._updates = 0

    @staticmethod
    def _validate(values) -> tuple[float, ...]:
        if type(values) not in (list, tuple) or len(values) != TILE_COUNT:
            raise A3TemporalPredictorError("tile change vector must contain exactly 16 values")
        result = []
        for value in values:
            if type(value) not in (int, float) or not math.isfinite(float(value)):
                raise A3TemporalPredictorError("tile change values must be finite numbers")
            number = float(value)
            if not 0.0 <= number <= 1.0:
                raise A3TemporalPredictorError("tile change values must be in [0,1]")
            result.append(number)
        return tuple(result)

    def _parameter_l2(self) -> float:
        return math.sqrt(sum(weight * weight for row in self._weights for weight in row))

    def _payload(self, *, status: str, prediction_error=None, baseline_error=None,
                 improvement=None, surprise=None, gradient_l2=0.0,
                 parameter_delta_l2=0.0) -> dict:
        return {
            "schema": "v14.a3-temporal-prediction/1",
            "status": status,
            "method": METHOD,
            "updates": self._updates,
            "warmup_updates": self.warmup_updates,
            "prediction_error_mae": None if prediction_error is None else round(prediction_error, 8),
            "persistence_baseline_mae": None if baseline_error is None else round(baseline_error, 8),
            "improvement_mae": None if improvement is None else round(improvement, 8),
            "shadow_surprise": None if surprise is None else round(surprise, 8),
            "gradient_l2": round(gradient_l2, 8),
            "parameter_delta_l2": round(parameter_delta_l2, 8),
            "parameter_l2": round(self._parameter_l2(), 8),
            "learning_rate": self.learning_rate,
            "persistent_weights": False,
            "weight_scope": "EPHEMERAL_SESSION_SHADOW",
            "authority": "SHADOW_ONLY",
            "truth_authority": 0,
            "learning_authority": False,
            "action_authority": False,
        }

    def unavailable(self, status: str = "UNAVAILABLE") -> dict:
        """Return a non-measured status after the caller resets this stream."""
        if type(status) is not str or not status or len(status) > 64:
            raise ValueError("status is invalid")
        return self._payload(status=status)

    def update(self, tile_delta) -> dict:
        """Predict before updating; expose a score only after the warm-up."""
        target = self._validate(tile_delta)
        if self._previous is None:
            self._previous = target
            return self._payload(status="WARMUP")

        features = self._previous
        prediction = tuple(max(0.0, min(1.0, sum(
            features[row] * self._weights[row][column] for row in range(INPUT_COUNT)
        ))) for column in range(TILE_COUNT))
        baseline_error = sum(abs(target[i] - self._previous[i]) for i in range(TILE_COUNT)) / TILE_COUNT
        model_error = sum(abs(target[i] - prediction[i]) for i in range(TILE_COUNT)) / TILE_COUNT
        measured = self._updates >= self.warmup_updates

        # Mean-squared-error LMS gradient. Clip the global gradient norm and
        # each parameter to keep the per-session model strictly bounded.
        gradient = [
            [2.0 * features[row] * (prediction[column] - target[column]) / TILE_COUNT
             for column in range(TILE_COUNT)]
            for row in range(INPUT_COUNT)
        ]
        gradient_l2 = math.sqrt(sum(value * value for row in gradient for value in row))
        scale = min(1.0, self.max_gradient_norm / max(gradient_l2, 1e-12))
        delta_squared = 0.0
        for row in range(INPUT_COUNT):
            for column in range(TILE_COUNT):
                delta = -self.learning_rate * gradient[row][column] * scale
                updated = max(-self.max_abs_weight, min(
                    self.max_abs_weight, self._weights[row][column] + delta,
                ))
                actual_delta = updated - self._weights[row][column]
                self._weights[row][column] = updated
                delta_squared += actual_delta * actual_delta

        self._previous = target
        self._updates += 1
        if not measured:
            return self._payload(
                status="WARMUP", gradient_l2=gradient_l2,
                parameter_delta_l2=math.sqrt(delta_squared),
            )
        improvement = baseline_error - model_error
        return self._payload(
            status="SHADOW_MEASURED", prediction_error=model_error,
            baseline_error=baseline_error, improvement=improvement,
            surprise=max(0.0, model_error - baseline_error),
            gradient_l2=gradient_l2,
            parameter_delta_l2=math.sqrt(delta_squared),
        )
