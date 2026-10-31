"""Default-OFF Run115K/116 B1/B2 -> typed JEF -> C3 postgen check.

The caller's generator is TRUSTED and may have external side effects; this is
NOT a sandbox, runtime delivery gate, or native inference proof. Even a PASS
is a non-delivering SHADOW observation with zero tool/learning authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .b1b2_c3_source_envelope_candidate import build_c3_source_envelope
from .common import dumps
from .context_os import controller
from .b1b2_jef_c3_source_role_bridge_candidate import (
    _read_bound_shadow_plan, build_b1b2_jef_c3_source_role_bridge,
)
from .two_source_pointer_shadow_candidate import bind_two_source
from .agi.jef_eligibility_source_shadow_run46b import propose

SCHEMA = "v13.b1b2_jef_c3_role_postgen_shadow.v1"
PASS = "SHADOW_C3_TYPED_CHOICE_REMAINING_MATCH"
MAX_OUTPUT_BYTES = 256


def _result(status, **extra):
    return {
        "schema": SCHEMA, "status": status,
        "callback_invoked": False, "source_rechecked": False,
        "formatter_match_shadow": False, "native_proof": False,
        "native_c2_proven": False, "native_jef_proven": False,
        "output_committed": False, "tool_dispatches": 0,
        "delivery_authority": 0, "learning_authority": 0,
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False, **extra,
    }


def _epoch(store):
    db = store.db
    if db.in_transaction:
        raise ValueError("ACTIVE_TRANSACTION_RED")
    return (db.total_changes, db.execute("PRAGMA data_version").fetchone()[0],
            store.generation_id)


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY_RED")
        out[key] = value
    return out


def _reject_constant(_):
    raise ValueError("NONFINITE_JSON_RED")


def _parse(raw):
    if type(raw) is not str:
        return None
    try:
        data = raw.encode("utf-8", "strict")
        if not 0 < len(data) <= MAX_OUTPUT_BYTES:
            return None
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
        if (type(value) is not dict or set(value) != {"choice", "remaining"}
                or value["choice"] not in ("A", "B", "NONE")
                or (value["choice"] == "NONE") !=
                (value["remaining"] is None)
                or (value["remaining"] is not None
                    and (type(value["remaining"]) is not int
                         or value["remaining"] < 0))):
            return None
        return value
    except (UnicodeError, ValueError, TypeError, OverflowError):
        return None


def evaluate(runtime, prior_event, current_event, offer_packet_ids, generator,
             *, operator_opt_in=False, callback_opt_in=False,
             approval_receipt=None):
    """Call trusted generator(messages) once; recheck source and exact output.

    Never feed this result to output, tool or human approval consumers. The
    callback may invoke a real model, but the guard does not certify that.
    """
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED_RED")
    if not callable(generator):
        return _result("INVALID_GENERATOR_RED")
    try:
        before = build_b1b2_jef_c3_source_role_bridge(
            runtime, prior_event, current_event, offer_packet_ids,
            operator_opt_in=True)
        if before.get("status") != "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED":
            return _result("SOURCE_PREFLIGHT_RED",
                           component_status=before.get("status"))
        prompt = before["messages"]
        if (type(prompt) is not list or len(prompt) != 2
                or [m.get("role") for m in prompt] != ["system", "user"]
                or before["messages_sha256"] != hashlib.sha256(
                    dumps(prompt).encode("utf-8")).hexdigest()
                or before.get("delivery_authority") != 0
                or before.get("learning_authority") != 0
                or before.get("output_committed") is not False):
            return _result("PROMPT_INTEGRITY_RED")
        payload = json.loads(prompt[1]["content"])
        candidate = before["typed_jef_candidate"]
        refs = before["source_refs"]
        if (type(candidate) is not dict
                or set(candidate) != {"choice", "remaining"}
                or candidate["choice"] not in ("A", "B", "NONE")
                or (candidate["choice"] == "NONE") !=
                (candidate["remaining"] is None)
                or payload.get("typed_jef_candidate") != candidate
                or payload.get("typed_candidate_authority") != 0
                or payload.get("body_hypotheses_are_facts") is not False
                or payload.get("body_model_quote_verified") is not False
                or payload.get("typed_candidate_origin") !=
                "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL"):
            return _result("TYPED_PAYLOAD_INTEGRITY_RED")
        bound = bind_two_source(runtime, prior_event, current_event,
                                operator_opt_in=True)
        body = build_c3_source_envelope(
            runtime, current_event, offer_packet_ids, operator_opt_in=True)
        jef = propose(runtime.store, refs[0], refs[1])
        plan = _read_bound_shadow_plan(runtime, before["context_plan_packet_id"],
                                       current_event, refs)
        if (bound.get("status") != "SHADOW_TWO_SOURCE_POINTER_VERIFIED"
                or [s["source_ref"] for s in bound["sources"]] != refs
                or payload.get("sources") != bound["sources"]
                or body.get("status") != "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL"
                or body.get("verified_quote_count") != before["verified_quote_count"]
                or jef.get("candidate") != candidate
                or jef.get("authority") != 0
                or jef.get("reason") != "EXACT_USER_SOURCE_RECIPE_SHADOW"
                or plan is None or controller(runtime)._load()[0]["mode"] != "SHADOW"):
            return _result("PREFLIGHT_LINEAGE_RED")
        epoch = _epoch(runtime.store)
        frozen_prompt = dumps(prompt)
        frozen_body = dumps(body)
        frozen_bound = dumps(bound)
        frozen_jef = dumps(jef)
    except Exception:
        return _result("SOURCE_PREFLIGHT_INTEGRITY_RED")
    messages = deepcopy(prompt)
    try:
        raw = generator(messages)
    except Exception as exc:
        return _result("CALLBACK_EXCEPTION_RED", callback_invoked=True,
                       error_type=type(exc).__name__)
    try:
        if dumps(messages) != frozen_prompt:
            return _result("CALLBACK_PROMPT_MUTATED_RED", callback_invoked=True)
        if _epoch(runtime.store) != epoch:
            return _result("CALLBACK_STORE_CHANGED_RED", callback_invoked=True)
        after_bound = bind_two_source(runtime, prior_event, current_event,
                                      operator_opt_in=True)
        after_body = build_c3_source_envelope(
            runtime, current_event, offer_packet_ids, operator_opt_in=True)
        after_jef = propose(runtime.store, refs[0], refs[1])
        after_plan = _read_bound_shadow_plan(
            runtime, before["context_plan_packet_id"], current_event, refs)
        if (dumps(after_bound) != frozen_bound
                or dumps(after_body) != frozen_body
                or dumps(after_jef) != frozen_jef
                or after_plan != plan
                or controller(runtime)._load()[0]["mode"] != "SHADOW"
                or _epoch(runtime.store) != epoch):
            return _result("POSTGEN_SOURCE_OR_OFFER_CHANGED_RED",
                           callback_invoked=True)
        base = {"callback_invoked": True, "source_rechecked": True,
                "messages_sha256": before["messages_sha256"],
                "context_plan_packet_id": before["context_plan_packet_id"]}
        parsed = _parse(raw)
        if parsed is None:
            return _result("FORMATTER_JSON_RED", **base)
        if parsed != candidate:
            return _result("FORMATTER_CANDIDATE_MISMATCH_RED", **base)
        return _result(PASS, formatter_match_shadow=True,
                       output_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                       output_bytes=len(raw.encode("utf-8")), **base)
    except Exception:
        return _result("POSTGEN_INTEGRITY_RED", callback_invoked=True)
