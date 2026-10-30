"""Run13S: fresh-Store-revalidated JEF->C3 source-exact SHADOW preview.

Operator-only candidate, no model calls, no chat egress, no learning.
Native C3 success and deterministic source fallback are never conflated.
"""
from __future__ import annotations

import hashlib
import sqlite3

from scripts.run13k_c3_copy_native import prompt_for
from v13.agi.jef_c3_shadow_prompt_run13i import propose_c3_context
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts

REVISION = "run13s-jef-c3-revalidated-preview-v1"
IDS = ("context_plan_packet_id", "query_event_id", "source_event_id")
BINDINGS = IDS + ("answer_sha256", "prompt_sha256", "answer", "candidate_prompt")


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _closed(reason, *, candidate_sha=None, audit_reason=None,
            native_calls=0, source_sha=None, text=None, origin=None):
    return {
        "revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
        "reason": reason, "preview_text": text,
        "preview_sha256": _hash(text) if type(text) is str else None,
        "preview_origin": origin, "candidate_sha256": candidate_sha,
        "source_answer_sha256": source_sha,
        "model_facts_verified": origin == "NATIVE_C3_FACTS_VERIFIED",
        "deterministic_fallback_used": origin == "FRESH_JEF_SOURCE_EXACT",
        "native_audit_reason": audit_reason,
        "native_calls_observed": native_calls,
        "model_called_by_preview": False,
        "operator_only": True, "no_autonomous_egress": True,
        "delivery_authority": 0, "context_authority": 0,
        "weight_updates": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def _valid_link(linked, plan_id, query_event_id, source_event_id):
    if type(linked) is not dict:
        return False
    if any(linked.get(k) != expected for k, expected in (
            ("context_plan_packet_id", plan_id),
            ("query_event_id", query_event_id),
            ("source_event_id", source_event_id))):
        return False
    try:
        prompt_for(linked, "COPY_DIRECT")
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        return False
    return True


def preview_after_native(store, plan_id, query_event_id, source_event_id,
                         linked_before, native_text, *, native_status,
                         native_reaped, native_role, native_calls):
    """Re-read Store after one completed C3 call before any SHADOW preview.

    A failed model copy may fall back to *fresh* JEF source text, never stale
    cached source. Native failure or source integrity failure always abstains.
    """
    if not _valid_link(linked_before, plan_id, query_event_id, source_event_id):
        return _closed("ABSTAIN_SOURCE_RED")
    if (native_status != "FINAL" or native_reaped is not True
            or native_role != "C3_LANGUAGE" or type(native_calls) is not int
            or native_calls != 1 or type(native_text) is not str):
        return _closed("ABSTAIN_NATIVE_RED",
                       native_calls=native_calls if type(native_calls) is int else 0)
    candidate_sha = _hash(native_text)
    try:
        linked_after = propose_c3_context(
            store, plan_id, query_event_id, source_event_id)
        if (not _valid_link(linked_after, plan_id, query_event_id, source_event_id)
                or any(linked_before.get(k) != linked_after.get(k)
                       for k in BINDINGS)):
            return _closed("ABSTAIN_SOURCE_RED",
                           candidate_sha=candidate_sha, native_calls=1)
        answer = linked_after["answer"]
        source_sha = linked_after["answer_sha256"]
        audit = audit_source_facts(linked_after, native_text)
        if (audit.get("status") != "SHADOW_NO_AUTHORITY"
                or audit.get("answer_sha256") != source_sha):
            return _closed("ABSTAIN_AUDIT_INTEGRITY_RED",
                           candidate_sha=candidate_sha, native_calls=1)
        if audit.get("result") == "FACTS_EXACT":
            return _closed(
                "MODEL_VERIFIED_PREVIEW", candidate_sha=candidate_sha,
                audit_reason=audit["reason"], native_calls=1,
                source_sha=source_sha, text=native_text,
                origin="NATIVE_C3_FACTS_VERIFIED")
        return _closed(
            "SOURCE_EXACT_FALLBACK_PREVIEW", candidate_sha=candidate_sha,
            audit_reason=audit["reason"], native_calls=1,
            source_sha=source_sha, text=answer,
            origin="FRESH_JEF_SOURCE_EXACT")
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError,
            AttributeError, UnicodeError, OverflowError):
        return _closed("ABSTAIN_SOURCE_RED",
                       candidate_sha=candidate_sha, native_calls=1)
