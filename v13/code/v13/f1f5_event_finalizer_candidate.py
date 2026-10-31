"""Default-off, event-bound F1/F5 no-delivery finalizer candidate.

This is a software SHADOW adapter, not wired to Runtime or C5/C6.
A caller-supplied generation callback is never a delivery permission.
"""
from __future__ import annotations

import hashlib
import json

from .source_consumer import verified_recall_messages


def _event_snapshot(memory, event_id, session):
    """Revalidate authoritative current USER source, event and generation."""
    if type(event_id) is not str or type(session) is not str:
        raise ValueError("EVENT_ID_OR_SESSION_TYPE")
    store = memory.s
    row = store.one("SELECT id,session_id,source_id,generation_id,packet "
                    "FROM events WHERE id=? AND session_id=?", (event_id, session))
    if not row:
        raise ValueError("EVENT_NOT_IN_SESSION")
    env = json.loads(row["packet"])
    if (type(env) is not dict or env.get("authority") != "AUTHORITATIVE"
            or env.get("kind") != "USER_TEXT" or env.get("event_id") != event_id
            or env.get("brain_generation_id") != row["generation_id"]
            or row["generation_id"] != store.generation_id):
        raise ValueError("EVENT_NOT_CURRENT_AUTHORITATIVE_USER")
    ref = env.get("source_ref")
    if (type(ref) is not dict or ref.get("source_id") != row["source_id"]
            or ref.get("modality") != "text" or ref.get("char_start") != 0):
        raise ValueError("EVENT_SOURCE_REF_INVALID")
    query = store.read_source(ref)
    source = store.one("SELECT chars FROM sources WHERE id=?", (row["source_id"],))
    if (not source or ref.get("char_end") != source["chars"]
            or type(query) is not str or not query.strip()):
        raise ValueError("EVENT_SOURCE_NOT_WHOLE")
    return {"query": query, "ref": ref, "generation": row["generation_id"]}


def _verified(memory, cfg, session, snapshot):
    admitted = verified_recall_messages(cfg, snapshot["query"], session, memory)
    decision = admitted.get("decision", {})
    if decision.get("status") != "ADMITTED" or admitted.get("messages") is None:
        return None
    return {"source": decision.get("source"), "count": decision.get("admitted_count"),
            "messages": admitted["messages"]}


def shadow_candidate(cfg, memory, session, event_id, generate, *, operator_opt_in=False):
    """Run an explicitly opted-in synthetic/native callback but NEVER deliver.

    Returns only status and an output digest; a future Runtime integration needs
    separate C5/C6 approval, atomic output checks and user-facing consent.
    A concurrent revoke during callback is caught by the final recheck; no
    claim of atomic multi-process source lock or revocation of a model prompt.
    """
    result = {"schema": "v13.f1f5_event_finalizer_candidate.v1",
              "status": "OFF", "callback_invoked": False,
              "delivery_authority": 0, "output_committed": False,
              "tool_dispatches": 0, "learning_authority": 0}
    if operator_opt_in is not True:
        return result
    if not callable(generate):
        return dict(result, status="INVALID_CALLBACK")
    try:
        initial = _event_snapshot(memory, event_id, session)
        first = _verified(memory, cfg, session, initial)
        if first is None:
            return dict(result, status="CLARIFY")
        # The second read is intentionally adjacent to callback invocation.
        before = _event_snapshot(memory, event_id, session)
        second = _verified(memory, cfg, session, before)
        if before != initial or second != first:
            return dict(result, status="STALE_BEFORE_DISPATCH")
    except Exception:
        return dict(result, status="EVENT_OR_SOURCE_RED")
    try:
        result["callback_invoked"] = True
        candidate = generate(second["messages"])
    except Exception:
        return dict(result, status="GENERATION_ERROR")
    if (type(candidate) is not str or not candidate.strip()
            or len(candidate.encode("utf-8", errors="surrogatepass")) > 512
            or any(ord(ch) < 32 and ch not in "\n\t" for ch in candidate)):
        return dict(result, status="INVALID_CANDIDATE")
    try:
        after = _event_snapshot(memory, event_id, session)
        third = _verified(memory, cfg, session, after)
        if after != initial or third != second:
            return dict(result, status="HELD_REVOKED_OR_CHANGED")
    except Exception:
        return dict(result, status="HELD_REVOKED_OR_CHANGED")
    return dict(result, status="SHADOW_HELD",
                candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
                candidate_bytes=len(candidate.encode("utf-8")))
