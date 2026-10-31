"""Default-OFF mixed-range JEF/B1/B2/C3 -> C5/F3 DRAFT -> C6 SHADOW.

The legacy C5 stager accepts only Maximum/Maximum JEF grammar. This isolated
candidate instead preserves the authenticated mixed Minimum/Maximum grammar
of Run73/74, with an atomic C5 DRAFT and independently rechecked C6 shadow.
A trusted C3 callback is called ONCE by Run84, never again by this module.
"""
from __future__ import annotations

import hashlib
import json

from .common import dumps, uid, now
from .contracts import packet, validate
from . import jef_b1b2_c3_dual_source_shadow as dual
from . import jef_b1b2_c3_postgen_shadow as postgen
from . import jef_f1f5_range_admission_shadow as admission
from .jef_f1f5_live_current_candidate import _latest_authoritative_user
from .jef_c3_c5_c6_fallback_draft_candidate import (
    _existing, _draft, EXPECTED,
)
from .c5_shadow_action_binding import _c5_shadow
from .jef_c3_schema_draft_candidate import decode_action

STATUS = "DUAL_SOURCE_C5_C6_DRAFT_PREFLIGHT_SHADOW"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _result(status, **extra):
    return {
        "schema": "v13.jef_b1b2_c3_c5c6_draft_shadow.v2",
        "status": status,
        "delivery_authority": 0,
        "learning_authority": 0,
        "tool_dispatches": 0,
        "output_committed": False,
        "native_proof": False,
        "real_tty_approved": False,
        "c3_native_output_receipt_persisted": False,
        "c3_receiver_success": False,
        "whole_system_complete": False,
        "jepa_weight": 0,
        **extra,
    }


def _still_current(runtime, event, offers, ids, expected):
    """Reconstruct all sources, role revisions, retained state and JEF action."""
    current = dual.build(runtime, event, offers, ids, operator_opt_in=True)
    return (current.get("status") == dual.STATUS
            and current.get("messages_sha256")
            == expected["dual_source_messages_sha256"]
            and current.get("jef_messages_sha256")
            == expected["jef_messages_sha256"]
            and current.get("b1b2_messages_sha256")
            == expected["b1b2_messages_sha256"]
            and current.get("typed_jef_action") == expected["source_action"]
            and current.get("human_source_lineage_verified") is True
            and current.get("formatter_only") is True)


def _human(runtime, event, ids, action, refs):
    """Source and human lineage recheck, also valid under Store.tx lock."""
    decision = admission.decide(
        runtime.memory, runtime.session, event["event_id"],
        event["source_ref"], ids, operator_opt_in=True)
    return (decision.get("admission_status") == admission.READY
            and decision.get("human_source_lineage_verified") is True
            and decision.get("suggested_action") == action
            and decision.get("source_ref_sha256") == refs
            and decision.get("authority") == 0
            and decision.get("model_called") is False
            and decision.get("native_calls") == 0)


def _stage_range(runtime, event, offers, ids, meta):
    """Atomic source-bound C5/F3 SHADOW DRAFT; no model and no delivery."""
    store = runtime.store
    session = runtime.session
    event_id = event["event_id"]
    try:
        with store.tx() as db:
            if _existing(store, session, event_id):
                return _result("EXISTING_DRAFT_OR_ACTION_RED")
            if (_latest_authoritative_user(store, session) != event_id
                    or not _human(runtime, event, ids,
                                  meta["source_action"],
                                  meta["source_ref_sha256"])
                    or not _still_current(runtime, event, offers, ids, meta)):
                return _result("SOURCE_CHANGED_BEFORE_ATOMIC_DRAFT")
            row = store.one(
                "SELECT session_id,generation_id FROM events WHERE id=?",
                (event_id,))
            if (row is None or row["session_id"] != session
                    or row["generation_id"] != store.generation_id):
                return _result("EVENT_GENERATION_BINDING_RED")
            generation = row["generation_id"]
            aid = uid("act")
            intent = packet(
                "ActionIntent", "C5_REPORT_BROKER", event_id, generation,
                action_id=aid, action_type="TEXT_REPORT",
                permission="local_text_only")
            corollary = packet(
                "CorollaryCopy", "F3_SELF", event_id, generation,
                action_id=aid, expected=EXPECTED, self_caused=True)
            validate("ActionIntent", intent)
            validate("CorollaryCopy", corollary)
            db.execute(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                (intent["packet_id"], "ActionIntent", event_id,
                 generation, dumps(intent), now()))
            db.execute(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                (corollary["packet_id"], "CorollaryCopy", event_id,
                 generation, dumps(corollary), now()))
            db.execute(
                "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",
                (aid, event_id, "TEXT_REPORT", "SHADOW_DRAFT",
                 corollary["packet_id"], dumps(EXPECTED), None, now()))
            mid = db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,"
                "metadata,created) VALUES (?,?,?,?,?,?,?)",
                (session, event_id, "assistant", meta["source_action"],
                 "DRAFT", dumps(meta), now())).lastrowid
        return _result("ATOMIC_RANGE_DRAFT_STAGED_SHADOW",
                       draft_message_id=mid, c5_action_id=aid,
                       shadow_draft_may_exist=True)
    except Exception:
        return _result("ATOMIC_RANGE_DRAFT_STORE_RED",
                       shadow_draft_may_exist=True)


def _c6_preflight(runtime, event, offers, ids, meta, staged):
    """Read-only integrity challenge of persisted draft; no approval."""
    store = runtime.store
    session = runtime.session
    event_id = event["event_id"]
    try:
        with store.tx():
            if (_latest_authoritative_user(store, session) != event_id
                    or not _human(runtime, event, ids,
                                  meta["source_action"],
                                  meta["source_ref_sha256"])
                    or not _still_current(runtime, event, offers, ids, meta)):
                return _result("C6_SOURCE_CHANGED_RED")
            if (store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE event_id=? "
                    "AND session_id=? AND role='assistant'",
                    (event_id, session))["n"] != 1
                    or store.one(
                    "SELECT COUNT(*) AS n FROM actions WHERE event_id=? "
                    "AND kind='TEXT_REPORT'", (event_id,))["n"] != 1):
                return _result("C6_DUPLICATE_DRAFT_OR_ACTION_RED")
            if (not _draft(store, staged["draft_message_id"], event_id,
                           session, meta["source_action"])
                    or _c5_shadow(store, staged["c5_action_id"],
                           event_id, session) is None):
                return _result("C6_C5_F3_BINDING_RED")
            row = store.one(
                "SELECT metadata FROM messages WHERE id=?",
                (staged["draft_message_id"],))
            stored = json.loads(row["metadata"])
            if (type(stored) is not dict or stored != meta
                    or _sha(meta["source_action"].encode("utf-8"))
                    != meta["candidate_sha256"]
                    or decode_action(meta.get("callback_output_json"))
                    != meta["source_action"]
                    or _sha(meta["callback_output_json"].encode("utf-8"))
                    != meta["callback_output_sha256"]):
                return _result("C6_PERSISTED_METADATA_RED")
        return _result("C6_DRAFT_INTEGRITY_SHADOW")
    except Exception:
        return _result("C6_STORE_OR_BINDING_RED")


def evaluate(runtime, event, offer_packet_ids, memory_ids, generator, *,
             operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Stage one SHADOW draft from one validated callback, C6 read-only check.

    A post-stage race can leave an orphan DRAFT; it is never rolled back by
    this bridge and never becomes an output/TTY permission credential.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if not callable(generator):
        return _result("INVALID_GENERATOR", callback_invoked=False)
    if type(event) is not dict or type(memory_ids) not in (list, tuple):
        return _result("INVALID_INPUT", callback_invoked=False)
    try:
        event_id = event["event_id"]
        if _existing(runtime.store, runtime.session, event_id):
            return _result("EXISTING_DRAFT_OR_ACTION_RED",
                           callback_invoked=False)
    except Exception:
        return _result("PREFLIGHT_INTEGRITY_RED", callback_invoked=False)
    captured = {}

    def capture_once(messages, schema):
        raw = generator(messages, schema)
        if type(raw) is str:
            try:
                if 0 < len(raw.encode("utf-8", "strict")) <= 1024:
                    captured["raw"] = raw
            except UnicodeError:
                pass
        return raw

    checked = postgen.evaluate(
        runtime, event, offer_packet_ids, memory_ids, capture_once,
        operator_opt_in=True, callback_opt_in=True)
    if checked.get("status") != postgen.STATUS:
        return _result("DUAL_SOURCE_C3_RED",
                       callback_invoked=checked.get("callback_invoked", False),
                       component_status=checked.get("status"))
    action = checked.get("parsed_action")
    if (action not in ("A", "B", "NONE")
            or checked.get("source_rechecked") is not True
            or any(type(checked.get(key)) is not str
                   for key in ("messages_sha256", "jef_messages_sha256",
                               "b1b2_messages_sha256", "output_sha256"))):
        return _result("POSTGEN_RECEIPT_RED", callback_invoked=True)
    raw = captured.get("raw")
    if (type(raw) is not str or decode_action(raw) != action
            or _sha(raw.encode("utf-8")) != checked["output_sha256"]):
        return _result("CALLBACK_REPLAY_SOURCE_RED", callback_invoked=True)
    decision = admission.decide(
        runtime.memory, runtime.session, event_id, event["source_ref"],
        memory_ids, operator_opt_in=True)
    if (decision.get("admission_status") != admission.READY
            or decision.get("suggested_action") != action
            or decision.get("human_source_lineage_verified") is not True
            or type(decision.get("source_ref_sha256")) is not list):
        return _result("RANGE_HUMAN_SOURCE_RED", callback_invoked=True)
    meta = {
        "shadow": True,
        "origin": "DUAL_SOURCE_SCHEMA_EXACT_SHADOW",
        "source_action": action,
        "source_ref_sha256": decision["source_ref_sha256"],
        "dual_source_messages_sha256": checked["messages_sha256"],
        "jef_messages_sha256": checked["jef_messages_sha256"],
        "b1b2_messages_sha256": checked["b1b2_messages_sha256"],
        "callback_output_sha256": checked["output_sha256"],
        "callback_output_json": raw,
        "candidate_sha256": _sha(action.encode("utf-8")),
        "model_formatter_status": postgen.STATUS,
        "body_hypotheses_are_facts": False,
    }
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              meta):
            return _result("SOURCE_CHANGED_BEFORE_DRAFT",
                           callback_invoked=True)
    except Exception:
        return _result("SOURCE_RECHECK_INTEGRITY_RED",
                       callback_invoked=True)
    staged = _stage_range(runtime, event, offer_packet_ids, memory_ids, meta)
    if staged.get("status") != "ATOMIC_RANGE_DRAFT_STAGED_SHADOW":
        return _result("C5_DRAFT_STAGE_RED", callback_invoked=True,
                       component_status=staged.get("status"),
                       shadow_draft_may_exist=staged.get(
                           "shadow_draft_may_exist", False))
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              meta):
            return _result("SOURCE_CHANGED_AFTER_DRAFT",
                           callback_invoked=True, shadow_draft_may_exist=True)
    except Exception:
        return _result("POSTSTAGE_SOURCE_INTEGRITY_RED",
                       callback_invoked=True, shadow_draft_may_exist=True)
    c6 = _c6_preflight(runtime, event, offer_packet_ids, memory_ids,
                       meta, staged)
    if c6.get("status") != "C6_DRAFT_INTEGRITY_SHADOW":
        return _result("C6_DRAFT_PREFLIGHT_RED", callback_invoked=True,
                       component_status=c6.get("status"),
                       shadow_draft_may_exist=True)
    try:
        if not _still_current(runtime, event, offer_packet_ids, memory_ids,
                              meta):
            return _result("SOURCE_CHANGED_AFTER_C6_PREFLIGHT",
                           callback_invoked=True, shadow_draft_may_exist=True)
    except Exception:
        return _result("POSTC6_SOURCE_INTEGRITY_RED",
                       callback_invoked=True, shadow_draft_may_exist=True)
    return _result(
        STATUS, callback_invoked=True, source_rechecked=True,
        formatter_match_shadow=True, c5_draft_staged=True,
        c6_preflight_only=True, shadow_draft_may_exist=True,
        c6_is_not_approval=True, shadow_action_status="SHADOW_DRAFT",
        typed_jef_action=action,
        dual_source_messages_sha256=meta["dual_source_messages_sha256"],
        callback_output_sha256=meta["callback_output_sha256"],
        dual_source_digest_persisted=True,
        callback_output_digest_persisted=True,
        callback_output_json_persisted=True,
        draft_message_id=staged["draft_message_id"],
        c5_action_id=staged["c5_action_id"])
