"""Default-OFF F1/F5 temporal source order bound inside atomic C5 DRAFT write.

Separate from the original frozen atomic candidate; no Runtime installation,
no FINAL/output/tool/learning authority. Native generation is never invoked
while SQLite BEGIN IMMEDIATE is held.
"""
from __future__ import annotations

import hashlib

from .common import uid, now, dumps
from .contracts import packet, validate
from .f1f5_event_finalizer_candidate import _event_snapshot, _verified
from .f1f5_c5c6_atomic_draft_candidate import (
    _candidate_ok, _locked_verified, check_staged_draft)
from .f1f5_temporal_source_gate_candidate import _ordered_source


def _result(status, **extra):
    return {"schema": "v13.f1f5_temporal_atomic_draft_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def stage_temporal_atomic_draft(cfg, memory, session, event_id, generate, *,
                                operator_opt_in=False):
    if operator_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if not callable(generate):
        return _result("INVALID_CALLBACK", callback_invoked=False)
    store = memory.s
    # _ordered_source needs the runtime's exact memory/session/store identity.
    class _View:
        pass
    runtime = _View()
    runtime.store = store
    runtime.memory = memory
    try:
        initial = _event_snapshot(memory, event_id, session)
        admitted = _verified(memory, cfg, session, initial)
        if admitted is None:
            return _result("CLARIFY", callback_invoked=False)
        with store.tx():
            if (_event_snapshot(memory, event_id, session) != initial
                    or _locked_verified(memory, cfg, session, initial) != admitted):
                return _result("SOURCE_CHANGED_BEFORE_DISPATCH", callback_invoked=False)
            temporal = _ordered_source(
                runtime, session, event_id, initial["generation"], admitted)
            if temporal != "SOURCE_ORDER_VERIFIED":
                return _result(temporal, callback_invoked=False)
    except Exception:
        return _result("EVENT_OR_SOURCE_RED", callback_invoked=False)
    try:
        candidate = generate(admitted["messages"])
    except Exception:
        return _result("GENERATION_ERROR", callback_invoked=True)
    if not _candidate_ok(candidate):
        return _result("INVALID_CANDIDATE", callback_invoked=True)
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    try:
        with store.tx() as db:
            if (_event_snapshot(memory, event_id, session) != initial
                    or _locked_verified(memory, cfg, session, initial) != admitted):
                return _result("SOURCE_CHANGED_BEFORE_DRAFT", callback_invoked=True)
            temporal = _ordered_source(
                runtime, session, event_id, initial["generation"], admitted)
            if temporal != "SOURCE_ORDER_VERIFIED":
                return _result("TEMPORAL_CHANGED_BEFORE_DRAFT",
                               callback_invoked=True, temporal_reason=temporal)
            aid = uid("act")
            expected = {"stream_owner": "C5_REPORT_BROKER", "type": "TEXT_REPORT"}
            intent = packet(
                "ActionIntent", "C5_REPORT_BROKER", event_id,
                initial["generation"], action_id=aid,
                action_type="TEXT_REPORT", permission="local_text_only")
            corollary = packet(
                "CorollaryCopy", "F3_SELF", event_id,
                initial["generation"], action_id=aid,
                expected=expected, self_caused=True)
            validate("ActionIntent", intent)
            validate("CorollaryCopy", corollary)
            db.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",
                       (intent["packet_id"], "ActionIntent", event_id,
                        initial["generation"], dumps(intent), now()))
            db.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",
                       (corollary["packet_id"], "CorollaryCopy", event_id,
                        initial["generation"], dumps(corollary), now()))
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",
                       (aid, event_id, "TEXT_REPORT", "DISPATCHED",
                        corollary["packet_id"], dumps(expected), None, now()))
            mid = db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                (session, event_id, "assistant", candidate, "DRAFT",
                 dumps({"shadow": True, "source_memory_id": admitted["source"]["memory_id"],
                        "candidate_sha256": digest,
                        "temporal_source_order": "VERIFIED_AT_DRAFT_TRANSACTION"}), now())
            ).lastrowid
    except Exception:
        return _result("STORE_OR_BINDING_RED", callback_invoked=True)
    return _result("TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT",
                   callback_invoked=True, temporal_source_verified=True,
                   draft_message_id=mid, c5_action_id=aid,
                   candidate_sha256=digest,
                   candidate_bytes=len(candidate.encode("utf-8")),
                   source_memory_id=admitted["source"]["memory_id"])


def check_temporal_staged_draft(cfg, memory, session, event_id, staged):
    """Read-only C5/F3/DRAFT check; never output approval."""
    if (type(staged) is not dict
            or staged.get("status") != "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT"
            or staged.get("temporal_source_verified") is not True):
        return _result("INVALID_STAGED_REFERENCE")
    original = dict(staged, status="DRAFT_STAGED_SHADOW_NO_COMMIT")
    checked = check_staged_draft(cfg, memory, session, event_id, original)
    if checked["status"] != "DRAFT_BOUND_SHADOW_NO_COMMIT":
        return _result(checked["status"])
    try:
        with memory.s.tx():
            snapshot = _event_snapshot(memory, event_id, session)
            admitted = _locked_verified(memory, cfg, session, snapshot)
            if (admitted is None or
                    admitted["source"]["memory_id"] != staged["source_memory_id"]):
                return _result("SOURCE_CHANGED_AFTER_DRAFT")
            class _View:
                pass
            runtime = _View()
            runtime.store = memory.s
            runtime.memory = memory
            if _ordered_source(
                    runtime, session, event_id, snapshot["generation"], admitted
                    ) != "SOURCE_ORDER_VERIFIED":
                return _result("TEMPORAL_SOURCE_REVOKED_AFTER_DRAFT")
    except Exception:
        return _result("POST_STAGE_SOURCE_RED")
    return _result("TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT",
                   draft_message_id=staged["draft_message_id"],
                   candidate_sha256=staged["candidate_sha256"])
