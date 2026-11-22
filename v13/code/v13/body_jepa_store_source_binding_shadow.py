"""Run117BF read-only exact Store USER SourceRef binding for Body-JEPA research.

This is a source-authentication *preflight*, not permission to train. Both
context and target spans must be exact slices of one persisted authoritative
USER event. The Store is re-read on every call; caller metadata alone is never
trusted. No model, output, tool, adapter, Age or runtime activation.
"""
from __future__ import annotations

import hashlib
import json

from .body_jepa_grouped_source_candidate import validate_training_rows

REVISION = "v13-bjepa-store-source-binding-shadow-run117bf-v1"
_SPAN_KEYS = frozenset(("char_start", "char_end"))
_REF_KEYS = frozenset(("source_id", "sha256", "char_start", "char_end", "modality"))


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def _span(store, full, part, source):
    if type(part) is not dict or set(part) != _REF_KEYS:
        raise ValueError("SOURCE_SPAN_SHAPE_RED")
    if any(part[key] != full[key] for key in _REF_KEYS - _SPAN_KEYS):
        raise ValueError("SOURCE_SPAN_ORIGIN_RED")
    start, end = part["char_start"], part["char_end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source):
        raise ValueError("SOURCE_SPAN_RANGE_RED")
    value = store.read_source(part)
    if value != source[start:end]:
        raise ValueError("SOURCE_SPAN_BYTES_RED")
    return value


def _authenticate_row(store, session, row):
    if (type(row) is not dict or type(row.get("event_id")) is not str
            or not 1 <= len(row["event_id"]) <= 128
            or not row["event_id"].isprintable()):
        raise ValueError("EVENT_ROW_RED")
    full = row.get("source_ref")
    if type(full) is not dict or set(full) != _REF_KEYS:
        raise ValueError("EVENT_REF_SHAPE_RED")
    if (type(full["source_id"]) is not str or not 1 <= len(full["source_id"]) <= 128
            or type(full["sha256"]) is not str or len(full["sha256"]) != 64
            or type(full["char_start"]) is not int or full["char_start"] != 0
            or type(full["char_end"]) is not int or full["char_end"] < 1
            or full["modality"] != "text"):
        raise ValueError("EVENT_REF_FULL_SOURCE_RED")
    stored = store.one(
        "SELECT e.session_id,e.source_id,e.generation_id,e.packet,"
        "s.kind AS source_kind,s.deleted AS source_deleted "
        "FROM events e JOIN sources s ON e.source_id=s.id WHERE e.id=?",
        (row["event_id"],))
    if (stored is None or stored["session_id"] != session
            or stored["source_id"] != full["source_id"]
            or stored["source_kind"] != "USER"
            or stored["source_deleted"] != 0):
        raise ValueError("EVENT_SESSION_OR_SOURCE_RED")
    try:
        packet = json.loads(stored["packet"])
    except (ValueError, TypeError):
        raise ValueError("EVENT_PACKET_RED") from None
    if (type(packet) is not dict
            or packet.get("event_id") != row["event_id"]
            or packet.get("source_ref") != full
            or packet.get("authority") != "AUTHORITATIVE"
            or packet.get("kind") != "USER_TEXT"
            or packet.get("brain_generation_id") != stored["generation_id"]):
        raise ValueError("EVENT_PACKET_BINDING_RED")
    source = store.read_source(full)
    if (full["char_end"] != len(source)
            or hashlib.sha256(source.encode("utf-8")).hexdigest() != full["sha256"]):
        raise ValueError("EVENT_SOURCE_BYTES_RED")
    ctx = row.get("context_ref")
    tgt = row.get("target_ref")
    context = _span(store, full, ctx, source)
    target = _span(store, full, tgt, source)
    if (ctx["char_end"] > tgt["char_start"]
            or type(row.get("prompt")) is not str
            or type(row.get("target")) is not str
            or not 1 <= len(context) <= 2048
            or not 1 <= len(target) <= 512
            or row["prompt"] != context or row["target"] != target):
        raise ValueError("EVENT_CONTEXT_TARGET_TEXT_RED")
    if (row.get("source_id") != full["source_id"]
            or row.get("source_sha256") != full["sha256"]
            or row.get("context_source_sha256") != full["sha256"]
            or row.get("target_source_sha256") != full["sha256"]):
        raise ValueError("EVENT_SOURCE_GROUP_CLAIM_RED")
    return {"event_id": row["event_id"], "source_ref": full,
            "context_ref": ctx, "target_ref": tgt,
            "generation_id": stored["generation_id"]}


def bind_store_rows(store, session, rows, *, heldout_rows=(),
                    operator_opt_in=False):
    """Return non-authoritative digest/coverage; no source text leaves Store."""
    if operator_opt_in is not True:
        return {"status": "OFF", "authority": 0, "native_calls": 0,
                "output_committed": False, "learning_authority": 0}
    if type(session) is not str or not 1 <= len(session) <= 128 or not session.isprintable():
        raise ValueError("SESSION_REQUIRED_RED")
    # Validate bounded, disjoint groups before accessing untrusted row refs.
    preflight = validate_training_rows(rows, heldout_rows=heldout_rows)
    provenance = [_authenticate_row(store, session, row)
                  for row in tuple(rows) + tuple(heldout_rows)]
    return {
        "revision": REVISION, "status": "SHADOW_STORE_SOURCE_BOUND",
        "cohort_sha256": preflight["cohort_sha256"],
        "source_group_count": preflight["source_group_count"],
        "repeated_view_count": preflight["repeated_view_count"],
        "path": preflight["path"],
        "event_provenance_sha256": _digest(provenance),
        "source_authentication": "EXACT_STORE_USER_EVENT_SPANS",
        "semantic_truth_authority": False,
        "operator_opt_in": True, "requires_recheck_before_use": True,
        "output_committed": False, "tool_dispatches": 0,
        "delivery_authority": 0, "learning_authority": 0,
        "authority": 0, "native_calls": 0, "redmi_measured": False,
        "body_jepa_available": False, "runtime_jepa_weight": 0,
        "utility_proven": False, "whole_system_complete": False,
    }


def recheck_store_rows(store, session, rows, prior, *, heldout_rows=(),
                       operator_opt_in=False):
    """Re-read exact bytes after an external callback; no training authorization."""
    if type(prior) is not dict or prior.get("status") != "SHADOW_STORE_SOURCE_BOUND":
        raise ValueError("PRIOR_STORE_RECEIPT_RED")
    fresh = bind_store_rows(store, session, rows, heldout_rows=heldout_rows,
                            operator_opt_in=operator_opt_in)
    if fresh != prior:
        raise ValueError("STORE_SOURCE_CHANGED_RED")
    return fresh
