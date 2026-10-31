"""Default-OFF JEF F1/F5 -> C3 post-generation source recheck (SHADOW).

This is a callback seam, not native proof or a live delivery gate. It never
turns a C3 response into a human decision or a TTY approval. The original
Run63 native RED is deliberately untouched.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .common import dumps
from . import jef_c3_typed_envelope_candidate as typed

MAX_OUTPUT_BYTES = 512
READY = "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL"


def _result(status, *, generator_invoked=False, source_rechecked=False,
            source_only_fallback_action=None, **extra):
    return {
        "schema": "v13.jef_c3_postgen_recheck_shadow.v1",
        "status": status,
        "generator_invoked": generator_invoked,
        "source_rechecked": source_rechecked,
        "source_only_fallback_action": source_only_fallback_action,
        "source_only_fallback_verified": (
            source_rechecked and source_only_fallback_action in ("A", "B", "NONE")),
        "c3_receiver_success": status == "FORMATTER_MATCH_SHADOW",
        "delivery_authority": 0,
        "output_committed": False,
        "tool_dispatches_by_guard": 0,
        "learning_authority": 0,
        "native_proof": False,
        "model_called_by_guard": False,
        "user_approved": False,
        **extra,
    }


def evaluate(memory, session, event_id, current_ref, memory_ids, generator,
             *, operator_opt_in=False, approval_receipt=None):
    """Call one controlled generator, then recheck exact current human sources.

    `generator(messages)` may call a local C3 model, but its effects are not
    certified by this guard. Never hand this diagnostic result to an output
    commit or tool dispatcher as a permission token.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if not callable(generator):
        return _result("INVALID_GENERATOR")
    before = typed.build_jef_c3_typed_envelope(
        memory, session, event_id, current_ref, memory_ids,
        operator_opt_in=True)
    if before.get("status") != READY:
        return _result("SOURCE_PREFLIGHT_RED",
                       source_status=before.get("status"))
    try:
        # Do not let a callback mutate the saved envelope used for comparison.
        original = dumps(before)
        messages = deepcopy(before["messages"])
        output = generator(messages)
    except Exception as exc:
        return _result("GENERATOR_EXCEPTION_RED", generator_invoked=True,
                       generator_error_type=type(exc).__name__)
    after = typed.build_jef_c3_typed_envelope(
        memory, session, event_id, current_ref, memory_ids,
        operator_opt_in=True)
    if after.get("status") != READY or dumps(after) != original:
        return _result("SOURCE_CHANGED_DURING_GENERATION_RED",
                       generator_invoked=True,
                       source_status=after.get("status"))
    # A source-only JEF decision remains distinct from the model's answer.
    fallback = after["typed_jef_action"]
    if type(output) is not str:
        return _result("FORMATTER_OUTPUT_RED", generator_invoked=True,
                       source_rechecked=True,
                       source_only_fallback_action=fallback)
    try:
        raw = output.encode("utf-8")
    except UnicodeError:
        return _result("FORMATTER_OUTPUT_RED", generator_invoked=True,
                       source_rechecked=True,
                       source_only_fallback_action=fallback)
    if not 0 < len(raw) <= MAX_OUTPUT_BYTES:
        return _result("FORMATTER_OUTPUT_RED", generator_invoked=True,
                       source_rechecked=True,
                       source_only_fallback_action=fallback)
    checked = typed.verify_jef_c3_formatter_output(after, output)
    match = (checked.get("status") == "FORMATTER_MATCH_SHADOW"
             and checked.get("formatter_match") is True)
    return _result("FORMATTER_MATCH_SHADOW" if match else "FORMATTER_MISMATCH_RED",
                   generator_invoked=True, source_rechecked=True,
                   source_only_fallback_action=None if match else fallback,
                   output_sha256=hashlib.sha256(raw).hexdigest(),
                   output_bytes=len(raw),
                   prompt_sha256=after["messages_sha256"])
