"""Default-OFF F1/F5 -> C5/C6 local TEXT_REPORT DRAFT, no output authority.

Software SHADOW only: source checks and the four C5/C6 staging writes share
one SQLite BEGIN IMMEDIATE. No FINAL, OUTPUT_COMMITTED, tool or native claim.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from .common import uid, now, dumps
from .contracts import packet, validate
from .f1f5_event_finalizer_candidate import _event_snapshot, _verified
from .agi import jef_c3_c5_c6_draft_shadow_run49 as c5


def _result(status, **extra):
    return {"schema": "v13.f1f5_c5c6_atomic_draft_shadow.v1",
            "status": status, "delivery_authority": 0, "output_committed": False,
            "tool_dispatches": 0, "learning_authority": 0, **extra}


def _candidate_ok(candidate):
    if type(candidate) is not str or not candidate.strip():
        return False
    try:
        encoded = candidate.encode("utf-8")
    except UnicodeError:
        return False
    return (len(encoded) <= 512
            and not any(ord(ch) < 32 and ch not in "\n\t" for ch in candidate))


def stage_draft(cfg, memory, session, event_id, generate, *, operator_opt_in=False):
    """Create exactly one C5/F3/action/C6 DRAFT set, or none.

    The callback is caller-supplied and this module is NOT Runtime-wired.
    A positive result is only a staged local hypothesis, not a permission to
    deliver. Future C6 must recheck permissions and source transactionally.
    """
    if operator_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if not callable(generate):
        return _result("INVALID_CALLBACK", callback_invoked=False)
    try:
        initial = _event_snapshot(memory, event_id, session)
        admitted = _verified(memory, cfg, session, initial)
        if admitted is None:
            return _result("CLARIFY", callback_invoked=False)
        if (_event_snapshot(memory, event_id, session) != initial
                or _verified(memory, cfg, session, initial) != admitted):
            return _result("STALE_BEFORE_DISPATCH", callback_invoked=False)
    except Exception:
        return _result("EVENT_OR_SOURCE_RED", callback_invoked=False)
    try:
        candidate = generate(admitted["messages"])
    except Exception:
        return _result("GENERATION_ERROR", callback_invoked=True)
    if not _candidate_ok(candidate):
        return _result("INVALID_CANDIDATE", callback_invoked=True)
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    store = memory.s
    try:
        with store.tx() as db:
            if (_event_snapshot(memory, event_id, session) != initial
                    or _verified(memory, cfg, session, initial) != admitted):
                return _result("SOURCE_CHANGED_BEFORE_DRAFT", callback_invoked=True)
            aid = uid("act")
            expected = {"stream_owner": "C5_REPORT_BROKER", "type": "TEXT_REPORT"}
            intent = packet("ActionIntent", "C5_REPORT_BROKER", event_id,
                            initial["generation"], action_id=aid,
                            action_type="TEXT_REPORT", permission="local_text_only")
            corollary = packet("CorollaryCopy", "F3_SELF", event_id,
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
                        "candidate_sha256": digest}), now())).lastrowid
    except Exception:
        return _result("STORE_OR_BINDING_RED", callback_invoked=True)
    return _result("DRAFT_STAGED_SHADOW_NO_COMMIT", callback_invoked=True,
                   draft_message_id=mid, c5_action_id=aid,
                   candidate_sha256=digest, candidate_bytes=len(candidate.encode("utf-8")),
                   source_memory_id=admitted["source"]["memory_id"])


def check_staged_draft(cfg, memory, session, event_id, staged):
    """Read-only validity check; NEVER approves future C6 delivery."""
    if (type(staged) is not dict
            or staged.get("status") != "DRAFT_STAGED_SHADOW_NO_COMMIT"
            or type(staged.get("draft_message_id")) is not int
            or type(staged.get("c5_action_id")) is not str
            or type(staged.get("candidate_sha256")) is not str):
        return _result("INVALID_STAGED_REFERENCE")
    store = memory.s
    try:
        with store.tx():
            snapshot = _event_snapshot(memory, event_id, session)
            admitted = _verified(memory, cfg, session, snapshot)
            if (admitted is None or
                    admitted["source"]["memory_id"] != staged.get("source_memory_id")):
                return _result("SOURCE_REVOKED_OR_CHANGED")
            row = store.one("SELECT text,metadata FROM messages WHERE id=?",
                            (staged["draft_message_id"],))
            if not row or hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != staged["candidate_sha256"]:
                return _result("DRAFT_TAMPERED")
            meta = json.loads(row["metadata"])
            if (type(meta) is not dict or meta.get("shadow") is not True
                    or meta.get("source_memory_id") != staged["source_memory_id"]
                    or meta.get("candidate_sha256") != staged["candidate_sha256"]):
                return _result("DRAFT_TAMPERED")
            if not c5._draft(store, staged["draft_message_id"], event_id, session, row["text"]):
                return _result("DRAFT_TAMPERED")
            if c5._c5(store, staged["c5_action_id"], event_id, session) is None:
                return _result("C5_BINDING_RED")
            return _result("DRAFT_BOUND_SHADOW_NO_COMMIT",
                           draft_message_id=staged["draft_message_id"],
                           candidate_sha256=staged["candidate_sha256"])
    except Exception:
        return _result("STORE_OR_BINDING_RED")
