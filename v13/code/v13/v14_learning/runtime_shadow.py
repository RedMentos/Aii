"""Post-commit, source-bound V14 temporal and World-prediction shadow consumers.

This module is deliberately record-only: it does not authorize optimizer updates.
"""
from pathlib import Path
import math
import os
import stat
import time

from .. import world_model
from ..contracts import packet
from .t8_store_authority import verify_committed_temporal_page, _object
from .t8_temporal_bridge import TemporalT8Bridge
from .world_jepa_consumer import WorldJEPAStoreConsumer


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _rows(store, kind, event_id, generation_id, limit=17, before=None):
    sql = "SELECT id,event_id,generation_id,payload,created FROM packets WHERE kind=? AND event_id=? AND generation_id=?"
    args = [kind, event_id, generation_id]
    if before is not None:
        sql += " AND created<=?"
        args.append(before)
    sql += " ORDER BY created DESC LIMIT ?"
    args.append(limit)
    rows = store.rows(sql, tuple(args))
    if type(rows) is not list or len(rows) >= limit:
        return None
    return rows


def _selection_for_event(store, event_id, generation_id, source_ref, before=None):
    rows = _rows(store, "ActionSelection", event_id, generation_id, 17, before)
    if rows is None:
        return None
    matches = []
    for row in rows:
        payload = _object(row.get("payload"), "ActionSelection")
        stage = payload.get("stage")
        if stage not in (None, "COMMIT"):
            continue
        if payload.get("producer_component") != "C5_ACTION_GATE":
            continue
        if payload.get("event_id") != event_id or payload.get("brain_generation_id") != generation_id:
            continue
        if payload.get("provenance") != [source_ref]:
            continue
        route = payload.get("route_hint")
        if route not in world_model.ACTIONS:
            continue
        matches.append((row, payload))
    return matches[0] if len(matches) == 1 else None


def online_world_shadow_prediction(runtime, store, event, role, input_chars, empirical_duration_s=None):
    """Expose OnlineWorld and numeric WorldJEPA receiver readouts as non-authoritative SHADOW data."""
    base = {
        "status": "NOT_READY",
        "role": str(role),
        "route_hint": None,
        "action_selection_packet_id": None,
        "decision_authority": "NONE",
        "calibration_status": "UNCALIBRATED",
        "empirical_duration_median_s": empirical_duration_s if _finite(empirical_duration_s) else None,
        "native_body_consumed": False,
        "native_body_weights_changed": False,
    }
    try:
        event_id = event.get("event_id")
        generation_id = event.get("brain_generation_id")
        source_ref = event.get("source_ref")
        if not isinstance(event_id, str) or not isinstance(generation_id, str) or not isinstance(source_ref, dict):
            base["status"] = "INVALID_EVENT"
            return base
        selected = _selection_for_event(store, event_id, generation_id, source_ref)
        if selected is None:
            base["status"] = "NO_UNIQUE_COMMITTED_SELECTION"
            return base
        selection_row, selection = selected
        route = selection.get("route_hint")
        base["route_hint"] = route
        base["action_selection_packet_id"] = str(selection_row.get("id"))
        if route not in world_model.ACTIONS or type(input_chars) is not int or input_chars < 0:
            base["status"] = "INVALID_MODEL_INPUT"
            return base
        event_created = event.get("created")
        clock = float(event_created) if _finite(event_created) else time.time()
        state = world_model.state_vec(input_chars, "NORMAL", (clock % 86400.0) / 3600.0)

        # The B1/B2/SELF readouts are numeric receiver heads, not native body
        # weights. They are exposed only after the explicitly gated JEPA
        # consumer has produced a persisted checkpoint.
        jepa_owner = getattr(store, "_v14_world_jepa_consumer", None)
        if jepa_owner is not None:
            readouts = {}
            for receiver_role in ("B1_DETAIL", "B2_GIST", "SELF_MODEL"):
                try:
                    readout = jepa_owner.readout(receiver_role, state, route)
                    readout["decision_authority"] = "NONE"
                    readouts[receiver_role] = readout
                except (ValueError, TypeError, KeyError, OSError, OverflowError, ArithmeticError) as exc:
                    readouts[receiver_role] = {
                        "status": "UNAVAILABLE",
                        "error": type(exc).__name__,
                        "decision_authority": "NONE",
                        "native_body_consumed": False,
                        "native_body_weights_changed": False,
                    }
            base["world_jepa_receivers"] = readouts
            if any(item.get("status") == "SHADOW_READOUT_ONLY" for item in readouts.values()):
                base["status"] = "SHADOW_ONLY"
                base["world_jepa_source"] = "PERSISTED_NUMERIC_WORLD_JEPA"
                base["world_jepa_decision_authority"] = "NONE"

        model_owner = getattr(runtime, "_online_world", None)
        if model_owner is None or getattr(model_owner, "model", None) is None:
            return base
        model = model_owner.model
        seen = getattr(model, "seen", 0)
        updates = getattr(model, "updates", 0)
        base["model_seen"] = int(seen) if type(seen) is int else 0
        base["model_updates"] = int(updates) if type(updates) is int else 0
        if type(seen) is not int or seen < 8:
            if base["status"] != "SHADOW_ONLY":
                base["status"] = "INSUFFICIENT_TRAINING_DATA"
            return base
        raw = model_owner.predict(state, route)
        if type(raw) not in (list, tuple) or len(raw) != 3 or not all(_finite(x) for x in raw):
            if base["status"] != "SHADOW_ONLY":
                base["status"] = "INVALID_PREDICTION"
            return base
        raw_duration = float(raw[0])
        raw_chars = float(raw[2]) * 8.0
        clipped_duration = max(0.0, min(8.19, raw_duration))
        clipped_chars = max(0.0, min(13.815, raw_chars))
        score = float(raw[1])
        base.update({
            "status": "SHADOW_ONLY",
            "decision_authority": "NONE",
            "calibration_status": "UNCALIBRATED",
            "predicted_duration_s": math.expm1(clipped_duration),
            "success_score_raw": score,
            "success_score_clipped": max(0.0, min(1.0, score)),
            "predicted_output_chars": math.expm1(clipped_chars),
            "clipped": clipped_duration != raw_duration or clipped_chars != raw_chars,
        })
        return base
    except (ValueError, TypeError, KeyError, OSError, OverflowError, ArithmeticError) as exc:
        base["status"] = "UNAVAILABLE"
        base["error"] = type(exc).__name__
        return base

def _secure_root(home):
    root = Path(home) / "v14_temporal"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise OSError("unsafe V14 temporal state directory")
    os.chmod(root, 0o700)
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("invalid V14 temporal state directory")
    return root


def _self_corollary_prediction(store, receipt):
    rows = _rows(store, "SelfCorollary", receipt.event_id, receipt.generation_id, 17, receipt.outcome_created)
    if rows is None:
        return None, "SELF_COROLLARY_SCAN_SATURATED"
    matches = []
    for row in rows:
        payload = _object(row.get("payload"), "SelfCorollary")
        if payload.get("action_id") == receipt.action_id:
            matches.append((row, payload))
    if len(matches) != 1:
        return None, "SELF_COROLLARY_CARDINALITY"
    row, payload = matches[0]
    if payload.get("packet_id") != row.get("id") or payload.get("event_id") != receipt.event_id:
        return None, "SELF_COROLLARY_IDENTITY"
    if payload.get("brain_generation_id") != receipt.generation_id or payload.get("provenance") != [receipt.source_ref]:
        return None, "SELF_COROLLARY_PROVENANCE"
    if not _finite(row.get("created")) or row["created"] > receipt.outcome_created:
        return None, "SELF_COROLLARY_AFTER_OUTCOME"
    permission = payload.get("permission_snapshot")
    if isinstance(permission, dict) and permission.get("external_tools") is True:
        return None, "SELF_COROLLARY_PERMISSION_SCOPE"
    observations = payload.get("predicted_observations")
    if type(observations) is not list:
        return None, "SELF_COROLLARY_OBSERVATIONS"
    status_predictions = [x for x in observations if isinstance(x, dict) and x.get("channel") == "action_status"]
    if len(status_predictions) != 1:
        return None, "SELF_COROLLARY_STATUS_PREDICTION"
    expected = status_predictions[0].get("value")
    if expected not in ("FINAL", "NOT_FINAL"):
        return None, "SELF_COROLLARY_STATUS_VALUE"
    costs = payload.get("expected_cost")
    duration = costs.get("duration_s") if isinstance(costs, dict) else None
    uncertainty = payload.get("uncertainty")
    if not _finite(duration) or not 0.0 <= float(duration) <= 3600.0:
        return None, "SELF_COROLLARY_DURATION"
    if not _finite(uncertainty) or not 0.0 <= float(uncertainty) <= 1.0:
        return None, "SELF_COROLLARY_UNCERTAINTY"
    prediction = {
        "expected_outcome": expected,
        "probability": 1.0 - float(uncertainty),
        "duration_s": float(duration),
        "tolerance_s": max(0.25, float(duration) * 0.20),
    }
    return {
        "prediction": prediction,
        "packet_id": str(row["id"]),
        "source": "SELF_COROLLARY_UNCALIBRATED",
        "calibration_status": "UNVALIDATED_HEURISTIC",
    }, "OK"


def _world_prediction_for_receipt(store, receipt):
    role = receipt.actual.get("role") if isinstance(receipt.actual, dict) else None
    if not isinstance(role, str) or not role:
        return {"status": "NO_ACTION_ROLE"}
    selected = _selection_for_event(store, receipt.event_id, receipt.generation_id, receipt.source_ref, receipt.created)
    if selected is None:
        return {"status": "NO_UNIQUE_ACTION_SELECTION"}
    selection_row, _ = selected
    rows = _rows(store, "ActionPrediction", receipt.event_id, receipt.generation_id, 17, receipt.outcome_created)
    if rows is None:
        return {"status": "ACTION_PREDICTION_SCAN_SATURATED"}
    matches = []
    for row in rows:
        payload = _object(row.get("payload"), "ActionPrediction")
        if payload.get("provenance") != [receipt.source_ref]:
            continue
        prediction = payload.get("prediction")
        if not isinstance(prediction, dict):
            continue
        if prediction.get("role") != role or prediction.get("action_selection_packet_id") != str(selection_row.get("id")):
            continue
        if prediction.get("online_world_shadow", {}).get("status") == "SHADOW_ONLY":
            matches.append((row, payload, prediction))
    if len(matches) != 1:
        return {"status": "NO_UNIQUE_SHADOW_PREDICTION"}
    row, payload, prediction = matches[0]
    shadow = prediction["online_world_shadow"]
    if not _finite(row.get("created")) or row["created"] > receipt.outcome_created:
        return {"status": "PREDICTION_AFTER_OUTCOME"}
    predicted_duration = shadow.get("predicted_duration_s")
    actual_duration = receipt.actual.get("action_duration_s")
    if not _finite(predicted_duration) or not 0.0 <= float(predicted_duration) <= 3600.0:
        return {"status": "INVALID_PREDICTED_DURATION"}
    if not _finite(actual_duration) or not 0.0 <= float(actual_duration) <= 86400.0:
        return {"status": "INVALID_ACTUAL_DURATION"}
    baseline = prediction.get("duration_median_s")
    baseline = float(baseline) if _finite(baseline) and 0.0 <= float(baseline) <= 3600.0 else None
    raw_score = shadow.get("success_score_raw")
    if not _finite(raw_score):
        return {"status": "INVALID_SUCCESS_SCORE"}
    clipped_score = max(0.0, min(1.0, float(raw_score)))
    censored = receipt.status in ("CANCELLED", "ABORTED", "OUTCOME_UNKNOWN", "INTERRUPTED")
    observed_success = None if censored else (1.0 if receipt.status == "FINAL" else 0.0)
    squared_error = None if observed_success is None else (clipped_score - observed_success) ** 2
    outcome = {
        "action_id": receipt.action_id,
        "prediction_packet_id": str(row.get("id")),
        "status": "SHADOW_ONLY",
        "action_selection_packet_id": str(selection_row.get("id")),
        "role": role,
        "route_hint": str(prediction.get("route_hint") or ""),
        "predicted_duration_s": float(predicted_duration),
        "actual_duration_s": float(actual_duration),
        "duration_error_s": float(actual_duration) - float(predicted_duration),
        "baseline_duration_s": baseline,
        "baseline_error_s": None if baseline is None else float(actual_duration) - baseline,
        "success_score_raw": float(raw_score),
        "success_score_clipped": clipped_score,
        "observed_success": observed_success,
        "success_squared_error_clipped": squared_error,
        "model_seen": int(shadow.get("model_seen", 0)),
        "calibration_status": "UNCALIBRATED",
        "decision_authority": "NONE",
        "receipt_fingerprint": receipt.fingerprint,
    }
    existing = store.rows(
        "SELECT id,payload FROM packets WHERE kind='WorldPredictionOutcome' AND event_id=? AND generation_id=? ORDER BY created DESC LIMIT 17",
        (receipt.event_id, receipt.generation_id),
    )
    if type(existing) is not list or len(existing) >= 17:
        return {"status": "WORLD_OUTCOME_SCAN_SATURATED"}
    matches_existing = []
    for item in existing:
        prior = _object(item.get("payload"), "WorldPredictionOutcome")
        if prior.get("action_id") == receipt.action_id:
            matches_existing.append((item, prior))
    if len(matches_existing) == 1:
        prior = matches_existing[0][1]
        if prior.get("prediction_packet_id") == outcome["prediction_packet_id"] and prior.get("receipt_fingerprint") == receipt.fingerprint:
            return {"status": "DUPLICATE", "packet_id": str(matches_existing[0][0].get("id"))}
        return {"status": "CONFLICT"}
    if len(matches_existing) > 1:
        return {"status": "CONFLICT"}
    created = packet(
        "WorldPredictionOutcome", "V14_WORLD_SHADOW", receipt.event_id, receipt.generation_id,
        [receipt.source_ref], **outcome
    )
    store.add_packet("WorldPredictionOutcome", created)
    return {"status": "CREATED", "packet_id": created["packet_id"]}


TEMPORAL_CURSOR_KEY = "v14.temporal.runtime_cursor"
WORLD_JEPA_PERMISSION_KEY = "v14.world_jepa.permissions"


def _world_jepa_permission_state(store):
    value, _ = store.state(
        WORLD_JEPA_PERMISSION_KEY,
        {"learning_enabled": False, "optimizer_permission": False, "steps": 40},
    )
    if type(value) is not dict:
        return False, False, 40
    learning_enabled = value.get("learning_enabled") is True
    optimizer_permission = value.get("optimizer_permission") is True
    steps = value.get("steps", 40)
    if type(steps) is not int or not 1 <= steps <= 2000:
        steps = 40
    return learning_enabled, optimizer_permission, steps


def consume_recent_committed(store, home, limit=64):
    """Consume oldest-first verified T8 pages; optionally train JEPA behind per-organ local gates."""
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("limit")
    root = _secure_root(home)
    bridge = TemporalT8Bridge(root, learning_enabled=False)
    cursor_state, cursor_version = store.state(TEMPORAL_CURSOR_KEY, {"scan_cursor": 0})
    if (type(cursor_state) is not dict or type(cursor_state.get("scan_cursor")) is not int
            or cursor_state["scan_cursor"] < 0):
        return {"status": "INVALID_TEMPORAL_CURSOR", "candidate_rows": 0, "verified": 0, "rejected": 0}
    cursor_before = cursor_state["scan_cursor"]
    receipts, rejected, next_cursor, scanned, censored_observed, has_more = (
        verify_committed_temporal_page(store, after_seq=cursor_before, limit=limit)
    )
    temporal_recorded = 0
    world_created = 0
    temporal_skipped = 0
    world_statuses = {}
    temporal_errors = 0
    world_errors = 0
    for receipt in receipts:
        try:
            world_result = _world_prediction_for_receipt(store, receipt)
            world_status = world_result.get("status", "UNKNOWN")
            world_statuses[world_status] = world_statuses.get(world_status, 0) + 1
            if world_status == "CREATED":
                world_created += 1
        except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
            world_errors += 1
            key = "ERROR_" + type(exc).__name__
            world_statuses[key] = world_statuses.get(key, 0) + 1
        try:
            prediction, prediction_status = _self_corollary_prediction(store, receipt)
            if prediction is None:
                temporal_skipped += 1
                continue
            result = bridge.consume(receipt, prediction["prediction"], optimizer_permission=False)
            store.log("v14_t8_temporal_shadow", receipt.event_id, {
                "action_id": receipt.action_id,
                "prediction_packet_id": prediction["packet_id"],
                "prediction_source": prediction["source"],
                "calibration_status": prediction["calibration_status"],
                "outcome_status": result.get("outcome"),
                "prediction_error": result.get("prediction_error"),
                "updated": bool(result.get("updated", False)),
                "pending_optimizer": bool(result.get("pending_optimizer", False)),
                "decision_authority": "NONE",
            })
            temporal_recorded += 1
        except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
            temporal_errors += 1
            try:
                store.log("v14_t8_temporal_shadow_error", receipt.event_id, {
                    "action_id": receipt.action_id, "error": type(exc).__name__,
                })
            except Exception:
                pass

    cursor_advanced = False
    cursor_error = None
    if next_cursor > cursor_before and temporal_errors == 0:
        try:
            store.set_state(TEMPORAL_CURSOR_KEY, {"scan_cursor": next_cursor}, expected=cursor_version)
            cursor_advanced = True
        except (ValueError, TypeError, OSError) as exc:
            cursor_error = type(exc).__name__

    learning_enabled, optimizer_permission, steps = _world_jepa_permission_state(store)
    jepa_result = {
        "status": "OFF" if not learning_enabled else "PENDING_OPTIMIZER_PERMISSION",
        "learning_enabled": learning_enabled,
        "optimizer_permission": optimizer_permission,
        "native_body_weights_changed": False,
        "decision_authority": "NONE",
    }
    if learning_enabled and optimizer_permission:
        try:
            consumer = getattr(store, "_v14_world_jepa_consumer", None)
            if consumer is None:
                consumer = WorldJEPAStoreConsumer(store, root / "world_jepa", learning_enabled=True)
                setattr(store, "_v14_world_jepa_consumer", consumer)
            jepa_result = consumer.update(
                limit=max(16, min(limit, 64)),
                steps=steps,
                optimizer_permission=True,
            )
            jepa_result["runtime_wired"] = True
            jepa_result["native_body_weights_changed"] = False
            jepa_result["decision_authority"] = "NONE"
        except (ValueError, TypeError, KeyError, OSError, OverflowError, ArithmeticError) as exc:
            jepa_result = {
                "status": "ERROR",
                "error": type(exc).__name__,
                "runtime_wired": True,
                "native_body_weights_changed": False,
                "decision_authority": "NONE",
            }
            try:
                store.log("v14_world_jepa_runtime_error", None, {"error": type(exc).__name__})
            except Exception:
                pass

    status = "RECORDED" if temporal_recorded or world_created else (
        "NO_VALID_PREDICTIONS" if receipts else "NO_NEW_TRANSITIONS"
    )
    if cursor_error:
        status = "CURSOR_CONFLICT_RETRY"
    elif temporal_errors:
        status = "TEMPORAL_RETRY_REQUIRED"
    return {
        "status": status,
        "candidate_rows": scanned,
        "verified": len(receipts),
        "rejected": rejected,
        "censored_observed": censored_observed,
        "temporal_recorded": temporal_recorded,
        "temporal_skipped": temporal_skipped,
        "world_outcomes_created": world_created,
        "world_outcome_statuses": world_statuses,
        "errors": temporal_errors + world_errors,
        "temporal_cursor_before": cursor_before,
        "temporal_cursor_after": next_cursor if cursor_advanced else cursor_before,
        "temporal_cursor_advanced": cursor_advanced,
        "has_more": has_more,
        "weight_updates": 0,
        "optimizer_permission": False,
        "learning_enabled": False,
        "world_jepa": jepa_result,
        "world_jepa_parameter_updates": jepa_result.get("status") == "UPDATED_EXPERIMENTAL_WORLD_JEPA",
        "native_body_weights_changed": False,
        "decision_authority": "NONE",
    }
