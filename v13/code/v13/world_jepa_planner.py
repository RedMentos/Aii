"""Source-bound numeric B1/B2/SELF receiver for the persistent WorldJEPA learner.

This is a real World/Planner SHADOW consumer of the learned numeric readout
heads. It is deliberately not native B1/B2 activation injection, not GGUF
weight editing, and has no action/decision authority.
"""
from __future__ import annotations

import hashlib
import json
import math

from . import world_model
from .world_jepa_runtime import memory_recall
from .world_jepa_receiver_matrix import receiver_matrix
from .world_jepa_store_authority import MAX_ACTION_OUTCOMES_PER_EVENT

STATE_PREFIX = "v14.world_jepa.planner_shadow:"
SCHEMA = "v14.world_jepa.planner-shadow/2"
TERMINAL = {
    "FINAL", "FAILED", "CANCELLED", "ERROR", "DEADLINE", "INTERRUPTED",
    "ABORTED", "OUTCOME_UNKNOWN", "REJECTED",
}
OBSERVED_ACTION_STATUSES = {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED"}


def _reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _object(raw):
    if type(raw) is not str:
        raise ValueError("persisted JSON text required")
    value = json.loads(
        raw,
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_object,
    )
    if type(value) is not dict:
        raise ValueError("persisted JSON object required")
    return value


def _finite(value, *, minimum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    return minimum is None or value >= minimum


def _committed_context(store, event_id):
    if type(event_id) is not str or not event_id or len(event_id) > 128:
        raise ValueError("invalid event id")
    event = store.one(
        "SELECT id,source_id,generation_id,packet,created FROM events WHERE id=?",
        (event_id,),
    )
    if not event:
        raise ValueError("event not found")
    envelope = _object(event["packet"])
    generation = event["generation_id"]
    if (envelope.get("event_id") != event_id
            or envelope.get("brain_generation_id") != generation
            or envelope.get("authority") != "AUTHORITATIVE"):
        raise ValueError("event envelope is not authoritative")
    source_ref = envelope.get("source_ref")
    if (type(source_ref) is not dict
            or source_ref.get("source_id") != event["source_id"]
            or source_ref.get("modality") != "text"
            or type(source_ref.get("sha256")) is not str
            or len(source_ref["sha256"]) != 64):
        raise ValueError("event SourceRef mismatch")
    source_text = store.read_source(source_ref)

    action = store.one(
        "SELECT id,status,expected,outcome,created FROM actions "
        "WHERE event_id=? AND outcome IS NOT NULL ORDER BY created DESC LIMIT 1",
        (event_id,),
    )
    if not action or action["status"] not in OBSERVED_ACTION_STATUSES:
        raise ValueError("no committed terminal ActionOutcome")
    actual = _object(action["outcome"])
    expected = _object(action["expected"])
    forecast = expected.get("forecast")
    if type(forecast) is not dict:
        raise ValueError("committed action has no forecast")
    input_chars = forecast.get("input_chars")
    resource_state = forecast.get("resource_state", "UNKNOWN")
    if (type(input_chars) is not int or input_chars != len(source_text)
            or type(resource_state) is not str
            or not _finite(action["created"], minimum=0)):
        raise ValueError("committed action forecast does not match source")

    outcomes = store.rows(
        "SELECT payload FROM packets WHERE kind='ActionOutcome' "
        "AND event_id=? AND generation_id=? ORDER BY created DESC LIMIT ?",
        (event_id, generation, MAX_ACTION_OUTCOMES_PER_EVENT + 1),
    )
    if type(outcomes) is not list or len(outcomes) > MAX_ACTION_OUTCOMES_PER_EVENT:
        raise ValueError("ActionOutcome scan bound")
    matching = []
    for row in outcomes:
        payload = _object(row["payload"])
        if payload.get("action_id") == action["id"]:
            matching.append(payload)
    if (len(matching) != 1
            or matching[0].get("brain_generation_id") != generation
            or matching[0].get("event_id") != event_id
            or matching[0].get("status") != action["status"]
            or matching[0].get("actual") != actual):
        raise ValueError("ActionOutcome packet does not match committed action row")

    hour = (float(action["created"]) % 86400.0) / 3600.0
    state = world_model.state_vec(input_chars, resource_state, hour)
    return {
        "event_id": event_id,
        "generation": generation,
        "action_id": action["id"],
        "action_status": action["status"],
        "source_ref": dict(source_ref),
        "source_sha256": source_ref["sha256"],
        "state": state,
        "resource_state": resource_state,
    }


def _candidate_score(action, readouts):
    b1 = readouts["B1_DETAIL"]
    b2 = readouts["B2_GIST"]
    self_model = readouts["SELF_MODEL"]
    if any(item.get("status") != "SHADOW_READOUT_ONLY"
           for item in (b1, b2, self_model)):
        return None
    detail = b1.get("prediction")
    gist = b2.get("prediction")
    self_prediction = self_model.get("prediction")
    if type(detail) is not dict or type(gist) is not dict or type(self_prediction) is not dict:
        return None
    duration = detail.get("predicted_action_duration_s")
    characters = detail.get("predicted_output_characters")
    success = gist.get("predicted_success_probability")
    self_success = self_prediction.get("predicted_success_probability")
    uncertainties = [b1.get("uncertainty"), b2.get("uncertainty"),
                     self_model.get("uncertainty")]
    if (not _finite(duration, minimum=0)
            or not _finite(characters, minimum=0)
            or not _finite(success, minimum=0)
            or success > 1
            or not _finite(self_success, minimum=0)
            or self_success > 1
            or any(not _finite(value, minimum=0) for value in uncertainties)):
        return None
    latency_cost = duration / (1.0 + duration)
    uncertainty_cost = min(1.0, max(uncertainties))
    disagreement_cost = min(1.0, abs(success - self_success))
    blended_success = 0.5 * success + 0.5 * self_success
    # This score is an uncalibrated comparison aid, not a probability or action policy.
    score = (blended_success - 0.20 * latency_cost
             - 0.10 * uncertainty_cost - 0.10 * disagreement_cost)
    return {
        "action": action,
        "shadow_score": float(score),
        "score_semantics": "UNCALIBRATED_COMPARISON_ONLY",
        "predicted_success_probability_b2": float(success),
        "predicted_success_probability_self": float(self_success),
        "predicted_action_duration_s_b1": float(duration),
        "predicted_output_characters_b1": float(characters),
        "uncertainty": float(max(uncertainties)),
        "role_readouts": {
            role: {
                "checkpoint_sha256": readouts[role].get("checkpoint_sha256"),
                "source_sha256": readouts[role].get("source_sha256"),
            }
            for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL")
        },
    }


def _fingerprint(record):
    # Bind the persisted identity to the complete receiver evidence, not only
    # the final ranking. A role's utility gate can change while the numeric
    # model checkpoint stays identical; an old planner record must not survive
    # that change through the idempotency shortcut.
    body = {
        "schema": record["schema"],
        "status": record["status"],
        "event_id": record["event_id"],
        "generation": record["brain_generation_id"],
        "action_id": record["action_id"],
        "source_ref": record["source_ref"],
        "checkpoint_sha256": record["checkpoint_sha256"],
        "candidate_readouts": record["candidate_readouts"],
        "ranked_actions": record["ranked_actions"],
        "memory_recall": record["memory_recall"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def consume_world_planner_shadow(store, event_id, home=None, actions=None, memory_limit=5):
    """Consume numeric B1/B2/SELF readouts into a persisted World/Planner shadow view."""
    try:
        context = _committed_context(store, event_id)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError,
            OverflowError, ArithmeticError) as exc:
        return {
            "status": "NO_COMMITTED_OUTCOME"
                      if "no committed terminal ActionOutcome" in str(exc)
                      else "SOURCE_OR_RECEIPT_REJECTED",
            "error": type(exc).__name__,
            "decision_authority": "NONE",
            "dispatch": False,
            "native_body_consumed": False,
        }
    candidates = tuple(world_model.ACTIONS if actions is None else actions)
    if (not candidates or len(candidates) > len(world_model.ACTIONS)
            or any(type(item) is not str or item not in world_model.ACTIONS for item in candidates)
            or len(set(candidates)) != len(candidates)):
        raise ValueError("invalid planner candidate actions")
    if type(memory_limit) is not int or not 1 <= memory_limit <= 32:
        raise ValueError("invalid memory limit")

    matrix = receiver_matrix(store, context["state"], candidates, home=home)
    ranked = []
    by_action = {}
    checkpoint_sha = None
    for action in candidates:
        role_values = matrix.get(action, {})
        for role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
            value = role_values.get(role, {})
            if value.get("checkpoint_sha256"):
                if checkpoint_sha is None:
                    checkpoint_sha = value["checkpoint_sha256"]
                elif checkpoint_sha != value["checkpoint_sha256"]:
                    raise ValueError("receiver checkpoint changed during planner read")
        score = _candidate_score(action, role_values)
        by_action[action] = {
            "status": "READY" if score is not None else "UNAVAILABLE",
            "B1_DETAIL": role_values.get("B1_DETAIL", {}),
            "B2_GIST": role_values.get("B2_GIST", {}),
            "SELF_MODEL": role_values.get("SELF_MODEL", {}),
            "baseline": "NOT_USED",
        }
        if score is not None:
            ranked.append(score)
    ranked.sort(key=lambda item: (-item["shadow_score"], item["action"]))
    if checkpoint_sha is None:
        return {
            "status": "NO_CHECKPOINT",
            "event_id": event_id,
            "source_ref": context["source_ref"],
            "decision_authority": "NONE",
            "dispatch": False,
            "native_body_consumed": False,
        }

    memory = {"status": "NO_RANKED_ACTION", "items": []}
    if ranked:
        memory = memory_recall(
            store, context["state"], ranked[0]["action"],
            limit=memory_limit, home=home,
        )
    record = {
        "schema": SCHEMA,
        "status": "SHADOW_PLANNER_READY" if ranked else "SHADOW_PLANNER_UNAVAILABLE",
        "event_id": context["event_id"],
        "brain_generation_id": context["generation"],
        "action_id": context["action_id"],
        "action_status": context["action_status"],
        "source_ref": context["source_ref"],
        "source_sha256": context["source_sha256"],
        "state_vector": [float(value) for value in context["state"]],
        "checkpoint_sha256": checkpoint_sha,
        "candidate_readouts": by_action,
        "ranked_actions": ranked,
        "memory_recall": memory,
        "decision_authority": "NONE",
        "dispatch": False,
        "native_body_consumed": False,
        "native_body_weights_changed": False,
        "representation": "NUMERIC_ROLE_READOUTS_NOT_NATIVE_BODY_LATENT",
    }
    record["fingerprint"] = _fingerprint(record)
    key = STATE_PREFIX + event_id
    for _ in range(3):
        previous, version = store.state(key, None)
        if type(previous) is dict and previous.get("fingerprint") == record["fingerprint"]:
            return previous | {"persisted": True, "idempotent": True}
        try:
            store.set_state(key, record, expected=version)
            return record | {"persisted": True, "idempotent": False}
        except ValueError as exc:
            if str(exc) != "Stale state write":
                raise
    return record | {"status": "PERSISTENCE_CONFLICT", "persisted": False}


def read_world_planner_shadow(store, event_id):
    """Read the persisted receiver result only while its exact source still exists."""
    key = STATE_PREFIX + event_id
    record, _ = store.state(key, None)
    if type(record) is not dict or record.get("schema") != SCHEMA:
        return {"status": "NOT_FOUND", "decision_authority": "NONE"}
    try:
        event = store.one("SELECT source_id,generation_id,packet FROM events WHERE id=?",
                          (event_id,))
        if not event:
            raise ValueError("event missing")
        envelope = _object(event["packet"])
        source_ref = record.get("source_ref")
        if (type(source_ref) is not dict
                or envelope.get("brain_generation_id") != record.get("brain_generation_id")
                or envelope.get("source_ref") != source_ref
                or source_ref.get("source_id") != event["source_id"]
                or _fingerprint(record) != record.get("fingerprint")):
            raise ValueError("source binding changed")
        store.read_source(source_ref)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError,
            OverflowError, ArithmeticError):
        return {"status": "SOURCE_REVOKED_OR_CHANGED", "decision_authority": "NONE"}
    state, _ = store.state("v14.world_jepa.store_consumer", {})
    active = state.get("active") if type(state) is dict else None
    if (type(active) is not dict
            or active.get("checkpoint_sha256") != record.get("checkpoint_sha256")):
        return record | {"status": "STALE_CHECKPOINT", "decision_authority": "NONE"}
    return record | {"persisted": True, "decision_authority": "NONE"}
