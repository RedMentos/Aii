"""Permission-gated runtime facade for the persistent WorldJEPA Store consumer.

This module is a deployable adapter API. It does not alter Runtime itself; Core
must call consume_after_commit after a committed T8 action and explicitly route
receiver_readouts to a real SHADOW consumer. Both local gates default closed.
The booleans in Store state are not an OS/security boundary.
"""
from pathlib import Path

from .world_jepa_consumer import WorldJEPAStoreConsumer

PERMISSION_KEY = "v14.world_jepa.permissions"
DEFAULT_PERMISSIONS = {
    "learning_enabled": False,
    "optimizer_permission": False,
    "steps": 40,
    "replay_mode": "uniform",
}
MAX_RUNTIME_PAGE = 256
MAX_RUNTIME_STEPS = 2000
RECEIVER_ROLES = ("B1_DETAIL", "B2_GIST", "SELF_MODEL")


def permission_state(store):
    """Read the two independent local gates; malformed values fail closed."""
    value, _ = store.state(PERMISSION_KEY, dict(DEFAULT_PERMISSIONS))
    if type(value) is not dict:
        value = {}
    learning_enabled = value.get("learning_enabled") is True
    optimizer_permission = value.get("optimizer_permission") is True
    steps = value.get("steps", DEFAULT_PERMISSIONS["steps"])
    if type(steps) is not int or not 1 <= steps <= MAX_RUNTIME_STEPS:
        steps = DEFAULT_PERMISSIONS["steps"]
    replay_mode = value.get("replay_mode", "uniform")
    if replay_mode not in ("uniform", "none"):
        replay_mode = "uniform"
    return {
        "learning_enabled": learning_enabled,
        "optimizer_permission": optimizer_permission,
        "steps": steps,
        "replay_mode": replay_mode,
    }


def _consumer(store, home, *, learning_enabled):
    root = Path(home if home is not None else store.home) / "world_jepa"
    current = getattr(store, "_v14_world_jepa_consumer", None)
    current_home = getattr(current, "home", None)
    if (current is None or current_home is None or Path(current_home) != root
            or (learning_enabled and getattr(current, "learning_enabled", False) is not True)):
        current = WorldJEPAStoreConsumer(
            store, root, learning_enabled=learning_enabled
        )
        setattr(store, "_v14_world_jepa_consumer", current)
    return current


def consume_after_commit(store, home=None, *, limit=64, cancel_check=None):
    """Run persistent JEPA only after a committed turn and only behind both gates."""
    if type(limit) is not int or not 16 <= limit <= MAX_RUNTIME_PAGE:
        raise ValueError("runtime page must be 16..256")
    if cancel_check is not None and not callable(cancel_check):
        raise ValueError("cancel_check must be callable")
    if cancel_check is not None and cancel_check():
        return {"status":"CANCELLED","decision_authority":"NONE",
                "native_body_consumed":False,"native_body_weights_changed":False}
    gates = permission_state(store)
    result = {
        "runtime_adapter_called": True,
        "learning_enabled": gates["learning_enabled"],
        "optimizer_permission": gates["optimizer_permission"],
        "decision_authority": "NONE",
        "native_body_consumed": False,
        "native_body_weights_changed": False,
    }
    if not gates["learning_enabled"]:
        result["status"] = "OFF"
        return result
    if not gates["optimizer_permission"]:
        result["status"] = "PENDING_OPTIMIZER_PERMISSION"
        return result
    try:
        learner = _consumer(store, home, learning_enabled=True)
        updated = learner.update(
            limit=limit,
            steps=gates["steps"],
            optimizer_permission=True,
            replay_mode=gates["replay_mode"],
            cancel_check=cancel_check,
        )
        result.update(updated)
        result.update({
            "runtime_adapter_called": True,
            "learning_enabled": True,
            "optimizer_permission": True,
            "decision_authority": "NONE",
            "native_body_consumed": False,
            "native_body_weights_changed": False,
        })
        return result
    except InterruptedError:
        result.update({"status":"CANCELLED","native_body_weights_changed":False})
        return result
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        result.update({"status": "ERROR", "error": type(exc).__name__})
        return result


def receiver_readout(store, role, state, action, home=None):
    """Read one persisted B1/B2/SELF numeric head as non-authoritative SHADOW data."""
    if role not in RECEIVER_ROLES:
        raise ValueError("unknown receiver role")
    try:
        learner = _consumer(store, home, learning_enabled=False)
        value = learner.readout(role, state, action)
        value.update({
            "decision_authority": "NONE",
            "native_body_consumed": False,
            "native_body_weights_changed": False,
        })
        return value
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        status = "NO_CHECKPOINT" if "checkpoint unavailable" in str(exc) else "UNAVAILABLE"
        return {
            "status": status,
            "role": role,
            "error": type(exc).__name__,
            "decision_authority": "NONE",
            "native_body_consumed": False,
            "native_body_weights_changed": False,
        }


def receiver_readouts(store, state, action, home=None):
    """Read B1_DETAIL, B2_GIST and SELF_MODEL from the same persisted generation."""
    return {
        role: receiver_readout(store, role, state, action, home)
        for role in RECEIVER_ROLES
    }


def memory_recall(store, state, action, *, limit=5, home=None):
    """Read source-linked episodic T8 memories without granting action authority."""
    try:
        learner = _consumer(store, home, learning_enabled=False)
        value = learner.recall(state, action, limit=limit)
        value.update({
            "decision_authority": "NONE",
            "native_memory_consumed": False,
            "native_body_consumed": False,
        })
        return value
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        return {
            "status": "UNAVAILABLE",
            "error": type(exc).__name__,
            "items": [],
            "decision_authority": "NONE",
            "native_memory_consumed": False,
            "native_body_consumed": False,
        }
