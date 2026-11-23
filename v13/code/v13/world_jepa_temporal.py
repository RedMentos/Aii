"""Persistent temporal WorldJEPA over verified T8 sequences.

This additive learner uses contiguous, source-verified ActionOutcome windows,
including known cancellations/interruptions as explicit omission outcomes.
It is a numeric SHADOW predictor with EMA/optimizer/checkpoint/replay/rollback;
it does not edit native B1/B2 GGUF weights or grant action authority.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
import re
import time
import threading
from pathlib import Path
import uuid
import weakref

import numpy as np

from v13 import world_jepa, world_jepa_shadow_checkpoint, world_model
from .common import dumps, now
from .contracts import packet
from .world_jepa_consumer import (
    receiver_utility_gate,
    ROLE_TARGETS,
)
from .world_jepa_learning_intent import (
    TARGET_ROLES as LEARNING_INTENT_TARGET_ROLES,
    create_learning_intents,
    fit_role_receivers_with_intents,
    finalize_weight_delta_receipts,
    validate_learning_intent,
    validate_weight_delta_receipt,
)
from .world_jepa_runtime import permission_state
from .world_jepa_store_authority import verify_committed_temporal_page, verify_rows


STATE_KEY = "v14.world_jepa.temporal_consumer"
REVISION = "v14-world-jepa-temporal-v2"
SCHEMA = 2
MAX_ROWS = 2048
MAX_PAGES = 4
PAGE_SIZE = 64
MAX_WINDOWS = 4096
MAX_SESSION_EVENTS = 256
MIN_WINDOWS = 16
MIN_PARTITION = 8
HISTORY_LENGTHS = (2, 3)
MAX_RECALL_CANDIDATES = 256
MAX_RECALL_VERIFY_PER_ACTION = 3
OBSERVED_RECALL_STATUSES = {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED"}
CENSORED = {"CANCELLED", "ABORTED", "INTERRUPTED"}
UNKNOWN = {"OUTCOME_UNKNOWN"}
TERMINAL = {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED"} | CENSORED | UNKNOWN
SHA256 = set("0123456789abcdef")
MAX_ACTION_SOURCE_REFS = 64

# Every live temporal consumer may hold a warm model object for an active
# checkpoint. Source-forget must invalidate all such process-local copies,
# not only a guessed Store attribute or the most recently created Runtime.
_TEMPORAL_CONSUMERS = weakref.WeakSet()
_TEMPORAL_CONSUMERS_LOCK = threading.RLock()
_SOURCE_REF_KEYS = {"source_id", "sha256", "char_start", "char_end", "modality"}


def _json_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite temporal checkpoint value")
    return value


def _finite_vector(value, size):
    return (type(value) in (list, tuple) and len(value) == size
            and all(type(x) in (int, float) and math.isfinite(x) for x in value))


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(ch not in SHA256 for ch in value):
        raise ValueError("invalid SHA256")
    return value


def _mapping(row):
    if type(row) is dict:
        return row
    try:
        return {key: row[key] for key in row.keys()}
    except Exception as exc:
        raise ValueError("invalid Store row") from exc


def _json_object(raw, name):
    if type(raw) is dict:
        return raw
    if type(raw) is not str:
        raise ValueError(name)

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(name + " duplicate key")
            value[key] = item
        return value

    value = json.loads(raw, object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError(name)
    return value


def _validated_source_ref(store, value):
    if type(value) is not dict or set(value) != _SOURCE_REF_KEYS:
        raise ValueError("ActionSelection source ref shape")
    source_id, source_sha = value.get("source_id"), value.get("sha256")
    start, end, modality = value.get("char_start"), value.get("char_end"), value.get("modality")
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(source_sha) is not str or len(source_sha) != 64
            or any(ch not in SHA256 for ch in source_sha)
            or type(start) is not int or type(end) is not int or not 0 <= start <= end
            or type(modality) is not str or not modality or len(modality) > 64):
        raise ValueError("ActionSelection source ref identity")
    if type(store.read_source(value)) is not str:
        raise ValueError("ActionSelection source ref read")
    return {
        "source_id": source_id, "sha256": source_sha,
        "char_start": start, "char_end": end, "modality": modality,
    }


def _selection_source_refs(store, receipt):
    rows = store.rows(
        """SELECT payload FROM packets
           WHERE kind='ActionSelection' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC LIMIT 17""",
        (receipt.event_id, receipt.generation_id, receipt.created),
    )
    if type(rows) is not list or len(rows) >= 17:
        raise ValueError("ActionSelection source scan bound")
    committed = []
    for raw in rows:
        packet_row = _mapping(raw)
        selection = _json_object(packet_row.get("payload"), "ActionSelection source payload")
        if (selection.get("event_id") != receipt.event_id
                or selection.get("brain_generation_id") != receipt.generation_id):
            raise ValueError("ActionSelection source binding")
        stage = selection.get("stage")
        if stage not in (None, "PREDICTION", "COMMIT"):
            raise ValueError("ActionSelection source stage")
        if stage != "PREDICTION":
            committed.append(selection)
    if len(committed) != 1:
        raise ValueError("ActionSelection source cardinality")
    raw_refs = committed[0].get("provenance")
    if type(raw_refs) is not list or not 1 <= len(raw_refs) <= MAX_ACTION_SOURCE_REFS:
        raise ValueError("ActionSelection source refs")
    refs, seen, source_hashes = [], set(), {}
    for raw_ref in raw_refs:
        ref = _validated_source_ref(store, raw_ref)
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        if key in seen:
            raise ValueError("duplicate ActionSelection source ref")
        prior = source_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("ActionSelection source digest changed")
        source_hashes[ref["source_id"]] = ref["sha256"]
        seen.add(key)
        refs.append(ref)
    if receipt.source_ref not in refs:
        raise ValueError("ActionSelection omitted event source")
    refs.sort(key=lambda item: (
        item["source_id"], item["sha256"], item["char_start"],
        item["char_end"], item["modality"],
    ))
    return refs


def _row_source_pairs(row):
    primary = (row.get("source_id"), _sha(row.get("source_sha256")))
    raw = row.get("source_refs")
    if raw is None:
        return [primary]
    if type(raw) is not list or not 1 <= len(raw) <= MAX_ACTION_SOURCE_REFS:
        raise ValueError("invalid temporal source ref set")
    pairs, seen, source_hashes = set(), set(), {}
    for item in raw:
        if type(item) is not dict or set(item) != _SOURCE_REF_KEYS:
            raise ValueError("invalid temporal source ref")
        source_id, digest = item.get("source_id"), item.get("sha256")
        start, end, modality = item.get("char_start"), item.get("char_end"), item.get("modality")
        if (type(source_id) is not str or not source_id or len(source_id) > 256
                or type(start) is not int or type(end) is not int or not 0 <= start <= end
                or type(modality) is not str or not modality or len(modality) > 64):
            raise ValueError("invalid temporal source ref identity")
        _sha(digest)
        key = (source_id, digest, start, end, modality)
        if key in seen:
            raise ValueError("duplicate temporal source ref")
        prior = source_hashes.get(source_id)
        if prior is not None and prior != digest:
            raise ValueError("temporal source identity changed digest")
        source_hashes[source_id] = digest
        seen.add(key)
        pairs.add((source_id, digest))
    if primary not in pairs:
        raise ValueError("primary event source omitted from source refs")
    return sorted(pairs)


def _row_has_source(row, source_id):
    return any(item[0] == source_id for item in _row_source_pairs(row))


def empty_state():
    return {
        "schema": SCHEMA,
        "revision": REVISION,
        "scan_cursor": 0,
        "pending_rows": [],
        "active": None,
        "previous": None,
    }


def _receipt_row(store, receipt):
    raw = receipt.training_row()
    proof = receipt.public_provenance()
    event_id = receipt.event_id
    event = store.one(
        "SELECT id,session_id,generation_id FROM events WHERE id=?",
        (event_id,),
    )
    if not event:
        raise ValueError("temporal event missing")
    event = _mapping(event)
    if event.get("generation_id") != receipt.generation_id:
        raise ValueError("temporal generation mismatch")
    session_id = event.get("session_id")
    if type(session_id) is not str or not session_id:
        raise ValueError("temporal session identity")
    status = receipt.status
    if status not in TERMINAL:
        raise ValueError("temporal terminal status")
    route = raw.get("a")
    if route not in world_model.ACTIONS:
        raise ValueError("temporal action route")
    source_id = proof.get("source_id")
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("temporal source identity")
    source_refs = _selection_source_refs(store, receipt)
    fingerprint = _sha(receipt.fingerprint)
    if len(source_refs) > 1:
        fingerprint = _json_hash({
            "receipt_fingerprint": fingerprint,
            "source_refs": [
                [item["source_id"], item["sha256"], item["char_start"],
                 item["char_end"], item["modality"]]
                for item in source_refs
            ],
        })
    return {
        "action_id": receipt.action_id,
        "event_id": event_id,
        "generation_id": receipt.generation_id,
        "session_id": session_id,
        "source_id": source_id,
        "source_sha256": _sha(proof.get("source_sha256")),
        "source_refs": source_refs,
        "fingerprint": fingerprint,
        "outcome_sha256": _sha(proof.get("outcome_sha256")),
        "created": float(receipt.created),
        "status": status,
        "censored": status in CENSORED,
        "s": [float(x) for x in raw.get("s", ())],
        "a": route,
        "y": [float(x) for x in raw.get("y", ())],
    }


def _validate_row(row):
    required = {
        "action_id", "event_id", "generation_id", "session_id", "source_id",
        "source_sha256", "fingerprint", "outcome_sha256", "created", "status",
        "censored", "s", "a", "y",
    }
    if (type(row) is not dict or not required <= set(row)
            or set(row) - required not in (set(), {"source_refs"})):
        raise ValueError("invalid temporal T8 row")
    for key in ("action_id", "event_id", "generation_id", "session_id", "source_id"):
        if type(row[key]) is not str or not row[key] or len(row[key]) > 256:
            raise ValueError("invalid temporal identity")
    for key in ("source_sha256", "fingerprint", "outcome_sha256"):
        _sha(row[key])
    if (type(row["created"]) not in (int, float) or not math.isfinite(row["created"])
            or row["status"] not in TERMINAL
            or type(row["censored"]) is not bool
            or row["censored"] != (row["status"] in CENSORED)
            or row["a"] not in world_model.ACTIONS
            or not _finite_vector(row["s"], 4)
            or not _finite_vector(row["y"], 3)):
        raise ValueError("invalid temporal T8 values")
    _row_source_pairs(row)


def _window_id(action_ids, history_length):
    return _json_hash({"actions": list(action_ids), "history": history_length})


def _temporal_features(history, target, history_length):
    previous = history[:-1]
    latest = history[-1]
    mean_outcome = np.mean(np.asarray([row["y"] for row in history], dtype=np.float64), axis=0)
    x = (
        list(latest["s"])
        + mean_outcome.tolist()
        + [float(any(row["censored"] for row in previous)), float(bool(latest["censored"])),
           float(history_length) / float(max(HISTORY_LENGTHS))]
    )
    x2 = (
        list(target["s"])
        + list(target["y"])
        + [float(bool(target["censored"])), 0.0,
           float(history_length) / float(max(HISTORY_LENGTHS))]
    )
    if len(x) != 10 or len(x2) != 10 or not np.isfinite(x).all() or not np.isfinite(x2).all():
        raise ValueError("invalid temporal window features")
    return x, x2


def build_temporal_windows(store, rows, cancel_check=None):
    """Build every valid contiguous offset; missing/unknown/revoked rows break a window."""
    by_session = {}
    for row in rows:
        _validate_row(row)
        if row["status"] in UNKNOWN:
            continue
        by_session.setdefault(row["session_id"], []).append(row)
    event_orders = {}
    session_ids = sorted(by_session)
    # Batch the event-order lookup. Per-session SQL round-trips are too expensive
    # on the Android SQLite store once the bounded replay grows.
    for offset in range(0, len(session_ids), 400):
        if cancel_check is not None and cancel_check():
            raise InterruptedError("temporal window build cancelled")
        batch = session_ids[offset:offset + 400]
        placeholders = ",".join("?" for _ in batch)
        event_rows = store.rows(
            "SELECT id,session_id,created FROM ("
            "SELECT id,session_id,created,"
            "ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY created,id) AS rn "
            "FROM events WHERE session_id IN (" + placeholders + ")) "
            "WHERE rn<=? ORDER BY session_id,created,id",
            tuple(batch) + (MAX_SESSION_EVENTS + 1,),
        )
        for item in event_rows:
            row = _mapping(item)
            event_orders.setdefault(row["session_id"], []).append(row["id"])
    windows = []
    for session_id, session_rows in by_session.items():
        if cancel_check is not None and cancel_check():
            raise InterruptedError("temporal window build cancelled")
        event_ids = event_orders.get(session_id, [])
        if len(event_ids) > MAX_SESSION_EVENTS:
            continue
        positions = {event_id: index for index, event_id in enumerate(event_ids)}
        by_event = {}
        for row in session_rows:
            by_event.setdefault(row["event_id"], []).append(row)
        # Multiple actions per event are not silently linearized into a fake sequence.
        if any(len(items) != 1 for items in by_event.values()):
            continue
        ordered = [by_event.get(event_id, [None])[0] for event_id in event_ids]
        for start in range(len(ordered)):
            if cancel_check is not None and cancel_check():
                raise InterruptedError("temporal window build cancelled")
            for history_length in HISTORY_LENGTHS:
                target_index = start + history_length
                if target_index >= len(ordered):
                    continue
                history = ordered[start:target_index]
                target = ordered[target_index]
                if target is None or len(history) != history_length or any(item is None for item in history):
                    continue
                sequence = history + [target]
                if len({item["generation_id"] for item in sequence}) != 1:
                    continue
                if any(item["status"] in UNKNOWN for item in sequence):
                    continue
                if any(positions.get(sequence[i + 1]["event_id"], -99)
                       != positions.get(sequence[i]["event_id"], -100) + 1
                       for i in range(len(sequence) - 1)):
                    continue
                x, x2 = _temporal_features(history, target, history_length)
                action_ids = [item["action_id"] for item in sequence]
                window_id = _window_id(action_ids, history_length)
                lineage_pairs = sorted({
                    pair
                    for item in sequence
                    for pair in _row_source_pairs(item)
                })
                windows.append({
                    "window_id": window_id,
                    "session_id": session_id,
                    "generation_id": target["generation_id"],
                    "action_ids": action_ids,
                    "source_ids": [item["source_id"] for item in sequence],
                    "source_sha256s": [item["source_sha256"] for item in sequence],
                    "lineage_source_ids": sorted({source_id for source_id, _digest in lineage_pairs}),
                    "lineage_source_sha256s": sorted({digest for _source_id, digest in lineage_pairs}),
                    "lineage_source_pairs": [list(pair) for pair in lineage_pairs],
                    "X": x,
                    "A": world_model.onehot(target["a"]),
                    "X2": x2,
                    "a": target["a"],
                    "y": list(target["y"]),
                    "censored": bool(target["censored"]),
                })
                if len(windows) > MAX_WINDOWS:
                    raise OverflowError("temporal window budget exceeded")
    return windows


def _split_windows(windows):
    """Split whole session/source-connected components, not overlapping rows."""
    if type(windows) is not list or len(windows) < MIN_WINDOWS:
        raise ValueError("insufficient temporal windows")
    sessions = sorted({window["session_id"] for window in windows})
    parent = {session: session for session in sessions}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    owner_by_source = {}
    for window in windows:
        session = window["session_id"]
        for source_key in window.get("lineage_source_ids", window["source_ids"]):
            previous = owner_by_source.get(source_key)
            if previous is None:
                owner_by_source[source_key] = session
            else:
                union(session, previous)
        for source_key in window.get("lineage_source_sha256s", window["source_sha256s"]):
            _sha(source_key)
            previous = owner_by_source.get(source_key)
            if previous is None:
                owner_by_source[source_key] = session
            else:
                union(session, previous)

    components = {}
    for session in sessions:
        components.setdefault(find(session), set()).add(session)
    component_keys = []
    for members in components.values():
        sources = sorted({
            source_sha
            for window in windows if window["session_id"] in members
            for source_sha in window.get(
                "lineage_source_sha256s", window["source_sha256s"]
            )
        })
        # Session IDs are random runtime identifiers. Partition order must depend
        # only on stable source-content digests, otherwise identical fixtures can
        # change train/holdout assignment across runs and Python environments.
        component_keys.append((_json_hash({"sources": sources}), members))
    component_keys.sort(key=lambda item: item[0])
    fold_by_session = {}
    for index, (_, members) in enumerate(component_keys):
        fold = "train" if index % 2 == 0 else "holdout"
        for session in members:
            fold_by_session[session] = fold
    train = [window for window in windows if fold_by_session[window["session_id"]] == "train"]
    holdout = [window for window in windows if fold_by_session[window["session_id"]] == "holdout"]
    if len(train) < MIN_PARTITION or len(holdout) < MIN_PARTITION:
        raise ValueError("insufficient source-disjoint temporal partitions")
    train_source_ids = {
        source for window in train
        for source in window.get("lineage_source_ids", window["source_ids"])
    }
    holdout_source_ids = {
        source for window in holdout
        for source in window.get("lineage_source_ids", window["source_ids"])
    }
    train_sources = {
        source for window in train
        for source in window.get("lineage_source_sha256s", window["source_sha256s"])
    }
    holdout_sources = {
        source for window in holdout
        for source in window.get("lineage_source_sha256s", window["source_sha256s"])
    }
    if train_source_ids & holdout_source_ids:
        raise ValueError("temporal source id leakage")
    if train_sources & holdout_sources:
        raise ValueError("temporal source digest leakage")
    train_sessions = {window["session_id"] for window in train}
    holdout_sessions = {window["session_id"] for window in holdout}
    if train_sessions & holdout_sessions:
        raise ValueError("temporal session leakage")
    return train, holdout, {
        "source_disjoint": True,
        "train_session_count": len(train_sessions),
        "holdout_session_count": len(holdout_sessions),
        "train_source_count": len(train_sources),
        "holdout_source_count": len(holdout_sources),
        "train_source_id_count": len(train_source_ids),
        "holdout_source_id_count": len(holdout_source_ids),
    }


def _arrays(windows):
    X = np.asarray([window["X"] for window in windows], dtype=np.float64)
    A = np.asarray([window["A"] for window in windows], dtype=np.float64)
    X2 = np.asarray([window["X2"] for window in windows], dtype=np.float64)
    if (X.ndim != 2 or X.shape[1] != 10 or A.shape != (len(X), 4)
            or X2.shape != X.shape or not all(np.isfinite(v).all() for v in (X, A, X2))):
        raise ValueError("invalid temporal training arrays")
    return X, A, X2


def _temporal_neuromodulation(store, train_windows, row_by_id, model):
    """Bind verified T8 prediction error to the existing world_predictor eligibility path."""
    from .neuromod import Neuromod, SLOW_DECAY

    errors_by_action = {}
    for window in train_windows:
        action_ids = window.get("action_ids")
        if type(action_ids) is not list or not action_ids:
            raise ValueError("temporal credit window identity")
        action_id = action_ids[-1]
        row = row_by_id.get(action_id)
        if row is None:
            raise ValueError("temporal credit target missing")
        mse = float(model.prediction_loss(*_arrays([window])))
        if not math.isfinite(mse) or mse < 0.0:
            raise ValueError("nonfinite temporal credit error")
        errors_by_action.setdefault(action_id, []).append(math.sqrt(mse))

    records = []
    for action_id, values in sorted(errors_by_action.items()):
        row = row_by_id[action_id]
        records.append((row, float(sum(values) / len(values))))
    if not records:
        raise ValueError("empty temporal credit batch")

    event_ids = sorted({row["event_id"] for row, _error in records})
    placeholders = ",".join("?" for _ in event_ids)
    traces_written = 0
    modulators_written = 0
    with store.tx() as connection:
        existing = connection.execute(
            "SELECT kind,event_id,payload FROM packets WHERE event_id IN ("
            + placeholders + ") AND kind IN ('LearningTrace','ModulatorPacket')",
            tuple(event_ids),
        ).fetchall()
        trace_ids = set()
        modulator_ids = set()
        for item in existing:
            payload = json.loads(item["payload"])
            if item["kind"] == "LearningTrace" and payload.get("path_id") == "world_predictor":
                trace_ids.add(item["event_id"])
            elif (item["kind"] == "ModulatorPacket"
                  and payload.get("producer_component") == "N10_NEUROMOD"
                  and payload.get("path_id") == "world_predictor"):
                modulator_ids.add(item["event_id"])
        for row, rmse in records:
            event_id = row["event_id"]
            generation_id = row["generation_id"]
            if event_id not in trace_ids:
                trace = packet(
                    "LearningTrace", "N10_NEUROMOD", event_id, generation_id, [],
                    path_id="world_predictor", activity=1.0,
                    eligibility=SLOW_DECAY, authority="SYSTEM",
                )
                connection.execute(
                    "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                    (trace["packet_id"], "LearningTrace", trace["event_id"],
                     trace["brain_generation_id"], dumps(trace), now()),
                )
                traces_written += 1
                trace_ids.add(event_id)
            if event_id not in modulator_ids:
                error_signal = min(1.0, max(0.0, rmse))
                modulator = packet(
                    "ModulatorPacket", "N10_NEUROMOD", event_id, generation_id, [],
                    epistemic_evidence=0.0, human_correction=0.0,
                    task_success=0.0, resource_cost=0.0, safety_veto=False,
                    channels={"world_prediction_error": error_signal},
                    source_class="real_deterministic_outcome",
                    finality="FINAL", path_id="world_predictor",
                )
                connection.execute(
                    "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                    (modulator["packet_id"], "ModulatorPacket", modulator["event_id"],
                     modulator["brain_generation_id"], dumps(modulator), now()),
                )
                modulators_written += 1
                modulator_ids.add(event_id)

    mean_rmse = float(sum(error for _row, error in records) / len(records))
    delta = min(1.0, mean_rmse)
    controller = Neuromod(store)
    mode = controller.local_mode()
    if mode not in {"SHADOW", "ACTIVE"}:
        raise ValueError("invalid temporal neuromodulation mode")
    local = controller.local_update("world_predictor", delta=delta, observe=False)
    gate = local["gate"]
    eligibility = float(gate["eligibility"])
    modulator = float(gate["modulator"]["combined"])
    age_plasticity = float(gate["age_plasticity"])
    meta_plasticity = float(
        gate["meta"]["p_applied"] if gate["meta"]["mode"] == "ACTIVE" else 1.0
    )
    proposed_scale = float(local["scale"])
    if gate["veto"]:
        status = "MODULATOR_VETO"
        learning_rate_scale = 0.0
    elif gate["conflict"]["verify_first"]:
        status = "MODULATOR_VERIFY_FIRST"
        learning_rate_scale = 0.0
    elif mode == "ACTIVE" and proposed_scale <= 0.0:
        status = "MODULATOR_NO_CREDIT"
        learning_rate_scale = 0.0
    else:
        status = "READY"
        # SHADOW records the same credit calculation but preserves the existing
        # baseline optimizer step. ACTIVE requires the explicit local toggle.
        learning_rate_scale = proposed_scale if mode == "ACTIVE" else 1.0
    return {
        "status": status,
        "mode": mode,
        "applied": bool(mode == "ACTIVE" and status == "READY"),
        "learning_rate_scale": learning_rate_scale,
        "proposed_scale": proposed_scale,
        "delta": delta,
        "eligibility": eligibility,
        "modulator": modulator,
        "age_plasticity": age_plasticity,
        "meta_plasticity": meta_plasticity,
        "mean_prediction_rmse": mean_rmse,
        "trace_packets_written": traces_written,
        "modulator_packets_written": modulators_written,
    }


def _source_sha(rows):
    material = []
    for row in sorted(rows, key=lambda item: item["action_id"]):
        item = {
            "action_id": row["action_id"],
            "source_id": row["source_id"],
            "source_sha256": row["source_sha256"],
            "fingerprint": row["fingerprint"],
            "outcome_sha256": row["outcome_sha256"],
        }
        if row.get("source_refs") is not None:
            item["source_refs"] = row["source_refs"]
        material.append(item)
    return _json_hash(material)


def _snapshot(model):
    return {
        "enc": {key: np.asarray(value).copy() for key, value in model.enc.items()},
        "tgt": {key: np.asarray(value).copy() for key, value in model.tgt.items()},
        "preds": [
            {key: np.asarray(value).copy() for key, value in predictor.items()}
            for predictor in model.preds
        ],
    }


def _delta(before, after, group):
    pairs = []
    if group == "preds":
        for left, right in zip(before[group], after[group]):
            pairs.extend((left[key], right[key]) for key in left)
    else:
        pairs.extend((before[group][key], after[group][key]) for key in before[group])
    return math.sqrt(sum(float(np.square(right - left).sum()) for left, right in pairs))


def _pack_holdout(windows, model):
    X, A, X2 = _arrays(windows)
    target_latents = np.asarray(model.latent(X2, target=True), dtype=np.float64)
    if (target_latents.ndim != 2 or target_latents.shape[0] != len(X)
            or target_latents.shape[1] < 1 or not np.isfinite(target_latents).all()):
        raise ValueError("invalid temporal retention target anchor")
    target_values = target_latents.tolist()
    return {
        "window_ids": [window["window_id"] for window in windows],
        "X": X.tolist(),
        "A": A.tolist(),
        "X2": X2.tolist(),
        "target_latents": target_values,
        "target_sha256": _json_hash(target_values),
        "source_ids": sorted({source for window in windows for source in window["source_ids"]}),
        "source_sha256s": sorted({source for window in windows for source in window["source_sha256s"]}),
        "lineage_source_ids": sorted({
            source for window in windows
            for source in window.get("lineage_source_ids", window["source_ids"])
        }),
        "lineage_source_sha256s": sorted({
            source for window in windows
            for source in window.get("lineage_source_sha256s", window["source_sha256s"])
        }),
    }


def _unpack_holdout(record):
    X = np.asarray(record["X"], dtype=np.float64)
    A = np.asarray(record["A"], dtype=np.float64)
    X2 = np.asarray(record["X2"], dtype=np.float64)
    target_latents = np.asarray(record.get("target_latents"), dtype=np.float64)
    if (X.ndim != 2 or X.shape[1] != 10 or A.shape != (len(X), 4)
            or X2.shape != X.shape or len(X) < 2
            or target_latents.ndim != 2 or target_latents.shape[0] != len(X)
            or target_latents.shape[1] < 1
            or not all(np.isfinite(v).all() for v in (X, A, X2, target_latents))
            or record.get("target_sha256") != _json_hash(target_latents.tolist())):
        raise ValueError("invalid persisted temporal holdout")
    return X, A, X2, target_latents


def _anchored_prediction_loss(model, X, A, target_latents):
    """Compare online predictions to a fixed EMA target coordinate snapshot."""
    predicted, _spread = model.predict(X, A)
    target = np.asarray(target_latents, dtype=np.float64)
    if (predicted.shape != target.shape or predicted.ndim != 2
            or not np.isfinite(predicted).all() or not np.isfinite(target).all()):
        raise ValueError("invalid anchored temporal prediction")
    value = float(np.mean(np.square(predicted - target)))
    if not math.isfinite(value):
        raise ValueError("nonfinite anchored temporal prediction loss")
    return value


def _ordered_session_history(store, experience_rows, session_id):
    """Order T8 rows by canonical event order, not receipt timestamps or UUIDs."""
    event_order = store.rows(
        "SELECT id FROM events WHERE session_id=? ORDER BY created DESC,id DESC LIMIT ?",
        (session_id, MAX_SESSION_EVENTS + 1),
    )
    event_order = list(reversed(event_order))
    positions = {_mapping(item)["id"]: index for index, item in enumerate(event_order)}
    history = [
        row for row in experience_rows
        if row["session_id"] == session_id and row["event_id"] in positions
    ]
    history.sort(key=lambda row: positions[row["event_id"]])
    if len({row["event_id"] for row in history}) != len(history):
        return history, positions, "MULTIPLE_ACTIONS_PER_EVENT"
    return history, positions, None


def _record_valid(record):
    required = {
        "checkpoint", "checkpoint_sha256", "source_sha256", "experience_rows",
        "processed_ids", "fingerprints", "train_window_ids", "holdout_window_ids",
        "receiver_heads", "receiver_metrics", "action_support", "retention_holdouts",
        "metrics", "scan_cursor", "fit_steps",
    }
    optional = {"learning_intents", "weight_delta_receipts"}
    if type(record) is not dict:
        raise ValueError("invalid temporal checkpoint record")
    record_keys = set(record)
    if not required <= record_keys or record_keys - required not in (set(), optional):
        raise ValueError("invalid temporal checkpoint record")
    if bool(record_keys & optional) and not optional <= record_keys:
        raise ValueError("incomplete temporal learning-intent record")
    name = record["checkpoint"]
    if type(name) is not str or re.fullmatch(r"jepa-[0-9a-f]{32}\.npz", name) is None:
        raise ValueError("invalid temporal checkpoint name")
    _sha(record["checkpoint_sha256"])
    _sha(record["source_sha256"])
    rows = record["experience_rows"]
    if type(rows) is not list or len(rows) > MAX_ROWS:
        raise ValueError("temporal replay row budget")
    fingerprints = record["fingerprints"]
    if type(fingerprints) is not dict or len(fingerprints) != len(rows):
        raise ValueError("temporal fingerprint map")
    for row in rows:
        _validate_row(row)
        if fingerprints.get(row["action_id"]) != row["fingerprint"]:
            raise ValueError("temporal fingerprint mismatch")
    if (type(record["processed_ids"]) is not list
            or set(record["processed_ids"]) != set(fingerprints)
            or len(record["processed_ids"]) != len(fingerprints)
            or type(record["scan_cursor"]) is not int or record["scan_cursor"] < 0
            or type(record["fit_steps"]) is not int or record["fit_steps"] < 1):
        raise ValueError("temporal checkpoint cursor")
    if (type(record["train_window_ids"]) is not list
            or type(record["holdout_window_ids"]) is not list
            or set(record["train_window_ids"]) & set(record["holdout_window_ids"])):
        raise ValueError("temporal split ids")
    if type(record["receiver_heads"]) is not dict or set(record["receiver_heads"]) != set(ROLE_TARGETS):
        raise ValueError("temporal receiver heads")
    for role, indices in ROLE_TARGETS.items():
        head = record["receiver_heads"][role]
        if type(head) is not dict or not {"weights", "bias"} <= set(head):
            raise ValueError("temporal receiver head shape")
        weights = np.asarray(head["weights"], dtype=np.float64)
        bias = np.asarray(head["bias"], dtype=np.float64)
        if (weights.ndim != 2 or weights.shape[1] != len(indices)
                or bias.shape != (len(indices),)
                or not np.isfinite(weights).all() or not np.isfinite(bias).all()):
            raise ValueError("temporal receiver head values")
    if type(record["receiver_metrics"]) is not dict or type(record["action_support"]) is not dict:
        raise ValueError("temporal receiver metrics")
    if any(action not in world_model.ACTIONS or type(count) is not int or count < 0
           for action, count in record["action_support"].items()):
        raise ValueError("temporal action support")
    if _source_sha(rows) != record["source_sha256"]:
        raise ValueError("temporal checkpoint source manifest mismatch")
    if type(record["retention_holdouts"]) is not list or len(record["retention_holdouts"]) > 3:
        raise ValueError("temporal retention cohort budget")
    for holdout in record["retention_holdouts"]:
        legacy_holdout_keys = {
            "window_ids", "X", "A", "X2", "target_latents", "target_sha256",
            "source_ids", "source_sha256s",
        }
        lineage_holdout_keys = legacy_holdout_keys | {
            "lineage_source_ids", "lineage_source_sha256s",
        }
        if type(holdout) is not dict or set(holdout) not in (
            legacy_holdout_keys, lineage_holdout_keys
        ):
            raise ValueError("temporal retention record shape")
        _unpack_holdout(holdout)
        if (type(holdout["window_ids"]) is not list
                or len(holdout["window_ids"]) != len(holdout["X"])
                or type(holdout["source_ids"]) is not list
                or type(holdout["source_sha256s"]) is not list
                or any(type(source) is not str or not source for source in holdout["source_ids"])):
            raise ValueError("temporal retention provenance")
        for source_sha in holdout["source_sha256s"]:
            _sha(source_sha)
        if set(holdout) == lineage_holdout_keys:
            lineage_ids = holdout["lineage_source_ids"]
            lineage_hashes = holdout["lineage_source_sha256s"]
            if (type(lineage_ids) is not list or type(lineage_hashes) is not list
                    or any(type(source) is not str or not source for source in lineage_ids)):
                raise ValueError("temporal retention lineage")
            for source_sha in lineage_hashes:
                _sha(source_sha)
            if (not set(holdout["source_ids"]) <= set(lineage_ids)
                    or not set(holdout["source_sha256s"]) <= set(lineage_hashes)):
                raise ValueError("temporal retention lineage")
        _sha(holdout["target_sha256"])
    if type(record["metrics"]) is not dict:
        raise ValueError("temporal metrics")
    if optional <= record_keys:
        intents = record["learning_intents"]
        receipts = record["weight_delta_receipts"]
        if (
            type(intents) is not dict or set(intents) != set(LEARNING_INTENT_TARGET_ROLES)
            or type(receipts) is not dict or set(receipts) != set(LEARNING_INTENT_TARGET_ROLES)
        ):
            raise ValueError("temporal learning-intent map")
        for role in LEARNING_INTENT_TARGET_ROLES:
            intent = intents[role]
            receipt = receipts[role]
            validate_learning_intent(intent)
            validate_weight_delta_receipt(receipt)
            if (
                intent["target_organ"] != role
                or receipt["target_organ"] != role
                or receipt["intent_id"] != intent["intent_id"]
                or receipt["receipt_id"] != intent.get("weight_delta_receipt_id")
                or receipt["checkpoint_sha256"] != record["checkpoint_sha256"]
                or intent.get("checkpoint_sha256") != record["checkpoint_sha256"]
                or receipt["source_provenance_sha256"] != intent["provenance_sha256"]
                or receipt["new_parameter_sha256"] != intent.get("new_parameter_sha256")
                or receipt["parameter_delta_norm"] != intent.get("parameter_delta_norm")
                or receipt["target_adapter_parameters_changed"] != intent["target_adapter_parameters_changed"]
                or receipt["receiver_utility_pass"] != intent.get("receiver_utility_pass")
            ):
                raise ValueError("temporal learning-intent receipt mismatch")
    return True


def _validate_state(state):
    if state is None:
        return empty_state()
    required = {"schema", "revision", "scan_cursor", "pending_rows", "active", "previous"}
    if (type(state) is not dict or set(state) != required
            or state.get("schema") != SCHEMA or state.get("revision") != REVISION
            or type(state.get("scan_cursor")) is not int or state["scan_cursor"] < 0):
        raise ValueError("incompatible temporal WorldJEPA state")
    for key in ("active", "previous"):
        if state[key] is not None:
            _record_valid(state[key])
    if type(state["pending_rows"]) is not list or len(state["pending_rows"]) > MAX_ROWS:
        raise ValueError("temporal pending row budget")
    active_ids = set(state["active"]["fingerprints"]) if state["active"] else set()
    seen = set()
    for row in state["pending_rows"]:
        _validate_row(row)
        if row["action_id"] in active_ids or row["action_id"] in seen:
            raise ValueError("duplicate temporal pending row")
        seen.add(row["action_id"])
    return state


class TemporalWorldJEPAStoreConsumer:
    """Store-backed dense temporal-window learner with EMA, replay and rollback."""

    def __init__(self, store, *, seed=29, ensemble=2):
        if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
            raise ValueError("temporal seed")
        if type(ensemble) is not int or not 2 <= ensemble <= 16:
            raise ValueError("temporal ensemble must provide a measurable spread")
        self.store = store
        self.seed = seed
        self.ensemble = ensemble
        self._ephemeral_model = None
        self._ephemeral_checkpoint_sha = None
        self.home = Path(store.home) / "world_jepa_temporal"
        if self.home.exists() and self.home.is_symlink():
            raise ValueError("temporal checkpoint directory symlink")
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.home, 0o700)
        if not self.home.is_dir() or self.home.is_symlink():
            raise ValueError("unsafe temporal checkpoint directory")
        # Share the exact WorldJEPA/EMA/source-forget flock without constructing
        # WorldJEPAStoreConsumer: its constructor performs blocking crash-recovery
        # cleanup, which would stall this optional foreground read before the
        # nonblocking receiver lock can run.
        self.lock_home = Path(store.home) / "world_jepa"
        if self.lock_home.exists() and self.lock_home.is_symlink():
            raise ValueError("unsafe WorldJEPA lock directory")
        self.lock_home.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.lock_home, 0o700)
        if not self.lock_home.is_dir() or self.lock_home.is_symlink():
            raise ValueError("unsafe WorldJEPA lock directory")
        self.lock_path = self.lock_home / "consumer.lock"
        with _TEMPORAL_CONSUMERS_LOCK:
            _TEMPORAL_CONSUMERS.add(self)

    @contextmanager
    def _locked(self, exclusive=True, blocking=True):
        if self.lock_path.is_symlink():
            raise ValueError("unsafe consumer lock")
        with open(self.lock_path, "a+b") as lock:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if not blocking:
                operation |= fcntl.LOCK_NB
            fcntl.flock(lock.fileno(), operation)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _read_state(self):
        value, version = self.store.state(STATE_KEY, None)
        return _validate_state(value), version

    def _load_model(self, record):
        _record_valid(record)
        path = self.home / record["checkpoint"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing temporal checkpoint")
        return world_jepa_shadow_checkpoint.load(
            path, record["source_sha256"], record["checkpoint_sha256"]
        )

    def warm_active_checkpoint(self, *, nonblocking=True):
        """Warm the exact active checkpoint from an idle/background path.

        Foreground B1/B2 reads use warm_only=True and never synchronously load
        a cold checkpoint. The shared flock prevents a concurrent update or
        source-forget operation from replacing the checkpoint during loading.
        """
        if type(nonblocking) is not bool:
            raise ValueError("invalid warm-cache lock mode")
        try:
            with self._locked(False, blocking=not nonblocking):
                state, _ = self._read_state()
                active = state["active"]
                if active is None:
                    self._ephemeral_model = None
                    self._ephemeral_checkpoint_sha = None
                    return {"status": "NO_CHECKPOINT", "decision_authority": "NONE"}
                checkpoint_sha = active["checkpoint_sha256"]
                if (self._ephemeral_model is not None
                        and self._ephemeral_checkpoint_sha == checkpoint_sha):
                    return {
                        "status": "ALREADY_WARM",
                        "checkpoint_sha256": checkpoint_sha,
                        "decision_authority": "NONE",
                    }
                model = self._load_model(active)
                self._ephemeral_model = model
                self._ephemeral_checkpoint_sha = checkpoint_sha
                return {
                    "status": "WARMED",
                    "checkpoint_sha256": checkpoint_sha,
                    "decision_authority": "NONE",
                }
        except BlockingIOError:
            return {"status": "LOCK_BUSY", "decision_authority": "NONE"}

    def _prune(self, state):
        keep = {
            record["checkpoint"]
            for record in (state["active"], state["previous"])
            if record is not None
        }
        for path in self.home.glob("jepa-*.npz"):
            if path.name not in keep and not path.is_symlink() and path.is_file():
                path.unlink(missing_ok=True)

    def update(self, *, limit=PAGE_SIZE, max_pages=MAX_PAGES, steps=80,
               optimizer_permission=False, replay_mode="uniform", cancel_check=None):
        if (type(limit) is not int or not 1 <= limit <= PAGE_SIZE
                or type(max_pages) is not int or not 1 <= max_pages <= MAX_PAGES
                or type(steps) is not int or not 1 <= steps <= 2000
                or type(optimizer_permission) is not bool
                or replay_mode not in {"uniform", "none"}
                or (cancel_check is not None and not callable(cancel_check))):
            raise ValueError("invalid temporal update configuration")
        if cancel_check is not None and cancel_check():
            return {"status": "CANCELLED", "checkpoint_committed": False}
        gates = permission_state(self.store)
        if not gates["learning_enabled"]:
            return {"status": "OFF", "checkpoint_committed": False,
                    "native_body_weights_changed": False}
        if not optimizer_permission or not gates["optimizer_permission"]:
            return {"status": "PENDING_OPTIMIZER_PERMISSION", "checkpoint_committed": False,
                    "native_body_weights_changed": False}
        with self._locked(True):
            state, version = self._read_state()
            cursor = state["scan_cursor"]
            pending = {row["action_id"]: row for row in state["pending_rows"]}
            active = state["active"]
            active_fingerprints = dict(active["fingerprints"]) if active else {}
            # A rejected update or explicit rollback keeps source-verified rows pending.
            # They remain eligible for a deliberate retry even after the scan cursor advances.
            retry_ids = set(pending) - set(active_fingerprints)
            new_ids = set()
            rejected = censored = unknown = scanned = 0
            has_more = False
            for _ in range(max_pages):
                if cancel_check is not None and cancel_check():
                    return {"status": "CANCELLED", "checkpoint_committed": False}
                receipts, bad, next_cursor, page_scanned, page_censored, has_more = (
                    verify_committed_temporal_page(
                        self.store, after_seq=cursor, limit=limit
                    )
                )
                rejected += bad
                censored += page_censored
                scanned += page_scanned
                for receipt in receipts:
                    if receipt.status in UNKNOWN:
                        unknown += 1
                        continue
                    row = _receipt_row(self.store, receipt)
                    prior = active_fingerprints.get(row["action_id"])
                    if prior is not None:
                        if prior != row["fingerprint"]:
                            raise ValueError("committed temporal T8 fingerprint changed")
                        continue
                    previous_pending = pending.get(row["action_id"])
                    if previous_pending is not None:
                        if previous_pending["fingerprint"] != row["fingerprint"]:
                            raise ValueError("pending temporal T8 fingerprint changed")
                        continue
                    pending[row["action_id"]] = row
                    new_ids.add(row["action_id"])
                cursor = next_cursor
                if not has_more:
                    break
            eligible_ids = new_ids | retry_ids
            if not eligible_ids:
                next_state = dict(state)
                next_state["scan_cursor"] = cursor
                next_state["pending_rows"] = sorted(
                    pending.values(), key=lambda item: (item["created"], item["action_id"])
                )
                if cursor != state["scan_cursor"] or next_state["pending_rows"] != state["pending_rows"]:
                    self.store.set_state(STATE_KEY, next_state, expected=version)
                return {
                    "status": "NO_NEW_TRANSITIONS" if active else "WAITING_FOR_MORE_T8_DATA",
                    "verified_receipts": len(new_ids), "rejected_receipts": rejected,
                    "censored_observed": censored, "unknown_skipped": unknown,
                    "scanned_rows": scanned, "scan_cursor": cursor, "has_more": has_more,
                    "pending_rows": len(pending), "checkpoint_committed": False,
                    "native_body_weights_changed": False,
                }
            old_rows = list(active["experience_rows"]) if active else []
            by_id = {row["action_id"]: row for row in old_rows}
            by_id.update(pending)
            all_rows = sorted(by_id.values(), key=lambda item: (item["created"], item["action_id"]))
            if len(all_rows) > MAX_ROWS:
                raise OverflowError("temporal T8 retention budget exhausted; no rows pruned")
            try:
                windows = build_temporal_windows(self.store, all_rows, cancel_check=cancel_check)
            except InterruptedError:
                return {"status": "CANCELLED", "checkpoint_committed": False,
                        "native_body_weights_changed": False}
            if len(windows) < MIN_WINDOWS:
                next_state = dict(state)
                next_state["scan_cursor"] = cursor
                next_state["pending_rows"] = sorted(
                    pending.values(), key=lambda item: (item["created"], item["action_id"])
                )
                self.store.set_state(STATE_KEY, next_state, expected=version)
                return {
                    "status": "WAITING_FOR_MORE_T8_DATA", "windows": len(windows),
                    "verified_receipts": len(new_ids), "rejected_receipts": rejected,
                    "censored_observed": censored, "unknown_skipped": unknown,
                    "scanned_rows": scanned, "scan_cursor": cursor, "has_more": has_more,
                    "pending_rows": len(pending), "checkpoint_committed": False,
                    "native_body_weights_changed": False,
                }
            try:
                train, holdout, split = _split_windows(windows)
            except ValueError as exc:
                # One long session is not a valid disjoint holdout: every
                # overlapping temporal window shares that session. Keep the
                # verified rows pending and wait for another independent
                # session instead of turning a normal cold-start condition
                # into a SleepRuntime ERROR.
                if str(exc) != "insufficient source-disjoint temporal partitions":
                    raise
                next_state = dict(state)
                next_state["scan_cursor"] = cursor
                next_state["pending_rows"] = sorted(
                    pending.values(), key=lambda item: (item["created"], item["action_id"])
                )
                self.store.set_state(STATE_KEY, next_state, expected=version)
                return {
                    "status": "WAITING_FOR_MORE_T8_DATA",
                    "reason": "NEED_MORE_SOURCE_DISJOINT_SESSIONS",
                    "windows": len(windows),
                    "train_windows": 0,
                    "holdout_windows": 0,
                    "verified_receipts": len(new_ids),
                    "rejected_receipts": rejected,
                    "censored_observed": censored,
                    "unknown_skipped": unknown,
                    "scanned_rows": scanned,
                    "scan_cursor": cursor,
                    "has_more": has_more,
                    "pending_rows": len(pending),
                    "checkpoint_committed": False,
                    "native_body_weights_changed": False,
                }
            if replay_mode == "none" and active is not None:
                train = [
                    window for window in train
                    if any(action_id in eligible_ids for action_id in window["action_ids"])
                ]
            if len(train) < MIN_PARTITION:
                next_state = dict(state)
                next_state["scan_cursor"] = cursor
                next_state["pending_rows"] = sorted(
                    pending.values(), key=lambda item: (item["created"], item["action_id"])
                )
                self.store.set_state(STATE_KEY, next_state, expected=version)
                return {
                    "status": "WAITING_FOR_MORE_T8_DATA", "windows": len(windows),
                    "train_windows": len(train), "holdout_windows": len(holdout),
                    "scan_cursor": cursor, "has_more": has_more,
                    "checkpoint_committed": False, "native_body_weights_changed": False,
                }
            train_arrays, holdout_arrays = _arrays(train), _arrays(holdout)
            X_train, A_train, X2_train = train_arrays
            X_holdout, A_holdout, X2_holdout = holdout_arrays
            if active is None:
                model = world_jepa.WorldJEPA(seed=self.seed, ensemble=self.ensemble)
                # Zero-step bootstrap creates a resumable optimizer state without
                # applying an unmodulated weight update before the credit gate.
                model.fit(X_train, A_train, X2_train, steps=0, log_every=1,
                          cancel_check=cancel_check)
            else:
                model = self._load_model(active)
            before_snapshot = _snapshot(model)
            # Hold EMA target coordinates fixed for this comparison. Comparing
            # prediction_loss before/after would move the target with the EMA.
            holdout_target_anchor = np.asarray(
                model.latent(X2_holdout, target=True), dtype=np.float64
            )
            holdout_before = _anchored_prediction_loss(
                model, X_holdout, A_holdout, holdout_target_anchor
            )
            retention_before = []
            for old_holdout in (active["retention_holdouts"] if active else []):
                old_X, old_A, _old_X2, old_target = _unpack_holdout(old_holdout)
                retention_before.append(
                    _anchored_prediction_loss(model, old_X, old_A, old_target)
                )
            train_steps = steps
            modulation = _temporal_neuromodulation(self.store, train, by_id, model)
            if modulation["status"] != "READY":
                return {
                    "status": modulation["status"],
                    "verified_receipts": len(new_ids),
                    "train_windows": len(train), "holdout_windows": len(holdout),
                    "scan_cursor": cursor, "has_more": has_more,
                    "neuromodulation": modulation,
                    "checkpoint_committed": False,
                    "native_body_weights_changed": False,
                }
            learning_rate_scale = modulation["learning_rate_scale"]
            try:
                model.partial_fit(
                    X_train, A_train, X2_train, steps=train_steps,
                    allow_optimizer_bootstrap=True,
                    cancel_check=cancel_check,
                    learning_rate_scale=learning_rate_scale,
                )
            except InterruptedError:
                return {"status": "CANCELLED", "checkpoint_committed": False,
                        "native_body_weights_changed": False}
            if cancel_check is not None and cancel_check():
                return {"status": "CANCELLED", "checkpoint_committed": False}
            after_snapshot = _snapshot(model)
            encoder_delta = _delta(before_snapshot, after_snapshot, "enc")
            predictor_delta = _delta(before_snapshot, after_snapshot, "preds")
            parameter_delta = encoder_delta + predictor_delta
            ema_delta = _delta(before_snapshot, after_snapshot, "tgt")
            holdout_after = _anchored_prediction_loss(
                model, X_holdout, A_holdout, holdout_target_anchor
            )
            shuffled_target = _anchored_prediction_loss(
                model, X_holdout, A_holdout, np.roll(holdout_target_anchor, 1, axis=0)
            )
            shuffled_action = _anchored_prediction_loss(
                model, X_holdout, np.roll(A_holdout, 1, axis=0), holdout_target_anchor
            )
            no_history = X_holdout.copy()
            no_history[:, :9] = 0.0
            no_history_loss = _anchored_prediction_loss(
                model, no_history, A_holdout, holdout_target_anchor
            )
            collapse = model.collapse_stats(X2_holdout)
            retention_after = []
            for old_holdout in (active["retention_holdouts"] if active else []):
                old_X, old_A, _old_X2, old_target = _unpack_holdout(old_holdout)
                retention_after.append(
                    _anchored_prediction_loss(model, old_X, old_A, old_target)
                )
            retention_pass = all(
                after <= before * 1.10 + 1e-9
                for before, after in zip(retention_before, retention_after)
            )
            utility_pass = (
                math.isfinite(holdout_after) and holdout_after <= holdout_before * 1.05 + 1e-9
                and holdout_after + 1e-9 < shuffled_target
                and holdout_after + 1e-9 < shuffled_action
                and not collapse.get("collapsed", True)
                and parameter_delta > 0.0 and ema_delta > 0.0
            )
            if not utility_pass or not retention_pass:
                next_state = dict(state)
                next_state["scan_cursor"] = cursor
                next_state["pending_rows"] = sorted(
                    pending.values(), key=lambda item: (item["created"], item["action_id"])
                )
                self.store.set_state(STATE_KEY, next_state, expected=version)
                attempt_metrics = _json_safe({
                    "train_windows": len(train), "holdout_windows": len(holdout),
                    "optimizer_steps": model._fit_steps, "steps_this_update": train_steps,
                    "replay_mode": replay_mode,
                    "verified_receipts": len(new_ids), "pending_retried": len(retry_ids),
                    "source_disjoint": split["source_disjoint"],
                    "train_session_count": split["train_session_count"],
                    "holdout_session_count": split["holdout_session_count"],
                    "holdout_mse_before": holdout_before, "holdout_mse_after": holdout_after,
                    "shuffled_target_mse": shuffled_target,
                    "shuffled_action_mse": shuffled_action,
                    "no_history_mse": no_history_loss,
                    "parameter_delta_norm": parameter_delta,
                    "encoder_delta_norm": encoder_delta,
                    "predictor_delta_norm": predictor_delta,
                    "ema_target_delta_norm": ema_delta,
                    "parent_checkpoint_sha256": active["checkpoint_sha256"] if active else None,
                    "retention_mse_before": retention_before,
                    "retention_mse_after": retention_after,
                    "retention_pass": retention_pass,
                    "retention_reference": "FIXED_EMA_TARGET_ANCHOR",
                    "holdout_target_sha256": _json_hash(holdout_target_anchor.tolist()),
                    "retention_target_sha256s": [
                        item["target_sha256"] for item in (active["retention_holdouts"] if active else [])
                    ],
                    "utility_pass": utility_pass,
                    "collapse": collapse,
                    "neuromodulation": modulation,
                })
                return {
                    "status": "RETENTION_GATE_REJECTED" if not retention_pass else "UTILITY_GATE_REJECTED",
                    "verified_receipts": len(new_ids), "pending_retried": len(retry_ids),
                    "train_windows": len(train), "holdout_windows": len(holdout),
                    "steps_this_update": train_steps, "optimizer_steps": model._fit_steps,
                    "replay_mode": replay_mode, "metrics": attempt_metrics,
                    "holdout_mse_before": holdout_before, "holdout_mse_after": holdout_after,
                    "shuffled_target_mse": shuffled_target,
                    "shuffled_action_mse": shuffled_action,
                    "no_history_mse": no_history_loss,
                    "parameter_delta_norm": parameter_delta,
                    "ema_target_delta_norm": ema_delta,
                    "retention_mse_before": retention_before,
                    "retention_mse_after": retention_after,
                    "retention_pass": retention_pass,
                    "collapse": collapse, "scan_cursor": cursor, "has_more": has_more,
                    "checkpoint_committed": False, "native_body_weights_changed": False,
                }
            learning_intents = create_learning_intents(
                train, holdout, active, gates, modulation
            )
            (
                receiver_heads, receiver_metrics, receiver_gates,
                learning_intents, receiver_delta_meta,
            ) = fit_role_receivers_with_intents(
                learning_intents, model, train_arrays, holdout_arrays,
                train, holdout, active, modulation,
            )
            action_support = {}
            for window in train:
                action_support[window["a"]] = action_support.get(window["a"], 0) + 1
            old_holdouts = list(active["retention_holdouts"]) if active else []
            retention_holdouts = (old_holdouts + [_pack_holdout(holdout, model)])[-3:]
            source_sha = _source_sha(all_rows)
            checkpoint_name = "jepa-" + uuid.uuid4().hex + ".npz"
            checkpoint_path = self.home / checkpoint_name
            checkpoint = world_jepa_shadow_checkpoint.save(model, checkpoint_path, source_sha)
            if cancel_check is not None and cancel_check():
                checkpoint_path.unlink(missing_ok=True)
                return {"status": "CANCELLED", "checkpoint_committed": False,
                        "native_body_weights_changed": False}
            metrics = _json_safe({
                "train_windows": len(train), "holdout_windows": len(holdout),
                "holdout_mse_before": holdout_before, "holdout_mse_after": holdout_after,
                "shuffled_target_mse": shuffled_target,
                "shuffled_action_mse": shuffled_action,
                "no_history_mse": no_history_loss,
                "parameter_delta_norm": parameter_delta,
                "encoder_delta_norm": encoder_delta,
                "predictor_delta_norm": predictor_delta,
                "ema_target_delta_norm": ema_delta,
                "parent_checkpoint_sha256": active["checkpoint_sha256"] if active else None,
                "optimizer_steps": model._fit_steps,
                "steps_this_update": train_steps,
                "censored_observed": censored, "unknown_skipped": unknown,
                "pending_retried": len(retry_ids),
                "source_disjoint": split["source_disjoint"],
                "train_session_count": split["train_session_count"],
                "holdout_session_count": split["holdout_session_count"],
                "train_source_count": split["train_source_count"],
                "holdout_source_count": split["holdout_source_count"],
                "retention_mse_before": retention_before,
                "retention_mse_after": retention_after,
                "retention_pass": retention_pass,
                "retention_reference": "FIXED_EMA_TARGET_ANCHOR",
                "holdout_target_sha256": _json_hash(holdout_target_anchor.tolist()),
                "retention_target_sha256s": [
                    item["target_sha256"] for item in (active["retention_holdouts"] if active else [])
                ],
                "replay_mode": replay_mode,
                "collapse": collapse,
                "neuromodulation": modulation,
                "receiver_gates": receiver_gates,
                "rejected_receipts": rejected,
                "scanned_rows": scanned,
                "has_more": has_more,
            })
            receiver_heads = _json_safe(receiver_heads)
            receiver_metrics = _json_safe(receiver_metrics)
            learning_intents, weight_delta_receipts = finalize_weight_delta_receipts(
                learning_intents, receiver_delta_meta, receiver_metrics,
                receiver_gates, checkpoint["sha256"], metrics,
            )
            record = {
                "checkpoint": checkpoint_name,
                "checkpoint_sha256": checkpoint["sha256"],
                "source_sha256": source_sha,
                "experience_rows": all_rows,
                "processed_ids": [row["action_id"] for row in all_rows],
                "fingerprints": {row["action_id"]: row["fingerprint"] for row in all_rows},
                "train_window_ids": [window["window_id"] for window in train],
                "holdout_window_ids": [window["window_id"] for window in holdout],
                "receiver_heads": receiver_heads,
                "receiver_metrics": receiver_metrics,
                "learning_intents": learning_intents,
                "weight_delta_receipts": weight_delta_receipts,
                "action_support": action_support,
                "retention_holdouts": retention_holdouts,
                "metrics": metrics,
                "scan_cursor": cursor,
                "fit_steps": model._fit_steps,
            }
            _record_valid(record)
            next_state = {
                "schema": SCHEMA, "revision": REVISION, "scan_cursor": cursor,
                "pending_rows": [], "active": record, "previous": active,
            }
            try:
                self.store.set_state(STATE_KEY, next_state, expected=version)
            except ValueError as exc:
                checkpoint_path.unlink(missing_ok=True)
                if "Stale state write" in str(exc):
                    return {"status": "CONCURRENT_STATE_CONFLICT_RETRY",
                            "new_receipts": len(new_ids), "checkpoint_discarded": True,
                            "native_body_weights_changed": False}
                raise
            except Exception:
                checkpoint_path.unlink(missing_ok=True)
                raise
            self._prune(next_state)
            return {
                "status": "UPDATED_EXPERIMENTAL_TEMPORAL_JEPA",
                "verified_receipts": len(new_ids), "pending_retried": len(retry_ids),
                "rejected_receipts": rejected,
                "censored_observed": censored, "unknown_skipped": unknown,
                "scanned_rows": scanned, "scan_cursor": cursor, "has_more": has_more,
                "windows": len(windows), "train_windows": len(train),
                "holdout_windows": len(holdout), "metrics": metrics,
                "neuromodulation": modulation,
                "learning_rate_scale": learning_rate_scale,
                "checkpoint_sha256": checkpoint["sha256"],
                "source_sha256": source_sha,
                "checkpoint_committed": True,
                "optimizer_state_persisted": checkpoint["optimizer_state_persisted"],
                "native_body_consumed": False,
                "native_body_weights_changed": False,
                "target_adapter_parameters_changed": {
                    role: receipt["target_adapter_parameters_changed"]
                    for role, receipt in weight_delta_receipts.items()
                },
                "learning_intent_ids": {
                    role: intent["intent_id"] for role, intent in learning_intents.items()
                },
                "weight_delta_receipt_ids": {
                    role: receipt["receipt_id"] for role, receipt in weight_delta_receipts.items()
                },
                "decision_authority": "NONE",
            }

    def rollback(self):
        with self._locked(True):
            state, version = self._read_state()
            if state["previous"] is None:
                return {"status": "NO_ROLLBACK_CHECKPOINT", "checkpoint_committed": False}
            current = state["active"]
            previous = state["previous"]
            previous_ids = set(previous["fingerprints"])
            pending = [
                row for row in (current["experience_rows"] if current else [])
                if row["action_id"] not in previous_ids
            ]
            next_state = {
                "schema": SCHEMA, "revision": REVISION,
                "scan_cursor": previous["scan_cursor"],
                "pending_rows": pending,
                "active": previous,
                "previous": None,
            }
            self.store.set_state(STATE_KEY, next_state, expected=version)
            self._prune(next_state)
            return {
                "status": "ROLLED_BACK",
                "checkpoint_sha256": previous["checkpoint_sha256"],
                "pending_rows": len(pending),
                "native_body_weights_changed": False,
            }

    def episodic_recall(self, session_id, history_length=2, limit=4,
                        nonblocking=False, budget_s=0.05, warm_only=False):
        """Retrieve source-verified train-split T8 episodes in the learned temporal space.

        Only the current query history and verified numeric outcomes are used.
        Holdout windows never enter the recall index; candidate SourceRefs are
        revalidated before they are returned. The result is prompt-level SHADOW
        context, not a native-memory write or action authority.
        """
        if (type(session_id) is not str or not session_id
                or history_length not in HISTORY_LENGTHS
                or type(limit) is not int or not 1 <= limit <= len(world_model.ACTIONS)
                or type(nonblocking) is not bool or type(warm_only) is not bool
                or type(budget_s) not in (int, float) or isinstance(budget_s, bool)
                or not math.isfinite(float(budget_s))
                or not 0.005 <= float(budget_s) <= 0.25):
            raise ValueError("invalid temporal episodic recall request")
        deadline = time.monotonic() + float(budget_s)

        def expired():
            return time.monotonic() >= deadline

        with self._locked(False, blocking=not nonblocking):
            state, _ = self._read_state()
            active = state["active"]
            if active is None:
                return {"status": "NO_CHECKPOINT", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            history, positions, history_error = _ordered_session_history(
                self.store, active["experience_rows"], session_id
            )
            if history_error:
                return {"status": history_error, "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            if len(history) < history_length:
                return {"status": "INSUFFICIENT_HISTORY", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            history_rows = history[-history_length:]
            if len({row["generation_id"] for row in history_rows}) != 1:
                return {"status": "GENERATION_GAP", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            if any(
                positions.get(right["event_id"], -99) != positions.get(left["event_id"], -100) + 1
                for left, right in zip(history_rows, history_rows[1:])
            ):
                return {"status": "NONCONTIGUOUS_HISTORY", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}

            verified_history, rejected_history = verify_rows(self.store, history_rows)
            if rejected_history or len(verified_history) != len(history_rows):
                return {
                    "status": "HISTORY_PROVENANCE_REJECTED", "items": [],
                    "rejected_history_rows": rejected_history,
                    "decision_authority": "NONE", "native_memory_consumed": False,
                }
            if expired():
                return {"status": "BUDGET_EXCEEDED", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}

            latest = history_rows[-1]
            mean_outcome = np.mean(
                np.asarray([row["y"] for row in history_rows], dtype=np.float64), axis=0
            )
            query_x = (
                list(latest["s"]) + mean_outcome.tolist()
                + [float(any(row["censored"] for row in history_rows[:-1])),
                   float(latest["censored"]),
                   float(history_length) / float(max(HISTORY_LENGTHS))]
            )
            model = self._ephemeral_model
            if (model is None
                    or self._ephemeral_checkpoint_sha != active["checkpoint_sha256"]):
                if warm_only:
                    return {
                        "status": "MODEL_NOT_WARM", "items": [],
                        "checkpoint_sha256": active["checkpoint_sha256"],
                        "decision_authority": "NONE", "native_memory_consumed": False,
                    }
                model = self._load_model(active)
                self._ephemeral_model = model
                self._ephemeral_checkpoint_sha = active["checkpoint_sha256"]
            query_latent = np.asarray(
                model.latent(np.asarray([query_x], dtype=np.float64), target=False),
                dtype=np.float64,
            )
            if (query_latent.ndim != 2 or query_latent.shape[0] != 1
                    or not np.isfinite(query_latent).all()):
                raise ValueError("invalid temporal episodic query latent")
            if expired():
                return {"status": "BUDGET_EXCEEDED", "items": [],
                        "checkpoint_sha256": active["checkpoint_sha256"],
                        "decision_authority": "NONE", "native_memory_consumed": False}

            train_window_ids = set(active["train_window_ids"])
            if not train_window_ids:
                return {"status": "NO_TRAIN_WINDOWS", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            row_by_id = {row["action_id"]: row for row in active["experience_rows"]}
            try:
                windows = build_temporal_windows(
                    self.store, active["experience_rows"], cancel_check=expired
                )
            except InterruptedError:
                return {"status": "BUDGET_EXCEEDED", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}
            if expired():
                return {"status": "BUDGET_EXCEEDED", "items": [],
                        "decision_authority": "NONE", "native_memory_consumed": False}

            query_action_ids = [receipt.action_id for receipt in verified_history]
            query_source_hashes = [receipt.source_ref["sha256"] for receipt in verified_history]
            try:
                query_source_ref_sets = [
                    _selection_source_refs(self.store, receipt) for receipt in verified_history
                ]
            except (ValueError, TypeError, KeyError):
                return {
                    "status": "QUERY_SOURCE_CONTEXT_REVOKED", "items": [],
                    "decision_authority": "NONE", "native_memory_consumed": False,
                }
            query_lineage_pairs = sorted({
                (ref["source_id"], ref["sha256"])
                for ref_set in query_source_ref_sets for ref in ref_set
            })
            query_lineage_source_ids = {source_id for source_id, _digest in query_lineage_pairs}
            query_lineage_source_hashes = {digest for _source_id, digest in query_lineage_pairs}
            query_action_set = set(query_action_ids)
            query_source_set = set(query_source_hashes)
            train_windows = []
            for window in windows:
                if window["window_id"] not in train_window_ids:
                    continue
                if len(window["action_ids"]) != history_length + 1:
                    continue
                if query_action_set.intersection(window["action_ids"]):
                    continue
                window_lineage_ids = set(
                    window.get("lineage_source_ids", window["source_ids"])
                )
                window_lineage_hashes = set(
                    window.get("lineage_source_sha256s", window["source_sha256s"])
                )
                if (query_source_set.intersection(window["source_sha256s"])
                        or query_lineage_source_ids.intersection(window_lineage_ids)
                        or query_lineage_source_hashes.intersection(window_lineage_hashes)):
                    continue
                target = row_by_id.get(window["action_ids"][-1])
                if target is None or target["status"] not in OBSERVED_RECALL_STATUSES:
                    continue
                train_windows.append((window, target))
            train_windows.sort(
                key=lambda pair: (pair[1]["created"], pair[1]["action_id"])
            )
            train_window_count_before_cap = len(train_windows)
            if len(train_windows) > MAX_RECALL_CANDIDATES:
                sample_indices = np.linspace(
                    0, len(train_windows) - 1, num=MAX_RECALL_CANDIDATES, dtype=np.int64
                )
                train_windows = [train_windows[int(index)] for index in sample_indices]
            if not train_windows:
                return {
                    "status": "NO_DISJOINT_TRAIN_EPISODES", "items": [],
                    "candidate_window_count": len(windows),
                    "train_window_count": 0,
                    "query_history_action_ids": query_action_ids,
                    "query_history_source_sha256s": query_source_hashes,
                    "query_lineage_source_ids": sorted(query_lineage_source_ids),
                    "query_lineage_source_sha256s": sorted(query_lineage_source_hashes),
                    "decision_authority": "NONE", "native_memory_consumed": False,
                }

            # Bound work between candidate batches; a foreground caller can
            # abandon the optional recall without processing all 256 windows.
            candidate_latent_parts = []
            for start in range(0, len(train_windows), 32):
                if expired():
                    return {"status": "BUDGET_EXCEEDED", "items": [],
                            "checkpoint_sha256": active["checkpoint_sha256"],
                            "decision_authority": "NONE",
                            "native_memory_consumed": False}
                chunk = train_windows[start:start + 32]
                candidate_x = np.asarray(
                    [window["X"] for window, _target in chunk], dtype=np.float64
                )
                chunk_latents = np.asarray(
                    model.latent(candidate_x, target=False), dtype=np.float64
                )
                if (chunk_latents.ndim != 2
                        or chunk_latents.shape[0] != len(chunk)
                        or chunk_latents.shape[1] != query_latent.shape[1]
                        or not np.isfinite(chunk_latents).all()):
                    raise ValueError("invalid temporal episodic candidate latents")
                candidate_latent_parts.append(chunk_latents)
                if expired():
                    return {"status": "BUDGET_EXCEEDED", "items": [],
                            "checkpoint_sha256": active["checkpoint_sha256"],
                            "decision_authority": "NONE",
                            "native_memory_consumed": False}
            candidate_latents = np.concatenate(candidate_latent_parts, axis=0)
            distances = np.linalg.norm(candidate_latents - query_latent[0], axis=1)
            if not np.isfinite(distances).all():
                raise ValueError("nonfinite temporal episodic distances")

            verified_cache = {}
            rejected_cache = set()
            items = []
            rejected_windows = 0
            for action in world_model.ACTIONS[:limit]:
                matches = [
                    (float(distances[index]), index)
                    for index, (window, _target) in enumerate(train_windows)
                    if window["a"] == action
                ]
                matches.sort(
                    key=lambda item: (
                        item[0],
                        -train_windows[item[1]][1]["created"],
                        train_windows[item[1]][1]["action_id"],
                    )
                )
                for distance, index in matches[:MAX_RECALL_VERIFY_PER_ACTION]:
                    if expired():
                        break
                    window, target = train_windows[index]
                    receipts = []
                    missing = []
                    for action_id in window["action_ids"]:
                        receipt = verified_cache.get(action_id)
                        if receipt is None and action_id not in rejected_cache:
                            missing.append(action_id)
                        else:
                            receipts.append(receipt)
                    if missing:
                        verified, rejected = verify_rows(
                            self.store, [row_by_id[action_id] for action_id in missing]
                        )
                        verified_ids = {receipt.action_id for receipt in verified}
                        rejected_cache.update(
                            action_id for action_id in missing if action_id not in verified_ids
                        )
                        rejected_windows += int(rejected > 0)
                        for receipt in verified:
                            verified_cache[receipt.action_id] = receipt
                        receipts = [verified_cache.get(action_id) for action_id in window["action_ids"]]
                    if any(receipt is None for receipt in receipts):
                        continue
                    try:
                        receipt_source_ref_sets = [
                            _selection_source_refs(self.store, receipt) for receipt in receipts
                        ]
                    except (ValueError, TypeError, KeyError):
                        rejected_windows += 1
                        continue
                    receipt_lineage_pairs = sorted({
                        (ref["source_id"], ref["sha256"])
                        for ref_set in receipt_source_ref_sets for ref in ref_set
                    })
                    expected_lineage_pairs = sorted(
                        tuple(pair) for pair in window.get(
                            "lineage_source_pairs",
                            [[source, digest] for source, digest in zip(
                                window["source_ids"], window["source_sha256s"]
                            )],
                        )
                    )
                    if (receipt_lineage_pairs != expected_lineage_pairs
                            or [receipt.source_ref["source_id"] for receipt in receipts]
                            != window["source_ids"]
                            or [receipt.source_ref["sha256"] for receipt in receipts]
                            != window["source_sha256s"]):
                        rejected_windows += 1
                        continue
                    target_receipt = receipts[-1]
                    if (target_receipt.action_id != target["action_id"]
                            or target_receipt.status not in OBSERVED_RECALL_STATUSES):
                        rejected_windows += 1
                        continue
                    y = target["y"]
                    duration_s = math.expm1(min(20.0, float(y[0])))
                    output_chars = math.expm1(min(20.0, float(y[2]) * 8.0))
                    items.append({
                        "action": action,
                        "distance": distance,
                        "window_id": window["window_id"],
                        "action_id": target["action_id"],
                        "event_id": target_receipt.event_id,
                        "generation_id": target_receipt.generation_id,
                        "target_status": target_receipt.status,
                        "source_ref": target_receipt.source_ref,
                        "source_refs": receipt_source_ref_sets[-1],
                        "source_sha256": target_receipt.source_ref["sha256"],
                        "window_action_ids": list(window["action_ids"]),
                        "window_source_sha256s": list(window["source_sha256s"]),
                        "window_source_refs": [receipt.source_ref for receipt in receipts],
                        "window_source_ref_sets": receipt_source_ref_sets,
                        "window_lineage_source_pairs": [list(pair) for pair in receipt_lineage_pairs],
                        "observed_outcome": {
                            "duration_s": round(min(86400.0, max(0.0, duration_s)), 2),
                            "success": target_receipt.status == "FINAL",
                            "output_characters": int(round(min(1000000.0, max(0.0, output_chars)))),
                        },
                    })
                    break
                if expired():
                    break

            budget_exhausted = expired()
            status = (
                "EPISODIC_RECALL_PARTIAL" if budget_exhausted and items
                else "BUDGET_EXCEEDED" if budget_exhausted
                else "EPISODIC_RECALL_SHADOW" if items
                else "NO_VERIFIED_TRAIN_EPISODES"
            )
            return {
                "status": status,
                "items": items,
                "checkpoint_sha256": active["checkpoint_sha256"],
                "training_source_sha256": active["source_sha256"],
                "history_length": history_length,
                "query_history_action_ids": query_action_ids,
                "query_history_source_sha256s": query_source_hashes,
                "query_lineage_source_ids": sorted(query_lineage_source_ids),
                "query_lineage_source_sha256s": sorted(query_lineage_source_hashes),
                "candidate_window_count": len(windows),
                "train_window_count_before_cap": train_window_count_before_cap,
                "train_window_count": len(train_windows),
                "candidate_cap": MAX_RECALL_CANDIDATES,
                "candidate_sampling": "TEMPORALLY_STRATIFIED_TRAIN_ONLY",
                "verified_item_count": len(items),
                "rejected_windows": rejected_windows,
                "train_split_only": True,
                "heldout_used": False,
                "source_disjoint_from_query": True,
                "text_disclosed": False,
                "budget_exhausted": budget_exhausted,
                "decision_authority": "NONE",
                "native_memory_consumed": False,
                "native_body_consumed": False,
                "native_body_weights_changed": False,
            }

    def receiver_readout(self, role, session_id, action, history_length=2):
        if role not in ROLE_TARGETS or action not in world_model.ACTIONS:
            raise ValueError("unknown temporal receiver")
        if type(session_id) is not str or not session_id or history_length not in HISTORY_LENGTHS:
            raise ValueError("invalid temporal receiver context")
        with self._locked(False):
            state, _ = self._read_state()
            active = state["active"]
            if active is None:
                return {"status": "NO_CHECKPOINT", "role": role,
                        "decision_authority": "NONE", "native_body_consumed": False}
            utility = receiver_utility_gate(active["receiver_metrics"], role)
            support = int(active["action_support"].get(action, 0))
            if not utility["accepted"] or support < 8:
                return {
                    "status": "RECEIVER_UTILITY_REJECTED",
                    "role": role, "receiver_utility": utility,
                    "support_samples": support, "support_min_samples": 8,
                    "checkpoint_sha256": active["checkpoint_sha256"],
                    "source_sha256": active["source_sha256"],
                    "decision_authority": "NONE",
                    "native_body_consumed": False,
                    "native_body_weights_changed": False,
                }
            history, positions, history_error = _ordered_session_history(
                self.store, active["experience_rows"], session_id
            )
            if history_error:
                return {"status": history_error, "role": role,
                        "decision_authority": "NONE", "native_body_consumed": False}
            if len(history) < history_length:
                return {"status": "INSUFFICIENT_HISTORY", "role": role,
                        "decision_authority": "NONE", "native_body_consumed": False}
            history_rows = history[-history_length:]
            if len({row["generation_id"] for row in history_rows}) != 1:
                return {"status": "GENERATION_GAP", "role": role,
                        "decision_authority": "NONE", "native_body_consumed": False}
            if any(
                positions.get(right["event_id"], -99) != positions.get(left["event_id"], -100) + 1
                for left, right in zip(history_rows, history_rows[1:])
            ):
                return {"status": "NONCONTIGUOUS_HISTORY", "role": role,
                        "decision_authority": "NONE", "native_body_consumed": False}
            previous, latest = history_rows[-2:]
            x = (
                list(latest["s"])
                + np.mean(np.asarray([row["y"] for row in history_rows], dtype=np.float64), axis=0).tolist()
                + [float(any(row["censored"] for row in history_rows[:-1])),
                   float(latest["censored"]), float(history_length) / float(max(HISTORY_LENGTHS))]
            )
            model = self._load_model(active)
            latent, spread = model.predict(
                np.asarray([x], dtype=np.float64),
                np.asarray([world_model.onehot(action)], dtype=np.float64),
            )
            head = active["receiver_heads"][role]
            prediction = latent[0] @ np.asarray(head["weights"], dtype=np.float64) + np.asarray(head["bias"], dtype=np.float64)
            if not np.isfinite(prediction).all():
                raise ValueError("nonfinite temporal receiver prediction")
            if role == "B1_DETAIL":
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0))),
                }
            elif role == "B2_GIST":
                output = {"predicted_success_probability": float(np.clip(prediction[0], 0.0, 1.0))}
            else:
                output = {
                    "predicted_action_duration_s": max(0.0, math.expm1(min(20.0, float(prediction[0])))),
                    "predicted_success_probability": float(np.clip(prediction[1], 0.0, 1.0)),
                    "predicted_output_characters": max(0.0, math.expm1(min(20.0, float(prediction[2]) * 8.0))),
                }
            intent = active.get("learning_intents", {}).get(role)
            receipt = active.get("weight_delta_receipts", {}).get(role)
            return {
                "status": "SHADOW_READOUT_ONLY",
                "role": role, "prediction": output,
                "uncertainty": float(np.asarray(spread).reshape(-1)[0]),
                "history_length": history_length,
                "checkpoint_sha256": active["checkpoint_sha256"],
                "source_sha256": active["source_sha256"],
                "history_action_ids": [row["action_id"] for row in history_rows],
                "history_source_sha256s": [row["source_sha256"] for row in history_rows],
                "history_lineage_source_ids": sorted({
                    source for row in history_rows for source, _digest in _row_source_pairs(row)
                }),
                "history_lineage_source_sha256s": sorted({
                    digest for row in history_rows for _source, digest in _row_source_pairs(row)
                }),
                "history_source_ref_sets": [row.get("source_refs", []) for row in history_rows],
                "support_samples": support,
                "receiver_utility": utility,
                "learning_intent_id": intent.get("intent_id") if intent else None,
                "weight_delta_receipt_id": receipt.get("receipt_id") if receipt else None,
                "target_adapter_revision": intent.get("target_model_revision") if intent else None,
                "decision_authority": "NONE",
                "native_body_consumed": False,
                "native_body_weights_changed": False,
            }


    def receiver_matrix(self, session_id, actions, history_length=2, nonblocking=False,
                        warm_only=False):
        """Batch temporal B1/B2/SELF readouts for the foreground bodyview contract."""
        if (type(session_id) is not str or not session_id
                or history_length not in HISTORY_LENGTHS or type(warm_only) is not bool
                or type(actions) not in (list, tuple) or not actions
                or len(actions) > len(world_model.ACTIONS)
                or any(type(action) is not str or action not in world_model.ACTIONS
                       for action in actions)
                or len(set(actions)) != len(actions)):
            raise ValueError("invalid temporal receiver matrix request")
        with self._locked(False, blocking=not nonblocking):
            state, _ = self._read_state()
            active = state["active"]
            if active is None:
                return {"status": "NO_CHECKPOINT", "matrix": {},
                        "decision_authority": "NONE", "native_body_consumed": False,
                        "native_body_weights_changed": False}
            model = self._ephemeral_model
            if (model is None
                    or self._ephemeral_checkpoint_sha != active["checkpoint_sha256"]):
                model = None
                if warm_only:
                    return {
                        "status": "MODEL_NOT_WARM", "matrix": {},
                        "checkpoint_sha256": active["checkpoint_sha256"],
                        "decision_authority": "NONE", "native_body_consumed": False,
                        "native_body_weights_changed": False,
                    }
            history, positions, history_error = _ordered_session_history(
                self.store, active["experience_rows"], session_id
            )
            if history_error:
                return {"status": history_error, "matrix": {},
                        "decision_authority": "NONE", "native_body_consumed": False}
            if len(history) < history_length:
                return {"status": "INSUFFICIENT_HISTORY", "matrix": {},
                        "decision_authority": "NONE", "native_body_consumed": False}
            history_rows = history[-history_length:]
            if len({row["generation_id"] for row in history_rows}) != 1:
                return {"status": "GENERATION_GAP", "matrix": {},
                        "decision_authority": "NONE", "native_body_consumed": False}
            if any(
                positions.get(right["event_id"], -99) != positions.get(left["event_id"], -100) + 1
                for left, right in zip(history_rows, history_rows[1:])
            ):
                return {"status": "NONCONTIGUOUS_HISTORY", "matrix": {},
                        "decision_authority": "NONE", "native_body_consumed": False}
            previous, latest = history_rows[-2:]
            x = (
                list(latest["s"])
                + np.mean(np.asarray([row["y"] for row in history_rows], dtype=np.float64), axis=0).tolist()
                + [float(any(row["censored"] for row in history_rows[:-1])),
                   float(latest["censored"]), float(history_length) / float(max(HISTORY_LENGTHS))]
            )
            if model is None:
                model = self._load_model(active)
                self._ephemeral_model = model
                self._ephemeral_checkpoint_sha = active["checkpoint_sha256"]
            X = np.repeat(np.asarray([x], dtype=np.float64), len(actions), axis=0)
            A = np.asarray([world_model.onehot(action) for action in actions], dtype=np.float64)
            latent, spread = model.predict(X, A)
            if (len(latent) != len(actions) or len(spread) != len(actions)
                    or not np.isfinite(latent).all() or not np.isfinite(spread).all()):
                raise ValueError("nonfinite temporal receiver matrix")
            history_action_ids = [row["action_id"] for row in history_rows]
            history_source_sha256s = [row["source_sha256"] for row in history_rows]
            history_lineage_source_ids = sorted({
                source for row in history_rows for source, _digest in _row_source_pairs(row)
            })
            history_lineage_source_sha256s = sorted({
                digest for row in history_rows for _source, digest in _row_source_pairs(row)
            })
            history_source_ref_sets = [row.get("source_refs", []) for row in history_rows]
            active_intents = active.get("learning_intents", {})
            active_receipts = active.get("weight_delta_receipts", {})
            learning_intent_ids = {
                role: active_intents[role]["intent_id"]
                for role in LEARNING_INTENT_TARGET_ROLES if role in active_intents
            }
            weight_delta_receipt_ids = {
                role: active_receipts[role]["receipt_id"]
                for role in LEARNING_INTENT_TARGET_ROLES if role in active_receipts
            }
            matrix = {}
            for index, action in enumerate(actions):
                support = int(active["action_support"].get(action, 0))
                matrix[action] = {}
                for role in ROLE_TARGETS:
                    utility = receiver_utility_gate(active["receiver_metrics"], role)
                    intent = active_intents.get(role)
                    receipt = active_receipts.get(role)
                    common = {
                        "role": role,
                        "support_samples": support,
                        "support_min_samples": 8,
                        "support_scope": "TRAIN_SPLIT_ONLY",
                        "checkpoint_sha256": active["checkpoint_sha256"],
                        "source_sha256": active["source_sha256"],
                        "history_length": history_length,
                        "history_action_ids": history_action_ids,
                        "history_source_sha256s": history_source_sha256s,
                        "history_lineage_source_ids": history_lineage_source_ids,
                        "history_lineage_source_sha256s": history_lineage_source_sha256s,
                        "history_source_ref_sets": history_source_ref_sets,
                        "receiver_utility": utility,
                        "learning_intent_id": intent.get("intent_id") if intent else None,
                        "weight_delta_receipt_id": receipt.get("receipt_id") if receipt else None,
                        "target_adapter_revision": intent.get("target_model_revision") if intent else None,
                        "decision_authority": "NONE",
                        "native_body_consumed": False,
                        "native_body_weights_changed": False,
                    }
                    if not utility["accepted"]:
                        matrix[action][role] = common | {
                            "status": "RECEIVER_UTILITY_REJECTED"
                        }
                        continue
                    if support < 8:
                        matrix[action][role] = common | {
                            "status": "ACTION_SUPPORT_INSUFFICIENT"
                        }
                        continue
                    head = active["receiver_heads"][role]
                    prediction = (
                        latent[index] @ np.asarray(head["weights"], dtype=np.float64)
                        + np.asarray(head["bias"], dtype=np.float64)
                    )
                    if not np.isfinite(prediction).all():
                        raise ValueError("nonfinite temporal receiver prediction")
                    if role == "B1_DETAIL":
                        output = {
                            "predicted_action_duration_s": max(
                                0.0, math.expm1(min(20.0, float(prediction[0])))
                            ),
                            "predicted_output_characters": max(
                                0.0, math.expm1(min(20.0, float(prediction[1]) * 8.0))
                            ),
                        }
                    elif role == "B2_GIST":
                        output = {
                            "predicted_success_probability": float(
                                np.clip(prediction[0], 0.0, 1.0)
                            )
                        }
                    else:
                        output = {
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
                    uncertainty = float(np.asarray(spread[index]).reshape(-1)[0])
                    if not math.isfinite(uncertainty) or uncertainty < 0:
                        raise ValueError("invalid temporal receiver uncertainty")
                    matrix[action][role] = common | {
                        "status": "SHADOW_READOUT_ONLY",
                        "prediction": output,
                        "uncertainty": uncertainty,
                    }
            return {
                "status": "SHADOW_READOUT_ONLY",
                "matrix": matrix,
                "session_id": session_id,
                "history_length": history_length,
                "history_action_ids": history_action_ids,
                "history_source_sha256s": history_source_sha256s,
                "history_lineage_source_ids": history_lineage_source_ids,
                "history_lineage_source_sha256s": history_lineage_source_sha256s,
                "history_source_ref_sets": history_source_ref_sets,
                "checkpoint_sha256": active["checkpoint_sha256"],
                "source_sha256": active["source_sha256"],
                "learning_intent_ids": learning_intent_ids,
                "weight_delta_receipt_ids": weight_delta_receipt_ids,
                "decision_authority": "NONE",
                "native_body_consumed": False,
                "native_body_weights_changed": False,
            }


_RUNTIME_CONSUMER_LOCK = threading.RLock()


def runtime_consumer(runtime):
    """Return one Runtime-scoped temporal consumer shared by idle and body paths."""
    store = getattr(runtime, "store", None)
    if store is None:
        raise ValueError("Runtime store is required for temporal JEPA")
    with _RUNTIME_CONSUMER_LOCK:
        learner = getattr(runtime, "_temporal_world_jepa_consumer", None)
        if learner is None or getattr(learner, "store", None) is not store:
            learner = TemporalWorldJEPAStoreConsumer(store)
            setattr(runtime, "_temporal_world_jepa_consumer", learner)
        return learner


def consume_temporal_after_commit(store, home=None, *, limit=PAGE_SIZE, max_pages=MAX_PAGES,
                                  steps=None, cancel_check=None, consumer=None, runtime=None):
    """Runtime adapter: warm read-only cache even when learning gates are closed."""
    gates = permission_state(store)
    learner = consumer
    if learner is None and runtime is not None:
        learner = runtime_consumer(runtime)
    if not gates["learning_enabled"]:
        cache = learner.warm_active_checkpoint(nonblocking=True) if learner else {}
        return {"status": "OFF", "checkpoint_committed": False,
                "native_body_weights_changed": False,
                "receiver_cache_status": cache.get("status", "NOT_REQUESTED")}
    if not gates["optimizer_permission"]:
        cache = learner.warm_active_checkpoint(nonblocking=True) if learner else {}
        return {"status": "PENDING_OPTIMIZER_PERMISSION", "checkpoint_committed": False,
                "native_body_weights_changed": False,
                "receiver_cache_status": cache.get("status", "NOT_REQUESTED")}
    if learner is None:
        learner = TemporalWorldJEPAStoreConsumer(store)
    if getattr(learner, "store", None) is not store:
        raise ValueError("temporal consumer belongs to a different Store")
    result = learner.update(
        limit=limit, max_pages=max_pages,
        steps=min(gates["steps"], 40) if steps is None else steps,
        optimizer_permission=True, replay_mode=gates["replay_mode"],
        cancel_check=cancel_check,
    )
    if result.get("status") not in {"CANCELLED", "ERROR"}:
        cache = learner.warm_active_checkpoint(nonblocking=True)
        result["receiver_cache_status"] = cache.get("status", "UNKNOWN")
    return result


def _record_references_source(store, record, source_id, pending_action_ids=()):
    """Check retained artifacts and the full scanned T8 prefix for one source.

    experience_rows is a bounded replay window (MAX_ROWS), not a complete
    provenance ledger. Older training examples can therefore disappear from
    that list while their influence remains in the active/rollback parameters.
    The per-checkpoint scan cursor lets source-forget conservatively inspect
    the durable ActionOutcome ledger for every eligible row in that prefix.
    """
    if record is None:
        return False
    if any(_row_has_source(row, source_id) for row in record.get("experience_rows", [])):
        return True
    for holdout in record.get("retention_holdouts", []):
        if source_id in holdout.get("lineage_source_ids", holdout.get("source_ids", [])):
            return True
    for intent in record.get("learning_intents", {}).values():
        if (source_id in intent.get("source_ids", [])
                or source_id in intent.get("validation_source_ids", [])):
            return True

    cursor = record.get("scan_cursor")
    if type(cursor) is int and cursor > 0:
        pending = set(pending_action_ids)
        # The Store state caps pending rows at MAX_ROWS. Reading one more than
        # that bound guarantees that an eligible scanned row outside the
        # pending set is found without a large SQLite NOT IN parameter list.
        rows = store.rows(
            """SELECT a.id FROM actions a
               JOIN events e ON e.id=a.event_id
               WHERE a.rowid<=? AND e.source_id=?
                 AND a.outcome IS NOT NULL AND a.expected LIKE ?
                 AND a.status IN (
                   'FINAL','FAILED','ERROR','DEADLINE','REJECTED',
                   'CANCELLED','ABORTED','INTERRUPTED'
               )
               ORDER BY a.rowid ASC LIMIT ?""",
            (cursor, source_id, '%"forecast"%', MAX_ROWS + 1),
        )
        if type(rows) is not list:
            raise ValueError("temporal source-forget history query")
        for row in rows:
            if _mapping(row).get("id") not in pending:
                return True
        selected_rows = store.rows(
            """SELECT DISTINCT a.id AS action_id
               FROM actions a
               JOIN events e ON e.id=a.event_id
               JOIN packets p ON p.kind='ActionSelection'
                    AND p.event_id=a.event_id AND p.generation_id=e.generation_id
               WHERE a.rowid<=? AND a.outcome IS NOT NULL AND a.expected LIKE ?
                 AND a.status IN (
                     'FINAL','FAILED','ERROR','DEADLINE','REJECTED',
                     'CANCELLED','ABORTED','INTERRUPTED'
                 )
                 AND p.created<=a.created
                 AND COALESCE(json_extract(p.payload,'$.stage'),'COMMIT')!='PREDICTION'
                 AND EXISTS (
                     SELECT 1 FROM json_each(p.payload,'$.provenance') AS source_ref
                     WHERE json_extract(source_ref.value,'$.source_id')=?
                 )
               ORDER BY a.rowid ASC LIMIT ?""",
            (cursor, '%"forecast"%', source_id, MAX_ROWS + 1),
        )
        if type(selected_rows) is not list or len(selected_rows) > MAX_ROWS:
            return True
        for row in selected_rows:
            if _mapping(row).get("action_id") not in pending:
                return True
    return False


def _temporal_checkpoint_path(store, record):
    """Resolve a validated checkpoint name without following a symlink."""
    home = Path(store.home) / "world_jepa_temporal"
    if home.is_symlink() or (home.exists() and not home.is_dir()):
        raise ValueError("unsafe temporal checkpoint directory during source forget")
    if not home.exists():
        return None
    name = record["checkpoint"]
    if re.fullmatch(r"jepa-[0-9a-f]{32}\.npz", name) is None:
        raise ValueError("invalid temporal checkpoint path during source forget")
    path = home / name
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("unsafe temporal checkpoint file during source forget")
    return path if path.exists() else None


def invalidate_source_under_guard(store, source_id):
    """Invalidate source-tainted temporal checkpoints while the shared JEPA flock is held.

    This is checkpoint invalidation and source-verified replay, not gradient
    unlearning. Callers must already hold the same flock used by temporal
    updates and base WorldJEPA source revocation.
    """
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise ValueError("invalid temporal source-forget identity")
    state, version = store.state(STATE_KEY, empty_state())
    state = _validate_state(state)
    active = state["active"]
    previous = state["previous"]
    pending_action_ids = {
        row["action_id"] for row in state["pending_rows"]
        if _row_has_source(row, source_id)
    }
    active_uses = _record_references_source(
        store, active, source_id, pending_action_ids
    )
    previous_uses = _record_references_source(
        store, previous, source_id, pending_action_ids
    )

    affected = []
    if active_uses:
        affected.append(active)
    if previous_uses:
        affected.append(previous)

    # Validate all file paths before mutating persistent state. A clean
    # previous checkpoint must exist before it can replace a tainted active.
    affected_paths = {}
    for record in affected:
        path = _temporal_checkpoint_path(store, record)
        if path is not None:
            affected_paths[path.name] = path

    # A checkpoint that survives this forget operation must still be
    # loadable; otherwise do not publish a state that points at a missing file.
    if active_uses and previous is not None and not previous_uses:
        clean_path = _temporal_checkpoint_path(store, previous)
        if clean_path is None:
            raise ValueError("clean previous temporal checkpoint is missing")
        world_jepa_shadow_checkpoint.load(
            clean_path, previous["source_sha256"], previous["checkpoint_sha256"]
        )
    elif previous_uses and active is not None:
        clean_path = _temporal_checkpoint_path(store, active)
        if clean_path is None:
            raise ValueError("active temporal checkpoint is missing")
        world_jepa_shadow_checkpoint.load(
            clean_path, active["source_sha256"], active["checkpoint_sha256"]
        )

    next_active = active
    next_previous = previous
    scan_cursor = state["scan_cursor"]
    pending_by_id = {
        row["action_id"]: row
        for row in state["pending_rows"]
        if not _row_has_source(row, source_id)
    }
    removed_pending = len(state["pending_rows"]) - len(pending_by_id)
    requeued = 0

    if active_uses:
        if previous is not None and not previous_uses:
            # The rollback checkpoint is source-clean. Restore it and replay
            # only the active-only rows; the source-forget request is omitted.
            next_active = previous
            next_previous = None
            scan_cursor = previous["scan_cursor"]
            retained_ids = set(previous["fingerprints"])
            for row in active["experience_rows"]:
                if row["action_id"] in retained_ids or _row_has_source(row, source_id):
                    continue
                if row["action_id"] not in pending_by_id:
                    pending_by_id[row["action_id"]] = row
                    requeued += 1
            fallback = "PREVIOUS_CHECKPOINT_PROMOTED"
        else:
            # No retained checkpoint is clean. Rebuild from the durable T8
            # ledger after deletion; deleted SourceRefs will fail verification.
            next_active = None
            next_previous = None
            scan_cursor = 0
            pending_by_id = {}
            fallback = "FULL_T8_REPLAY_REQUIRED"
    elif previous_uses:
        # The live predictor is clean; only its rollback candidate is tainted.
        next_previous = None
        fallback = "ACTIVE_CHECKPOINT_PRESERVED"
    else:
        fallback = "NO_RETAINED_CHECKPOINT_REFERENCE"

    next_state = {
        "schema": SCHEMA,
        "revision": REVISION,
        "scan_cursor": scan_cursor,
        "pending_rows": sorted(
            pending_by_id.values(),
            key=lambda row: (row["created"], row["action_id"]),
        ),
        "active": next_active,
        "previous": next_previous,
    }
    if next_state != state:
        store.set_state(STATE_KEY, next_state, expected=version)

    # The state no longer references these checkpoints. The shared JEPA
    # flock prevents readers from observing the transition mid-cleanup.
    target_sha = (
        next_state["active"]["checkpoint_sha256"]
        if next_state["active"] is not None else None
    )
    with _TEMPORAL_CONSUMERS_LOCK:
        for cached in tuple(_TEMPORAL_CONSUMERS):
            if (cached.store is store
                    and (target_sha is None
                         or getattr(cached, "_ephemeral_checkpoint_sha", None) != target_sha)):
                cached._ephemeral_model = None
                cached._ephemeral_checkpoint_sha = None

    for path in affected_paths.values():
        path.unlink(missing_ok=True)

    report = {
        "temporal_pending_rows_removed": removed_pending,
        "temporal_checkpoints_invalidated": len(affected),
        "temporal_fallback": fallback,
        "temporal_rows_requeued": requeued,
    }
    return report



@contextmanager
def combined_source_forget_guard(store, source_id):
    """Compose base WorldJEPA revocation and temporal checkpoint invalidation."""
    from .world_jepa_consumer import _base_source_forget_guard

    with _base_source_forget_guard(store, source_id) as base_report:
        temporal_report = invalidate_source_under_guard(store, source_id)
        yield dict(base_report) | temporal_report
