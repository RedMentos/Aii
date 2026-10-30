"""Run13I: JEF exact Store facts -> C3_LANGUAGE prompt candidate, SHADOW only.

No native calls, model dispatch, live chat egress, Store writes or learning.
A future native consumer must revalidate exact sources at egress.
"""
from __future__ import annotations

import hashlib
import sqlite3

from v13.agi.budget_answer_shadow_run13b import _render
from v13.agi.context_source_link_budget_run13e import propose_pointer

REVISION = "run13i-jef-c3-source-prompt-shadow-v1"
PREFIX = (
    "SHADOW EVALUATION ONLY. C3_LANGUAGE: restate the four source-verified "
    "facts below without changing names, amounts or the faster option. "
    "Add no new claims. If unsure, reply ABSTAIN.\n"
    "VERIFIED_FACTS:\n"
)
MAX_ANSWER_BYTES = 512
MAX_PROMPT_BYTES = 768


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _closed(reason):
    return {
        "revision": REVISION, "status": "SHADOW_NO_AUTHORITY",
        "reason": reason, "consumer_role": "C3_LANGUAGE",
        "answer": None, "answer_sha256": None,
        "candidate_prompt": None, "prompt_sha256": None,
        "operator_only": True, "no_autonomous_egress": True,
        "delivery_authority": 0, "context_authority": 0,
        "native_calls": 0, "model_called": False, "weight_updates": False,
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }


def propose_c3_context(store, plan_id, query_event_id, source_event_id):
    """Build a bounded candidate from two identical Run13E source witnesses."""
    try:
        first = propose_pointer(store, plan_id, query_event_id, source_event_id)
        if (type(first) is not dict
                or first.get("reason") != "CONTEXT_SOURCE_LINK_BUDGET_SHADOW"
                or first.get("status") != "SHADOW_NO_AUTHORITY"
                or first.get("delivery_authority") != 0
                or first.get("native_calls") != 0
                or first.get("weight_updates") is not False
                or first.get("context_plan_packet_id") != plan_id
                or first.get("query_event_id") != query_event_id
                or first.get("source_event_id") != source_event_id):
            return _closed("SOURCE_LINK_UNAVAILABLE")
        answer = first.get("answer")
        candidate = first.get("candidate")
        if (type(answer) is not str or type(candidate) is not dict
                or not 0 < len(answer.encode("utf-8")) <= MAX_ANSWER_BYTES
                or _render(candidate) != answer
                or first.get("answer_sha256") != _digest(answer)):
            return _closed("SOURCE_ANSWER_INTEGRITY_RED")
        prompt = PREFIX + answer
        if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            return _closed("C3_PROMPT_BUDGET_RED")
        second = propose_pointer(store, plan_id, query_event_id, source_event_id)
        if second != first:
            return _closed("SOURCE_CHANGED_BEFORE_C3_SHADOW")
        return {
            **_closed("VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE"),
            "answer": answer, "answer_sha256": _digest(answer),
            "candidate_prompt": prompt, "prompt_sha256": _digest(prompt),
            "context_plan_packet_id": plan_id,
            "query_event_id": query_event_id,
            "source_event_id": source_event_id,
        }
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError,
            UnicodeError, sqlite3.Error):
        return _closed("SOURCE_C3_CONTEXT_INTEGRITY_RED")


def audit_c3_text(context, output):
    """Exact-copy fidelity only. Not a semantic verifier or delivery gate."""
    status = "INTEGRITY_RED"
    if type(context) is dict and type(output) is str:
        answer = context.get("answer")
        prompt = context.get("candidate_prompt")
        if (context.get("reason") == "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE"
                and context.get("status") == "SHADOW_NO_AUTHORITY"
                and context.get("delivery_authority") == 0
                and context.get("context_authority") == 0
                and context.get("native_calls") == 0
                and context.get("model_called") is False
                and context.get("weight_updates") is False
                and type(answer) is str and type(prompt) is str
                and 0 < len(answer.encode("utf-8")) <= MAX_ANSWER_BYTES
                and prompt == PREFIX + answer
                and len(prompt.encode("utf-8")) <= MAX_PROMPT_BYTES
                and context.get("answer_sha256") == _digest(answer)
                and context.get("prompt_sha256") == _digest(prompt)):
            status = "EXACT_COPY" if output == answer else "NOT_VERIFIED"
    return {
        "status": status, "delivery_authority": 0, "context_authority": 0,
        "model_called_by_auditor": False, "native_calls": 0,
        "weight_updates": False, "learning_mode": "RECORD_ONLY",
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "jepa_weight": 0, "whole_system_complete": False,
    }
