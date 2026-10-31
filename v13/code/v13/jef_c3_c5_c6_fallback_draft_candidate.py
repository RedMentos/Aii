"""Default-OFF JEF human F1/F5 -> C3 -> C5/F3 DRAFT -> C6 SHADOW.

Source-only fallback is not a C3 success. SQLite DRAFT is not visible output.
No native proof, TTY approval, tool, learning, or production Runtime wiring.
"""
from __future__ import annotations

import hashlib
import json

from .common import dumps, uid, now
from .contracts import packet, validate
from . import jef_c3_postgen_recheck_candidate as postgen
from . import jef_c3_typed_envelope_candidate as typed
from . import jef_f1f5_source_admission as admission
from .jef_f1f5_live_current_candidate import _latest_authoritative_user
from .agi.jef_c3_c5_c6_draft_shadow_run49 import _c5, _draft

STAGED = "JEF_C5_SOURCE_ONLY_DRAFT_STAGED_SHADOW"
SOURCE_READY = "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
HUMAN_READY = "F1F5_SESSION_VERIFIED_SHADOW"
EXPECTED = {"stream_owner": "C5_REPORT_BROKER", "type": "TEXT_REPORT"}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _result(status, **extra):
    return {
        "schema": "v13.jef_c3_c5_c6_fallback_draft_shadow.v1",
        "status": status,
        "delivery_authority": 0,
        "output_committed": False,
        "tool_dispatches": 0,
        "learning_authority": 0,
        "native_proof": False,
        "c3_receiver_success": False,
        "real_tty_approved": False,
        **extra,
    }


def _existing(store, session, event_id):
    return (store.one(
        "SELECT id FROM messages WHERE event_id=? AND session_id=? "
        "AND role='assistant' LIMIT 1", (event_id, session)) is not None
        or store.one(
            "SELECT id FROM actions WHERE event_id=? AND kind='TEXT_REPORT' LIMIT 1",
            (event_id,)) is not None)


def _locked_human(memory, session, event_id, current_ref, memory_ids,
                  expected_action, expected_refs):
    """Caller holds Store.tx; avoid nested BEGIN IMMEDIATE."""
    store = memory.s
    if _latest_authoritative_user(store, session) != event_id:
        return False
    decision = admission.decide(memory, session, event_id,
                                current_ref, memory_ids)
    return (
        decision.get("admission_status") == HUMAN_READY
        and decision.get("human_source_lineage_verified") is True
        and decision.get("suggested_action") == expected_action
        and decision.get("source_ref_sha256") == expected_refs
        and decision.get("authority") == 0
        and decision.get("model_called") is False
        and decision.get("native_calls") == 0
    )


def stage(memory, session, event_id, current_ref, memory_ids, generator, *,
          operator_opt_in=False, callback_opt_in=False,
          approval_receipt=None, formatter_receipt=None):
    """Stage exactly one source-verified DRAFT; never commit output."""
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", callback_invoked=False)
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED", callback_invoked=False)
    if not callable(generator):
        return _result("INVALID_CALLBACK", callback_invoked=False)
    store = memory.s
    try:
        with store.tx():
            if _existing(store, session, event_id):
                return _result("EXISTING_OUTPUT_OR_ACTION_RED",
                               callback_invoked=False)
    except Exception:
        return _result("OUTPUT_PREFLIGHT_INTEGRITY_RED", callback_invoked=False)

    guarded = postgen.evaluate(
        memory, session, event_id, current_ref, memory_ids, generator,
        operator_opt_in=True)
    status = guarded.get("status")
    if status not in ("FORMATTER_MATCH_SHADOW", "FORMATTER_MISMATCH_RED"):
        return _result("JEF_C3_GENERATION_RED",
                       callback_invoked=guarded.get("generator_invoked", False),
                       generator_status=status)
    try:
        envelope = typed.build_jef_c3_typed_envelope(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (envelope.get("status") != SOURCE_READY
                or envelope.get("messages_sha256")
                != guarded.get("prompt_sha256")):
            return _result("SOURCE_CHANGED_BEFORE_DRAFT",
                           callback_invoked=True)
        action = envelope["typed_jef_action"]
        origin = ("MODEL_EXACT_SHADOW" if status == "FORMATTER_MATCH_SHADOW"
                  else "SOURCE_ONLY_FALLBACK_C3_RED")
        if (status == "FORMATTER_MATCH_SHADOW"
                and guarded.get("output_sha256") != _sha(action.encode("utf-8"))):
            return _result("FORMATTER_DIGEST_RED", callback_invoked=True)
        if (status == "FORMATTER_MISMATCH_RED"
                and (guarded.get("source_only_fallback_action") != action
                     or guarded.get("source_only_fallback_verified") is not True)):
            return _result("FALLBACK_SOURCE_RED", callback_invoked=True)
        refs = envelope["source_ref_sha256"]
        prompt_sha = envelope["messages_sha256"]
        candidate_sha = _sha(action.encode("utf-8"))
        metadata = {
            "shadow": True,
            "origin": origin,
            "source_action": action,
            "source_ref_sha256": refs,
            "prompt_sha256": prompt_sha,
            "candidate_sha256": candidate_sha,
            "model_formatter_status": status,
        }
        schema_receipt = None
        if formatter_receipt is not None:
            if not callable(formatter_receipt) or status != "FORMATTER_MATCH_SHADOW":
                return _result("SCHEMA_RECEIPT_RED", callback_invoked=True)
            try:
                from .jef_c3_schema_draft_candidate import decode_action, SCHEMA_SHA256
                raw_schema_output = formatter_receipt()
                if decode_action(raw_schema_output) != action:
                    return _result("SCHEMA_RECEIPT_RED", callback_invoked=True)
                raw_bytes = raw_schema_output.encode("utf-8", "strict")
                schema_receipt = {
                    "schema_sha256": SCHEMA_SHA256,
                    "output_sha256": _sha(raw_bytes),
                    "output_bytes": len(raw_bytes),
                    "prompt_sha256": prompt_sha,
                }
                metadata["schema_receipt"] = schema_receipt
            except Exception:
                return _result("SCHEMA_RECEIPT_RED", callback_invoked=True)
        with store.tx() as db:
            if _existing(store, session, event_id):
                return _result("EXISTING_OUTPUT_OR_ACTION_RED",
                               callback_invoked=True)
            if not _locked_human(memory, session, event_id, current_ref,
                                 memory_ids, action, refs):
                return _result("SOURCE_CHANGED_BEFORE_DRAFT",
                               callback_invoked=True)
            event = store.one(
                "SELECT session_id,generation_id FROM events WHERE id=?",
                (event_id,))
            if event is None or event["session_id"] != session:
                return _result("EVENT_BINDING_RED", callback_invoked=True)
            generation = event["generation_id"]
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
                (aid, event_id, "TEXT_REPORT", "DISPATCHED",
                 corollary["packet_id"], dumps(EXPECTED), None, now()))
            mid = db.execute(
                "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                "VALUES (?,?,?,?,?,?,?)",
                (session, event_id, "assistant", action, "DRAFT",
                 dumps(metadata), now())).lastrowid
        result = _result(
            STAGED, callback_invoked=True,
            draft_message_id=mid, c5_action_id=aid,
            source_action=action, source_ref_sha256=refs,
            prompt_sha256=prompt_sha, candidate_sha256=candidate_sha,
            candidate_bytes=len(action.encode("utf-8")),
            model_formatter_status=status, draft_origin=origin,
            source_only_fallback=(status == "FORMATTER_MISMATCH_RED"),
            shadow_draft_may_exist=True)
        if schema_receipt is not None:
            result["schema_receipt"] = schema_receipt
            result["schema_receipt_persisted"] = True
        return result
    except Exception:
        return _result("STORE_OR_BINDING_RED", callback_invoked=True,
                       shadow_draft_may_exist=True)


def preflight(memory, session, event_id, current_ref, memory_ids, staged, *,
              operator_opt_in=False, approval_receipt=None):
    """Read-only C6 challenge, never a TTY credential or output commit."""
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(staged) is not dict or staged.get("status") != STAGED
            or type(staged.get("draft_message_id")) is not int
            or type(staged.get("c5_action_id")) is not str
            or staged.get("source_action") not in ("A", "B", "NONE")
            or staged.get("draft_origin") not in (
                "MODEL_EXACT_SHADOW", "SOURCE_ONLY_FALLBACK_C3_RED")
            or type(staged.get("source_ref_sha256")) is not list
            or type(staged.get("prompt_sha256")) is not str):
        return _result("INVALID_STAGED_REFERENCE")
    try:
        current = typed.build_jef_c3_typed_envelope(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (current.get("status") != SOURCE_READY
                or current.get("messages_sha256") != staged["prompt_sha256"]
                or current.get("source_ref_sha256") != staged["source_ref_sha256"]
                or current.get("typed_jef_action") != staged["source_action"]):
            return _result("SOURCE_PROMPT_CHANGED_AFTER_DRAFT")
    except Exception:
        return _result("C6_SOURCE_PROMPT_INTEGRITY_RED")
    store = memory.s
    try:
        with store.tx():
            action = staged["source_action"]
            refs = staged["source_ref_sha256"]
            if not _locked_human(memory, session, event_id, current_ref,
                                 memory_ids, action, refs):
                return _result("SOURCE_CHANGED_AFTER_DRAFT")
            if _existing(store, session, event_id) is False:
                return _result("DRAFT_MISSING")
            if (store.one(
                    "SELECT COUNT(*) AS n FROM messages WHERE event_id=? "
                    "AND session_id=? AND role='assistant'",
                    (event_id, session))["n"] != 1
                    or store.one(
                    "SELECT COUNT(*) AS n FROM actions WHERE event_id=? "
                    "AND kind='TEXT_REPORT'", (event_id,))["n"] != 1):
                return _result("DUPLICATE_OUTPUT_OR_ACTION_RED")
            if not _draft(store, staged["draft_message_id"], event_id,
                          session, action):
                return _result("DRAFT_BINDING_RED")
            if _c5(store, staged["c5_action_id"], event_id, session) is None:
                return _result("C5_F3_BINDING_RED")
            row = store.one(
                "SELECT metadata FROM messages WHERE id=?",
                (staged["draft_message_id"],))
            meta = json.loads(row["metadata"])
            expected_meta = {
                "shadow": True,
                "origin": staged["draft_origin"],
                "source_action": action,
                "source_ref_sha256": refs,
                "prompt_sha256": staged["prompt_sha256"],
                "candidate_sha256": staged["candidate_sha256"],
                "model_formatter_status": staged["model_formatter_status"],
            }
            if "schema_receipt" in staged:
                receipt = staged["schema_receipt"]
                from .jef_c3_schema_draft_candidate import SCHEMA_SHA256
                if (type(receipt) is not dict
                        or set(receipt) != {"schema_sha256", "output_sha256",
                                            "output_bytes", "prompt_sha256"}
                        or staged.get("schema_receipt_persisted") is not True
                        or receipt["schema_sha256"] != SCHEMA_SHA256
                        or receipt["prompt_sha256"] != staged["prompt_sha256"]
                        or type(receipt["output_sha256"]) is not str
                        or len(receipt["output_sha256"]) != 64
                        or any(ch not in "0123456789abcdef"
                               for ch in receipt["output_sha256"])
                        or type(receipt["output_bytes"]) is not int
                        or not 0 < receipt["output_bytes"] <= 1024):
                    return _result("SCHEMA_RECEIPT_REFERENCE_RED")
                expected_meta["schema_receipt"] = receipt
            elif staged.get("schema_receipt_persisted") is True:
                return _result("SCHEMA_RECEIPT_REFERENCE_RED")
            if (type(meta) is not dict or meta != expected_meta
                or staged["candidate_sha256"] != _sha(action.encode("utf-8"))
                or staged["candidate_bytes"] != len(action.encode("utf-8"))
                or (staged["source_only_fallback"]
                    != (staged["model_formatter_status"]
                        == "FORMATTER_MISMATCH_RED"))
                or (staged["draft_origin"] == "MODEL_EXACT_SHADOW"
                    and staged["model_formatter_status"]
                    != "FORMATTER_MATCH_SHADOW")):
                return _result("DRAFT_METADATA_OR_SOURCE_RED")
            return _result(
                "NEEDS_REAL_TTY_APPROVAL",
                preflight_only=True, source_rechecked=True,
                source_only_fallback=staged["source_only_fallback"],
                model_formatter_status=staged["model_formatter_status"],
                candidate_sha256=staged["candidate_sha256"],
                c5_binding_verified=True)
    except Exception:
        return _result("C6_STORE_OR_BINDING_RED")
