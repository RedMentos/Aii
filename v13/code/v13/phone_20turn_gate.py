"""Privacy-safe, read-only 20-turn *local metadata* gate for V13 Redmi.

Checks the 20 most recent assistant events from ONE latest chat session only.
This is NOT a task-quality benchmark, native-process attestation, proof of
learned latent transfer or approval to promote a release. Neither assistant nor
user text, prompts, source refs, session IDs, event IDs, paths, hashes or model
names are selected for the report. No turns or inference are created.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sqlite3
import sys

from .phone_offer_delivery_audit import (
    MAX_JSON_BYTES, ROLES, _audit_one, connect_readonly,
)

SCHEMA = "v13.phone-20turn-local-metadata-gate/1"
WINDOW = 20
STATUS = {"FINAL", "ERROR", "DEADLINE", "CANCELLED", "INTERRUPTED",
          "STREAMING", "OUTPUT_COMMITTED", "DRAFT"}
MAX_EVENT_ID = 160
MAX_SESSION_ID = 160
MAX_SECONDS = 3600.
MAX_RSS_BYTES = 1 << 44


def _finite(value, maximum=MAX_SECONDS, *, positive=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value < (0 if not positive else 0.000001)
            or value > maximum):
        return None
    return round(float(value), 3)


def _integer(value, max_value=1_000_000):
    return value if type(value) is int and 0 <= value <= max_value else None


def _metadata(raw, original_bytes):
    if (type(original_bytes) is not int or not 0 <= original_bytes <= MAX_JSON_BYTES
            or not isinstance(raw, (bytes, str))):
        return None
    try:
        document = json.loads(raw)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        return None
    return document if type(document) is dict else None


def check(conn):
    """Read-only latest-session cohort, never a quality or phone-attestation PASS."""
    latest = conn.execute(
        "SELECT session_id FROM messages WHERE role IN ('assistant','user') "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if not latest or type(latest[0]) is not str or not 0 < len(latest[0]) <= MAX_SESSION_ID:
        return _empty("NO_LATEST_CHAT_SESSION")
    # Deliberately no assistant/user text, packet bodies or file paths.
    rows = conn.execute(
        "SELECT event_id,status,length(CAST(metadata AS BLOB)),"
        "substr(CAST(metadata AS BLOB),1,?) "
        "FROM messages "
        "WHERE session_id=? AND role='assistant' AND event_id IS NOT NULL "
        "ORDER BY id DESC LIMIT ?",
        (MAX_JSON_BYTES + 1, latest[0], WINDOW)).fetchall()
    count = len(rows)
    status_counts = {kind: 0 for kind in sorted(STATUS)}
    status_counts["UNKNOWN"] = 0
    malformed = 0
    duplicates = 0
    seen = set()
    native = 0
    reported = 0
    timing_present = 0
    within_deadline = 0
    native_first_token_present = 0
    zero_c3_tokens = 0
    native_http200 = 0
    quoted_c4 = 0
    body_role_turns = {r: {"attempt": 0, "selected_delivered_quoted_metadata": 0,
                           "rendered_http200_reported": 0} for r in ROLES}
    max_seconds = None
    max_native_rss_mib = None

    for offset, (event_id, status, nbytes, raw) in enumerate(rows):
        event_valid = (type(event_id) is str and
                       0 < len(event_id) <= MAX_EVENT_ID and event_id not in seen)
        if not event_valid:
            duplicates += int(type(event_id) is str and event_id in seen)
        else:
            seen.add(event_id)
        status_key = status if type(status) is str and status in STATUS else "UNKNOWN"
        status_counts[status_key] += 1
        meta = _metadata(raw, nbytes)
        if not event_valid or meta is None:
            malformed += 1
            continue
        model_generated = meta.get("model_generated") is True
        report = meta.get("runner")
        report = report if type(report) is dict else {}
        c3_tokens = _integer(report.get("generated_tokens"))
        c3_done = (status == "FINAL" and model_generated
                   and report.get("role") == "C3_LANGUAGE"
                   and report.get("status") == "FINAL"
                   and c3_tokens is not None and c3_tokens > 0
                   and meta.get("output_authority") != "SOURCE_SYSTEM_REPORT")
        if c3_done:
            native += 1
        if model_generated:
            reported += 1
        if report.get("role") == "C3_LANGUAGE" and c3_tokens == 0:
            zero_c3_tokens += 1
        duration = _finite(meta.get("duration_s"))
        if duration is not None:
            max_seconds = max(max_seconds or 0., duration)
        budget_cfg = meta.get("effective_config")
        deadline = _finite(
            budget_cfg.get("deadline_seconds") if type(budget_cfg) is dict else None,
            positive=True)
        if c3_done and duration is not None and deadline is not None:
            timing_present += 1
            within_deadline += int(duration <= deadline)
        if c3_done and _finite(report.get("ttft_s")) is not None:
            native_first_token_present += 1
        rss = _integer(report.get("sampled_peak_rss_bytes"), MAX_RSS_BYTES)
        if rss is not None:
            mib = round(rss / (1024 * 1024), 1)
            max_native_rss_mib = max(max_native_rss_mib or 0., mib)
        # Reuse the already tested exact-packet B1/B2 audit. This only proves
        # stored source-quoted receipts and runtime-reported native template
        # submission; it does not re-read user source text.
        try:
            turn = _audit_one(conn, offset + 1, event_id, status, raw)
        except (TypeError, ValueError, RecursionError):
            # A corrupted telemetry JSON tree may exceed Python's nesting
            # limit even when its byte size is bounded. Never let a malformed
            # private row produce a traceback or a positive cohort.
            malformed += 1
            continue
        if turn["audit_incomplete"]:
            malformed += 1
            continue
        for role in ROLES:
            record = turn["roles"][role]
            body_role_turns[role]["attempt"] += int(record["native_attempts"] > 0)
            body_role_turns[role]["selected_delivered_quoted_metadata"] += int(
                record["native_attempts"] > 0
                and record["selected_quoted_receipts"] > 0 and c3_done)
            body_role_turns[role]["rendered_http200_reported"] += int(
                record["native_attempts"] > 0
                and record.get("native_template_http200_submitted") is True and c3_done)
        # A packet/receipt without a logged B-model attempt does NOT establish
        # the actual B1/B2 contribution, even when C3 accepted a prompt.
        both_attempted_quoted = bool(
            c3_done and all(turn["roles"][role]["native_attempts"] > 0
                            and turn["roles"][role]["selected_quoted_receipts"] > 0
                            for role in ROLES))
        quoted_c4 += int(both_attempted_quoted)
        native_http200 += int(
            both_attempted_quoted
            and len(turn["native_template_http200_submitted_roles"]) == 2)

    if not count:
        local_status = "NO_ASSISTANT_EVENTS_IN_LATEST_SESSION"
    elif count < WINDOW:
        local_status = "FEWER_THAN_20_ASSISTANT_EVENTS"
    elif malformed or duplicates:
        local_status = "MALFORMED_OR_AMBIGUOUS_TURN_METADATA"
    elif status_counts["FINAL"] != WINDOW:
        local_status = "NONFINAL_TURNS_IN_COHORT"
    elif native != WINDOW:
        local_status = "NATIVE_C3_EXECUTION_NOT_RECORDED_FOR_ALL_TURNS"
    elif timing_present != WINDOW:
        local_status = "MISSING_NATIVE_DEADLINE_EVIDENCE"
    elif within_deadline != WINDOW:
        local_status = "NATIVE_DEADLINE_EXCEEDED"
    elif native_first_token_present != WINDOW:
        local_status = "MISSING_NATIVE_FIRST_TOKEN_TIMINGS"
    elif not quoted_c4:
        local_status = "NO_BOTH_BODY_SELECTED_QUOTED_RECEIPTS"
    elif not native_http200:
        local_status = "NO_BOTH_BODY_NATIVE_TEMPLATE_SUBMISSION_WITNESS"
    else:
        local_status = "LOCAL_METADATA_COHORT_COMPLETE_DEVICE_REVIEW_REQUIRED"

    return {
        "schema": SCHEMA,
        "source": "LOCAL_READ_ONLY_SQLITE_ONE_SESSION_METADATA",
        "local_status": local_status,
        "turns_required": WINDOW,
        "assistant_turns_scanned": count,
        "status_counts": status_counts,
        "invalid_or_oversized_metadata_turns": malformed,
        "duplicate_assistant_event_ids": duplicates,
        "reported_model_generated_turns": reported,
        "native_c3_final_positive_token_turns": native,
        "c3_reported_zero_token_turns": zero_c3_tokens,
        "native_ttft_sampled_turns": native_first_token_present,
        "native_deadline_available_turns": timing_present,
        "native_within_declared_deadline_turns": within_deadline,
        "maximum_turn_seconds": max_seconds,
        "maximum_runner_reported_rss_mib": max_native_rss_mib,
        "both_body_selected_quoted_metadata_receipt_turns": quoted_c4,
        "both_body_native_template_http200_reported_turns": native_http200,
        "body_roles": body_role_turns,
        "device_physical_execution_independently_verified": False,
        "mixed_task_suite_verified": False,
        "answer_quality_verified": False,
        "latency_baseline_verified_on_redmi": False,
        "native_latent_communication_verified": False,
        "release_approved": False,
        "warning": ("A local SQLite metadata cohort is never evidence of 20 "
                    "independently verified Redmi model tasks, correctness, "
                    "native model identity, or functional release acceptance."),
    }


def _empty(reason):
    return {
        "schema": SCHEMA, "source": "LOCAL_READ_ONLY_SQLITE_ONE_SESSION_METADATA",
        "local_status": reason, "turns_required": WINDOW,
        "assistant_turns_scanned": 0,
        "device_physical_execution_independently_verified": False,
        "mixed_task_suite_verified": False,
        "answer_quality_verified": False, "release_approved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only last-20 local native metadata; no text exported")
    parser.add_argument("--home", type=Path, default=Path.home() / "v13")
    args = parser.parse_args(argv)
    try:
        conn = connect_readonly(args.home)
        try:
            result = check(conn)
        finally:
            conn.close()
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError) as exc:
        result = _empty("LOCAL_READ_UNAVAILABLE_" + type(exc).__name__)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["local_status"] == "LOCAL_METADATA_COHORT_COMPLETE_DEVICE_REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    sys.exit(main())
