"""Read-only audit of the persisted A/B -> C4 -> C3 turn path.

The report contains counts, role labels and runner metrics only. It never returns
user text, prompt text, token IDs, raw audio, or source bytes. It is not a device
attestation and cannot prove native latent injection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any


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
    blob = home / "data" / "blobs" / sha
    if blob.is_file():
        raw = blob.read_bytes()
    else:
        compressed = blob.with_name(sha + ".z")
        if not compressed.is_file():
            return False
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(compressed.read_bytes(), 64 * 1024 * 1024)
            if decoder.unconsumed_tail or not decoder.eof:
                return False
        except zlib.error:
            return False
    if hashlib.sha256(raw).hexdigest() != sha:
        return False
    try:
        return end <= len(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return False


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
        elif isinstance(item, str) and len(item) <= 160:
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


def audit_event(home: str | Path, event_id: str) -> dict:
    """Audit one persisted event through read-only SQLite and source blobs."""
    root = Path(home).expanduser().resolve()
    db_path = root / "data" / "db" / "brain.sqlite3"
    if not db_path.is_file():
        raise FileNotFoundError("V13 Store database not found")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id is required")

    conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        event_row = conn.execute(
            "SELECT packet,created FROM events WHERE id=?", (event_id,)
        ).fetchone()
        if not event_row:
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
        coalition_ids = {
            item_id
            for cycle in focal_cycles
            for item_id in cycle.get("coalition", [])
            if isinstance(item_id, str)
        }
        focal_item_ids = {
            item.get("item_id") for item in focal_items
            if isinstance(item.get("item_id"), str)
        }
        c4_consumed_ids = set(offer_roles) & coalition_ids & focal_item_ids
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
        query_bound_roles = {
            offer.get("role") for offer in offers
            if isinstance(offer.get("role"), str)
            and query_roles.get(offer.get("query_packet_id")) == offer.get("role")
        }
        query_binding_status = "PASS" if required_roles <= query_bound_roles else ("PARTIAL" if query_bound_roles else "FAIL")
        c3_roles = {
            offer_roles[x] for x in (c3_context_ids & c4_consumed_ids & selected_ids)
        }
        required_roles = {"B1_DETAIL", "B2_GIST"}
        c4_status = "PASS" if required_roles <= c4_roles else ("PARTIAL" if c4_roles else "FAIL")
        c3_status = "PASS" if required_roles <= c3_roles else ("PARTIAL" if c3_roles else "FAIL")

        runner_metrics = _safe_metrics(metadata.get("runner"))
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
        if c3_status != "PASS":
            warnings.append("B1_B2_NOT_BOTH_SOURCE_BOUND_IN_C3_CONTEXT")
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
                "model_revision": metadata.get("model_revision"),
                "prompt_token_source": runner_metrics.get("prompt_token_source"),
                "native_completion_http_200": runner_metrics.get("native_completion_http_200"),
                "native_template_submitted": runner_metrics.get("native_template_submitted"),
                "native_attention_or_semantic_use_proven": runner_metrics.get("native_attention_or_semantic_use_proven"),
                "can_latent_tap": runner_metrics.get("CAN_LATENT_TAP"),
                "can_latent_inject": runner_metrics.get("CAN_LATENT_INJECT"),
                "can_train_body": runner_metrics.get("CAN_TRAIN_BODY"),
                "evidence_level": runner_metrics.get("evidence_level", "METRICS_MISSING_OR_INCOMPLETE"),
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
                "Store/runner telemetry only; not Android-device attestation, "
                "native weight-update proof, or trained latent receiver-effect proof."
            ),
        }
    finally:
        conn.close()


def audit_latest(home: str | Path) -> dict:
    root = Path(home).expanduser().resolve()
    db_path = root / "data" / "db" / "brain.sqlite3"
    if not db_path.is_file():
        raise FileNotFoundError("V13 Store database not found")
    conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        row = conn.execute("SELECT id FROM events ORDER BY created DESC LIMIT 1").fetchone()
        if not row:
            raise KeyError("no events in Store")
        event_id = row[0]
    finally:
        conn.close()
    return audit_event(root, event_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only V13 per-turn organ-flow audit")
    parser.add_argument("--home", default="~/v13", help="V13 runtime home")
    parser.add_argument("--event-id", help="audit one event; default is latest")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)
    try:
        report = audit_event(args.home, args.event_id) if args.event_id else audit_latest(args.home)
    except (FileNotFoundError, KeyError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "ERROR", "error": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":") if args.compact else None, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
