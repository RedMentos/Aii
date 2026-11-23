"""Default-OFF JEF/C3 constrained JSON -> source-bound C5/F3 DRAFT SHADOW.

This adapter is not a new decision-maker, native proof, or output credential.
It converts only an exact Run68-shaped JSON response to the old source-bound
one-token formatter interface; malformed or wrong actions never fall back.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .common import dumps
from .jef_c3_c5_c6_fallback_draft_candidate import stage as _stage, STAGED

SCHEMA = {
    "type": "object",
    "properties": {"action": {"type": "string", "enum": ["A", "B", "NONE"]}},
    "required": ["action"],
    "additionalProperties": False,
}
SCHEMA_SHA256 = hashlib.sha256(dumps(SCHEMA).encode("utf-8")).hexdigest()
MAX_JSON_BYTES = 1024


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_SCHEMA_KEY")
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError("NONFINITE_SCHEMA_JSON")


def decode_action(output):
    """Fail-closed exact JSON parser. Never normalize or extract substrings."""
    if type(output) is not str:
        return None
    try:
        raw = output.encode("utf-8", "strict")
        if not 0 < len(raw) <= MAX_JSON_BYTES:
            return None
        value = json.loads(output, object_pairs_hook=_unique,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError):
        return None
    if (type(value) is not dict or set(value) != {"action"}
            or type(value["action"]) is not str
            or value["action"] not in ("A", "B", "NONE")):
        return None
    return value["action"]


def _prompt_action(messages):
    """The old stage independently authenticates this typed prompt to Store."""
    if (type(messages) is not list or len(messages) != 2
            or type(messages[0]) is not dict
            or type(messages[1]) is not dict
            or messages[0].get("role") != "system"
            or messages[1].get("role") != "user"
            or type(messages[1].get("content")) is not str):
        raise ValueError("SCHEMA_PROMPT_SHAPE_RED")
    payload = json.loads(messages[1]["content"], object_pairs_hook=_unique,
                         parse_constant=_reject_constant)
    if type(payload) is not dict:
        raise ValueError("SCHEMA_PROMPT_PAYLOAD_RED")
    action = payload.get("typed_jef_action")
    if type(action) is not str or action not in ("A", "B", "NONE"):
        raise ValueError("SCHEMA_TYPED_ACTION_RED")
    return action


def stage_schema(memory, session, event_id, current_ref, memory_ids, generator,
                 *, operator_opt_in=False, callback_opt_in=False,
                 approval_receipt=None):
    """Request schema from generator(messages, schema), stage one DRAFT only.

    Source, current USER and prompt are rechecked by the existing stage before
    and after the callback, and again under the C5 SQLite transaction.
    This adapter never makes a malformed C3 output into source-only fallback.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return {"status": "OFF", "schema_adapter": True,
                "delivery_authority": 0, "output_committed": False,
                "tool_dispatches": 0, "learning_authority": 0,
                "native_proof": False, "real_tty_approved": False,
                "callback_invoked": False}
    if approval_receipt is not None:
        return {"status": "REAL_TTY_APPROVAL_UNSUPPORTED",
                "schema_adapter": True, "delivery_authority": 0,
                "output_committed": False, "tool_dispatches": 0,
                "learning_authority": 0, "native_proof": False,
                "real_tty_approved": False, "callback_invoked": False}
    if not callable(generator):
        return {"status": "INVALID_CALLBACK", "schema_adapter": True,
                "delivery_authority": 0, "output_committed": False,
                "tool_dispatches": 0, "learning_authority": 0,
                "native_proof": False, "real_tty_approved": False,
                "callback_invoked": False}
    evidence = {}

    def checked(messages):
        expected = _prompt_action(messages)
        schema = deepcopy(SCHEMA)
        output = generator(messages, schema)
        if schema != SCHEMA:
            raise ValueError("SCHEMA_MUTATED_RED")
        action = decode_action(output)
        if action is None:
            raise ValueError("SCHEMA_OUTPUT_RED")
        if action != expected:
            raise ValueError("SCHEMA_ACTION_MISMATCH_RED")
        raw = output.encode("utf-8", "strict")
        evidence["output_sha256"] = hashlib.sha256(raw).hexdigest()
        evidence["output_bytes"] = len(raw)
        return action

    result = _stage(memory, session, event_id, current_ref, memory_ids, checked,
                    operator_opt_in=True, callback_opt_in=True,
                    approval_receipt=None)
    result = dict(result)
    result["schema_adapter"] = True
    result["schema_sha256"] = SCHEMA_SHA256
    # No model-output digest is promoted to a persistent C6 credential.
    if result.get("status") == STAGED and evidence:
        result["schema_formatter_status"] = "SCHEMA_EXACT_SHADOW"
        result["schema_output_sha256"] = evidence["output_sha256"]
        result["schema_output_bytes"] = evidence["output_bytes"]
        result["schema_receipt_persisted"] = False
        result["schema_c3_receiver_success"] = False
    else:
        result["schema_formatter_status"] = "SCHEMA_REJECTED_OR_SOURCE_RED"
    return result
