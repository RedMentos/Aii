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
SCHEMA = "v13.phone-offer-delivery-audit/2"
PROMPT_RECEIPT_REVISIONS = frozenset(("v13.native-offer-prompt-receipt/1", "v13.native-offer-prompt-receipt/2"))
TOKENIZER_API = "llama.cpp-server /tokenize with_pieces=true, add_special=false, parse_special=true"
TOKENIZER_API_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
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
    if (witness.get("revision") not in PROMPT_RECEIPT_REVISIONS
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



def _valid_sha256(value):
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _native_prefill_token_count_match(report):
    prompt_tokens = _count(report.get("prompt_tokens"))
    timings = report.get("timings")
    if type(timings) is not dict or prompt_tokens is None:
        return False
    prompt_n, cache_n = timings.get("prompt_n"), timings.get("cache_n")
    return (type(prompt_n) is int and prompt_n >= 0
            and type(cache_n) is int and cache_n >= 0
            and prompt_n + cache_n == prompt_tokens)


def _native_prompt_inclusion_mode(report, template_roles, native_c3_output,
                                  incomplete, prefill_count_matched):
    if (not native_c3_output or incomplete or set(template_roles) != set(ROLES)
            or not prefill_count_matched):
        return None
    witness = report.get("native_offer_prompt_receipt")
    if type(witness) is not dict:
        return None
    request_sha = witness.get("native_request_prompt_sha256")
    prompt_sha = witness.get("native_prompt_sha256")
    if (witness.get("native_completion_http_200") is not True
            or witness.get("native_template_submitted") is not True
            or witness.get("native_request_prompt_submitted") is not True
            or witness.get("native_request_prompt_matches_admission") is not True
            or not _valid_sha256(prompt_sha)
            or not _valid_sha256(request_sha)
            or request_sha != prompt_sha):
        return None
    return "HTTP_COMPLETION_PROMPT_HASH_AND_PREFILL_COUNT"


def _native_prompt_token_span_receipts(report, template_roles, selected_ids, events,
                                      native_prompt_inclusion_verified, incomplete):
    """Validate sanitized per-role quote-token spans against this exact C3 request.

    The audit cross-checks the runtime receipt, request hash, prefill count and
    delivered packet IDs. It does not re-run the native tokenizer or prove
    attention/semantic use; token pieces and quote text are never returned.
    """
    if (not native_prompt_inclusion_verified or incomplete
            or set(template_roles) != set(ROLES)):
        return {}
    witness = report.get("native_offer_prompt_receipt")
    if (type(witness) is not dict
            or witness.get("revision") != "v13.native-offer-prompt-receipt/2"
            or witness.get("status") != "RENDERED_WITH_QUOTES"
            or witness.get("native_token_spans_verified") is not True
            or witness.get("native_token_spans_status") != "VERIFIED_EXACT"
            or witness.get("native_token_span_semantic_use_proven") is not False
            or witness.get("native_tokenizer_api") != TOKENIZER_API
            or witness.get("native_tokenizer_api_revision") != TOKENIZER_API_REVISION
            or witness.get("native_token_span_method") !=
               "UTF8_BYTE_PIECE_RECONSTRUCTION_AND_UNIQUE_PREFILL_SUBSEQUENCE"):
        return {}
    prompt_sha = witness.get("native_prompt_sha256")
    if (not _valid_sha256(prompt_sha)
            or witness.get("native_token_spans_prompt_sha256") != prompt_sha
            or witness.get("native_token_spans_piece_stream_sha256") != prompt_sha
            or witness.get("native_token_spans_prefill_token_ids_sha256")
               != witness.get("native_token_ids_sha256")
            or not _valid_sha256(witness.get("native_token_spans_content_token_ids_sha256"))
            or not _valid_sha256(witness.get("native_token_spans_prefill_token_ids_sha256"))):
        return {}
    prompt_bytes = _count(witness.get("native_prompt_utf8_bytes"))
    prefill_tokens = _count(witness.get("native_token_spans_prefill_tokens"))
    content_tokens = _count(witness.get("native_token_spans_content_tokens"))
    prefix = _count(witness.get("native_token_spans_special_prefix_tokens"))
    suffix = _count(witness.get("native_token_spans_special_suffix_tokens"))
    reported_prompt_tokens = _count(report.get("prompt_tokens"))
    if (prompt_bytes is None or prompt_bytes == 0
            or prefill_tokens is None or prefill_tokens != reported_prompt_tokens
            or content_tokens is None or content_tokens == 0
            or prefix is None or suffix is None
            or prefix + suffix > 2
            or content_tokens + prefix + suffix != prefill_tokens):
        return {}
    rows = witness.get("offers")
    if type(rows) is not list or len(rows) != len(ROLES):
        return {}
    result, seen_roles, token_ranges = {}, set(), []
    for row in rows:
        if type(row) is not dict:
            return {}
        role, ident, quote_count = (row.get("role"), row.get("packet_id"),
                                   row.get("rendered_quote_count"))
        if (type(role) is not str or role not in ROLES or role in seen_roles
                or role not in template_roles
                or type(ident) is not str or not 0 < len(ident) <= 256
                or ident not in selected_ids
                or ident not in events[role]["delivered_ids"]
                or not (type(events[role]["offers"].get(ident)) is int
                        and events[role]["offers"][ident] > 0)
                or type(quote_count) is not int or not 1 <= quote_count <= 8):
            return {}
        spans = row.get("quote_byte_spans")
        if type(spans) is not list or len(spans) != quote_count:
            return {}
        safe_spans, quote_indexes = [], set()
        for span in spans:
            if type(span) is not dict:
                return {}
            quote_index = span.get("quote_index")
            byte_start, byte_end = span.get("byte_start"), span.get("byte_end")
            token_start, token_end = span.get("token_start"), span.get("token_end")
            token_count = span.get("token_count")
            token_hash = span.get("token_ids_sha256")
            if (type(quote_index) is not int or not 0 <= quote_index < quote_count
                    or quote_index in quote_indexes
                    or type(byte_start) is not int or type(byte_end) is not int
                    or not 0 <= byte_start < byte_end <= prompt_bytes
                    or type(token_start) is not int or type(token_end) is not int
                    or not 0 <= token_start < token_end <= prefill_tokens
                    or type(token_count) is not int or token_count != token_end - token_start
                    or span.get("token_boundary_exact") is not True
                    or span.get("status") != "EXACT"
                    or not _valid_sha256(token_hash)):
                return {}
            quote_indexes.add(quote_index)
            token_ranges.append((token_start, token_end))
            safe_spans.append({
                "quote_index": quote_index,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "token_start": token_start,
                "token_end": token_end,
                "token_count": token_count,
                "token_ids_sha256": token_hash,
                "token_boundary_exact": True,
                "status": "EXACT",
            })
        if quote_indexes != set(range(quote_count)):
            return {}
        result[role] = safe_spans
        seen_roles.add(role)
    if seen_roles != set(ROLES):
        return {}
    ordered = sorted(token_ranges)
    if any(current[0] < previous[1]
           for previous, current in zip(ordered, ordered[1:])):
        return {}
    return result


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
    native_prefill_token_count_matched = _native_prefill_token_count_match(report)
    native_prompt_inclusion_mode = _native_prompt_inclusion_mode(
        report, native_template_roles, native_c3_output, incomplete,
        native_prefill_token_count_matched)
    native_prompt_inclusion_verified = native_prompt_inclusion_mode is not None
    native_token_span_receipts = _native_prompt_token_span_receipts(
        report, native_template_roles, selected_ids, events,
        native_prompt_inclusion_verified, incomplete)
    native_prompt_token_spans_verified = set(native_token_span_receipts) == set(ROLES)
    for role in ROLES:
        roles[role]["native_prompt_offer_inclusion_verified"] = bool(
            native_prompt_inclusion_verified and role in native_template_roles)
        roles[role]["native_prompt_token_spans_verified"] = role in native_token_span_receipts
        roles[role]["native_prompt_token_spans"] = native_token_span_receipts.get(role, [])
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
        "native_prefill_token_count_matched": native_prefill_token_count_matched,
        "native_prompt_offer_inclusion_verified": native_prompt_inclusion_verified,
        "native_prompt_inclusion_mode": native_prompt_inclusion_mode,
        "native_prompt_token_spans_verified": native_prompt_token_spans_verified,
        "native_prompt_token_span_roles": sorted(native_token_span_receipts),
        "native_prompt_token_span_mode": (
            "EXACT_UTF8_BYTE_TO_NATIVE_PREFILL_TOKEN_IDS"
            if native_prompt_token_spans_verified else None),
        "native_prompt_token_span_semantic_use_proven": False,
        "c3_prompt_inclusion_proven": native_prompt_inclusion_verified,
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
    both_native_prompt_inclusion = sum(
        t["native_prompt_offer_inclusion_verified"] for t in turns)
    both_native_prompt_token_spans = sum(
        t["native_prompt_token_spans_verified"] for t in turns)
    zero_token_c3_deadlines = sum(
        t["turn_status"] == "DEADLINE"
        and t["c3_reporter"] and t["c3_generated_tokens"] == 0
        for t in turns)
    incomplete_turns = sum(t["audit_incomplete"] for t in turns)
    proof_status = ("NO_ASSISTANT_TURNS" if not turns
                    else "BOUNDED_METADATA_INCOMPLETE" if incomplete_turns
                    else "BOTH_BODY_NATIVE_PROMPT_TOKEN_SPANS_VERIFIED" if both_native_prompt_token_spans
                    else "BOTH_BODY_NATIVE_PROMPT_INCLUSION_VERIFIED" if both_native_prompt_inclusion
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
            "both_body_native_prompt_inclusion_verified_turns": both_native_prompt_inclusion,
            "both_body_native_prompt_token_spans_verified_turns": both_native_prompt_token_spans,
            "native_prompt_token_spans_verified": both_native_prompt_token_spans > 0,
            "native_token_span_semantic_use_proven": False,
            "c3_deadline_zero_token_turns": zero_token_c3_deadlines,
            "incomplete_metadata_turns": incomplete_turns,
            "native_prompt_offer_inclusion_verified": both_native_prompt_inclusion > 0,
            "native_request_prompt_hash_match_observed": both_native_prompt_inclusion > 0,
            "native_prefill_token_count_match_observed": both_native_prompt_inclusion > 0,
            "native_template_submission_reported_by_runtime": both_native > 0,
            "source_span_revalidated_by_audit": False,
            "learned_latent_exchange_verified": False,
            "device_functional_acceptance": "NOT_VERIFIED",
        },
        "device_proof": "NOT_INDEPENDENTLY_VERIFIED",
        "evidence_boundary": (
            "LOCAL_SQLITE_METADATA_PLUS_EXACT_UTF8_NATIVE_TOKEN_SPANS"
            if both_native_prompt_token_spans else
            "LOCAL_SQLITE_METADATA_PLUS_EXACT_NATIVE_PROMPT_BINDING"
            if both_native_prompt_inclusion else
            "LOCAL_SQLITE_METADATA_PLUS_REPORTED_HTTP_200_NATIVE_TEMPLATE_RECEIPTS"
            if both_native else "METADATA_RECEIPTS_AND_NATIVE_TOKEN_COUNTS_ONLY"),
        "warning": "Exact prompt inclusion requires the request prompt hash to match the post-admission template witness and native prompt_n+cache_n to match the admitted token count. Token spans additionally require exact UTF-8 piece reconstruction and a unique content-token subsequence in the add-special prefill. They do not prove attention, semantic use, learned latent exchange or Redmi installation.",
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
