"""STABLE-style task-normalized dual drift controller for NumPy WorldJEPA.

This is an explicit experimental adaptation, not a verbatim STABLE reproduction.
It calibrates a per-step squared-drift budget on the first task, then applies a
fixed-anchor gradient penalty and projected dual update on later tasks. The
controller stores only scalar state; parameter anchors are the active checkpoint
loaded for the current update and are never serialized as hidden copies.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = "v14.world-jepa.stable-drift.v1"
CONFIG = {
    "budget_scale": 1.25,
    "dual_lr": 0.05,
    "dead_zone": 0.05,
    "lambda_max": 1000.0,
}
MAX_STEPS = 10**9


def _number(value, *, minimum=0.0, maximum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        return False
    return maximum is None or value <= maximum


def _group_state(value):
    required = {
        "budget_per_step", "lambda", "last_drift_sq",
        "calibration_steps", "last_steps",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("invalid STABLE controller group state")
    if (not _number(value["budget_per_step"], minimum=1e-12)
            or not _number(value["lambda"], maximum=CONFIG["lambda_max"])
            or not _number(value["last_drift_sq"])
            or type(value["calibration_steps"]) is not int
            or not 1 <= value["calibration_steps"] <= MAX_STEPS
            or type(value["last_steps"]) is not int
            or not 0 <= value["last_steps"] <= MAX_STEPS):
        raise ValueError("invalid STABLE controller group values")
    return {
        "budget_per_step": float(value["budget_per_step"]),
        "lambda": float(value["lambda"]),
        "last_drift_sq": float(value["last_drift_sq"]),
        "calibration_steps": value["calibration_steps"],
        "last_steps": value["last_steps"],
    }


def validate_state(value, ensemble):
    if value is None:
        return None
    if (type(ensemble) is not int or not 1 <= ensemble <= 16
            or type(value) is not dict
            or set(value) != {"schema", "config", "main", "bootstrap"}
            or value["schema"] != SCHEMA
            or type(value["config"]) is not dict
            or set(value["config"]) != set(CONFIG)
            or any(value["config"][key] != expected for key, expected in CONFIG.items())
            or type(value["bootstrap"]) is not list
            or len(value["bootstrap"]) != ensemble - 1):
        raise ValueError("incompatible STABLE controller state")
    return {
        "schema": SCHEMA,
        "config": dict(CONFIG),
        "main": _group_state(value["main"]),
        "bootstrap": [_group_state(item) for item in value["bootstrap"]],
    }


def compose_state(main, bootstrap):
    return validate_state({
        "schema": SCHEMA,
        "config": dict(CONFIG),
        "main": main,
        "bootstrap": list(bootstrap),
    }, len(bootstrap) + 1)


class StableDriftController:
    """One controller per optimizer parameter group."""

    def __init__(self, params, state, steps):
        if (type(params) is not dict or not params
                or type(steps) is not int or not 0 <= steps <= MAX_STEPS):
            raise ValueError("invalid STABLE optimizer group")
        self.params = params
        self.anchor = {}
        for key, value in params.items():
            if (type(key) is not str or not key or type(value) is not np.ndarray
                    or value.dtype != np.dtype("float64") or not value.size
                    or not np.isfinite(value).all()):
                raise ValueError("invalid STABLE anchor parameter")
            self.anchor[key] = np.array(value, copy=True, order="C")
        self.steps = steps
        self.calibrating = state is None
        if state is None:
            self.budget_per_step = None
            self.lambda_value = 0.0
            self.calibration_steps = max(1, steps)
        else:
            checked = _group_state(state)
            self.budget_per_step = checked["budget_per_step"]
            self.lambda_value = checked["lambda"]
            self.calibration_steps = checked["calibration_steps"]
        self.last_drift_sq = 0.0

    def adjusted_gradients(self, gradients):
        if type(gradients) is not dict or any(key not in self.params for key in gradients):
            raise ValueError("invalid STABLE gradient group")
        if self.calibrating or self.lambda_value <= 0.0:
            return gradients
        adjusted = {}
        for key, gradient in gradients.items():
            value = np.asarray(gradient, dtype=np.float64)
            if value.shape != self.params[key].shape or not np.isfinite(value).all():
                raise ValueError("invalid STABLE gradient tensor")
            adjusted[key] = value + (
                2.0 * self.lambda_value * (self.params[key] - self.anchor[key])
            )
        return adjusted

    def observe(self, step):
        if type(step) is not int or not 1 <= step <= max(1, self.steps):
            raise ValueError("invalid STABLE observation step")
        total = 0.0
        for key, value in self.params.items():
            delta = value - self.anchor[key]
            total += float(np.sum(delta * delta, dtype=np.float64))
        if not math.isfinite(total) or total < 0.0:
            raise ValueError("nonfinite STABLE drift")
        self.last_drift_sq = total
        if not self.calibrating:
            budget = max(1e-12, self.budget_per_step * step)
            ratio = total / budget
            upper = 1.0 + CONFIG["dead_zone"]
            lower = 1.0 - CONFIG["dead_zone"]
            if ratio > upper:
                self.lambda_value = min(
                    CONFIG["lambda_max"],
                    self.lambda_value + CONFIG["dual_lr"] * (ratio - upper),
                )
            elif ratio < lower:
                self.lambda_value = max(
                    0.0,
                    self.lambda_value * math.exp(-CONFIG["dual_lr"] * (lower - ratio)),
                )
        return total

    def export_state(self):
        budget_per_step = self.budget_per_step
        calibration_steps = self.calibration_steps
        if self.calibrating:
            budget_per_step = max(
                1e-12,
                self.last_drift_sq / max(1, self.steps) * CONFIG["budget_scale"],
            )
            calibration_steps = max(1, self.steps)
        return {
            "budget_per_step": float(budget_per_step),
            "lambda": float(self.lambda_value),
            "last_drift_sq": float(self.last_drift_sq),
            "calibration_steps": calibration_steps,
            "last_steps": self.steps,
        }
