"""Run75 source-authenticated JEF range -> C3 typed formatter envelope (SHADOW).

A typed action is deliberately visible to C3; this tests formatting, NOT
independent source reasoning. Never calls a model or authorizes output.
"""
from __future__ import annotations

import hashlib
import json

from .common import dumps
from .jef_f1f5_range_admission_shadow import decide as human_decide, READY

STATUS = "JEF_RANGE_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"
SYSTEM = (
    "You are the C3_LANGUAGE JSON formatter, not the rule decision maker. "
    "Copy the authenticated typed_jef_action from the user JSON exactly into "
    "one JSON object with the sole key action and value A, B or NONE. "
    "Do not recompute rules or invent values. Return JSON only."
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _result(status, **extra):
    return {
        "schema": "v13.jef_range_c3_typed_envelope_shadow.v1",
        "status": status,
        "authority": 0,
        "delivery_authority": 0,
        "learning_authority": 0,
        "model_called": False,
        "native_calls": 0,
        "output_committed": False,
        "real_tty_approved": False,
        "tool_dispatches": 0,
        "jepa_weight": 0,
        "whole_system_complete": False,
        **extra,
    }


def build(memory, session, event_id, current_ref, memory_ids, *,
          operator_opt_in=False, approval_receipt=None):
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    try:
        decision = human_decide(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (decision.get("admission_status") != READY
                or decision.get("human_source_lineage_verified") is not True
                or decision.get("suggested_action") not in ("A", "B", "NONE")
                or decision.get("authority") != 0
                or decision.get("model_called") is not False):
            return _result("F1F5_RANGE_SOURCE_ADMISSION_RED",
                           admission_status=decision.get("admission_status"))
        refs = decision["source_ref_sha256"]
        if (type(refs) is not list or len(refs) != 2
                or any(type(h) is not str or len(h) != 64 for h in refs)):
            return _result("SOURCE_REF_BINDING_RED")
        payload = {
            "typed_jef_action": decision["suggested_action"],
            "human_source_lineage_verified": True,
            "source_ref_sha256": refs,
            "current_source_ref_sha256": _sha(dumps(current_ref).encode("utf-8")),
            "rule_parser_revision": decision["revision"],
        }
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": dumps(payload)}]
        return _result(
            STATUS, typed_jef_action=decision["suggested_action"],
            source_ref_sha256=refs,
            current_source_ref_sha256=payload["current_source_ref_sha256"],
            human_source_lineage_verified=True,
            memory_id_hashes=decision["memory_id_hashes"],
            messages=messages,
            messages_sha256=_sha(dumps(messages).encode("utf-8")),
            formatter_only=True, independent_reasoning_proven=False)
    except (ValueError, TypeError, KeyError, AttributeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError):
        return _result("SOURCE_OR_PROMPT_INTEGRITY_RED")
