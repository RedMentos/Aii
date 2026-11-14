"""Read-only local audit: did native B1/B2 actually reach the single C3 report?

Does not create turns, load models, write learning state, read user text, upload
anything or treat synthetic tests as native Redmi evidence. It inspects only
existing SQLite metadata, sanitized telemetry and packet role/IDs. The current
runtime emits `body_offer_delivered` after a fully stored source-bound offer.
Older stored offers without that receipt are labelled LEGACY_PACKET_NO_RECEIPT.
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
ADMISSION_STATUSES = frozenset(("ADMITTED","PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET"))
ADMISSION_OMISSIONS = frozenset((
    "C3_LAYER_TASK_CONTEXT","C3_LAYER_DIGEST","C3_LAYER_USER_MODEL",
    "OLD_NATIVE_HISTORY","BODY_SOURCE_ADDRESS_METADATA",
    "BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS","BODY_NON_SOURCE_STATE_DETAIL",
    "BODY_DUPLICATE_EXACT_DETAIL_WINDOWS","BODY_GLOBAL_SPACE_POINTER_METADATA",
    "BODY_OLDER_SELF_OUTCOMES_NOT_IN_NATIVE_VIEW","BODY_DUPLICATE_STREAM_SOURCE",
))



def _obj(text):
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
        "status":(raw.get("status") if raw.get("status") in ADMISSION_STATUSES else "UNKNOWN"),
        "original_prompt_tokens":_count(raw.get("original_prompt_tokens")),
        "prompt_tokens":_count(raw.get("prompt_tokens")),
        "target_tokens":_count(raw.get("target_tokens")),
        "omitted":[x for x in reasons[:16] if isinstance(x,str) and x in ADMISSION_OMISSIONS],
        "source_text_rewritten":raw.get("source_text_rewritten") is True,
    }


def _role_from_packet(payload, kind):
    value = _obj(payload)
    role = value.get("role" if kind == "OfferPacket" else "target_role")
    return role if role in ROLES else None


def _audit_one(conn, index, event_id, status, metadata):
    meta = _obj(metadata)
    raw_selected = meta.get("selected_offer_ids") or []
    selected_ids = set(x for x in raw_selected
                       if isinstance(raw_selected, list) and isinstance(x, str))
    report = meta.get("runner") or {}
    report = report if isinstance(report, dict) else {}
    reporter = report.get("role") if report.get("role") == "C3_LANGUAGE" else None
    events = {r: {"query_count": 0, "attempts": [], "offers": {},
                  "delivered_ids": set()} for r in ROLES}
    for kind, payload, packet_id in conn.execute(
            "SELECT kind,payload,id FROM packets WHERE event_id=? "
            "AND kind IN ('QueryPacket','OfferPacket')", (event_id,)):
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

    for kind, raw in conn.execute(
            "SELECT kind,metrics FROM telemetry WHERE event_id=? "
            "AND kind IN (?,?) ORDER BY id ASC", (event_id, *KINDS)):
        data = _obj(raw)
        role = data.get("role")
        if role not in ROLES:
            continue
        if kind == "body_offer_delivered":
            ident = data.get("packet_id")
            if isinstance(ident, str):
                events[role]["delivered_ids"].add(ident)
        else:
            runner = data.get("runner")
            runner = runner if isinstance(runner, dict) else {}
            native_status = data.get("status", runner.get("status"))
            native_status = native_status if native_status in STATUSES else "UNKNOWN"
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
        attempts = record["attempts"]
        if selected and reporter == "C3_LANGUAGE" and status == "FINAL":
            result = "IN_FINAL_C3_REPORT"
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
            "source_bound_offer_packets": len(packets),
            "delivery_receipts": len(receipts & set(packets)),
            "selected_for_report": len(selected),
            "last_native": attempts[-1] if attempts else None,
        }
    c3phases = _safe_phases(report)
    return {
        "index_newest_first": index,
        "turn_status": status if status in STATUSES else "UNKNOWN",
        "c3_reporter": reporter is not None,
        "c3_phase_seconds": c3phases,
        "c3_prompt_tokens": _count(report.get("prompt_tokens")),
        "c3_generated_tokens": _count(report.get("generated_tokens")),
        "c3_prompt_admission": _prompt_admission(report),
        "roles": roles,
    }


def audit(conn, limit=10):
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("turn count must be 1..20")
    # Avoid ever selecting user/assistant text: metadata, roles and counts only.
    messages = conn.execute(
        "SELECT event_id,status,metadata FROM messages "
        "WHERE role='assistant' AND event_id IS NOT NULL "
        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
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
    return {
        "schema": SCHEMA,
        "source": "LOCAL_SQLITE_METADATA_ONLY",
        "device_proof": "NOT_INDEPENDENTLY_VERIFIED",
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
    uri = "file:" + quote(str(db.absolute()), safe="/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=3)


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
