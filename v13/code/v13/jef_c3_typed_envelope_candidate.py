"""Default-OFF JEF/F1F5 -> C3 typed formatter envelope, SHADOW only.

Uses two real HumanDecision SourceRefs, not body hypotheses or C3 self-claims.
No native model invocation, output commit, TTY approval or learning authority.
"""
from __future__ import annotations

import hashlib

from .common import dumps
from . import jef_typed_source_shadow as typed
from .jef_f1f5_live_current_candidate import (
    decide_current_turn, _latest_authoritative_user)

SYSTEM = (
    "You are a formatter, not a decision maker. Copy the source-verified "
    "typed JEF action exactly. Return only A, B or NONE as one uppercase "
    "token. Do not add explanations, JSON, punctuation or extra text."
)


def _result(status, **extra):
    return {"schema": "v13.jef_c3_typed_envelope_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False,
            "model_called": False, **extra}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_jef_c3_typed_envelope(memory, session, event_id, current_ref,
                                memory_ids, *, operator_opt_in=False,
                                approval_receipt=None):
    """Construct only a source-verified two-role prompt, never call C3."""
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(session) is not str or type(event_id) is not str
            or type(current_ref) is not dict
            or type(memory_ids) not in (tuple, list)
            or len(memory_ids) != 2 or memory_ids[0] == memory_ids[1]):
        return _result("INVALID_INPUT")
    first = decide_current_turn(
        memory, session, event_id, current_ref, memory_ids,
        operator_opt_in=True)
    if first.get("live_current_status") != "JEF_LIVE_CURRENT_VERIFIED_SHADOW":
        return _result("JEF_CURRENT_SOURCE_RED",
                       admission_status=first.get("live_current_status"))
    try:
        store = memory.s
        with store.tx():
            if _latest_authoritative_user(store, session) != event_id:
                return _result("STALE_USER_EVENT_RED")
            current = typed._read_full(store, current_ref)
            req = typed.CURRENT.fullmatch(current)
            if req is None:
                return _result("CURRENT_GRAMMAR_RED")
            keys = {
                "policy": f"Project {req['id']} archived {req['domain']} policy",
                "sheet": f"Project {req['id']} latest {req['domain']} option sheet",
            }
            rows = {}
            for mid, expected in zip(memory_ids, (keys["policy"], keys["sheet"])):
                row = memory.candidate(mid, session)
                if row["key_text"] != expected:
                    return _result("SOURCE_ORDER_OR_FOREIGN_MEMORY_RED")
                rows[row["key_text"]] = row
            if len(rows) != 2 or set(rows) != set(keys.values()):
                return _result("SOURCE_SET_RED")
            refs = [rows[keys[k]]["source_ref"] for k in ("policy", "sheet")]
            ref_hashes = [typed._sha(typed._canonical(ref)) for ref in refs]
            if ref_hashes != first.get("source_ref_sha256"):
                return _result("JEF_SOURCE_REF_CHANGED")
            policy, sheet = [typed._read_full(store, ref) for ref in refs]
            if (typed.POLICY.fullmatch(policy) is None
                    or typed.SHEET.fullmatch(sheet) is None):
                return _result("TYPED_SOURCE_GRAMMAR_RED")
            payload = {
                "current_source": current,
                "current_source_sha256": current_ref["sha256"],
                "policy_source": policy,
                "sheet_source": sheet,
                "source_ref_sha256": ref_hashes,
                "typed_jef_action": first["suggested_action"],
                "candidate_authority": 0,
            }
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": dumps(payload)},
            ]
            prompt_sha = _sha(dumps(messages).encode("utf-8"))
        second = decide_current_turn(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (second.get("live_current_status")
                != "JEF_LIVE_CURRENT_VERIFIED_SHADOW"
                or dumps(second) != dumps(first)):
            return _result("POST_PROMPT_SOURCE_CHANGED")
        return _result(
            "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL",
            messages=messages, messages_sha256=prompt_sha,
            typed_jef_action=first["suggested_action"],
            source_ref_sha256=ref_hashes,
            current_source_sha256=current_ref["sha256"],
            source_rechecked=True,
            formatter_only=True)
    except Exception:
        return _result("JEF_C3_SOURCE_INTEGRITY_RED")


def verify_jef_c3_formatter_output(envelope, output):
    """Strict diagnostic equality; never a real TTY/output permission."""
    if (type(envelope) is not dict
            or envelope.get("status")
            != "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
            or type(envelope.get("messages")) is not list
            or type(envelope.get("messages_sha256")) is not str
            or _sha(dumps(envelope["messages"]).encode("utf-8"))
            != envelope["messages_sha256"]
            or envelope.get("typed_jef_action") not in ("A", "B", "NONE")
            or type(output) is not str):
        return _result("FORMATTER_INPUT_RED", formatter_match=False)
    match = output == envelope["typed_jef_action"]
    return _result("FORMATTER_MATCH_SHADOW" if match else "FORMATTER_MISMATCH_RED",
                   formatter_match=match,
                   output_sha256=_sha(output.encode("utf-8")),
                   source_rechecked=False,
                   native_evidence=False)
