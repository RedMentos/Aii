"""Batched B1/B2/SELF readouts from one persisted WorldJEPA checkpoint.

This is a read-only SHADOW adapter. It does not dispatch actions or modify
native body activations/weights. Kept separate from the existing runtime so
the receiver can be introduced as a strictly additive package.
"""
from pathlib import Path
import math

import numpy as np

from . import world_model
from .world_jepa_consumer import WorldJEPAStoreConsumer, receiver_utility_gate

RECEIVER_ROLES = ("B1_DETAIL", "B2_GIST", "SELF_MODEL")


def _state_vector(state):
    if (not isinstance(state, (list, tuple)) or len(state) != 4
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in state)):
        raise ValueError("invalid receiver state vector")
    return [float(value) for value in state]


def _readout_output(role, prediction):
    if role == "B1_DETAIL":
        return {
            "predicted_action_duration_s": max(
                0.0, math.expm1(min(20.0, float(prediction[0])))
            ),
            "predicted_output_characters": max(
                0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0))
            ),
        }
    if role == "B2_GIST":
        return {
            "predicted_success_probability": float(
                np.clip(prediction[0], 0.0, 1.0)
            )
        }
    return {
        "predicted_action_duration_s": max(
            0.0, math.expm1(min(20.0, float(prediction[0])))
        ),
        "predicted_success_probability": float(
            np.clip(prediction[1], 0.0, 1.0)
        ),
        "predicted_output_characters": max(
            0.0, math.expm1(min(20.0, float(prediction[2]) * 8.0))
        ),
    }


def receiver_matrix(store, state, actions, home=None):
    """Read role heads for candidate actions with exactly one checkpoint load."""
    vector = _state_vector(state)
    if (type(actions) not in (list, tuple) or not actions
            or len(actions) > len(world_model.ACTIONS)
            or any(type(action) is not str or action not in world_model.ACTIONS
                   for action in actions)
            or len(set(actions)) != len(actions)):
        raise ValueError("invalid receiver action list")
    root = Path(home if home is not None else store.home) / "world_jepa"
    learner = WorldJEPAStoreConsumer(store, root, learning_enabled=False)
    try:
        with learner._locked(False):
            stored, _ = learner._read_state()
            active = stored["active"]
            if active is None:
                raise ValueError("WorldJEPA checkpoint unavailable")
            model = learner._load_model(active)
            # Apply the same per-role held-out admission used by the single-readout
            # API. The Planner consumes this batched path directly, so gating only
            # WorldJEPAStoreConsumer.readout would leave a real consumer bypass.
            utility_by_role = {
                role: receiver_utility_gate(active.get("metrics"), role)
                for role in RECEIVER_ROLES
            }
            matrix = {}
            for action in actions:
                x = np.asarray([vector + [0.0, 0.0, 0.0]], dtype=np.float64)
                a = np.asarray([world_model.onehot(action)], dtype=np.float64)
                latent, spread = model.predict(x, a)
                uncertainty = float(np.asarray(spread).reshape(-1)[0])
                if not math.isfinite(uncertainty) or uncertainty < 0:
                    raise ValueError("nonfinite receiver uncertainty")
                matrix[action] = {}
                for role in RECEIVER_ROLES:
                    utility = utility_by_role[role]
                    if not utility["accepted"]:
                        matrix[action][role] = {
                            "role": role,
                            "status": "RECEIVER_UTILITY_REJECTED",
                            "receiver_utility": utility,
                            "checkpoint_sha256": active["checkpoint_sha256"],
                            "source_sha256": active["source_sha256"],
                            "decision_authority": "NONE",
                            "native_body_consumed": False,
                            "native_body_weights_changed": False,
                        }
                        continue
                    head = active["receiver_heads"][role]
                    weights = np.asarray(head["weights"], dtype=np.float64)
                    bias = np.asarray(head["bias"], dtype=np.float64)
                    prediction = latent[0] @ weights + bias
                    if not np.isfinite(prediction).all():
                        raise ValueError("nonfinite receiver prediction")
                    matrix[action][role] = {
                        "role": role,
                        "prediction": _readout_output(role, prediction),
                        "uncertainty": uncertainty,
                        "checkpoint_sha256": active["checkpoint_sha256"],
                        "source_sha256": active["source_sha256"],
                        "status": "SHADOW_READOUT_ONLY",
                        "receiver_utility": utility,
                        "decision_authority": "NONE",
                        "native_body_consumed": False,
                        "native_body_weights_changed": False,
                    }
            return matrix
    except (ValueError, TypeError, KeyError, OSError, OverflowError,
            ArithmeticError, AttributeError) as exc:
        status = "NO_CHECKPOINT" if "checkpoint unavailable" in str(exc) else "UNAVAILABLE"
        return {
            action: {
                role: {
                    "status": status,
                    "role": role,
                    "error": type(exc).__name__,
                    "decision_authority": "NONE",
                    "native_body_consumed": False,
                    "native_body_weights_changed": False,
                }
                for role in RECEIVER_ROLES
            }
            for action in actions
        }
