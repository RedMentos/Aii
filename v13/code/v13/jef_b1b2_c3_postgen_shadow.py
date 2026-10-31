"""Default-OFF JEF/B1/B2 -> C3 post-generation integrity boundary (Run84).

Software SHADOW diagnostic. It cannot sandbox or undo callback side effects;
callbacks must be trusted. It never stages output, dispatches tools, learns,
issues TTY approval, or proves native model quality.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .common import dumps
from . import jef_b1b2_c3_dual_source_shadow as dual
from .jef_c3_schema_draft_candidate import (
    SCHEMA, SCHEMA_SHA256, decode_action,
)

TABLES = ("sources", "events", "memories", "actions", "messages", "packets")
STATUS = "DUAL_SOURCE_C3_FORMATTER_MATCH_SHADOW"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _result(status, **extra):
    return {
        "schema": "v13.jef_b1b2_c3_postgen_shadow.v1",
        "status": status,
        "callback_invoked": False,
        "source_rechecked": False,
        "model_called_by_guard": False,
        "native_proof": False,
        "output_committed": False,
        "delivery_authority": 0,
        "learning_authority": 0,
        "tool_dispatches": 0,
        "real_tty_approved": False,
        "schema_sha256": SCHEMA_SHA256,
        "jepa_weight": 0,
        "whole_system_complete": False,
        **extra,
    }


def _store_snapshot(runtime):
    """Detect writes (including same-row UPDATE) on one or other connection.

    This is mutation detection, NOT a rollback, isolation or permission gate.
    """
    store = runtime.store
    db = store.db
    if db.in_transaction:
        raise ValueError("ACTIVE_TRANSACTION_RED")
    counts = tuple(store.one(
        "SELECT COUNT(*) AS n FROM " + table)["n"] for table in TABLES)
    return (counts, db.total_changes,
            db.execute("PRAGMA data_version").fetchone()[0],
            db.in_transaction)


def evaluate(runtime, event, offer_packet_ids, memory_ids, generator, *,
             operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Invoke trusted generator(messages, schema) once, revalidate everything.

    No result from this function is a C5/C6/TTY credential. A malformed or
    mismatched answer is RED, never silently substituted with JEF's action.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if not callable(generator):
        return _result("INVALID_GENERATOR")
    try:
        before = dual.build(runtime, event, offer_packet_ids, memory_ids,
                            operator_opt_in=True)
        if before.get("status") != dual.STATUS:
            return _result("SOURCE_PREFLIGHT_RED",
                           component_status=before.get("status"))
        prompt = before["messages"]
        if (type(prompt) is not list or len(prompt) != 2
                or before["messages_sha256"] != _sha(
                    dumps(prompt).encode("utf-8"))
                or before.get("typed_jef_action") not in ("A", "B", "NONE")
                or before.get("human_source_lineage_verified") is not True
                or before.get("formatter_only") is not True):
            return _result("ENVELOPE_INTEGRITY_RED")
        frozen = dumps(before)
        epoch = _store_snapshot(runtime)
    except Exception:
        return _result("SOURCE_PREFLIGHT_INTEGRITY_RED")
    messages = deepcopy(prompt)
    schema = deepcopy(SCHEMA)
    try:
        raw = generator(messages, schema)
    except Exception as exc:
        return _result("CALLBACK_EXCEPTION_RED", callback_invoked=True,
                       error_type=type(exc).__name__)
    try:
        if dumps(messages) != dumps(prompt) or schema != SCHEMA:
            return _result("CALLBACK_PROMPT_OR_SCHEMA_MUTATED_RED",
                           callback_invoked=True)
        if _store_snapshot(runtime) != epoch:
            return _result("CALLBACK_STORE_MUTATION_RED",
                           callback_invoked=True)
        after = dual.build(runtime, event, offer_packet_ids, memory_ids,
                           operator_opt_in=True)
        if (after.get("status") != dual.STATUS
                or dumps(after) != frozen
                or after["messages_sha256"] != before["messages_sha256"]
                or after["typed_jef_action"] != before["typed_jef_action"]):
            return _result("POSTGEN_SOURCE_CHANGED_RED",
                           callback_invoked=True,
                           component_status=after.get("status"))
        if _store_snapshot(runtime) != epoch:
            return _result("POSTGEN_STORE_MUTATION_RED",
                           callback_invoked=True)
        base = {
            "callback_invoked": True,
            "source_rechecked": True,
            "messages_sha256": before["messages_sha256"],
            "jef_messages_sha256": before["jef_messages_sha256"],
            "b1b2_messages_sha256": before["b1b2_messages_sha256"],
            "typed_jef_action": before["typed_jef_action"],
        }
        action = decode_action(raw)
        if action is None:
            return _result("FORMATTER_JSON_RED", **base)
        digest = _sha(raw.encode("utf-8", "strict"))
        base["output_sha256"] = digest
        base["output_bytes"] = len(raw.encode("utf-8", "strict"))
        if action != before["typed_jef_action"]:
            return _result("FORMATTER_ACTION_MISMATCH_RED",
                           parsed_action=action, **base)
        return _result(STATUS, parsed_action=action,
                       formatter_match=True, **base)
    except Exception as exc:
        return _result("POSTGEN_INTEGRITY_RED", callback_invoked=True,
                       error_type=type(exc).__name__)
