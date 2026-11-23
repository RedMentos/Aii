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
OPTIMIZER_REVISION = "RIDGE_CLOSED_FORM_V1"
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
                "method": "CLOSED_FORM_RIDGE",
                "gradient_norm": None,
                "max_gradient_norm": None,
                "max_steps": 1,
                "learning_rate_scale": float(modulation["learning_rate_scale"]),
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
        or intent["optimizer_revision"] != OPTIMIZER_REVISION
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
        or budget.get("method") != "CLOSED_FORM_RIDGE"
        or budget.get("gradient_norm") is not None
        or budget.get("max_gradient_norm") is not None
        or budget.get("max_steps") != 1
        or not _finite(budget.get("learning_rate_scale"), minimum=0.0, maximum=1.0)
    ):
        raise ValueError("learning intent learning signals")
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
        weights, bias = _ridge_head(z_train, target_train)
        old_head = old_heads.get(role)
        old_mse = None
        if old_head is not None:
            old_weights, old_bias = _head_parameters(old_head)
            if old_weights.shape != weights.shape or old_bias.shape != bias.shape:
                raise ValueError("prior receiver adapter shape mismatch")
            old_prediction = z_holdout @ old_weights + old_bias
            old_mse = _mse(old_prediction, target_holdout)
        if role in TARGET_ROLES:
            intent = intents[role]
            credit_scale = (
                1.0 if modulation["mode"] == "SHADOW"
                else max(0.0, min(1.0, float(intent["neuromodulation"]["proposed_scale"])))
            )
            if old_head is None:
                weights = weights * credit_scale
                bias = bias * credit_scale
                old_weights = np.zeros_like(weights)
                old_bias = np.zeros_like(bias)
                old_mse = _mse(
                    np.tile(target_train.mean(axis=0), (len(target_holdout), 1)),
                    target_holdout,
                )
                old_sha = None
            else:
                weights = old_weights + credit_scale * (weights - old_weights)
                bias = old_bias + credit_scale * (bias - old_bias)
                old_sha = _head_sha(old_head)
            intent["applied_credit_scale"] = credit_scale
        else:
            old_weights = np.asarray(old_head["weights"], dtype=np.float64) if old_head else np.zeros_like(weights)
            old_bias = np.asarray(old_head["bias"], dtype=np.float64) if old_head else np.zeros_like(bias)
            old_sha = _head_sha(old_head) if old_head else None
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
    required = {
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
    if type(receipt) is not dict or set(receipt) != required:
        raise ValueError("weight delta receipt shape")
    role = receipt["target_organ"]
    if (
        receipt["schema"] != "v14.weight_delta_receipt.v1"
        or role not in TARGET_ROLES
        or receipt["producer_organ"] != "WORLD_JEPA_TEMPORAL"
        or receipt["target_model_revision"] != TARGET_ADAPTER_REVISION
        or receipt["target_parameter_scope"] != role + ".temporal_receiver_head.weights+bias"
        or receipt["optimizer_revision"] != OPTIMIZER_REVISION
        or receipt["consumer"] != CONSUMER
        or receipt["target_adapter_retention"] != "NOT_MEASURED"
        or receipt["gradient_norm"] is not None
        or receipt["gradient_measured"] is not False
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
