"""Default-OFF, read-only C6 egress preflight for temporal F1/F5 DRAFT.

A fingerprint is NOT a user approval, capability token or output credential.
This module never commits, streams, finalizes or reveals candidate text.
"""
from __future__ import annotations

import hashlib
import json
import re

from .common import dumps
from .actionlearn import egress
from .f1f5_event_finalizer_candidate import _event_snapshot
from .f1f5_c5c6_atomic_draft_candidate import _locked_verified
from .f1f5_temporal_atomic_draft_candidate import check_temporal_staged_draft
from .f1f5_temporal_source_gate_candidate import _ordered_source
from .source_consumer import entities, strict_exact_amount


def _result(status, **extra):
    return {"schema": "v13.c6_temporal_draft_preflight.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def preflight_temporal_draft(cfg, memory, session, event_id, staged, *,
                             operator_opt_in=False, approval_receipt=None):
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(staged) is not dict
            or staged.get("status") != "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT"):
        return _result("INVALID_STAGED_REFERENCE")
    checked = check_temporal_staged_draft(cfg, memory, session, event_id, staged)
    if checked["status"] != "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT":
        return _result("SOURCE_OR_DRAFT_RED")
    store = memory.s
    try:
        with store.tx():
            event = _event_snapshot(memory, event_id, session)
            admitted = _locked_verified(memory, cfg, session, event)
            if (admitted is None
                    or admitted["source"]["memory_id"] != staged["source_memory_id"]):
                return _result("SOURCE_CHANGED")
            class _View:
                pass
            runtime = _View()
            runtime.store = store
            runtime.memory = memory
            if _ordered_source(runtime, session, event_id,
                               event["generation"], admitted) != "SOURCE_ORDER_VERIFIED":
                return _result("TEMPORAL_SOURCE_RED")
            drafts = store.rows(
                "SELECT id,status,role,text,metadata FROM messages "
                "WHERE event_id=? AND role='assistant'", (event_id,))
            if len(drafts) != 1 or drafts[0]["id"] != staged["draft_message_id"] \
                    or drafts[0]["status"] != "DRAFT":
                return _result("COMPETING_OR_COMMITTED_OUTPUT_RED")
            draft = drafts[0]
            meta = json.loads(draft["metadata"])
            if (meta.get("shadow") is not True
                    or meta.get("source_memory_id") != staged["source_memory_id"]
                    or meta.get("temporal_source_order")
                    != "VERIFIED_AT_DRAFT_TRANSACTION"
                    or meta.get("candidate_sha256") != staged["candidate_sha256"]):
                return _result("DRAFT_METADATA_RED")
            candidate = draft["text"]
            digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
            if digest != staged["candidate_sha256"]:
                return _result("CANDIDATE_HASH_RED")
            action = store.one(
                "SELECT kind,status,event_id FROM actions WHERE id=?",
                (staged["c5_action_id"],))
            if (not action or action["kind"] != "TEXT_REPORT"
                    or action["status"] != "DISPATCHED"
                    or action["event_id"] != event_id):
                return _result("C5_ACTION_RED")
            if not egress("TEXT_REPORT", candidate)["ok"]:
                return _result("C6_EGRESS_RED")
            source = admitted["source"]
            names = entities(source["topic"])
            if len(names) != 1:
                return _result("PROJECT_SCOPE_RED")
            name = next(iter(names))
            if not re.search(r"\b(?:Project|Projekt)\s+"+re.escape(name)+r"\b",
                             candidate, re.I):
                return _result("PROJECT_GROUNDING_RED")
            amount = source["value"].split(" ", 1)[0]
            if (not strict_exact_amount(candidate, amount)
                    or re.findall(r"(?<![A-Za-z0-9_])\d+(?:[.,]\d+)*(?![A-Za-z0-9_])",
                                  candidate) != [amount]):
                return _result("NUMERIC_GROUNDING_RED")
            fingerprint = hashlib.sha256(dumps({
                "kind": "C6_PREFLIGHT_NOT_APPROVAL",
                "session": session, "event": event_id,
                "generation": event["generation"],
                "draft_id": staged["draft_message_id"],
                "candidate_sha256": digest,
                "action_id": staged["c5_action_id"],
                "source_memory_id": staged["source_memory_id"],
                "source_ref": source["source_ref"],
            }).encode("utf-8")).hexdigest()
            return _result("NEEDS_REAL_TTY_APPROVAL",
                           fingerprint_sha256=fingerprint,
                           candidate_sha256=digest,
                           candidate_bytes=len(candidate.encode("utf-8")),
                           draft_message_id=staged["draft_message_id"],
                           preflight_only=True)
    except Exception:
        return _result("PREFLIGHT_INTEGRITY_RED")
