"""Tiny source-bound A4 utility predictor.

This is a bounded linear reward-prediction head, not a contextual-bandit
exploration policy and not a backbone model. It is trained from completed
AttentionResponse outcomes, remains shadow-only unless the parent Attention
policy is explicitly switched ACTIVE, and can be rolled back independently.
"""
from __future__ import annotations

import math
import time
from typing import Mapping, Sequence

FEATURE_REVISION = "a4-attention-features-v1"
HEAD_REVISION = "a4-attention-utility-head-v1"
FEATURE_NAMES = (
    "priority", "budget_norm",
    "gain_perceptual", "gain_callosum", "gain_workspace", "gain_focal", "gain_action",
    "source_bound", "teacher_view", "high_res", "span_norm", "ref_count_norm",
    "requester_JEF", "requester_B1", "requester_B2", "requester_SALIENCE",
    "requester_WORLD", "requester_A4", "requester_TEACHER", "requester_OTHER",
    "target_A_SOURCE", "target_B1", "target_B2", "target_MEMORY", "target_WORLD", "target_TOOL", "target_SELF", "target_OTHER",
    "reason_novelty", "reason_conflict", "reason_exactness", "reason_goal", "reason_verify", "reason_recall", "reason_OTHER",
)
REQUESTERS = ("JEF", "B1", "B2", "SALIENCE", "WORLD", "A4", "TEACHER")
TARGETS = ("A_SOURCE", "B1", "B2", "MEMORY", "WORLD", "TOOL", "SELF")
REASONS = ("novelty", "conflict", "exactness", "goal", "verify", "recall")
GAIN_NAMES = ("perceptual", "callosum", "workspace", "focal", "action")
EVENT_BUDGET = 1024
LEARNING_RATE = 0.08
MAX_UPDATE_NORM = 0.05
MAX_WEIGHT = 2.0
MIN_PREDICTION_N = 4
MAX_CHECKPOINTS = 8


class PolicyHeadError(ValueError):
    pass


def _clamp(value: float, low: float, high: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise PolicyHeadError("policy head value must be finite")
    return max(low, min(high, value))


def build_features(*, requester: str, target: str, reason: str, priority: float,
                   budget: int, resolution: str, source_ref, refs: Sequence,
                   gains: Mapping[str, float]) -> list[float]:
    if type(requester) is not str or not requester or type(target) is not str or not target or type(reason) is not str or not reason:
        raise PolicyHeadError("attention feature categories must be non-empty strings")
    if isinstance(budget, bool) or type(budget) not in (int, float) or not math.isfinite(float(budget)) or budget < 1:
        raise PolicyHeadError("attention budget must be a positive finite number")
    if not isinstance(gains, Mapping) or any(name not in gains for name in GAIN_NAMES):
        raise PolicyHeadError("attention gain snapshot is incomplete")
    refs = tuple(refs or ())
    values = [
        _clamp(priority, 0.0, 1.0),
        _clamp(math.log1p(min(budget, EVENT_BUDGET)) / math.log1p(EVENT_BUDGET), 0.0, 1.0),
    ]
    values.extend(_clamp(gains[name], 0.0, 1.0) for name in GAIN_NAMES)
    span = 0
    if source_ref is not None:
        if not isinstance(source_ref, Mapping):
            raise PolicyHeadError("SourceRef must be a mapping")
        start, end = source_ref.get("char_start"), source_ref.get("char_end")
        if type(start) is int and type(end) is int and 0 <= start <= end:
            span = end - start
        else:
            start, end = source_ref.get("start_ms"), source_ref.get("end_ms")
            if type(start) is int and type(end) is int and 0 <= start <= end:
                span = end - start
            else:
                start, end = source_ref.get("frame_start"), source_ref.get("frame_end")
                if type(start) is int and type(end) is int and 0 <= start <= end:
                    span = end - start
    values.extend([
        1.0 if source_ref is not None or bool(refs) else 0.0,
        1.0 if resolution == "teacher_view" else 0.0,
        1.0 if resolution == "high_res" else 0.0,
        _clamp(span / 4096.0, 0.0, 1.0),
        _clamp(len(refs) / 4.0, 0.0, 1.0),
    ])
    values.extend(1.0 if requester == name else 0.0 for name in REQUESTERS)
    values.append(1.0 if requester not in REQUESTERS else 0.0)
    values.extend(1.0 if target == name else 0.0 for name in TARGETS)
    values.append(1.0 if target not in TARGETS else 0.0)
    values.extend(1.0 if reason == name else 0.0 for name in REASONS)
    values.append(1.0 if reason not in REASONS else 0.0)
    return validate_features(values)


def validate_features(features: Sequence[float]) -> list[float]:
    if not isinstance(features, (list, tuple)) or len(features) != len(FEATURE_NAMES):
        raise PolicyHeadError("attention feature vector geometry mismatch")
    out = []
    for value in features:
        if type(value) not in (int, float):
            raise PolicyHeadError("attention feature vector must be numeric")
        out.append(_clamp(value, 0.0, 1.0))
    return out


def empty_head() -> dict:
    return {
        "revision": HEAD_REVISION,
        "weights": [0.0] * len(FEATURE_NAMES),
        "bias": 0.0,
        "n": 0,
        "updates": 0,
        "checkpoints": [],
        "last_update": None,
    }


def validate_head(head: Mapping) -> None:
    if not isinstance(head, Mapping) or head.get("revision") != HEAD_REVISION:
        raise PolicyHeadError("attention policy head revision mismatch")
    weights = head.get("weights")
    if not isinstance(weights, list) or len(weights) != len(FEATURE_NAMES):
        raise PolicyHeadError("attention policy head weight geometry mismatch")
    if any(type(value) not in (int, float) or not math.isfinite(float(value)) or abs(float(value)) > MAX_WEIGHT for value in weights):
        raise PolicyHeadError("attention policy head contains invalid weights")
    if type(head.get("bias")) not in (int, float) or not math.isfinite(float(head["bias"])) or abs(float(head["bias"])) > MAX_WEIGHT:
        raise PolicyHeadError("attention policy head bias is invalid")
    for key in ("n", "updates"):
        if type(head.get(key)) is not int or head[key] < 0:
            raise PolicyHeadError("attention policy head counters are invalid")
    checkpoints = head.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) > MAX_CHECKPOINTS:
        raise PolicyHeadError("attention policy head checkpoint list is invalid")


def _raw_prediction(head: Mapping, features: Sequence[float]) -> float:
    x = validate_features(features)
    z = float(head["bias"]) + sum(float(w) * value for w, value in zip(head["weights"], x))
    return math.tanh(z)


def predict(head: Mapping, features: Sequence[float] | None) -> float | None:
    validate_head(head)
    if features is None or head["n"] < MIN_PREDICTION_N:
        return None
    return _raw_prediction(head, features)


def update(head: dict, features: Sequence[float], target: float, *,
           modulator_scale: float, source_weight: float,
           response_packet_id: str, provenance_sha256: str,
           source_class: str) -> dict | None:
    """One bounded SGD step: eligibility=request features, error=reward residual,
    modulator=source weight, plasticity=N10 step factor.
    """
    validate_head(head)
    x = validate_features(features)
    target = _clamp(target, -1.0, 1.0)
    scale = _clamp(modulator_scale, 0.0, 1.0) * _clamp(source_weight, 0.0, 1.0)
    if scale <= 0.0:
        return None
    if type(response_packet_id) is not str or not response_packet_id:
        raise PolicyHeadError("response packet ID is required")
    if type(provenance_sha256) is not str or len(provenance_sha256) != 64:
        raise PolicyHeadError("provenance digest is required")
    prediction = _raw_prediction(head, x)
    error = target - prediction
    gradient = error * (1.0 - prediction * prediction)
    rate = LEARNING_RATE * scale
    delta = [rate * gradient * value for value in x]
    delta_bias = rate * gradient
    norm = math.sqrt(sum(value * value for value in delta) + delta_bias * delta_bias)
    if norm <= 1e-15:
        return None
    cap = min(1.0, MAX_UPDATE_NORM / norm)
    delta = [value * cap for value in delta]
    delta_bias *= cap
    checkpoint = {
        "weights": list(head["weights"]),
        "bias": float(head["bias"]),
        "n": head["n"],
        "updates": head["updates"],
        "last_update": head.get("last_update"),
        "response_packet_id": response_packet_id,
        "provenance_sha256": provenance_sha256,
        "source_class": source_class,
        "created_wall_time": time.time(),
    }
    head["checkpoints"] = (head["checkpoints"] + [checkpoint])[-MAX_CHECKPOINTS:]
    head["weights"] = [_clamp(w + d, -MAX_WEIGHT, MAX_WEIGHT) for w, d in zip(head["weights"], delta)]
    head["bias"] = _clamp(head["bias"] + delta_bias, -MAX_WEIGHT, MAX_WEIGHT)
    head["n"] += 1
    head["updates"] += 1
    applied_norm = math.sqrt(sum(value * value for value in delta) + delta_bias * delta_bias)
    head["last_update"] = {
        "response_packet_id": response_packet_id,
        "provenance_sha256": provenance_sha256,
        "source_class": source_class,
        "prediction_before": prediction,
        "target": target,
        "prediction_error": error,
        "modulator_scale": modulator_scale,
        "source_weight": source_weight,
        "applied_update_norm": applied_norm,
        "created_wall_time": time.time(),
    }
    validate_head(head)
    return dict(head["last_update"])


def rollback(head: dict, *, authority: str) -> dict:
    """Restore the last pre-update head checkpoint. Scalar priors/N10 packets are not rolled back."""
    if authority != "EXPLICIT_HUMAN":
        raise PermissionError("attention policy head rollback requires explicit human authority")
    validate_head(head)
    if not head["checkpoints"]:
        raise PolicyHeadError("no attention policy head checkpoint is available")
    checkpoint = head["checkpoints"].pop()
    head["weights"] = list(checkpoint["weights"])
    head["bias"] = float(checkpoint["bias"])
    head["n"] = checkpoint["n"]
    head["updates"] = checkpoint["updates"]
    head["last_update"] = {
        "rollback_of": checkpoint["response_packet_id"],
        "provenance_sha256": checkpoint["provenance_sha256"],
        "created_wall_time": time.time(),
    }
    validate_head(head)
    return dict(head["last_update"])


def report(head: Mapping) -> dict:
    validate_head(head)
    norm = math.sqrt(sum(float(value) ** 2 for value in head["weights"]) + float(head["bias"]) ** 2)
    return {
        "revision": head["revision"],
        "feature_revision": FEATURE_REVISION,
        "feature_count": len(FEATURE_NAMES),
        "n": head["n"],
        "updates": head["updates"],
        "weight_l2": round(norm, 8),
        "checkpoint_count": len(head["checkpoints"]),
        "last_update": head.get("last_update"),
        "prediction_ready": head["n"] >= MIN_PREDICTION_N,
        "learning_rate": LEARNING_RATE,
        "max_update_norm": MAX_UPDATE_NORM,
    }
