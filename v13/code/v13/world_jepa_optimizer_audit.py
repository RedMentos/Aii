"""Read-only audit of persisted WorldJEPA parameters and optimizer resume state.

The audit is deliberately source-bound through the existing checkpoint loader.
It exposes hashes, norms and step counters only; never raw source text, receipt
payloads, optimizer arrays or native body weights.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

from . import world_jepa_shadow_checkpoint, world_jepa_training_state


def _checked_arrays(values, label):
    if type(values) is not dict or not values:
        raise ValueError(f"missing {label} arrays")
    result = {}
    for name, value in values.items():
        if type(name) is not str or not name or len(name) > 256:
            raise ValueError(f"invalid {label} array name")
        array = np.asarray(value)
        if (array.dtype.kind not in "fiu" or array.size == 0
                or not np.isfinite(array).all()):
            raise ValueError(f"invalid finite {label} array")
        result[name] = np.ascontiguousarray(array)
    return result


def _digest(arrays):
    digest = hashlib.sha256()
    for name, array in sorted(arrays.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _norm(arrays):
    total = math.fsum(
        float(np.sum(array.astype(np.float64, copy=False) ** 2, dtype=np.float64))
        for array in arrays.values()
    )
    if not math.isfinite(total) or total < 0:
        raise ValueError("nonfinite WorldJEPA audit norm")
    return math.sqrt(total)


def _model_groups(model):
    training = world_jepa_training_state.from_model(model)
    encoder = _checked_arrays(model.enc, "encoder")
    predictor = _checked_arrays({
        f"{index}:{name}": value
        for index, member in enumerate(model.preds)
        for name, value in member.items()
    }, "predictor")
    target = _checked_arrays(model.tgt, "EMA target")
    inverse = _checked_arrays(training["inverse"], "inverse dynamics")

    main = training["main"]
    main_moments = _checked_arrays({
        f"m:{name}": value for name, value in main["m"].items()
    } | {
        f"v:{name}": value for name, value in main["v"].items()
    }, "main optimizer moment")
    bootstrap_moments = {}
    for index, member in enumerate(training["bootstrap"]):
        adam = member["adam"]
        arrays = _checked_arrays({
            f"m:{name}": value for name, value in adam["m"].items()
        } | {
            f"v:{name}": value for name, value in adam["v"].items()
        }, "bootstrap optimizer moment")
        bootstrap_moments.update({f"{index}:{name}": value for name, value in arrays.items()})
    return training, {
        "encoder": encoder,
        "predictor": predictor,
        "ema_target": target,
        "inverse": inverse,
        "main_moments": main_moments,
        "bootstrap_moments": bootstrap_moments,
    }


def audit_model(model):
    """Validate one loaded model and return a bounded, JSON-safe audit record."""
    training, groups = _model_groups(model)
    parameter = {
        **{f"encoder:{key}": value for key, value in groups["encoder"].items()},
        **{f"predictor:{key}": value for key, value in groups["predictor"].items()},
    }
    optimizer = {
        **{f"main:{key}": value for key, value in groups["main_moments"].items()},
        **{f"bootstrap:{key}": value for key, value in groups["bootstrap_moments"].items()},
    }
    fit_steps = getattr(model, "_fit_steps", None)
    if type(fit_steps) is not int or fit_steps < 0:
        raise ValueError("invalid WorldJEPA fit step count")
    return {
        "status": "VERIFIED",
        "scope": "PRIVATE_WORLD_JEPA_SHADOW_ONLY",
        "fit_steps": fit_steps,
        "optimizer_origin": training["origin"],
        "optimizer_main_step": int(training["main"]["t"]),
        "optimizer_bootstrap_steps": [
            int(member["adam"]["t"]) for member in training["bootstrap"]
        ],
        "optimizer_state_present": True,
        "parameter_sha256": _digest(parameter),
        "ema_target_sha256": _digest(groups["ema_target"]),
        "inverse_sha256": _digest(groups["inverse"]),
        "optimizer_state_sha256": _digest(optimizer),
        "parameter_norm": _norm(parameter),
        "ema_target_norm": _norm(groups["ema_target"]),
        "optimizer_moment_norm": _norm(optimizer),
        "native_body_consumed": False,
        "native_body_weights_changed": False,
    }


def audit_checkpoint(path, source_sha256, expected_sha256):
    """Verify checkpoint bytes/provenance, then audit the restored optimizer."""
    model = world_jepa_shadow_checkpoint.load(path, source_sha256, expected_sha256)
    result = audit_model(model)
    result.update({
        "checkpoint_verified": True,
        "checkpoint_sha256": expected_sha256,
    })
    return result


def compare_models(before, after):
    """Return numeric parameter, EMA and optimizer-state deltas without exposing arrays."""
    _, left = _model_groups(before)
    _, right = _model_groups(after)
    deltas = {}
    for group in ("encoder", "predictor", "ema_target", "inverse",
                  "main_moments", "bootstrap_moments"):
        a, b = left[group], right[group]
        if set(a) != set(b):
            raise ValueError(f"WorldJEPA {group} structure changed during comparison")
        total = 0.0
        for name in sorted(a):
            if a[name].shape != b[name].shape:
                raise ValueError(f"WorldJEPA {group} shape changed during comparison")
            delta = b[name].astype(np.float64, copy=False) - a[name].astype(np.float64, copy=False)
            total += float(np.sum(delta * delta, dtype=np.float64))
        if not math.isfinite(total) or total < 0:
            raise ValueError(f"nonfinite WorldJEPA {group} delta")
        deltas[group + "_delta_norm"] = math.sqrt(total)
    deltas["parameter_delta_norm"] = math.sqrt(
        deltas["encoder_delta_norm"] ** 2 + deltas["predictor_delta_norm"] ** 2
    )
    deltas["optimizer_moment_delta_norm"] = math.sqrt(
        deltas["main_moments_delta_norm"] ** 2
        + deltas["bootstrap_moments_delta_norm"] ** 2
    )
    return deltas
