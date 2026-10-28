"""Read-only, non-authoritative Store -> German SHADOW use-boundary candidate.

This independently owned Run11 candidate does not edit Runtime/Store or
Run24/Run29/Run31 sources. A SHA256 ticket is an accidental-tamper checksum,
NOT a signature, capability, permission or proof of an original human rule.
Only the current Store is re-read; revocation after return is still possible.
"""
import copy
import hashlib
import json
import re

from scripts import run21_event_source_adapter_shadow as adapter
from scripts import run23_store_typed_bridge_shadow as bridge

SCHEMA = "v13.run11.store-shadow-use-boundary.v1"
SCOPE = "EVENT_SOURCE_INTEGRITY_ONLY"
ROLES = ("old", "sheet", "current")


class Refusal(ValueError):
    """The persisted source or SHADOW ticket cannot be revalidated."""


def _digest(value):
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise Refusal("ticket_not_canonical_json") from exc
    return hashlib.sha256(canonical).hexdigest()


def _snapshot(store, session, project, refs):
    """Re-read original Store events AND the linked FINAL user messages."""
    try:
        reader = adapter.EventSourceReader(store, session, project, refs)
        rows = {role: reader(refs[role]) for role in ROLES}
    except Exception as exc:
        raise Refusal("source_not_live_or_lineage_changed") from exc
    snapshot = {role: {"seq": rows[role]["seq"],
                       "sha256": rows[role]["sha256"]}
                for role in ROLES}
    for row in snapshot.values():
        if (type(row["seq"]) is not int or row["seq"] < 0 or
                not isinstance(row["sha256"], str) or
                re.fullmatch("[0-9a-f]{64}", row["sha256"]) is None):
            raise Refusal("source_snapshot_format")
    return snapshot


def _candidate(store, session, project, refs, temporal_mode, option_role):
    try:
        result = bridge.evaluate(
            store, session, project, refs, temporal_mode, option_role)
    except Exception as exc:
        raise Refusal("typed_shadow_source_refused") from exc
    if (not isinstance(result, dict) or
            result.get("revision") != bridge.REVISION or
            result.get("status") != "SHADOW_ONLY" or
            result.get("authority") is not False or
            result.get("f5_decision_authority") is not False or
            result.get("native_executed") is not False or
            result.get("model_output_used") is not False or
            type(result.get("jepa_weight")) is not int or
            result.get("jepa_weight") != 0 or
            result.get("canonical_gate_pass") is not False or
            result.get("verification_scope") != SCOPE or
            result.get("action") not in ("A", "B", "NONE") or
            result.get("source_refs") != refs):
        raise Refusal("non_shadow_candidate")
    hashes = result.get("all_three_source_hashes")
    if (not isinstance(hashes, dict) or set(hashes) != set(ROLES) or
            any(not isinstance(hashes[k], str) or
                re.fullmatch("[0-9a-f]{64}", hashes[k]) is None
                for k in ROLES) or
            result.get("source_hashes") != {
                "current": hashes["current"], "old": hashes["old"],
                "options": hashes[option_role]}):
        raise Refusal("candidate_source_hash_mismatch")
    return result


def _payload(ticket):
    if not isinstance(ticket, dict) or set(ticket) != {
            "schema", "session", "project", "refs", "temporal_mode",
            "option_role", "candidate", "sources", "seal_sha256"}:
        raise Refusal("ticket_shape")
    if ticket["schema"] != SCHEMA:
        raise Refusal("ticket_schema")
    if (not isinstance(ticket["session"], str) or
            not ticket["session"] or
            not isinstance(ticket["project"], str) or
            re.fullmatch("[A-Za-z]+", ticket["project"]) is None or
            not isinstance(ticket["refs"], dict) or
            set(ticket["refs"]) != set(ROLES) or
            any(not isinstance(v, str) or not v
                for v in ticket["refs"].values()) or
            len(set(ticket["refs"].values())) != 3 or
            ticket["temporal_mode"] not in (
                "RETAIN_PRIOR_RULES", "REVISED_CURRENT_RULES") or
            ticket["option_role"] not in ("sheet", "current") or
            not isinstance(ticket["candidate"], dict) or
            not isinstance(ticket["sources"], dict) or
            set(ticket["sources"]) != set(ROLES)):
        raise Refusal("ticket_contract")
    for role in ROLES:
        row = ticket["sources"][role]
        if (not isinstance(row, dict) or set(row) != {"seq", "sha256"} or
                type(row["seq"]) is not int or row["seq"] < 0 or
                not isinstance(row["sha256"], str) or
                re.fullmatch("[0-9a-f]{64}", row["sha256"]) is None):
            raise Refusal("ticket_source_shape")
    if (not isinstance(ticket["seal_sha256"], str) or
            re.fullmatch("[0-9a-f]{64}", ticket["seal_sha256"]) is None):
        raise Refusal("ticket_digest_shape")
    return {k: v for k, v in ticket.items() if k != "seal_sha256"}


def seal_candidate(store, session, project, refs, temporal_mode, option_role):
    """Snapshot a deterministic SHADOW candidate, never a permission token."""
    before = _snapshot(store, session, project, refs)
    candidate = _candidate(store, session, project, refs,
                           temporal_mode, option_role)
    after = _snapshot(store, session, project, refs)
    if before != after:
        raise Refusal("source_changed_during_seal")
    if (candidate.get("source_refs") != refs or
            candidate.get("all_three_source_hashes") != {
                role: before[role]["sha256"] for role in ROLES}):
        raise Refusal("candidate_source_binding")
    payload = {
        "schema": SCHEMA, "session": session, "project": project,
        "refs": dict(refs), "temporal_mode": temporal_mode,
        "option_role": option_role, "candidate": copy.deepcopy(candidate),
        "sources": before}
    return {**payload, "seal_sha256": _digest(payload)}


def inspect_shadow(store, ticket, session, project):
    """Revalidate at a *read-only SHADOW* inspection boundary.

    No atomic transaction extends beyond this call. Callers MUST NOT use this
    output to authorize a side effect, F5 decision, learning or live answer.
    """
    payload = _payload(ticket)
    if _digest(payload) != ticket["seal_sha256"]:
        raise Refusal("ticket_modified")
    if session != payload["session"] or project != payload["project"]:
        raise Refusal("consumer_session_or_project_mismatch")
    before = _snapshot(store, session, project, payload["refs"])
    if before != payload["sources"]:
        raise Refusal("source_changed_after_candidate_return")
    fresh = _candidate(store, session, project, payload["refs"],
                       payload["temporal_mode"], payload["option_role"])
    if fresh != payload["candidate"]:
        raise Refusal("typed_candidate_changed_after_return")
    after = _snapshot(store, session, project, payload["refs"])
    if after != before:
        raise Refusal("source_changed_during_shadow_inspection")
    return {
        "schema": SCHEMA, "status": "SHADOW_ONLY",
        "verification_scope": SCOPE, "action": fresh["action"],
        "authority": False, "f5_decision_authority": False,
        "native_executed": False, "model_output_used": False,
        "canonical_gate_pass": False, "jepa_weight": 0, "read_only": True,
        "post_return_atomic": False,
        "source_refs": dict(payload["refs"]),
        "source_hashes": {role: after[role]["sha256"] for role in ROLES}}
