"""Small NumPy STABLE-style drift governor for experimental WorldJEPA updates.

Independent adaptation of the paper's primal-dual idea; no upstream code copied.
Disabled unless the caller explicitly opts in.
"""
from __future__ import annotations
import math
import numpy as np

SCHEMA = "v14.world-jepa.stable-drift.v1"
GROUP_PREFIX = {"encoder": "e", "predictor": "p", "inverse": "i"}
_ALLOWED = {"enabled", "budget_sq", "dual_lr", "lambda_init", "lambda_max", "deadzone", "decay"}


def default_state():
    return {"schema": SCHEMA, "groups": {
        name: {"budget_sq": None, "dual_lambda": 0.0, "last_drift_sq": 0.0,
               "max_drift_sq": 0.0, "task_count": 0, "controlled_steps": 0}
        for name in GROUP_PREFIX
    }}


def _finite(value, strict=False):
    return (type(value) in (int, float) and not isinstance(value, bool)
            and math.isfinite(float(value)) and (float(value) > 0 if strict else float(value) >= 0))


def _number(value, name):
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("invalid WorldJEPA drift " + name)
    return float(value)


def validate_state(value=None):
    if value is None:
        return default_state()
    if type(value) is not dict or set(value) != {"schema", "groups"} or value["schema"] != SCHEMA:
        raise ValueError("invalid WorldJEPA drift state")
    if type(value["groups"]) is not dict or set(value["groups"]) != set(GROUP_PREFIX):
        raise ValueError("invalid WorldJEPA drift groups")
    result = default_state()
    fields = {"budget_sq", "dual_lambda", "last_drift_sq", "max_drift_sq", "task_count", "controlled_steps"}
    for name in GROUP_PREFIX:
        item = value["groups"][name]
        if type(item) is not dict or set(item) != fields:
            raise ValueError("invalid WorldJEPA drift group state")
        budget = item["budget_sq"]
        if budget is not None and not _finite(budget, strict=True):
            raise ValueError("invalid WorldJEPA drift budget")
        if (not _finite(item["dual_lambda"]) or not _finite(item["last_drift_sq"])
                or not _finite(item["max_drift_sq"])
                or type(item["task_count"]) is not int or item["task_count"] < 0
                or type(item["controlled_steps"]) is not int or item["controlled_steps"] < 0):
            raise ValueError("invalid WorldJEPA drift counters")
        result["groups"][name] = {
            "budget_sq": None if budget is None else float(budget),
            "dual_lambda": float(item["dual_lambda"]),
            "last_drift_sq": float(item["last_drift_sq"]),
            "max_drift_sq": float(item["max_drift_sq"]),
            "task_count": item["task_count"],
            "controlled_steps": item["controlled_steps"],
        }
    return result


def normalize_config(value=None):
    if value is None:
        value = {"enabled": False}
    if type(value) is not dict or set(value) - _ALLOWED:
        raise ValueError("invalid WorldJEPA drift config")
    enabled = value.get("enabled", False)
    if type(enabled) is not bool:
        raise ValueError("invalid WorldJEPA drift enabled flag")
    result = {
        "enabled": enabled,
        "budget_sq": value.get("budget_sq"),
        "dual_lr": _number(value.get("dual_lr", 0.03), "dual learning rate"),
        "lambda_init": _number(value.get("lambda_init", 1.0), "initial multiplier"),
        "lambda_max": _number(value.get("lambda_max", 100.0), "multiplier cap"),
        "deadzone": _number(value.get("deadzone", 0.05), "deadzone"),
        "decay": _number(value.get("decay", 0.95), "multiplier decay"),
    }
    if (result["dual_lr"] <= 0 or result["lambda_init"] < 0
            or result["lambda_max"] <= 0 or result["lambda_max"] < result["lambda_init"]
            or not 0 <= result["deadzone"] < 0.5 or not 0 < result["decay"] < 1):
        raise ValueError("invalid WorldJEPA drift hyperparameters")
    budget = result["budget_sq"]
    if isinstance(budget, dict):
        if set(budget) - set(GROUP_PREFIX):
            raise ValueError("invalid WorldJEPA group drift budget")
        checked = {}
        for name, raw in budget.items():
            if raw is not None and not _finite(raw, strict=True):
                raise ValueError("invalid WorldJEPA group drift budget")
            checked[name] = None if raw is None else float(raw)
        result["budget_sq"] = checked
    elif budget is not None:
        if not _finite(budget, strict=True):
            raise ValueError("invalid WorldJEPA drift budget")
        result["budget_sq"] = float(budget)
    return result


def _budget_for(config, name):
    budget = config["budget_sq"]
    return budget.get(name) if type(budget) is dict else budget


def _drift_sq(params, anchor):
    if set(params) != set(anchor):
        raise ValueError("WorldJEPA drift anchor layout mismatch")
    total = 0.0
    for key, current in params.items():
        current, prior = np.asarray(current), np.asarray(anchor[key])
        if current.shape != prior.shape or not np.isfinite(current).all() or not np.isfinite(prior).all():
            raise ValueError("WorldJEPA drift tensor mismatch")
        total += float(np.sum((current - prior) ** 2))
    if not math.isfinite(total):
        raise ValueError("nonfinite WorldJEPA parameter drift")
    return total


def prepare_task(state, config, params_by_group, *, has_prior_training):
    state, config = validate_state(state), normalize_config(config)
    if type(has_prior_training) is not bool or type(params_by_group) is not dict:
        raise ValueError("invalid WorldJEPA drift task")
    anchors, active, calibrating, lambdas = {}, set(), set(), {}
    next_state = validate_state(state)
    if not config["enabled"]:
        return {"state": next_state, "config": config, "anchors": anchors,
                "active": active, "calibrating": calibrating, "lambdas": lambdas}
    if set(params_by_group) != set(GROUP_PREFIX):
        raise ValueError("invalid WorldJEPA trainable groups")
    for name, params in params_by_group.items():
        if type(params) is not dict:
            raise ValueError("invalid WorldJEPA trainable group")
        if not params:
            continue
        override = _budget_for(config, name)
        if override is not None:
            next_state["groups"][name]["budget_sq"] = override
        anchors[name] = {key: np.array(value, copy=True) for key, value in params.items()}
        item = next_state["groups"][name]
        if not has_prior_training:
            calibrating.add(name)
            continue
        if item["budget_sq"] is None:
            if item["last_drift_sq"] > 0:
                item["budget_sq"] = item["last_drift_sq"]
            else:
                calibrating.add(name)
                continue
        active.add(name)
        lambdas[name] = item["dual_lambda"] if item["dual_lambda"] > 0 else config["lambda_init"]
    return {"state": next_state, "config": config, "anchors": anchors,
            "active": active, "calibrating": calibrating, "lambdas": lambdas}


def apply_pullback(params_by_group, gradients, prepared):
    result = dict(gradients)
    for name in prepared["active"]:
        for key, current in params_by_group[name].items():
            if key not in result:
                continue
            grad = np.asarray(result[key])
            if grad.shape != np.asarray(current).shape or not np.isfinite(grad).all():
                raise ValueError("invalid WorldJEPA drift gradient")
            result[key] = grad + 2.0 * prepared["lambdas"][name] * (
                current - prepared["anchors"][name][key]
            )
    return result


def update_dual(prepared, params_by_group):
    cfg = prepared["config"]
    for name in prepared["active"]:
        item = prepared["state"]["groups"][name]
        budget = item["budget_sq"]
        drift = _drift_sq(params_by_group[name], prepared["anchors"][name])
        item["max_drift_sq"] = max(item["max_drift_sq"], drift)
        if drift > budget * (1.0 + cfg["deadzone"]):
            prepared["lambdas"][name] = min(
                cfg["lambda_max"],
                prepared["lambdas"][name] + cfg["dual_lr"] * (drift / budget - 1.0),
            )
        elif drift < budget * (1.0 - cfg["deadzone"]):
            prepared["lambdas"][name] = max(0.0, prepared["lambdas"][name] * cfg["decay"])


def finish_task(prepared, params_by_group, *, steps):
    if type(steps) is not int or steps < 0:
        raise ValueError("invalid WorldJEPA drift step count")
    state = validate_state(prepared["state"])
    if not prepared["config"]["enabled"]:
        return state
    cfg = prepared["config"]
    for name, params in params_by_group.items():
        if not params or name not in prepared["anchors"]:
            continue
        item = state["groups"][name]
        drift = _drift_sq(params, prepared["anchors"][name])
        item["max_drift_sq"] = max(item["max_drift_sq"], drift)
        if name in prepared["calibrating"]:
            budget = _budget_for(cfg, name)
            item["budget_sq"] = float(max(drift, 1e-12) if budget is None else budget)
            item["dual_lambda"] = cfg["lambda_init"]
        elif name in prepared["active"]:
            item["dual_lambda"] = float(prepared["lambdas"][name])
            item["controlled_steps"] += steps
        item["last_drift_sq"] = float(drift)
        item["task_count"] += 1
    return validate_state(state)


def summary(state, *, enabled=False):
    checked = validate_state(state)
    return {"enabled": bool(enabled), "groups": {
        name: dict(item) for name, item in checked["groups"].items()
    }}
