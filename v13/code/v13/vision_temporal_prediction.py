"""Tiny session-local online predictor for A3 tile-change patterns.

This is an ephemeral shadow learner, not a visual encoder or semantic motion
model. It predicts the next 16-tile A3 cosine-delta vector from the previous
vector using 256 transition weights plus a zero-context-only bias row (272
parameters). The bias is active only when the previous delta vector is all
zero, so it can learn zero-to-event transitions without shifting non-zero
contexts. It reports pre-update error against a persistence baseline. The default
ALWAYS policy preserves one bounded LMS update per observation; ERROR_GATED
is an experimental ablation that updates only while residual MAE exceeds
max(1e-8, 0.25 × persistence MAE). ERROR_HYSTERESIS uses separate persistence-
relative open/close thresholds (0.10 / 0.05) to avoid threshold-band chatter.
Both ablations are SHADOW_ONLY and do not control A4; all states reset on
stream reset/revocation.
"""
from __future__ import annotations

import math


TILE_COUNT = 16
INPUT_COUNT = TILE_COUNT + 1  # 16 previous deltas plus zero-context bias
METHOD = "A3_TILE_DELTA_ONLINE_LMS_ZERO_CONTEXT_BIAS_V2"


class A3TemporalPredictorError(ValueError):
    """Malformed input or invalid predictor configuration."""


class A3TemporalPredictor:
    """Bounded online linear next-change predictor with ephemeral weights."""

    def __init__(self, *, learning_rate: float = 0.25,
                 warmup_updates: int = 4, max_gradient_norm: float = 1.0,
                 max_abs_weight: float = 2.0, update_policy: str = "ALWAYS",
                 gate_open_ratio: float = 0.10,
                 gate_close_ratio: float = 0.05) -> None:
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
        if type(update_policy) is not str or update_policy not in {
            "ALWAYS", "ERROR_GATED", "ERROR_HYSTERESIS",
        }:
            raise ValueError("update_policy must be ALWAYS, ERROR_GATED or ERROR_HYSTERESIS")
        if (type(gate_open_ratio) not in (int, float)
                or not math.isfinite(float(gate_open_ratio))
                or not 0.0 < float(gate_open_ratio) <= 10.0):
            raise ValueError("gate_open_ratio must be finite in (0,10]")
        if (type(gate_close_ratio) not in (int, float)
                or not math.isfinite(float(gate_close_ratio))
                or not 0.0 <= float(gate_close_ratio) < float(gate_open_ratio)):
            raise ValueError("gate_close_ratio must be finite in [0,gate_open_ratio)")
        self.gate_open_ratio = float(gate_open_ratio)
        self.gate_close_ratio = float(gate_close_ratio)
        self._gate_open = False
        self._gate_transitions = 0
        self.learning_rate = float(learning_rate)
        self.warmup_updates = warmup_updates
        self.update_policy = update_policy
        self.max_gradient_norm = float(max_gradient_norm)
        self.max_abs_weight = float(max_abs_weight)
        self._weights = [[0.0] * TILE_COUNT for _ in range(INPUT_COUNT)]
        self._previous = None
        self._updates = 0
        self._observations = 0

    def reset(self) -> None:
        """Erase the session-local predictor and all learned numeric state."""
        self._weights = [[0.0] * TILE_COUNT for _ in range(INPUT_COUNT)]
        self._previous = None
        self._updates = 0
        self._observations = 0
        self._gate_open = False
        self._gate_transitions = 0

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

    def _update_hysteresis_gate(self, model_error: float, baseline_error: float) -> tuple[bool, float]:
        """Update a persistence-relative error gate with separate open/close thresholds."""
        if (type(model_error) not in (int, float)
                or not math.isfinite(float(model_error)) or float(model_error) < 0.0
                or type(baseline_error) not in (int, float)
                or not math.isfinite(float(baseline_error)) or float(baseline_error) < 0.0):
            raise A3TemporalPredictorError("hysteresis gate errors must be finite nonnegative numbers")
        relative_error = float(model_error) / max(1e-8, float(baseline_error))
        was_open = self._gate_open
        if not was_open and relative_error >= self.gate_open_ratio:
            self._gate_open = True
        elif was_open and relative_error <= self.gate_close_ratio:
            self._gate_open = False
        if self._gate_open != was_open:
            self._gate_transitions += 1
        return self._gate_open, relative_error

    def _payload(self, *, status: str, prediction_error=None, baseline_error=None,
                 improvement=None, surprise=None, gradient_l2=0.0,
                 parameter_delta_l2=0.0, update_gate="NONE",
                 prediction_error_exceeds_gate=False, gate_relative_error=None) -> dict:
        return {
            "schema": "v14.a3-temporal-prediction/1",
            "status": status,
            "method": METHOD,
            "updates": self._updates,
            "observations": self._observations,
            "update_fraction": round(self._updates / max(1, self._observations), 6),
            "update_policy": self.update_policy,
            "update_gate_rule": (
                "PERSISTENCE_RELATIVE_ERROR_HYSTERESIS"
                if self.update_policy == "ERROR_HYSTERESIS"
                else "MODEL_MAE_GT_MAX_EPSILON_OR_0.25_PERSISTENCE_MAE"
                if self.update_policy == "ERROR_GATED" else "ALWAYS"
            ),
            "update_gate": update_gate,
            "prediction_error_exceeds_gate": bool(prediction_error_exceeds_gate),
            "gate_open": self._gate_open,
            "gate_transition_count": self._gate_transitions,
            "gate_open_ratio": self.gate_open_ratio,
            "gate_close_ratio": self.gate_close_ratio,
            "gate_relative_error": (
                None if gate_relative_error is None else round(gate_relative_error, 8)
            ),
            "warmup_updates": self.warmup_updates,
            "prediction_error_mae": None if prediction_error is None else round(prediction_error, 8),
            "persistence_baseline_mae": None if baseline_error is None else round(baseline_error, 8),
            "improvement_mae": None if improvement is None else round(improvement, 8),
            "shadow_surprise": None if surprise is None else round(surprise, 8),
            "gradient_l2": round(gradient_l2, 8),
            "parameter_delta_l2": round(parameter_delta_l2, 8),
            "parameter_l2": round(self._parameter_l2(), 8),
            "learning_rate": self.learning_rate,
            "parameter_count": INPUT_COUNT * TILE_COUNT,
            "bias_policy": "ZERO_CONTEXT_ONLY",
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

        # A permanent constant bias caused old-pattern drift in the
        # disjoint-pattern retention control. Activate this row only for a
        # zero-change context; non-zero temporal contexts cannot update it.
        features = self._previous + (1.0 if not any(self._previous) else 0.0,)
        prediction = tuple(max(0.0, min(1.0, sum(
            features[row] * self._weights[row][column] for row in range(INPUT_COUNT)
        ))) for column in range(TILE_COUNT))
        baseline_error = sum(abs(target[i] - self._previous[i]) for i in range(TILE_COUNT)) / TILE_COUNT
        model_error = sum(abs(target[i] - prediction[i]) for i in range(TILE_COUNT)) / TILE_COUNT
        measured = self._observations >= self.warmup_updates
        error_gate_open = model_error > max(1e-8, baseline_error * 0.25)
        gate_relative_error = None
        if self.update_policy == "ERROR_HYSTERESIS":
            error_gate_open, gate_relative_error = self._update_hysteresis_gate(
                model_error, baseline_error,
            )
            should_update = error_gate_open
            update_gate = "HYSTERESIS_OPEN" if error_gate_open else "HYSTERESIS_CLOSED"
        elif self.update_policy == "ERROR_GATED":
            should_update = error_gate_open
            update_gate = "ERROR_GATE_OPEN" if error_gate_open else "ERROR_GATE_CLOSED"
        else:
            should_update = True
            update_gate = "ALWAYS"

        gradient_l2 = 0.0
        delta_squared = 0.0
        if should_update:
            # Mean-squared-error LMS gradient. Clip the global gradient norm and
            # each parameter to keep the per-session model strictly bounded.
            gradient = [
                [2.0 * features[row] * (prediction[column] - target[column]) / TILE_COUNT
                 for column in range(TILE_COUNT)]
                for row in range(INPUT_COUNT)
            ]
            gradient_l2 = math.sqrt(sum(value * value for row in gradient for value in row))
            scale = min(1.0, self.max_gradient_norm / max(gradient_l2, 1e-12))
            for row in range(INPUT_COUNT):
                for column in range(TILE_COUNT):
                    delta = -self.learning_rate * gradient[row][column] * scale
                    updated = max(-self.max_abs_weight, min(
                        self.max_abs_weight, self._weights[row][column] + delta,
                    ))
                    actual_delta = updated - self._weights[row][column]
                    self._weights[row][column] = updated
                    delta_squared += actual_delta * actual_delta
            self._updates += 1

        self._previous = target
        self._observations += 1
        if not measured:
            return self._payload(
                status="WARMUP", gradient_l2=gradient_l2,
                parameter_delta_l2=math.sqrt(delta_squared), update_gate=update_gate,
                prediction_error_exceeds_gate=error_gate_open,
                gate_relative_error=gate_relative_error,
            )
        improvement = baseline_error - model_error
        return self._payload(
            status="SHADOW_MEASURED", prediction_error=model_error,
            baseline_error=baseline_error, improvement=improvement,
            surprise=max(0.0, model_error - baseline_error),
            gradient_l2=gradient_l2,
            parameter_delta_l2=math.sqrt(delta_squared), update_gate=update_gate,
            prediction_error_exceeds_gate=error_gate_open,
            gate_relative_error=gate_relative_error,
        )
