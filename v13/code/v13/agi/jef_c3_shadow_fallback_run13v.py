"""Run13V: source-rechecked JEF/C3 answer selection, strictly SHADOW.

No Runtime integration, native call, chat egress, Store write or learning.
Source pointer recheck is best-effort, NOT atomic delivery authorization.
"""
from __future__ import annotations

import hashlib
import sqlite3

from scripts.run13k_c3_copy_native import COPY_PREFIX, COPY_SUFFIX
from .c3_source_fidelity_shadow_run13m import audit_source_facts
from .jef_c3_shadow_prompt_run13i import (
    MAX_ANSWER_BYTES, MAX_PROMPT_BYTES, PREFIX, propose_c3_context,
)

REVISION = "run13v-jef-c3-source-rechecked-fallback-shadow-v1"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
MAX_C3_BYTES = 768


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _closed(reason, *, text=None, provenance="NONE", source_ok=False,
            receipt_ok=False, fidelity_reason=None):
    return {
        "revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
        "reason": reason, "selected_text": text,
        "selected_text_sha256": _sha(text) if text is not None else None,
        "selected_provenance": provenance,
        "source_revalidated": source_ok, "native_receipt_bound": receipt_ok,
        "c3_fidelity_reason": fidelity_reason,
        "operator_only": True, "no_autonomous_egress": True,
        "delivery_authority": 0, "context_authority": 0,
        "native_calls_by_mux": 0, "model_called_by_mux": False,
        "store_writes_by_mux": 0, "weight_updates": False,
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "utility_gate_pass": False, "whole_system_complete": False,
    }


def _source_snapshot_ok(snapshot, plan_id, query_id, source_id):
    if (type(snapshot) is not dict
            or snapshot.get("reason") != "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE"
            or snapshot.get("status") != "SHADOW_NO_AUTHORITY"
            or snapshot.get("delivery_authority") != 0
            or snapshot.get("context_authority") != 0
            or snapshot.get("native_calls") != 0
            or snapshot.get("model_called") is not False
            or snapshot.get("weight_updates") is not False
            or snapshot.get("context_plan_packet_id") != plan_id
            or snapshot.get("query_event_id") != query_id
            or snapshot.get("source_event_id") != source_id):
        return False
    answer, prompt = snapshot.get("answer"), snapshot.get("candidate_prompt")
    try:
        return (type(answer) is str and type(prompt) is str
                and 0 < len(answer.encode("utf-8")) <= MAX_ANSWER_BYTES
                and prompt == PREFIX + answer
                and len(prompt.encode("utf-8")) <= MAX_PROMPT_BYTES
                and snapshot.get("answer_sha256") == _sha(answer)
                and snapshot.get("prompt_sha256") == _sha(prompt))
    except UnicodeError:
        return False


def _native_receipt_ok(receipt, snapshot):
    if type(receipt) is not dict:
        return False
    answer = snapshot["answer"]
    allowed_prompts = {
        snapshot["prompt_sha256"],
        _sha(COPY_PREFIX + answer + COPY_SUFFIX),
    }
    return (receipt.get("native_role") == "C3_LANGUAGE"
            and receipt.get("native_status") == "FINAL"
            and receipt.get("native_calls") == 1
            and receipt.get("native_reaped") is True
            and type(receipt.get("native_pid")) is int
            and receipt["native_pid"] > 0
            and type(receipt.get("native_release")) is dict
            and receipt["native_release"].get("process_reaped") is True
            and receipt.get("model_sha256") == MODEL_SHA
            and receipt.get("model_revision") == MODEL_REVISION
            and receipt.get("source_event_id") == snapshot["source_event_id"]
            and receipt.get("query_event_id") == snapshot["query_event_id"]
            and receipt.get("context_plan_packet_id") == snapshot["context_plan_packet_id"]
            and receipt.get("answer_sha256") == snapshot["answer_sha256"]
            and receipt.get("prompt_sha256") in allowed_prompts)


def select_shadow(store, plan_id, query_id, source_id, snapshot,
                  c3_text=None, native_receipt=None):
    """Return operator-only selected text, never user delivery or authority."""
    if (not all(type(x) is str and x for x in (plan_id, query_id, source_id))
            or not _source_snapshot_ok(snapshot, plan_id, query_id, source_id)):
        return _closed("SNAPSHOT_OR_SOURCE_IDS_RED")
    try:
        fresh = propose_c3_context(store, plan_id, query_id, source_id)
        if (fresh != snapshot
                or not _source_snapshot_ok(fresh, plan_id, query_id, source_id)):
            return _closed("SOURCE_CHANGED_OR_REVOKED_AT_SELECTION")
        answer = fresh["answer"]
        receipt_ok = _native_receipt_ok(native_receipt, fresh)
        if not receipt_ok:
            return _closed("NATIVE_RECEIPT_UNBOUND_JEF_FALLBACK",
                           text=answer, provenance="JEF_VERIFIED_FALLBACK_SHADOW",
                           source_ok=True)
        if type(c3_text) is not str:
            return _closed("C3_NON_TEXT_JEF_FALLBACK", text=answer,
                           provenance="JEF_VERIFIED_FALLBACK_SHADOW",
                           source_ok=True, receipt_ok=True)
        try:
            if len(c3_text.encode("utf-8")) > MAX_C3_BYTES:
                return _closed("C3_OUTPUT_BUDGET_JEF_FALLBACK", text=answer,
                               provenance="JEF_VERIFIED_FALLBACK_SHADOW",
                               source_ok=True, receipt_ok=True)
        except UnicodeError:
            return _closed("C3_ENCODING_JEF_FALLBACK", text=answer,
                           provenance="JEF_VERIFIED_FALLBACK_SHADOW",
                           source_ok=True, receipt_ok=True)
        fidelity = audit_source_facts(fresh, c3_text)
        if fidelity.get("result") == "FACTS_EXACT":
            return _closed("C3_SOURCE_FACTS_VERIFIED", text=c3_text,
                           provenance="C3_FACTS_VERIFIED_SHADOW",
                           source_ok=True, receipt_ok=True,
                           fidelity_reason=fidelity.get("reason"))
        return _closed("C3_UNFAITHFUL_JEF_FALLBACK", text=answer,
                       provenance="JEF_VERIFIED_FALLBACK_SHADOW",
                       source_ok=True, receipt_ok=True,
                       fidelity_reason=fidelity.get("reason"))
    except (TypeError, ValueError, KeyError, AttributeError,
            OverflowError, UnicodeError, sqlite3.Error):
        return _closed("SOURCE_RECHECK_EXCEPTION_RED")