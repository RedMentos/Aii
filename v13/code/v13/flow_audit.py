"""Read-only audit of the persisted A/B -> C4 -> C3 turn path.

The report contains counts, role labels and runner metrics only. It never returns
user text, prompt text, token IDs, raw audio, or source bytes. It is not a device
attestation and cannot prove native latent injection.
"""
from __future__ import annotations

import argparse
import codecs
import errno
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import sys
import zlib
from pathlib import Path
from typing import Any

from .android_control import _reject_unapproved_symlink_ancestors, _validate_audit_parent_ancestry

_SAFE_ROLES = frozenset({
    "A0_RAW", "A1_SEGMENTATION", "A2_TEACHER", "A3_STUDENT", "A4_SALIENCE", "A5_PERCEPTION",
    "B1_DETAIL", "B2_GIST", "B3_CALLOSUM", "B4", "B5", "C1_EXEC", "C2_CONTROL",
    "C3_LANGUAGE", "C4_FOCAL", "C5_ACTION", "C6_TEXT",
})
_SAFE_STATUS = re.compile(r"^[A-Z0-9_]{1,64}$")
_SAFE_MODEL_LABEL = re.compile(r"^[A-Za-z0-9_.: -]{1,80}$")


def _json(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if isinstance(value, (str, bytes, bytearray)) else fallback
    except (ValueError, TypeError):
        return fallback


def _ref_key(ref: Any) -> tuple | None:
    if not isinstance(ref, dict):
        return None
    required = ("source_id", "sha256", "char_start", "char_end", "modality")
    if any(k not in ref for k in required):
        return None
    if not isinstance(ref["source_id"], str) or not isinstance(ref["sha256"], str):
        return None
    if type(ref["char_start"]) is not int or type(ref["char_end"]) is not int:
        return None
    if not isinstance(ref["modality"], str):
        return None
    return tuple(ref[k] for k in required)


def _source_valid(conn: sqlite3.Connection, home: Path, ref: Any) -> bool:
    key = _ref_key(ref)
    if key is None:
        return False
    source_id, sha, start, end, _modality = key
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        return False
    row = conn.execute(
        "SELECT hash,chars,deleted FROM sources WHERE id=?", (source_id,)
    ).fetchone()
    if not row or row["deleted"] or row["hash"] != sha:
        return False
    if not (0 <= start <= end <= row["chars"]):
        return False

    # Resolve only a private, regular content-addressed entry. lstat + O_NOFOLLOW
    # + fstat identity prevents a symlink swap between validation and open.
    max_bytes = 32 * 1024 * 1024
    blobs_dir = home / "data" / "blobs"
    blob = blobs_dir / sha
    compressed = blobs_dir / (sha + ".z")
    fd = None
    try:
        for directory in (home / "data", blobs_dir):
            directory_stat = directory.lstat()
            if (not stat.S_ISDIR(directory_stat.st_mode)
                    or directory_stat.st_uid != os.getuid()):
                return False

        # If an uncompressed entry exists but is unsafe, fail closed rather
        # than silently falling back to a second representation.
        try:
            blob.lstat()
            path = blob
        except FileNotFoundError:
            path = compressed

        if not hasattr(os, "O_NOFOLLOW"):
            return False
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.getuid() or before.st_size > max_bytes):
            return False
        flags = (os.O_RDONLY | os.O_NOFOLLOW
                 | getattr(os, "O_CLOEXEC", 0)
                 | getattr(os, "O_NONBLOCK", 0))
        fd = os.open(path, flags)
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or opened.st_uid != os.getuid()
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                or opened.st_size != before.st_size or opened.st_size > max_bytes):
            return False

        digest = hashlib.sha256()
        utf8 = codecs.getincrementaldecoder("utf-8")()
        char_count = 0
        total = 0
        decompressor = zlib.decompressobj() if path == compressed else None
        with os.fdopen(fd, "rb", closefd=False) as stream:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                parts = [decompressor.decompress(chunk, max_bytes - total + 1)] if decompressor else [chunk]
                for part in parts:
                    total += len(part)
                    if total > max_bytes:
                        return False
                    digest.update(part)
                    char_count += len(utf8.decode(part, final=False))
                    if decompressor and decompressor.unconsumed_tail:
                        return False
            if decompressor:
                tail = decompressor.flush()
                total += len(tail)
                if total > max_bytes or not decompressor.eof or decompressor.unused_data:
                    return False
                digest.update(tail)
                char_count += len(utf8.decode(tail, final=False))
        char_count += len(utf8.decode(b"", final=True))
        return digest.hexdigest() == sha and char_count == row["chars"] and end <= char_count
    except (OSError, UnicodeDecodeError, zlib.error):
        return False
    finally:
        if fd is not None:
            os.close(fd)


def _safe_metrics(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    out = {}
    for key in (
        "role", "status", "actual_model", "prompt_tokens",
        "original_prompt_tokens", "generated_tokens", "ttft_s",
        "duration_s", "sampled_peak_pss_bytes", "sampled_peak_rss_bytes",
        "CAN_LATENT_TAP", "CAN_LATENT_INJECT", "CAN_TRAIN_BODY",
        "native_completion_http_200", "native_template_submitted",
        "native_attention_or_semantic_use_proven",
    ):
        item = value.get(key)
        if isinstance(item, bool) and key.startswith("CAN_"):
            out[key] = item
        elif type(item) is int:
            out[key] = item
        elif type(item) is float and math.isfinite(item):
            out[key] = item
        elif isinstance(item, str):
            if key == "role" and item in _SAFE_ROLES:
                out[key] = item
            elif key == "status" and _SAFE_STATUS.fullmatch(item):
                out[key] = item
            elif key == "actual_model" and _SAFE_MODEL_LABEL.fullmatch(item):
                out[key] = item
    receipt = value.get("native_offer_prompt_receipt")
    has_receipt_token_count = False
    if isinstance(receipt, dict):
        for key in ("prompt_tokens", "original_prompt_tokens", "admitted_prompt_tokens"):
            item = receipt.get(key)
            if type(item) is int:
                out.setdefault(key, item)
                has_receipt_token_count = True
        for key in ("native_completion_http_200", "native_template_submitted",
                    "native_attention_or_semantic_use_proven"):
            item = receipt.get(key)
            if type(item) is bool:
                out[key] = item
    if has_receipt_token_count:
        out["prompt_token_source"] = "NATIVE_TOKENIZE_RECEIPT"
    elif type(value.get("prompt_tokens")) is int:
        out["prompt_token_source"] = "RUNNER_REPORTED"
    elif isinstance(receipt, dict):
        out["prompt_token_source"] = "NATIVE_TEMPLATE_WITNESS"
    if value.get("synthetic") is True or value.get("test_fixture") is True:
        out["evidence_level"] = "SYNTHETIC_FIXTURE"
    elif isinstance(out.get("actual_model"), str) and type(out.get("prompt_tokens")) is int:
        out["evidence_level"] = "RUNTIME_REPORTED_NOT_DEVICE_VERIFIED"
    else:
        out["evidence_level"] = "METRICS_MISSING_OR_INCOMPLETE"
    return out


def _payload(row: sqlite3.Row) -> dict:
    value = _json(row["payload"], {})
    return value if isinstance(value, dict) else {}


def _readonly_store_connection(home: str | Path) -> tuple[Path, sqlite3.Connection]:
    """Open the live Store read-only under the shared Android path boundary.

    Reuse AndroidControl's exact parent/ancestor policy, including the narrowly
    allowed AOSP /data aliases and system:system 0771 directories. The final
    Store DB is opened once with O_NOFOLLOW for identity/owner/link checks, then
    SQLite opens it with mode=ro and query_only. Parent protection blocks
    cross-UID replacement; a malicious same-UID race remains out of scope.
    """
    getuid = getattr(os, "getuid", None)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if getuid is None or nofollow is None:
        raise PermissionError("safe V13 Store read unavailable")

    requested = Path(home).expanduser() / "data" / "db" / "brain.sqlite3"
    raw_path = Path(os.path.abspath(os.fspath(requested)))
    canonical_parent = _reject_unapproved_symlink_ancestors(raw_path.parent, getuid())
    parent = _validate_audit_parent_ancestry(canonical_parent, getuid())
    db_path = parent / raw_path.name

    flags = (
        os.O_RDONLY
        | nofollow
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(db_path, flags)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EISDIR, errno.ENOTDIR}:
            raise PermissionError("unsafe V13 Store database") from exc
        raise
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != getuid()
            or before.st_nlink != 1
            or before.st_mode & 0o022
        ):
            raise PermissionError("unsafe V13 Store database")
        current = db_path.lstat()
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise PermissionError("V13 Store database changed before SQLite open")

        conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
        try:
            after = db_path.lstat()
            if (
                not stat.S_ISREG(after.st_mode)
                or after.st_uid != getuid()
                or after.st_nlink != 1
                or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise PermissionError("V13 Store database changed during SQLite open")
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            root = db_path.parents[2]
            return root, conn
        except BaseException:
            conn.close()
            raise
    finally:
        os.close(fd)


def audit_event(home: str | Path, event_id: str, *, session_id: str | None = None) -> dict:
    """Audit one event; an optional session_id constrains the local selector."""
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id is required")
    if session_id is not None and (
        not isinstance(session_id, str) or not session_id.strip()
    ):
        raise ValueError("session_id must be a nonempty string when supplied")

    root, conn = _readonly_store_connection(home)
    try:
        event_row = conn.execute(
            "SELECT packet,created,session_id FROM events WHERE id=?", (event_id,)
        ).fetchone()
        if not event_row or (session_id is not None and event_row["session_id"] != session_id):
            raise KeyError("event not found")
        event_packet = _json(event_row["packet"], {})
        if not isinstance(event_packet, dict):
            event_packet = {}

        message_row = conn.execute(
            "SELECT status,metadata,created FROM messages "
            "WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        metadata = _json(message_row["metadata"], {}) if message_row else {}
        if not isinstance(metadata, dict):
            metadata = {}

        packet_rows = conn.execute(
            "SELECT kind,payload FROM packets WHERE event_id=? ORDER BY created,id",
            (event_id,),
        ).fetchall()
        packets = [_payload(row) | {"_kind": row["kind"]} for row in packet_rows]
        by_kind: dict[str, list[dict]] = {}
        for packet in packets:
            by_kind.setdefault(packet["_kind"], []).append(packet)

        percepts = by_kind.get("PerceptPacket", [])
        modalities = sorted({
            p.get("modality") for p in percepts if isinstance(p.get("modality"), str)
        })

        queries = by_kind.get("QueryPacket", [])
        query_roles = {
            p.get("packet_id"): p.get("target_role")
            for p in queries
            if isinstance(p.get("packet_id"), str) and isinstance(p.get("target_role"), str)
        }
        offers = by_kind.get("OfferPacket", [])
        offer_metrics = {}
        offer_roles = {}
        for offer in offers:
            packet_id = offer.get("packet_id")
            role = offer.get("role")
            if isinstance(packet_id, str) and isinstance(role, str):
                offer_roles[packet_id] = role
                metrics = offer.get("native_metrics")
                if not isinstance(metrics, dict):
                    metrics = (offer.get("offer") or {}).get("native_metrics", {})
                offer_metrics[packet_id] = _safe_metrics(metrics)

        focal_cycles = by_kind.get("FocalCycle", [])
        focal_items = by_kind.get("FocalItem", [])
        # Only the most recent C4 cycle represents the current coalition.
        current_cycle = focal_cycles[-1] if focal_cycles else {}
        current_coalition = current_cycle.get("coalition", [])
        coalition_ids = {
            item_id for item_id in current_coalition
            if isinstance(item_id, str)
        } if isinstance(current_coalition, list) else set()
        focal_by_id = {
            item.get("item_id"): item for item in focal_items
            if isinstance(item.get("item_id"), str)
        }
        selected_ids = metadata.get("selected_offer_ids", [])
        if not isinstance(selected_ids, list):
            selected_ids = []
        selected_ids = {x for x in selected_ids if isinstance(x, str)}

        context_refs = metadata.get("context_source_refs", [])
        if not isinstance(context_refs, list):
            context_refs = []
        context_keys = {key for ref in context_refs if (key := _ref_key(ref)) is not None}

        all_refs = [event_packet.get("source_ref")]
        for packet_value in packets:
            all_refs.extend(packet_value.get("provenance", []) if isinstance(packet_value.get("provenance"), list) else [])
            all_refs.extend(packet_value.get("source_refs", []) if isinstance(packet_value.get("source_refs"), list) else [])
            all_refs.extend(packet_value.get("evidence_refs", []) if isinstance(packet_value.get("evidence_refs"), list) else [])
            if isinstance(packet_value.get("source_ref"), dict):
                all_refs.append(packet_value["source_ref"])
        all_refs.extend(context_refs)
        unique_refs = {}
        malformed_refs = 0
        for ref in all_refs:
            key = _ref_key(ref)
            if key is not None:
                unique_refs[key] = ref
            elif ref is not None:
                malformed_refs += 1
        valid_keys = {
            key for key, ref in unique_refs.items() if _source_valid(conn, root, ref)
        }

        # A persisted FocalItem counts only when it retains the exact source
        # evidence from its OfferPacket; an ID-only match is insufficient.
        c4_consumed_ids = set()
        for offer in offers:
            packet_id = offer.get("packet_id")
            if not isinstance(packet_id, str) or packet_id not in coalition_ids:
                continue
            focal = focal_by_id.get(packet_id)
            evidence = offer.get("evidence_refs") or (offer.get("provenance") or [])[:1]
            focal_sources = focal.get("source_refs") if isinstance(focal, dict) else None
            evidence_keys = {_ref_key(ref) for ref in evidence} if isinstance(evidence, list) else set()
            focal_keys = {_ref_key(ref) for ref in focal_sources} if isinstance(focal_sources, list) else set()
            if (
                isinstance(focal, dict)
                and focal.get("source_kind") == offer.get("role")
                and focal.get("state_type") == "ACTIVE"
                and evidence_keys
                and None not in evidence_keys
                and evidence_keys <= focal_keys
                and evidence_keys <= valid_keys
            ):
                c4_consumed_ids.add(packet_id)

        c3_context_ids = set()
        for offer in offers:
            packet_id = offer.get("packet_id")
            evidence = offer.get("evidence_refs") or (offer.get("provenance") or [])[:1]
            keys = [_ref_key(ref) for ref in evidence] if isinstance(evidence, list) else []
            if (
                isinstance(packet_id, str)
                and keys
                and all(key is not None and key in context_keys and key in valid_keys for key in keys)
            ):
                c3_context_ids.add(packet_id)

        c4_roles = {offer_roles[x] for x in c4_consumed_ids}
        required_roles = {"B1_DETAIL", "B2_GIST"}
        query_bound_roles = {
            offer.get("role") for offer in offers
            if isinstance(offer.get("role"), str)
            and query_roles.get(offer.get("query_packet_id")) == offer.get("role")
        }
        query_binding_status = "PASS" if required_roles <= query_bound_roles else ("PARTIAL" if query_bound_roles else "FAIL")
        c3_roles = {
            offer_roles[x] for x in (c3_context_ids & c4_consumed_ids & selected_ids)
        }
        c4_status = "PASS" if required_roles <= c4_roles else ("PARTIAL" if c4_roles else "FAIL")
        c3_context_status = "PASS" if required_roles <= c3_roles else ("PARTIAL" if c3_roles else "FAIL")
        runner_metrics = _safe_metrics(metadata.get("runner"))
        semantic_use_reported = runner_metrics.get("native_attention_or_semantic_use_proven") is True
        c3_semantic_use_status = (
            "RUNTIME_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
            if semantic_use_reported else "UNVERIFIED"
        )
        if c3_context_status == "PASS":
            c3_status = (
                "CONTEXT_PRESENT_RUNTIME_REPORTED_USE"
                if semantic_use_reported else "CONTEXT_PRESENT_SEMANTIC_USE_UNVERIFIED"
            )
        elif c3_context_status == "PARTIAL":
            c3_status = "PARTIAL_CONTEXT"
        else:
            c3_status = "FAIL"
        action_packets = by_kind.get("ActionSelection", [])
        selected_action = action_packets[-1].get("selected", {}) if action_packets else {}
        if not isinstance(selected_action, dict):
            selected_action = {}
        suppressed = action_packets[-1].get("suppressed", []) if action_packets else []
        suppressed_roles = sorted({
            item.get("role") for item in suppressed
            if isinstance(item, dict) and isinstance(item.get("role"), str)
        }) if isinstance(suppressed, list) else []

        tap_count = len(by_kind.get("LatentTapPacket", []))
        symbolic_count = sum(
            1 for item in by_kind.get("MessagePacket", [])
            if item.get("channel") == "SYMBOLIC"
        )
        receiver_count = sum(
            len(by_kind.get(kind, []))
            for kind in ("LatentReceiverPacket", "ReceiverCalibration")
        )

        action_rows = conn.execute(
            "SELECT status FROM actions WHERE event_id=? ORDER BY created,id", (event_id,)
        ).fetchall()
        outcome_count = len(by_kind.get("ActionOutcome", []))

        body_evidence = [
            offer_metrics.get(offer.get("packet_id"), {})
            for offer in offers
        ]
        metrics = body_evidence + ([runner_metrics] if runner_metrics else [])
        if any(item.get("evidence_level") == "SYNTHETIC_FIXTURE" for item in metrics):
            overall_evidence = "SYNTHETIC_FIXTURE"
        elif any(item.get("evidence_level") == "RUNTIME_REPORTED_NOT_DEVICE_VERIFIED" for item in metrics):
            overall_evidence = "RUNTIME_REPORTED_NOT_DEVICE_VERIFIED"
        else:
            overall_evidence = "METRICS_MISSING_OR_INCOMPLETE"

        warnings = []
        if not offers:
            warnings.append("NO_BODY_OFFERS")
        if c4_status != "PASS":
            warnings.append("B1_B2_NOT_BOTH_CONSUMED_BY_C4")
        if c3_context_status != "PASS":
            warnings.append("B1_B2_NOT_BOTH_SOURCE_BOUND_IN_C3_CONTEXT")
        elif semantic_use_reported:
            warnings.append("C3_SEMANTIC_USE_RUNTIME_REPORTED_NOT_INDEPENDENTLY_VERIFIED")
        else:
            warnings.append("C3_SEMANTIC_USE_UNVERIFIED")
        if not message_row:
            warnings.append("NO_ASSISTANT_MESSAGE")
        if len(valid_keys) != len(unique_refs) or malformed_refs:
            warnings.append("SOURCE_REF_INTEGRITY_INCOMPLETE")

        return {
            "schema": "v14.turn-flow-audit/1",
            "event_id": event_id,
            "assistant_status": message_row["status"] if message_row else None,
            "read_only": True,
            "private_text_returned": False,
            "perception": {"packet_count": len(percepts), "modalities": modalities},
            "queries": {
                "count": len(queries),
                "target_roles": sorted({
                    p.get("target_role") for p in queries
                    if isinstance(p.get("target_role"), str)
                }),
            },
            "bodies": {
                "offer_count": len(offers),
                "roles": sorted(set(offer_roles.values())),
                "query_binding_status": query_binding_status,
                "offers": [
                    {
                        "role": offer_roles.get(p.get("packet_id")),
                        "query_target_role": query_roles.get(p.get("query_packet_id")),
                        "query_role_match": query_roles.get(p.get("query_packet_id")) == p.get("role"),
                        "prompt_tokens": offer_metrics.get(p.get("packet_id"), {}).get("prompt_tokens"),
                        "generated_tokens": offer_metrics.get(p.get("packet_id"), {}).get("generated_tokens"),
                        "status": offer_metrics.get(p.get("packet_id"), {}).get("status"),
                        "actual_model": offer_metrics.get(p.get("packet_id"), {}).get("actual_model"),
                        "model_revision": p.get("model_revision"),
                        "prompt_token_source": offer_metrics.get(p.get("packet_id"), {}).get("prompt_token_source"),
                        "evidence_level": offer_metrics.get(p.get("packet_id"), {}).get("evidence_level", "METRICS_MISSING_OR_INCOMPLETE"),
                    }
                    for p in offers
                ],
            },
            "c4": {
                "cycle_count": len(focal_cycles),
                "focal_item_count": len(focal_items),
                "consumed_offer_count": len(c4_consumed_ids),
                "consumed_roles": sorted(c4_roles),
                "selected_offer_count": len(selected_ids),
                "status": c4_status,
            },
            "c3": {
                "source_bound_offer_count": len(c3_context_ids & c4_consumed_ids & selected_ids),
                "source_bound_roles": sorted(c3_roles),
                "context_source_ref_count": len(context_refs),
                "prompt_tokens": runner_metrics.get("prompt_tokens"),
                "generated_tokens": runner_metrics.get("generated_tokens"),
                "ttft_s": runner_metrics.get("ttft_s"),
                "duration_s": runner_metrics.get("duration_s"),
                "actual_model": runner_metrics.get("actual_model"),
                "prompt_token_source": runner_metrics.get("prompt_token_source"),
                "native_completion_http_200": runner_metrics.get("native_completion_http_200"),
                "native_template_submitted": runner_metrics.get("native_template_submitted"),
                "native_attention_or_semantic_use_proven": runner_metrics.get("native_attention_or_semantic_use_proven"),
                "can_latent_tap": runner_metrics.get("CAN_LATENT_TAP"),
                "can_latent_inject": runner_metrics.get("CAN_LATENT_INJECT"),
                "can_train_body": runner_metrics.get("CAN_TRAIN_BODY"),
                "evidence_level": runner_metrics.get("evidence_level", "METRICS_MISSING_OR_INCOMPLETE"),
                "context_binding_status": c3_context_status,
                "semantic_use_status": c3_semantic_use_status,
                "status": c3_status,
            },
            "c5": {
                "selected_action_type": selected_action.get("action_type"),
                "selected_role": selected_action.get("role"),
                "suppressed_roles": suppressed_roles,
                "action_outcome_packet_count": outcome_count,
                "world_action_statuses": [row["status"] for row in action_rows],
            },
            "latent": {
                "tap_packet_count": tap_count,
                "symbolic_message_count": symbolic_count,
                "receiver_packet_count": receiver_count,
                "native_injection_proven": False,
                "status": "TAP_ONLY" if tap_count else ("SYMBOLIC_ONLY" if symbolic_count else "NO_LATENT_EVIDENCE"),
            },
            "source_integrity": {
                "unique_refs_checked": len(unique_refs) + malformed_refs,
                "valid_refs": len(valid_keys),
                "invalid_refs": len(unique_refs) - len(valid_keys) + malformed_refs,
            },
            "evidence_level": overall_evidence,
            "warnings": warnings,
            "claim_boundary": (
                "Store/runner telemetry only; source-bound context is not proof of model attention or semantic use, "
                "and this is not Android-device attestation, native weight-update proof, or trained latent receiver-effect proof."
            ),
        }
    finally:
        conn.close()


def audit_latest(home: str | Path, *, session_id: str | None = None) -> dict:
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id is required for latest-event audit")
    root, conn = _readonly_store_connection(home)
    try:
        row = conn.execute(
            "SELECT id FROM events WHERE session_id=? ORDER BY created DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            raise KeyError("no events in Store for this session")
        event_id = row[0]
    finally:
        conn.close()
    return audit_event(root, event_id, session_id=session_id)


def audit_latest_completed(home: str | Path) -> dict | None:
    """Audit the newest persisted assistant turn across all sessions.

    This selector is for the global dashboard only. The standalone CLI keeps
    its explicit session requirement; the returned audit is still bound to the
    selected event's actual session before any packet/source inspection.
    """
    root, conn = _readonly_store_connection(home)
    try:
        row = conn.execute(
            "SELECT e.id,e.session_id FROM messages m "
            "JOIN events e ON e.id=m.event_id "
            "WHERE m.role='assistant' AND m.event_id IS NOT NULL "
            "AND m.status IN ('FINAL','DEADLINE','ERROR','CANCELLED','INTERRUPTED') "
            "ORDER BY m.id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        event_id, session_id = row["id"], row["session_id"]
        if not isinstance(event_id, str) or not event_id or not isinstance(session_id, str) or not session_id:
            raise ValueError("invalid latest assistant event binding")
    finally:
        conn.close()
    return audit_event(root, event_id, session_id=session_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only V13 per-turn organ-flow audit")
    parser.add_argument("--home", default="~/v13", help="V13 runtime home")
    parser.add_argument("--event-id", help="explicit local event selector; not session-scoped unless --session-id is also supplied")
    parser.add_argument("--session-id", help="required for latest-event selection; when paired with --event-id, restricts it to that session")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)
    try:
        if args.session_id is not None and not args.session_id.strip():
            raise ValueError("session_id must be nonempty when supplied")
        if not args.event_id and not args.session_id:
            raise ValueError("session_id is required when selecting the latest event")
        report = (
            audit_event(args.home, args.event_id, session_id=args.session_id)
            if args.event_id
            else audit_latest(args.home, session_id=args.session_id)
        )
    except (FileNotFoundError, KeyError, ValueError, PermissionError, sqlite3.Error) as exc:
        print(json.dumps({"status": "ERROR", "error": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":") if args.compact else None, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
