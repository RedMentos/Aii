"""Run117CW: default-OFF live Store source-only C3 callback, SHADOW only.

One untrusted callback can be a future native model adapter, but this module
cannot certify native inference. It never delivers, dispatches or learns.
"""
from __future__ import annotations

import copy
import hashlib
import json

from .common import dumps
from . import jef_c3_source_only_shadow_candidate as source

READY = "SOURCE_ONLY_C3_CALLBACK_SHADOW"
SCHEMA = {
    "type": "object",
    "properties": {"action": {"type": "string", "enum": ["A", "B", "NONE"]}},
    "required": ["action"], "additionalProperties": False,
}
MAX_RAW_BYTES = 1024


def _sha(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_ACTION_KEY_RED")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("NONFINITE_ACTION_RED")


def decode(raw):
    if type(raw) is not str or not 0 < len(raw.encode("utf-8")) <= MAX_RAW_BYTES:
        return None
    try:
        obj = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, TypeError, OverflowError, UnicodeError):
        return None
    if (type(obj) is not dict or set(obj) != {"action"}
            or type(obj["action"]) is not str
            or obj["action"] not in ("A", "B", "NONE")):
        return None
    return obj["action"]


def _result(status, **fields):
    return {
        "schema": "v13.run117cw.c3_source_callback_shadow.v1",
        "status": status, "authority": 0,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "output_committed": False,
        "native_proof": False, "native_calls_verified": 0,
        "model_callback_invocations": 0,
        "independent_reasoning_proven": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        **fields,
    }


def _epoch(store):
    return (
        store.db.total_changes,
        store.db.execute("PRAGMA data_version").fetchone()[0],
        store.one("SELECT COUNT(*) AS n FROM actions")["n"],
        store.one("SELECT COUNT(*) AS n FROM messages")["n"],
    )


def invoke(memory, session, event_id, current_ref, memory_ids, callback, *,
           operator_opt_in=False, approval_receipt=None):
    """Bound callback under real human-source admission; no live output authority.

    A post-callback Store/source recheck is useful for SHADOW research only:
    it is not a transaction spanning native inference and cannot authorize
    any later output, tool, state or learning commit.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if not callable(callback):
        return _result("INVALID_CALLBACK_RED")
    try:
        before = source.build(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (before.get("status") != source.STATUS
                or before.get("oracle_action_visible") is not False
                or before.get("delivery_authority") != 0
                or before.get("learning_authority") != 0
                or before.get("model_called") is not False):
            return _result("SOURCE_ADMISSION_RED",
                           admission_status=before.get("status"))
        messages = before["messages"]
        digest = before["messages_sha256"]
        if (type(messages) is not list or len(messages) != 2
                or [m.get("role") for m in messages] != ["system", "user"]
                or _sha(messages) != digest):
            return _result("PROMPT_INTEGRITY_RED")
        payload = json.loads(messages[1]["content"])
        if (payload.get("typed_jef_action_visible") is not False
                or any(k in payload for k in (
                    "oracle", "expected_action", "suggested_action",
                    "typed_jef_action", "wrong_typed_action_synthetic_only"))):
            return _result("ORACLE_LEAK_RED")
        epoch = _epoch(memory.s)
        sent = copy.deepcopy(messages)
        raw = None
        error = None
        try:
            raw = callback(sent, copy.deepcopy(SCHEMA))
        except Exception as exc:
            error = type(exc).__name__
        changed = (_sha(sent) != digest or _sha(messages) != digest
                   or _epoch(memory.s) != epoch)
        after = source.build(
            memory, session, event_id, current_ref, memory_ids,
            operator_opt_in=True)
        if (changed or after.get("status") != source.STATUS
                or after.get("messages_sha256") != digest
                or after.get("source_ref_sha256") != before.get("source_ref_sha256")
                or after.get("current_source_ref_sha256") != before.get("current_source_ref_sha256")
                or _epoch(memory.s) != epoch):
            return _result("SOURCE_OR_CALLBACK_MUTATION_RED",
                           model_callback_invocations=1,
                           source_rechecked=False)
        if error is not None:
            return _result("MODEL_CALLBACK_ERROR_RED",
                           model_callback_invocations=1,
                           callback_error_type=error, source_rechecked=True)
        action = decode(raw)
        if action is None:
            return _result("MODEL_OUTPUT_INVALID_RED",
                           model_callback_invocations=1, source_rechecked=True)
        return _result(
            READY, model_callback_invocations=1,
            source_rechecked=True, source_only=True,
            oracle_action_visible=False,
            messages_sha256=digest,
            source_ref_sha256=before["source_ref_sha256"],
            current_source_ref_sha256=before["current_source_ref_sha256"],
            shadow_action=action,  # non-delivering diagnostic, not a tool decision
            raw_output_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )
    except (ValueError, TypeError, KeyError, AttributeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError):
        return _result("SOURCE_CALLBACK_INTEGRITY_RED")
