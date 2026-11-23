"""Typed, source-bound LearningIntent and WeightDeltaReceipt for the B1/B2 temporal receiver adapters.

The target is the small float receiver head consumed by B1/B2 bodyview, not either
native GGUF/base model. The adapter remains SHADOW and carries no action or write
authority over native body weights.
"""
from __future__ import annotations

import hashlib
import json
import math
import time

import numpy as np

from .world_jepa_consumer import ROLE_TARGETS, _mse, _ridge_head, receiver_utility_gate

REVISION = "v14-learning-intent-v1"
TARGET_ADAPTER_REVISION = "v14-temporal-receiver-adapter-v1"
OBJECTIVE_REVISION = "v14-temporal-receiver-outcome-mse-v1"
OPTIMIZER_REVISION = "ADAM_MSE_V1"
LEGACY_OPTIMIZER_REVISION = "RIDGE_CLOSED_FORM_V1"
MAX_ADAPTER_STEPS = 64
MAX_GRADIENT_NORM = 1.0
BASE_ADAPTER_LEARNING_RATE = 0.01
ANCHOR_STRENGTH = 0.01
ADAM_BETA1 = 0.9
ADAM_BETA2 = 0.999
ADAM_EPSILON = 1e-8
TARGET_ROLES = ("B1_DETAIL", "B2_GIST")
CONSUMER = "bodyview._temporal_world_jepa_body_readout"
MAX_IDS = 8192


def _digest(value):
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha(value):
    if type(value) is not str or len(value) != 64:
        raise ValueError("learning-intent SHA256")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValueError("learning-intent SHA256")
    return value


def _finite(value, *, minimum=None, maximum=None):
    if type(value) not in (int, float) or isinstance(value, bool):
        return False
    number = float(value)
    return (
        math.isfinite(number)
        and (minimum is None or number >= minimum)
        and (maximum is None or number <= maximum)
    )


def _unique(values, name, *, sha256=False):
    if type(values) not in (list, tuple) or not values or len(values) > MAX_IDS:
        raise ValueError("learning-intent " + name)
    result = []
    seen = set()
    for value in values:
        if sha256:
            _sha(value)
        elif (
            type(value) is not str or not 1 <= len(value) <= 160
            or value.strip() != value or not value.isprintable()
        ):
            raise ValueError("learning-intent " + name)
        if value in seen:
            raise ValueError("duplicate learning-intent " + name)
        seen.add(value)
        result.append(value)
    return sorted(result)


def _window_ids(windows):
    if type(windows) is not list or not windows:
        raise ValueError("learning-intent windows")
    values = []
    for window in windows:
        if type(window) is not dict:
            raise ValueError("learning-intent window")
        values.append(window.get("window_id"))
    return _unique(values, "window ids")


def _window_field_ids(windows, field, *, sha256=False):
    values = []
    for window in windows:
        current = window.get(field)
        if type(current) is not list:
            raise ValueError("learning-intent window field " + field)
        values.extend(current)
    for value in values:
        if sha256:
            _sha(value)
        elif (
            type(value) is not str or not 1 <= len(value) <= 160
            or value.strip() != value or not value.isprintable()
        ):
            raise ValueError("learning-intent window field " + field)
    return _unique(sorted(set(values)), field, sha256=sha256)


def _window_lineage_field_ids(windows, lineage_field, fallback_field, *, sha256=False):
    values = []
    for window in windows:
        current = window.get(lineage_field, window.get(fallback_field))
        if type(current) is not list:
            raise ValueError("learning-intent window field " + lineage_field)
        values.extend(current)
    for value in values:
        if sha256:
            _sha(value)
        elif (
            type(value) is not str or not 1 <= len(value) <= 160
            or value.strip() != value or not value.isprintable()
        ):
            raise ValueError("learning-intent window field " + lineage_field)
    return _unique(sorted(set(values)), lineage_field, sha256=sha256)


def _head_parameters(head):
    if type(head) is not dict or not {"weights", "bias"} <= set(head):
        raise ValueError("receiver adapter head shape")
    weights = np.asarray(head["weights"], dtype=np.float64)
    bias = np.asarray(head["bias"], dtype=np.float64)
    if (
        weights.ndim != 2 or bias.ndim != 1
        or weights.shape[1] != len(bias)
        or not np.isfinite(weights).all() or not np.isfinite(bias).all()
    ):
        raise ValueError("receiver adapter head values")
    return weights, bias


def _head_sha(head):
    return _digest({
        "target_indices": list(head["target_indices"]),
        "weights": np.asarray(head["weights"], dtype=np.float64).tolist(),
        "bias": np.asarray(head["bias"], dtype=np.float64).tolist(),
    })


def _adam_head(z, target, initial_weights, initial_bias, *, steps,
               learning_rate, max_gradient_norm, anchor_strength,
               beta1=ADAM_BETA1, beta2=ADAM_BETA2, epsilon=ADAM_EPSILON):
    """Bounded full-batch Adam update for one small B1/B2 float receiver head.

    The prior adapter is the anchor. Only source-disjoint T8 training rows are
    passed here; holdout rows are evaluated after the final parameter update.
    """
    X = np.asarray(z, dtype=np.float64)
    Y = np.asarray(target, dtype=np.float64)
    weights = np.asarray(initial_weights, dtype=np.float64).copy()
    bias = np.asarray(initial_bias, dtype=np.float64).copy()
    if (
        X.ndim != 2 or Y.ndim != 2 or len(X) < 1 or len(X) != len(Y)
        or weights.shape != (X.shape[1], Y.shape[1])
        or bias.shape != (Y.shape[1],)
        or not np.isfinite(X).all() or not np.isfinite(Y).all()
        or not np.isfinite(weights).all() or not np.isfinite(bias).all()
        or type(steps) is not int or not 1 <= steps <= MAX_ADAPTER_STEPS
        or not _finite(learning_rate, minimum=0.0, maximum=0.1)
        or not _finite(max_gradient_norm, minimum=0.01, maximum=10.0)
        or not _finite(anchor_strength, minimum=0.0, maximum=1.0)
        or not _finite(beta1, minimum=0.0, maximum=0.999)
        or not _finite(beta2, minimum=0.0, maximum=0.9999)
        or not _finite(epsilon, minimum=1e-12, maximum=1e-4)
    ):
        raise ValueError("invalid bounded Adam receiver inputs")

    anchor_weights = weights.copy()
    anchor_bias = bias.copy()
    first_w = np.zeros_like(weights)
    second_w = np.zeros_like(weights)
    first_b = np.zeros_like(bias)
    second_b = np.zeros_like(bias)
    gradient_norm_max = 0.0
    clip_count = 0
    train_mse_before = _mse(X @ weights + bias, Y)

    for step in range(1, steps + 1):
        residual = X @ weights + bias - Y
        grad_w = (2.0 / len(X)) * (X.T @ residual)
        grad_b = (2.0 / len(X)) * np.sum(residual, axis=0)
        grad_w += anchor_strength * (weights - anchor_weights)
        grad_b += anchor_strength * (bias - anchor_bias)
        gradient_norm = math.sqrt(
            float(np.sum(grad_w * grad_w)) + float(np.sum(grad_b * grad_b))
        )
        if not math.isfinite(gradient_norm):
            raise ValueError("nonfinite receiver gradient")
        gradient_norm_max = max(gradient_norm_max, gradient_norm)
        if gradient_norm > max_gradient_norm:
            scale = max_gradient_norm / gradient_norm
            grad_w *= scale
            grad_b *= scale
            clip_count += 1

        first_w = beta1 * first_w + (1.0 - beta1) * grad_w
        second_w = beta2 * second_w + (1.0 - beta2) * (grad_w * grad_w)
        first_b = beta1 * first_b + (1.0 - beta1) * grad_b
        second_b = beta2 * second_b + (1.0 - beta2) * (grad_b * grad_b)
        corrected_first_w = first_w / (1.0 - beta1 ** step)
        corrected_second_w = second_w / (1.0 - beta2 ** step)
        corrected_first_b = first_b / (1.0 - beta1 ** step)
        corrected_second_b = second_b / (1.0 - beta2 ** step)
        if learning_rate > 0.0:
            weights -= learning_rate * corrected_first_w / (
                np.sqrt(corrected_second_w) + epsilon
            )
            bias -= learning_rate * corrected_first_b / (
                np.sqrt(corrected_second_b) + epsilon
            )
        if not np.isfinite(weights).all() or not np.isfinite(bias).all():
            raise ValueError("nonfinite receiver adapter parameters")

    train_mse_after = _mse(X @ weights + bias, Y)
    return weights, bias, {
        "gradient_norm": gradient_norm_max,
        "steps_executed": steps,
        "gradient_clip_count": clip_count,
        "effective_learning_rate": float(learning_rate),
        "train_mse_before": train_mse_before,
        "train_mse_after": train_mse_after,
    }


def create_learning_intents(train_windows, holdout_windows, active_record,
                            permissions, modulation, *, now=None):
    """Create one source-disjoint intent per B1/B2 adapter before its target fit."""
    if type(permissions) is not dict or type(modulation) is not dict:
        raise ValueError("learning-intent gates")
    if permissions.get("learning_enabled") is not True:
        raise PermissionError("learning intent requires learning_enabled")
    if permissions.get("optimizer_permission") is not True:
        raise PermissionError("learning intent requires optimizer_permission")
    if modulation.get("status") != "READY" or modulation.get("mode") not in {"SHADOW", "ACTIVE"}:
        raise PermissionError("learning intent neuromodulation gate")
    for key in ("eligibility", "modulator", "age_plasticity", "meta_plasticity",
                "proposed_scale", "learning_rate_scale", "mean_prediction_rmse", "delta"):
        if not _finite(modulation.get(key), minimum=0.0 if key != "proposed_scale" else -1.0):
            raise ValueError("learning intent modulation " + key)
    if type(modulation.get("trace_packets_written")) is not int or modulation["trace_packets_written"] < 0:
        raise ValueError("learning intent trace count")

    train_ids = _window_ids(train_windows)
    validation_ids = _window_ids(holdout_windows)
    if set(train_ids) & set(validation_ids):
        raise ValueError("learning intent train/validation window overlap")
    train_source_ids = _window_lineage_field_ids(
        train_windows, "lineage_source_ids", "source_ids"
    )
    validation_source_ids = _window_lineage_field_ids(
        holdout_windows, "lineage_source_ids", "source_ids"
    )
    train_source_hashes = _window_lineage_field_ids(
        train_windows, "lineage_source_sha256s", "source_sha256s", sha256=True
    )
    validation_source_hashes = _window_lineage_field_ids(
        holdout_windows, "lineage_source_sha256s", "source_sha256s", sha256=True
    )
    train_transitions = _window_field_ids(train_windows, "action_ids")
    validation_transitions = _window_field_ids(holdout_windows, "action_ids")
    if (
        set(train_source_ids) & set(validation_source_ids)
        or set(train_source_hashes) & set(validation_source_hashes)
        or set(train_transitions) & set(validation_transitions)
    ):
        raise ValueError("learning intent source/transition cohort overlap")

    old_retention_ids = []
    if active_record is not None:
        raw_retention_ids = active_record.get("holdout_window_ids", [])
        if raw_retention_ids:
            old_retention_ids = _unique(raw_retention_ids, "old retention ids")
    provenance = {
        "train_window_ids": train_ids,
        "validation_window_ids": validation_ids,
        "train_source_ids": train_source_ids,
        "train_source_sha256s": train_source_hashes,
        "validation_source_ids": validation_source_ids,
        "validation_source_sha256s": validation_source_hashes,
        "train_t8_transition_ids": train_transitions,
        "validation_t8_transition_ids": validation_transitions,
    }
    provenance_sha = _digest(provenance)
    timestamp = time.time() if now is None else float(now)
    if not math.isfinite(timestamp) or timestamp <= 0:
        raise ValueError("learning intent clock")
    consent_snapshot = {
        "learning_enabled": True,
        "optimizer_permission": True,
        "steps": permissions.get("steps"),
        "replay_mode": permissions.get("replay_mode"),
        "authority": "SHADOW_NO_AGE_ACTION",
    }
    if type(consent_snapshot["steps"]) is not int or consent_snapshot["steps"] < 1:
        raise ValueError("learning intent optimizer steps")
    if consent_snapshot["replay_mode"] not in {"uniform", "none"}:
        raise ValueError("learning intent replay mode")

    intents = {}
    for role in TARGET_ROLES:
        target_scope = role + ".temporal_receiver_head.weights+bias"
        identity = {
            "revision": REVISION,
            "target_organ": role,
            "target_model_revision": TARGET_ADAPTER_REVISION,
            "target_parameter_scope": target_scope,
            "provenance_sha256": provenance_sha,
            "optimizer_revision": OPTIMIZER_REVISION,
        }
        intent = {
            "schema": "v14.learning_intent.v1",
            "revision": REVISION,
            "intent_id": _digest(identity),
            "producer_organ": "WORLD_JEPA_TEMPORAL",
            "target_organ": role,
            "target_model_revision": TARGET_ADAPTER_REVISION,
            "target_parameter_scope": target_scope,
            "objective_revision": OBJECTIVE_REVISION,
            "optimizer_revision": OPTIMIZER_REVISION,
            "source_ids": train_source_ids,
            "source_sha256s": train_source_hashes,
            "t8_transition_ids": train_transitions,
            "validation_source_ids": validation_source_ids,
            "validation_source_sha256s": validation_source_hashes,
            "validation_t8_transition_ids": validation_transitions,
            "provenance_sha256": provenance_sha,
            "train_cohort_ids": train_ids,
            "validation_cohort_ids": validation_ids,
            "old_retention_cohort_ids": old_retention_ids,
            "consent_snapshot": consent_snapshot,
            "eligibility_trace": {
                "path_id": "world_predictor",
                "value": float(modulation["eligibility"]),
                "trace_packets_written": modulation["trace_packets_written"],
            },
            "prediction_error": {
                "mean_prediction_rmse": float(modulation["mean_prediction_rmse"]),
                "delta": float(modulation["delta"]),
            },
            "neuromodulation": {
                "mode": modulation["mode"],
                "status": modulation["status"],
                "modulator": float(modulation["modulator"]),
                "proposed_scale": float(modulation["proposed_scale"]),
                "learning_rate_scale": float(modulation["learning_rate_scale"]),
                "age_plasticity": float(modulation["age_plasticity"]),
                "meta_plasticity": float(modulation["meta_plasticity"]),
                "applied": modulation.get("applied") is True,
            },
            "gradient_budget": {
                "method": "BOUNDED_ADAM_MSE",
                "gradient_norm": None,
                "max_gradient_norm": MAX_GRADIENT_NORM,
                "max_steps": min(MAX_ADAPTER_STEPS, consent_snapshot["steps"]),
                "learning_rate_scale": float(modulation["learning_rate_scale"]),
                "base_learning_rate": BASE_ADAPTER_LEARNING_RATE,
                "anchor_strength": ANCHOR_STRENGTH,
                "beta1": ADAM_BETA1,
                "beta2": ADAM_BETA2,
                "epsilon": ADAM_EPSILON,
            },
            "age_capability": "SHADOW_ONLY_NO_NATIVE_BODY_RIGHT",
            "approval_id": None,
            "expires_at": timestamp + 600.0,
            "status": "PENDING_TARGET_OPTIMIZER",
            "authority": "NONE",
            "native_body_weights_changed": False,
            "target_adapter_parameters_changed": False,
            "consumer": CONSUMER,
        }
        validate_learning_intent(intent)
        intents[role] = intent
    return intents


def validate_learning_intent(intent):
    required = {
        "schema", "revision", "intent_id", "producer_organ", "target_organ",
        "target_model_revision", "target_parameter_scope", "objective_revision",
        "optimizer_revision", "source_ids", "source_sha256s", "t8_transition_ids",
        "validation_source_ids", "validation_source_sha256s",
        "validation_t8_transition_ids", "provenance_sha256", "train_cohort_ids",
        "validation_cohort_ids", "old_retention_cohort_ids", "consent_snapshot",
        "eligibility_trace", "prediction_error", "neuromodulation", "gradient_budget",
        "age_capability", "approval_id", "expires_at", "status", "authority",
        "native_body_weights_changed", "target_adapter_parameters_changed", "consumer",
    }
    optional = {
        "applied_credit_scale", "old_parameter_sha256", "new_parameter_sha256",
        "parameter_delta_norm", "parameter_count", "holdout_mse_before",
        "holdout_mse_after", "receiver_utility_pass", "consumer_eligible",
        "weight_delta_receipt_id", "checkpoint_sha256",
    }
    if (
        type(intent) is not dict or not required <= set(intent)
        or set(intent) - required - optional
    ):
        raise ValueError("learning intent shape")
    role = intent["target_organ"]
    if (
        intent["schema"] != "v14.learning_intent.v1"
        or intent["revision"] != REVISION
        or role not in TARGET_ROLES
        or intent["producer_organ"] != "WORLD_JEPA_TEMPORAL"
        or intent["target_model_revision"] != TARGET_ADAPTER_REVISION
        or intent["target_parameter_scope"] != role + ".temporal_receiver_head.weights+bias"
        or intent["objective_revision"] != OBJECTIVE_REVISION
        or intent["optimizer_revision"] not in {OPTIMIZER_REVISION, LEGACY_OPTIMIZER_REVISION}
        or intent["age_capability"] != "SHADOW_ONLY_NO_NATIVE_BODY_RIGHT"
        or intent["approval_id"] is not None
        or intent["authority"] != "NONE"
        or intent["native_body_weights_changed"] is not False
        or intent["consumer"] != CONSUMER
        or intent["status"] not in {
            "PENDING_TARGET_OPTIMIZER", "SHADOW_ADAPTER_UPDATED", "SHADOW_ADAPTER_UNCHANGED",
        }
        or type(intent["target_adapter_parameters_changed"]) is not bool
        or not _finite(intent["expires_at"], minimum=0.0)
    ):
        raise ValueError("learning intent contract")
    _sha(intent["intent_id"])
    _sha(intent["provenance_sha256"])
    source_ids = _unique(intent["source_ids"], "source ids")
    source_hashes = _unique(intent["source_sha256s"], "source hashes", sha256=True)
    transitions = _unique(intent["t8_transition_ids"], "transition ids")
    validation_sources = _unique(intent["validation_source_ids"], "validation source ids")
    validation_hashes = _unique(intent["validation_source_sha256s"], "validation source hashes", sha256=True)
    validation_transitions = _unique(intent["validation_t8_transition_ids"], "validation transition ids")
    train_cohorts = _unique(intent["train_cohort_ids"], "train cohort ids")
    validation_cohorts = _unique(intent["validation_cohort_ids"], "validation cohort ids")
    if (
        set(source_ids) & set(validation_sources)
        or set(source_hashes) & set(validation_hashes)
        or set(transitions) & set(validation_transitions)
        or set(train_cohorts) & set(validation_cohorts)
    ):
        raise ValueError("learning intent cohort leakage")
    provenance = {
        "train_window_ids": train_cohorts,
        "validation_window_ids": validation_cohorts,
        "train_source_ids": source_ids,
        "train_source_sha256s": source_hashes,
        "validation_source_ids": validation_sources,
        "validation_source_sha256s": validation_hashes,
        "train_t8_transition_ids": transitions,
        "validation_t8_transition_ids": validation_transitions,
    }
    if _digest(provenance) != intent["provenance_sha256"]:
        raise ValueError("learning intent provenance digest")
    identity = {
        "revision": REVISION,
        "target_organ": role,
        "target_model_revision": TARGET_ADAPTER_REVISION,
        "target_parameter_scope": role + ".temporal_receiver_head.weights+bias",
        "provenance_sha256": intent["provenance_sha256"],
    }
    if intent["optimizer_revision"] == OPTIMIZER_REVISION:
        identity["optimizer_revision"] = OPTIMIZER_REVISION
    if _digest(identity) != intent["intent_id"]:
        raise ValueError("learning intent identity digest")
    _unique(intent["old_retention_cohort_ids"], "old retention cohort ids") if intent["old_retention_cohort_ids"] else None
    consent = intent["consent_snapshot"]
    if (
        type(consent) is not dict or consent.get("learning_enabled") is not True
        or consent.get("optimizer_permission") is not True
        or consent.get("authority") != "SHADOW_NO_AGE_ACTION"
        or type(consent.get("steps")) is not int or consent["steps"] < 1
        or consent.get("replay_mode") not in {"uniform", "none"}
    ):
        raise ValueError("learning intent consent snapshot")
    eligibility = intent["eligibility_trace"]
    error = intent["prediction_error"]
    modulation = intent["neuromodulation"]
    budget = intent["gradient_budget"]
    if (
        type(eligibility) is not dict or eligibility.get("path_id") != "world_predictor"
        or not _finite(eligibility.get("value"), minimum=0.0, maximum=1.0)
        or type(eligibility.get("trace_packets_written")) is not int
        or eligibility["trace_packets_written"] < 0
        or type(error) is not dict
        or not _finite(error.get("mean_prediction_rmse"), minimum=0.0)
        or not _finite(error.get("delta"), minimum=0.0, maximum=1.0)
        or type(modulation) is not dict
        or modulation.get("mode") not in {"SHADOW", "ACTIVE"}
        or modulation.get("status") != "READY"
        or not _finite(modulation.get("modulator"), minimum=0.0, maximum=1.0)
        or not _finite(modulation.get("proposed_scale"), minimum=-1.0, maximum=1.0)
        or not _finite(modulation.get("learning_rate_scale"), minimum=0.0, maximum=1.0)
        or not _finite(modulation.get("age_plasticity"), minimum=0.0, maximum=1.0)
        or not _finite(modulation.get("meta_plasticity"), minimum=0.0, maximum=1.0)
        or type(modulation.get("applied")) is not bool
        or type(budget) is not dict
        or not _finite(budget.get("learning_rate_scale"), minimum=0.0, maximum=1.0)
    ):
        raise ValueError("learning intent learning signals")
    if intent["optimizer_revision"] == LEGACY_OPTIMIZER_REVISION:
        if (
            budget.get("method") != "CLOSED_FORM_RIDGE"
            or budget.get("gradient_norm") is not None
            or budget.get("max_gradient_norm") is not None
            or budget.get("max_steps") != 1
        ):
            raise ValueError("learning intent legacy optimizer budget")
    else:
        if (
            budget.get("method") != "BOUNDED_ADAM_MSE"
            or (budget.get("gradient_norm") is not None
                and not _finite(budget.get("gradient_norm"), minimum=0.0))
            or not _finite(budget.get("max_gradient_norm"), minimum=0.01, maximum=10.0)
            or type(budget.get("max_steps")) is not int
            or not 1 <= budget["max_steps"] <= MAX_ADAPTER_STEPS
            or not _finite(budget.get("base_learning_rate"), minimum=0.000001, maximum=0.1)
            or not _finite(budget.get("anchor_strength"), minimum=0.0, maximum=1.0)
            or not _finite(budget.get("beta1"), minimum=0.0, maximum=0.999)
            or not _finite(budget.get("beta2"), minimum=0.0, maximum=0.9999)
            or not _finite(budget.get("epsilon"), minimum=1e-12, maximum=1e-4)
        ):
            raise ValueError("learning intent gradient optimizer budget")
        if "steps_executed" in budget and (
            type(budget["steps_executed"]) is not int
            or not 0 <= budget["steps_executed"] <= budget["max_steps"]
        ):
            raise ValueError("learning intent gradient steps")
        if "gradient_clip_count" in budget and (
            type(budget["gradient_clip_count"]) is not int
            or budget["gradient_clip_count"] < 0
            or budget["gradient_clip_count"] > budget.get("steps_executed", budget["max_steps"])
        ):
            raise ValueError("learning intent gradient clip count")
        if "effective_learning_rate" in budget and not _finite(
            budget["effective_learning_rate"], minimum=0.0, maximum=budget["base_learning_rate"]
        ):
            raise ValueError("learning intent effective learning rate")
    if "applied_credit_scale" in intent and not _finite(intent["applied_credit_scale"], minimum=0.0, maximum=1.0):
        raise ValueError("learning intent applied credit")
    if "old_parameter_sha256" in intent and intent["old_parameter_sha256"] is not None:
        _sha(intent["old_parameter_sha256"])
    if "new_parameter_sha256" in intent:
        _sha(intent["new_parameter_sha256"])
    if "parameter_delta_norm" in intent and not _finite(intent["parameter_delta_norm"], minimum=0.0):
        raise ValueError("learning intent parameter delta")
    if "parameter_count" in intent and (type(intent["parameter_count"]) is not int or intent["parameter_count"] < 1):
        raise ValueError("learning intent parameter count")
    for key in ("holdout_mse_before", "holdout_mse_after"):
        if key in intent and not _finite(intent[key], minimum=0.0):
            raise ValueError("learning intent holdout metric")
    for key in ("receiver_utility_pass", "consumer_eligible"):
        if key in intent and type(intent[key]) is not bool:
            raise ValueError("learning intent receiver gate")
    for key in ("weight_delta_receipt_id", "checkpoint_sha256"):
        if key in intent:
            _sha(intent[key])
    return True


def fit_role_receivers_with_intents(intents, model, train_arrays, holdout_arrays,
                                    train_rows, holdout_rows, active_record, modulation):
    """Target-organ optimizer for B1/B2's bounded float receiver heads.

    The same source-disjoint ridge objective as the previous receiver is retained.
    SHADOW preserves the full baseline fit; ACTIVE blends only by the approved
    local neuromodulation scale. No native GGUF/body tensor is written.
    """
    if type(intents) is not dict or set(intents) != set(TARGET_ROLES):
        raise ValueError("B1/B2 LearningIntent set")
    expected_provenance = {
        "train_window_ids": _window_ids(train_rows),
        "validation_window_ids": _window_ids(holdout_rows),
        "train_source_ids": _window_field_ids(train_rows, "source_ids"),
        "train_source_sha256s": _window_field_ids(train_rows, "source_sha256s", sha256=True),
        "validation_source_ids": _window_field_ids(holdout_rows, "source_ids"),
        "validation_source_sha256s": _window_field_ids(holdout_rows, "source_sha256s", sha256=True),
        "train_t8_transition_ids": _window_field_ids(train_rows, "action_ids"),
        "validation_t8_transition_ids": _window_field_ids(holdout_rows, "action_ids"),
    }
    expected_provenance_sha = _digest(expected_provenance)
    for role in TARGET_ROLES:
        validate_learning_intent(intents[role])
        if intents[role]["target_organ"] != role:
            raise ValueError("LearningIntent target-organ binding mismatch")
        if intents[role]["provenance_sha256"] != expected_provenance_sha:
            raise ValueError("LearningIntent source cohort binding mismatch")
        if intents[role]["status"] != "PENDING_TARGET_OPTIMIZER":
            raise ValueError("LearningIntent already consumed")
        if intents[role]["expires_at"] <= time.time():
            raise PermissionError("LearningIntent expired")
    z_train, _ = model.predict(train_arrays[0], train_arrays[1])
    z_holdout, _ = model.predict(holdout_arrays[0], holdout_arrays[1])
    y_train = np.asarray([row["y"] for row in train_rows], dtype=np.float64)
    y_holdout = np.asarray([row["y"] for row in holdout_rows], dtype=np.float64)
    if (
        z_train.ndim != 2 or z_holdout.ndim != 2
        or len(z_train) != len(y_train) or len(z_holdout) != len(y_holdout)
        or not np.isfinite(z_train).all() or not np.isfinite(z_holdout).all()
        or not np.isfinite(y_train).all() or not np.isfinite(y_holdout).all()
    ):
        raise ValueError("LearningIntent receiver data")
    heads, metrics, delta_meta = {}, {}, {}
    old_heads = active_record.get("receiver_heads", {}) if active_record else {}
    for role, indices in ROLE_TARGETS.items():
        target_train = y_train[:, indices]
        target_holdout = y_holdout[:, indices]
        ridge_weights, ridge_bias = _ridge_head(z_train, target_train)
        old_head = old_heads.get(role)
        if old_head is not None:
            old_weights, old_bias = _head_parameters(old_head)
            if old_weights.shape != ridge_weights.shape or old_bias.shape != ridge_bias.shape:
                raise ValueError("prior receiver adapter shape mismatch")
            old_prediction = z_holdout @ old_weights + old_bias
            old_mse = _mse(old_prediction, target_holdout)
            old_sha = _head_sha(old_head)
        else:
            old_weights = np.zeros_like(ridge_weights)
            old_bias = np.zeros_like(ridge_bias)
            old_mse = _mse(
                np.tile(target_train.mean(axis=0), (len(target_holdout), 1)),
                target_holdout,
            )
            old_sha = None

        gradient = None
        if role in TARGET_ROLES:
            intent = intents[role]
            if intent["optimizer_revision"] != OPTIMIZER_REVISION:
                raise ValueError("new target optimizer requires ADAM_MSE_V1 intent")
            credit_scale = (
                1.0 if modulation["mode"] == "SHADOW"
                else max(0.0, min(1.0, float(intent["neuromodulation"]["proposed_scale"])))
            )
            budget = intent["gradient_budget"]
            effective_lr = (
                float(budget["base_learning_rate"])
                * float(budget["learning_rate_scale"])
                * credit_scale
            )
            weights, bias, gradient = _adam_head(
                z_train, target_train, old_weights, old_bias,
                steps=int(budget["max_steps"]),
                learning_rate=effective_lr,
                max_gradient_norm=float(budget["max_gradient_norm"]),
                anchor_strength=float(budget["anchor_strength"]),
                beta1=float(budget["beta1"]),
                beta2=float(budget["beta2"]),
                epsilon=float(budget["epsilon"]),
            )
            budget["gradient_norm"] = float(gradient["gradient_norm"])
            budget["steps_executed"] = int(gradient["steps_executed"])
            budget["gradient_clip_count"] = int(gradient["gradient_clip_count"])
            budget["effective_learning_rate"] = float(gradient["effective_learning_rate"])
            intent["applied_credit_scale"] = credit_scale
        else:
            # SELF keeps its prior closed-form shadow readout; B1/B2 alone use
            # the explicit gradient-backed target-organ optimizer.
            weights, bias = ridge_weights, ridge_bias

        prediction = z_holdout @ weights + bias
        mean_prediction = np.tile(target_train.mean(axis=0), (len(target_holdout), 1))
        zero_latent_prediction = np.tile(bias, (len(target_holdout), 1))
        shuffled_prediction = np.roll(z_holdout, 1, axis=0) @ weights + bias
        prefix = role.lower()
        metrics[prefix + "_holdout_mse"] = _mse(prediction, target_holdout)
        metrics[prefix + "_mean_baseline_mse"] = _mse(mean_prediction, target_holdout)
        metrics[prefix + "_zero_latent_mse"] = _mse(zero_latent_prediction, target_holdout)
        metrics[prefix + "_shuffled_latent_mse"] = _mse(shuffled_prediction, target_holdout)
        metrics[prefix + "_gain_vs_mean"] = (
            metrics[prefix + "_mean_baseline_mse"] - metrics[prefix + "_holdout_mse"]
        )
        head = {
            "target_indices": list(indices),
            "weights": weights.tolist(),
            "bias": bias.tolist(),
        }
        heads[role] = head
        if role in TARGET_ROLES:
            metrics[prefix + "_prior_adapter_mse"] = float(old_mse)
            metrics[prefix + "_ridge_control_mse"] = _mse(
                z_holdout @ ridge_weights + ridge_bias, target_holdout
            )
            metrics[prefix + "_gradient_norm"] = float(gradient["gradient_norm"])
            metrics[prefix + "_gradient_steps"] = int(gradient["steps_executed"])
            metrics[prefix + "_gradient_clip_count"] = int(gradient["gradient_clip_count"])
            metrics[prefix + "_train_mse_before"] = float(gradient["train_mse_before"])
            metrics[prefix + "_train_mse_after"] = float(gradient["train_mse_after"])
            new_params = np.concatenate((weights.reshape(-1), bias.reshape(-1)))
            old_params = np.concatenate((old_weights.reshape(-1), old_bias.reshape(-1)))
            delta_norm = float(np.linalg.norm(new_params - old_params))
            intent["old_parameter_sha256"] = old_sha
            intent["new_parameter_sha256"] = _head_sha(head)
            intent["parameter_delta_norm"] = delta_norm
            intent["parameter_count"] = int(new_params.size)
            intent["holdout_mse_before"] = float(old_mse)
            intent["holdout_mse_after"] = float(metrics[prefix + "_holdout_mse"])
            intent["target_adapter_parameters_changed"] = bool(delta_norm > 1e-12)
            delta_meta[role] = {
                "old_parameter_sha256": old_sha,
                "new_parameter_sha256": intent["new_parameter_sha256"],
                "parameter_delta_norm": delta_norm,
                "parameter_count": int(new_params.size),
                "holdout_mse_before": float(old_mse),
                "holdout_mse_after": float(metrics[prefix + "_holdout_mse"]),
                "gradient_norm": float(gradient["gradient_norm"]),
                "gradient_steps": int(gradient["steps_executed"]),
                "gradient_clip_count": int(gradient["gradient_clip_count"]),
            }
    gates = {role: receiver_utility_gate(metrics, role) for role in ROLE_TARGETS}
    for role in TARGET_ROLES:
        intents[role]["receiver_utility_pass"] = gates[role]["accepted"] is True
        intents[role]["consumer_eligible"] = (
            gates[role]["accepted"] is True
            and intents[role]["target_adapter_parameters_changed"] is True
        )
        intents[role]["status"] = (
            "SHADOW_ADAPTER_UPDATED"
            if intents[role]["target_adapter_parameters_changed"]
            else "SHADOW_ADAPTER_UNCHANGED"
        )
        validate_learning_intent(intents[role])
    return heads, metrics, gates, intents, delta_meta


def finalize_weight_delta_receipts(intents, delta_meta, receiver_metrics,
                                   receiver_gates, checkpoint_sha256, world_metrics):
    """Bind the target adapter diffs to the exact persisted WorldJEPA checkpoint."""
    _sha(checkpoint_sha256)
    receipts = {}
    finalized = {}
    for role in TARGET_ROLES:
        intent = dict(intents[role])
        validate_learning_intent(intent)
        meta = delta_meta[role]
        prefix = role.lower()
        if intent["optimizer_revision"] == LEGACY_OPTIMIZER_REVISION:
            payload = {
                "schema": "v14.weight_delta_receipt.v1",
                "intent_id": intent["intent_id"],
                "producer_organ": intent["producer_organ"],
                "target_organ": role,
                "target_model_revision": intent["target_model_revision"],
                "target_parameter_scope": intent["target_parameter_scope"],
                "source_provenance_sha256": intent["provenance_sha256"],
                "old_parameter_sha256": meta["old_parameter_sha256"],
                "new_parameter_sha256": meta["new_parameter_sha256"],
                "parameter_delta_norm": meta["parameter_delta_norm"],
                "parameter_count": meta["parameter_count"],
                "gradient_norm": None,
                "gradient_measured": False,
                "holdout_mse_before": meta["holdout_mse_before"],
                "holdout_mse_after": meta["holdout_mse_after"],
                "mean_baseline_mse": float(receiver_metrics[prefix + "_mean_baseline_mse"]),
                "zero_latent_mse": float(receiver_metrics[prefix + "_zero_latent_mse"]),
                "shuffled_latent_mse": float(receiver_metrics[prefix + "_shuffled_latent_mse"]),
                "receiver_utility_pass": receiver_gates[role]["accepted"] is True,
                "world_retention_pass": world_metrics.get("retention_pass") is True,
                "world_retention_mse_before": world_metrics.get("retention_mse_before", []),
                "world_retention_mse_after": world_metrics.get("retention_mse_after", []),
                "target_adapter_retention": "NOT_MEASURED",
                "optimizer_revision": intent["optimizer_revision"],
                "checkpoint_sha256": checkpoint_sha256,
                "consumer": intent["consumer"],
                "target_adapter_parameters_changed": intent["target_adapter_parameters_changed"],
                "native_body_weights_changed": False,
                "approval_id": None,
                "decision_authority": "NONE",
                "status": "SHADOW_RECEIPT",
            }
        else:
            payload = {
                "schema": "v14.weight_delta_receipt.v2",
                "intent_id": intent["intent_id"],
                "producer_organ": intent["producer_organ"],
                "target_organ": role,
                "target_model_revision": intent["target_model_revision"],
                "target_parameter_scope": intent["target_parameter_scope"],
                "source_provenance_sha256": intent["provenance_sha256"],
                "old_parameter_sha256": meta["old_parameter_sha256"],
                "new_parameter_sha256": meta["new_parameter_sha256"],
                "parameter_delta_norm": meta["parameter_delta_norm"],
                "parameter_count": meta["parameter_count"],
                "gradient_norm": float(meta["gradient_norm"]),
                "gradient_measured": True,
                "gradient_steps": int(meta["gradient_steps"]),
                "gradient_clip_count": int(meta["gradient_clip_count"]),
                "holdout_mse_before": meta["holdout_mse_before"],
                "holdout_mse_after": meta["holdout_mse_after"],
                "mean_baseline_mse": float(receiver_metrics[prefix + "_mean_baseline_mse"]),
                "zero_latent_mse": float(receiver_metrics[prefix + "_zero_latent_mse"]),
                "shuffled_latent_mse": float(receiver_metrics[prefix + "_shuffled_latent_mse"]),
                "receiver_utility_pass": receiver_gates[role]["accepted"] is True,
                "world_retention_pass": world_metrics.get("retention_pass") is True,
                "world_retention_mse_before": world_metrics.get("retention_mse_before", []),
                "world_retention_mse_after": world_metrics.get("retention_mse_after", []),
                "target_adapter_retention": "NOT_MEASURED",
                "optimizer_revision": intent["optimizer_revision"],
                "checkpoint_sha256": checkpoint_sha256,
                "consumer": intent["consumer"],
                "target_adapter_parameters_changed": intent["target_adapter_parameters_changed"],
                "native_body_weights_changed": False,
                "approval_id": None,
                "decision_authority": "NONE",
                "status": "SHADOW_RECEIPT",
            }
        receipt = dict(payload)
        receipt["receipt_id"] = _digest(payload)
        validate_weight_delta_receipt(receipt)
        intent["weight_delta_receipt_id"] = receipt["receipt_id"]
        intent["checkpoint_sha256"] = checkpoint_sha256
        validate_learning_intent(intent)
        receipts[role] = receipt
        finalized[role] = intent
    return finalized, receipts


def validate_weight_delta_receipt(receipt):
    base_required = {
        "schema", "receipt_id", "intent_id", "producer_organ", "target_organ",
        "target_model_revision", "target_parameter_scope", "source_provenance_sha256",
        "old_parameter_sha256", "new_parameter_sha256", "parameter_delta_norm",
        "parameter_count", "gradient_norm", "gradient_measured", "holdout_mse_before",
        "holdout_mse_after", "mean_baseline_mse", "zero_latent_mse",
        "shuffled_latent_mse", "receiver_utility_pass", "world_retention_pass",
        "world_retention_mse_before", "world_retention_mse_after",
        "target_adapter_retention", "optimizer_revision", "checkpoint_sha256",
        "consumer", "target_adapter_parameters_changed", "native_body_weights_changed",
        "approval_id", "decision_authority", "status",
    }
    gradient_fields = {"gradient_steps", "gradient_clip_count"}
    if type(receipt) is not dict:
        raise ValueError("weight delta receipt shape")
    legacy = (
        receipt.get("schema") == "v14.weight_delta_receipt.v1"
        and set(receipt) == base_required
        and receipt.get("optimizer_revision") == LEGACY_OPTIMIZER_REVISION
    )
    gradient = (
        receipt.get("schema") == "v14.weight_delta_receipt.v2"
        and set(receipt) == base_required | gradient_fields
        and receipt.get("optimizer_revision") == OPTIMIZER_REVISION
    )
    if not (legacy or gradient):
        raise ValueError("weight delta receipt shape")
    role = receipt["target_organ"]
    if (
        role not in TARGET_ROLES
        or receipt["producer_organ"] != "WORLD_JEPA_TEMPORAL"
        or receipt["target_model_revision"] != TARGET_ADAPTER_REVISION
        or receipt["target_parameter_scope"] != role + ".temporal_receiver_head.weights+bias"
        or receipt["consumer"] != CONSUMER
        or receipt["target_adapter_retention"] != "NOT_MEASURED"
        or receipt["approval_id"] is not None
        or receipt["native_body_weights_changed"] is not False
        or receipt["decision_authority"] != "NONE"
        or receipt["status"] != "SHADOW_RECEIPT"
        or type(receipt["receiver_utility_pass"]) is not bool
        or type(receipt["world_retention_pass"]) is not bool
        or type(receipt["target_adapter_parameters_changed"]) is not bool
        or type(receipt["parameter_count"]) is not int or receipt["parameter_count"] < 1
        or not _finite(receipt["parameter_delta_norm"], minimum=0.0)
    ):
        raise ValueError("weight delta receipt contract")
    if legacy:
        if receipt["gradient_norm"] is not None or receipt["gradient_measured"] is not False:
            raise ValueError("legacy receipt gradient contract")
    else:
        if (
            not _finite(receipt["gradient_norm"], minimum=0.0)
            or receipt["gradient_measured"] is not True
            or type(receipt["gradient_steps"]) is not int
            or not 1 <= receipt["gradient_steps"] <= MAX_ADAPTER_STEPS
            or type(receipt["gradient_clip_count"]) is not int
            or not 0 <= receipt["gradient_clip_count"] <= receipt["gradient_steps"]
        ):
            raise ValueError("gradient receipt contract")
    _sha(receipt["receipt_id"])
    _sha(receipt["intent_id"])
    _sha(receipt["source_provenance_sha256"])
    _sha(receipt["new_parameter_sha256"])
    _sha(receipt["checkpoint_sha256"])
    if receipt["old_parameter_sha256"] is not None:
        _sha(receipt["old_parameter_sha256"])
    for key in (
        "holdout_mse_before", "holdout_mse_after", "mean_baseline_mse",
        "zero_latent_mse", "shuffled_latent_mse",
    ):
        if not _finite(receipt[key], minimum=0.0):
            raise ValueError("weight delta receipt metric")
    for key in ("world_retention_mse_before", "world_retention_mse_after"):
        value = receipt[key]
        if type(value) is not list or any(not _finite(item, minimum=0.0) for item in value):
            raise ValueError("weight delta receipt retention")
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if _digest(payload) != receipt["receipt_id"]:
        raise ValueError("weight delta receipt digest")
    return True
