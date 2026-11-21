"""Read-only local audit: did native B1/B2 actually reach the single C3 report?

Does not create turns, load models, write learning state, read user text, upload
anything or treat synthetic tests as native Redmi evidence. It inspects only
existing SQLite metadata, sanitized telemetry and packet role/IDs. The current
runtime emits `body_offer_delivered` after a fully stored source-bound offer.
Older stored offers without that receipt are labelled LEGACY_PACKET_NO_RECEIPT.
A C4 selection + C3 runner completion is metadata evidence, NOT proof the
selected content survived native prompt admission, influenced C3 tokens or
crossed through learned latent-space communication.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote


ROLES = ("B1_DETAIL", "B2_GIST")
STATUSES = {"FINAL", "ERROR", "DEADLINE", "CANCELLED", "INTERRUPTED"}
PHASES = {"load", "template", "prefill", "stream"}
KINDS = ("body_offer_attempt", "body_offer_delivered")
SCHEMA = "v13.phone-offer-delivery-audit/1"
MAX_JSON_BYTES = 262144
MAX_ROWS_PER_TURN = 2000
ADMISSION_STATUSES = frozenset(("ADMITTED","PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET"))
ADMISSION_OMISSIONS = frozenset((
    "C3_LAYER_TASK_CONTEXT","C3_LAYER_DIGEST","C3_LAYER_USER_MODEL",
    "OLD_NATIVE_HISTORY","BODY_SOURCE_ADDRESS_METADATA",
    "BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS","BODY_NON_SOURCE_STATE_DETAIL",
    "BODY_DUPLICATE_EXACT_DETAIL_WINDOWS","BODY_GLOBAL_SPACE_POINTER_METADATA",
    "BODY_OLDER_SELF_OUTCOMES_NOT_IN_NATIVE_VIEW","BODY_DUPLICATE_STREAM_SOURCE",
))



def _obj(text):
    # Packet/telemetry metadata is untrusted diagnostic data. A corrupt
    # record must not stop a no-text phone audit or exhaust JSON parsing.
    if type(text) not in (str, bytes) or len(text) > MAX_JSON_BYTES:
        return {}
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError, UnicodeError):
        return {}


def _count(value):
    return value if type(value) is int and 0 <= value <= 100000 else None


def _duration(value):
    return round(float(value), 3) if (
        type(value) in (int, float) and math.isfinite(value)
        and 0 <= value <= 36000
    ) else None


def _safe_phases(metrics):
    phases = metrics.get("stage_durations_s")
    if not isinstance(phases, dict):
        return {}
    return {k: time_s for k, value in phases.items()
            if k in {"load_s", "template_s", "prefill_to_first_token_s", "stream_s"}
            if (time_s := _duration(value)) is not None}


def _prompt_admission(metrics):
    """Only safe token counts and fixed omission enums, never model/user text."""
    raw=metrics.get("prompt_admission")
    if not isinstance(raw,dict):
        return None
    reasons=raw.get("removed_layers")
    if not isinstance(reasons,list):
        reasons=[]
    return {
        "revision_verified":raw.get("revision") == "v13.native-prompt-admission/1",
        "status":(raw.get("status") if type(raw.get("status")) is str and raw.get("status") in ADMISSION_STATUSES else "UNKNOWN"),
        "original_prompt_tokens":_count(raw.get("original_prompt_tokens")),
        "prompt_tokens":_count(raw.get("prompt_tokens")),
        "target_tokens":_count(raw.get("target_tokens")),
        "omitted":[x for x in reasons[:16] if type(x) is str and x in ADMISSION_OMISSIONS],
        "source_text_rewritten":raw.get("source_text_rewritten") is True,
    }


def _role_from_packet(payload, kind):
    value = _obj(payload)
    role = value.get("role" if kind == "OfferPacket" else "target_role")
    return role if role in ROLES else None


def _runtime_native_template_receipts(report, selected, events):
    """Cross-check the runtime's reported HTTP-200 template witness against local packet IDs.

    The audit does NOT independently attest the server, hashes, source text or
    model attention. Mismatched, stale, malformed and absent claims fail closed.
    """
    witness = report.get("native_offer_prompt_receipt")
    if type(witness) is not dict:
        return set()
    if (witness.get("revision") != "v13.native-offer-prompt-receipt/1"
            or witness.get("status") != "RENDERED_WITH_QUOTES"
            or witness.get("native_template_submitted") is not True
            or witness.get("native_completion_http_200") is not True
            or witness.get("native_template_rendered") is not True
            or witness.get("source_span_revalidated_here") is not False
            or witness.get("native_semantic_use_proven") is not False):
        return set()
    rows = witness.get("offers")
    if type(rows) is not list or not 1 <= len(rows) <= len(ROLES):
        return set()
    seen, matched = set(), set()
    for row in rows:
        if type(row) is not dict:
            return set()
        role, ident, n = (row.get("role"), row.get("packet_id"),
                          row.get("rendered_quote_count"))
        if (type(role) is not str or role not in ROLES or role in seen
                or type(ident) is not str or not 0 < len(ident) <= 256
                or type(n) is not int or not 1 <= n <= 8):
            return set()
        seen.add(role)
        # This reported native template must refer to this turn's selected,
        # durably delivered, quoted packet of the exact expected role.
        if (ident not in selected or ident not in events[role]["delivered_ids"]
                or not (type(events[role]["offers"].get(ident)) is int
                        and events[role]["offers"][ident] > 0)):
            return set()
        matched.add(role)
    return matched


def _audit_one(conn, index, event_id, status, metadata):
    meta = _obj(metadata)
    raw_selected = meta.get("selected_offer_ids")
    # Selecting before validating the type used to throw on malformed
    # integer/dict metadata; never trust recorded role/packet IDs.
    selected_ids = {x for x in raw_selected[:128]
                    if type(x) is str and 0 < len(x) <= 256} \
                   if isinstance(raw_selected, list) else set()
    report = meta.get("runner") or {}
    report = report if isinstance(report, dict) else {}
    reporter = report.get("role") if report.get("role") == "C3_LANGUAGE" else None
    native_c3_tokens = _count(report.get("generated_tokens"))
    native_c3_output = (reporter is not None and status == "FINAL"
                        and native_c3_tokens is not None and native_c3_tokens > 0)
    events = {r: {"query_count": 0, "attempts": [], "offers": {},
                  "delivered_ids": set()} for r in ROLES}
    # Bound SQL materialization before a corrupt/private payload enters
    # Python, and keep an explicit truncation signal for fail-closed verdicts.
    packet_rows = conn.execute(
        "SELECT kind,substr(CAST(payload AS BLOB),1,?),id FROM packets WHERE event_id=? "
        "AND kind IN ('QueryPacket','OfferPacket') ORDER BY rowid LIMIT ?",
        (MAX_JSON_BYTES+1, event_id, MAX_ROWS_PER_TURN+1)).fetchall()
    packet_rows_truncated = len(packet_rows) > MAX_ROWS_PER_TURN
    for kind, payload, packet_id in packet_rows[:MAX_ROWS_PER_TURN]:
        role = _role_from_packet(payload, kind)
        if role is None:
            continue
        if kind == "QueryPacket":
            events[role]["query_count"] += 1
        elif isinstance(packet_id, str):
            obj = _obj(payload)
            evidence = obj.get("evidence_refs")
            events[role]["offers"][packet_id] = (
                len(evidence) if isinstance(evidence, list) else None)

    telemetry_rows = conn.execute(
        "SELECT kind,substr(CAST(metrics AS BLOB),1,?) FROM telemetry WHERE event_id=? "
        "AND kind IN (?,?) ORDER BY id ASC LIMIT ?",
        (MAX_JSON_BYTES+1, event_id, *KINDS, MAX_ROWS_PER_TURN+1)).fetchall()
    telemetry_rows_truncated = len(telemetry_rows) > MAX_ROWS_PER_TURN
    incomplete = packet_rows_truncated or telemetry_rows_truncated
    for kind, raw in telemetry_rows[:MAX_ROWS_PER_TURN]:
        data = _obj(raw)
        role = data.get("role")
        if role not in ROLES:
            continue
        if kind == "body_offer_delivered":
            ident = data.get("packet_id")
            if type(ident) is str and 0 < len(ident) <= 256:
                events[role]["delivered_ids"].add(ident)
        else:
            runner = data.get("runner")
            runner = runner if isinstance(runner, dict) else {}
            native_status = data.get("status", runner.get("status"))
            native_status = native_status if type(native_status) is str and native_status in STATUSES else "UNKNOWN"
            phase = runner.get("last_phase")
            events[role]["attempts"].append({
                "native_status": native_status,
                "last_phase": phase if phase in PHASES else None,
                "phase_seconds": _safe_phases(runner),
                "prompt_tokens": _count(runner.get("prompt_tokens")),
                "generated_tokens": _count(runner.get("generated_tokens")),
                "duration_s": _duration(runner.get("duration_s")),
                "prompt_admission": _prompt_admission(runner),
            })

    roles = {}
    for role, record in events.items():
        packets = record["offers"]
        receipts = record["delivered_ids"]
        selected = set(packets) & selected_ids
        # A receipt for *another* packet of this role is not evidence that
        # the C4-selected packet reached the source-checked consumer.
        selected_delivered = selected & receipts
        quoted = {pid for pid, count in packets.items()
                  if type(count) is int and count > 0}
        attempts = record["attempts"]
        if incomplete:
            result = "INCOMPLETE_AUDIT_ROW_CAP"
        elif selected and not selected_delivered:
            result = "SELECTED_WITHOUT_DELIVERY_RECEIPT"
        elif selected_delivered and native_c3_output:
            # Legacy status name: only C4 selection + delivered receipt +
            # C3 token output are proven; native prompt inclusion is NOT.
            result = "IN_FINAL_C3_REPORT"
        elif selected_delivered and reporter == "C3_LANGUAGE" and status == "FINAL":
            result = "SELECTED_C3_FINAL_ZERO_TOKEN_EVIDENCE"
        elif selected:
            result = "SELECTED_BUT_REPORT_UNFINISHED"
        elif packets and not receipts:
            result = "LEGACY_PACKET_NO_RECEIPT"
        elif packets:
            result = "DELIVERED_NOT_SELECTED"
        elif attempts and any(a["native_status"] in {"ERROR", "DEADLINE", "CANCELLED"}
                              for a in attempts):
            result = "NATIVE_FAILED_NO_OFFER"
        elif attempts:
            result = "NATIVE_COMPLETED_NO_VALID_OFFER"
        elif record["query_count"]:
            result = "QUERY_PREPARED_NO_NATIVE_ATTEMPT"
        else:
            result = "NOT_ATTEMPTED"
        roles[role] = {
            "delivery": result,
            "query_count": record["query_count"],
            "native_attempts": len(attempts),
            "source_bound_offer_packets": len(packets),  # legacy: all stored packets, including unquoted
            "quoted_offer_packets": len(quoted),
            "delivery_receipts": len(receipts & set(packets)),
            "selected_for_report": len(selected),
            "selected_delivery_receipts": len(selected_delivered),
            "selected_quoted_receipts": len(selected_delivered & quoted),
            "last_native": attempts[-1] if attempts else None,
        }
    native_template_roles = (_runtime_native_template_receipts(report, selected_ids, events)
                             if native_c3_output and not incomplete else set())
    for role in ROLES:
        roles[role]["native_template_http200_submitted"] = role in native_template_roles
    c3phases = _safe_phases(report)
    return {
        "index_newest_first": index,
        "turn_status": status if status in STATUSES else "UNKNOWN",
        "c3_reporter": reporter is not None,
        "c3_phase_seconds": c3phases,
        "c3_prompt_tokens": _count(report.get("prompt_tokens")),
        "c3_generated_tokens": native_c3_tokens,
        "c3_native_output_observed": native_c3_output,
        "native_template_http200_submitted_roles": sorted(native_template_roles),
        "audit_incomplete": incomplete,
        "c3_prompt_inclusion_proven": False,
        "c3_semantic_use_proven": False,
        "native_latent_exchange_proven": False,
        "c3_prompt_admission": _prompt_admission(report),
        "roles": roles,
    }


def audit(conn, limit=10):
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("turn count must be 1..20")
    # Avoid ever selecting user/assistant text: metadata, roles and counts only.
    messages = conn.execute(
        "SELECT event_id,status,substr(CAST(metadata AS BLOB),1,?) FROM messages "
        "WHERE role='assistant' AND event_id IS NOT NULL "
        "ORDER BY id DESC LIMIT ?", (MAX_JSON_BYTES+1, limit)).fetchall()
    seen = set()
    turns = []
    for eid, status, metadata in messages:
        if not isinstance(eid, str) or eid in seen:
            continue
        seen.add(eid)
        turns.append(_audit_one(conn, len(turns) + 1, eid, status, metadata))
    summary = {}
    for role in ROLES:
        summary[role] = {
            "native_attempt_turns": sum(t["roles"][role]["native_attempts"] > 0
                                        for t in turns),
            "valid_offer_turns": sum(t["roles"][role]["source_bound_offer_packets"] > 0
                                    for t in turns),
            "in_final_c3_report_turns": sum(
                t["roles"][role]["delivery"] == "IN_FINAL_C3_REPORT"
                for t in turns),
            "native_failed_turns": sum(
                t["roles"][role]["delivery"] == "NATIVE_FAILED_NO_OFFER"
                for t in turns),
        }
    # This is a *diagnostic* gate, not a functional model-acceptance gate.
    # Counting both bodies without linking selected packet IDs to delivery
    # receipts, and then observing real C3 token output, would hide P0 failures.
    both = sum(
        t["c3_native_output_observed"] and not t["audit_incomplete"]
        and all(t["roles"][r]["delivery"] == "IN_FINAL_C3_REPORT"
                and t["roles"][r]["selected_quoted_receipts"] > 0
                for r in ROLES)
        for t in turns)
    both_native = sum(
        t["c3_native_output_observed"] and not t["audit_incomplete"]
        and all(t["roles"][r]["native_template_http200_submitted"] for r in ROLES)
        for t in turns)
    zero_token_c3_deadlines = sum(
        t["turn_status"] == "DEADLINE"
        and t["c3_reporter"] and t["c3_generated_tokens"] == 0
        for t in turns)
    incomplete_turns = sum(t["audit_incomplete"] for t in turns)
    proof_status = ("NO_ASSISTANT_TURNS" if not turns
                    else "BOUNDED_METADATA_INCOMPLETE" if incomplete_turns
                    else "BOTH_BODY_NATIVE_TEMPLATE_HTTP200_REPORTED" if both_native
                    else "BOTH_BODY_C4_C3_METADATA_ONLY" if both
                    else "B1_B2_TO_C3_CHAIN_NOT_OBSERVED")
    return {
        "schema": SCHEMA,
        "source": "LOCAL_SQLITE_METADATA_ONLY",
        "end_to_end_gate": {
            "status": proof_status,
            "both_body_selected_delivered_and_c3_generated_turns": both,
            "both_body_native_template_http200_reported_turns": both_native,
            "c3_deadline_zero_token_turns": zero_token_c3_deadlines,
            "incomplete_metadata_turns": incomplete_turns,
            "native_prompt_offer_inclusion_verified": False,
            "native_template_submission_reported_by_runtime": both_native > 0,
            "source_span_revalidated_by_audit": False,
            "learned_latent_exchange_verified": False,
            "device_functional_acceptance": "NOT_VERIFIED",
        },
        "device_proof": "NOT_INDEPENDENTLY_VERIFIED",
        "evidence_boundary": (
            "LOCAL_SQLITE_METADATA_PLUS_REPORTED_HTTP_200_NATIVE_TEMPLATE_RECEIPTS"
            if both_native else "METADATA_RECEIPTS_AND_NATIVE_TOKEN_COUNTS_ONLY"),
        "warning": "Template receipts are runtime-reported evidence that the exact typed hypothesis layer survived native rendering and was submitted to an HTTP 200 completion endpoint; no independent native-device attestation, attention, semantic use or learned latent exchange is established.",
        "turn_count": len(turns),
        "roles": summary,
        "turns": turns,
    }


def connect_readonly(home):
    home = Path(home).expanduser()
    dbdir = home / "data" / "db"
    db = dbdir / "brain.sqlite3"
    # A real installed database is private. Fail closed on unexpected
    # symlinks, ownership or missing files rather than creating a new DB.
    for path in (home, home / "data", dbdir, db):
        if path.is_symlink():
            raise ValueError("symlinked runtime database path")
    if not db.is_file() or db.stat().st_uid != os.getuid():
        raise ValueError("local runtime database unavailable")
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = db.with_name(db.name + suffix)
        if sidecar.is_symlink() or (
                sidecar.exists() and (not sidecar.is_file()
                                      or sidecar.stat().st_uid != os.getuid())):
            raise ValueError("unsafe runtime database sidecar")
    # SQLite read-only connections may create a missing -shm file in WAL
    # mode. Refuse that case rather than claiming a read-only audit that
    # mutates the owner's live phone storage.
    with db.open("rb") as source:
        header = source.read(20)
    if len(header) != 20 or not header.startswith(b"SQLite format 3\x00"):
        raise ValueError("invalid SQLite database header")
    if header[18:20] == b"\x02\x02" and not all(
            db.with_name(db.name + suffix).is_file()
            for suffix in ("-wal", "-shm")):
        raise ValueError("WAL coordination files unavailable")
    uri = "file:" + quote(str(db.absolute()), safe="/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=.3, isolation_level=None)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local no-text B1/B2-to-C3 delivery audit")
    parser.add_argument("--home", type=Path, default=Path.home() / "v13")
    parser.add_argument("--turns", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        with connect_readonly(args.home) as conn:
            print(json.dumps(audit(conn, args.turns), ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, sqlite3.Error, ValueError, UnicodeError) as exc:
        # Do not expose filesystem paths, SQL or private payloads in errors.
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
