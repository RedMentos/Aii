"""Bounded A5 -> JEF observation admission; no silent evidence loss.

A5 raw packet remains in its original store. This produces a *reference* for
native prompt budgeting, never a substitute for source inspection or consent.
No microphone/UI access and no model/learning/action authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping


class A5AdmissionError(ValueError):
    pass


def admit_a5(packet: Mapping, *, max_bytes: int = 256, consent: bool = False) -> dict:
    """Return a small source-bound routing envelope, not untrusted packet text."""
    if not consent:
        raise PermissionError("A5_CONSENT_REQUIRED")
    if not isinstance(packet, Mapping):
        raise A5AdmissionError("PACKET_NOT_MAPPING")
    if max_bytes < 160 or max_bytes > 4096:
        raise A5AdmissionError("INVALID_BUDGET")
    source = packet.get("source")
    if not isinstance(source, Mapping) or source.get("authorized") is not True:
        raise A5AdmissionError("SOURCE_NOT_AUTHORIZED")
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id or len(source_id) > 128:
        raise A5AdmissionError("INVALID_SOURCE")
    schema = packet.get("schema")
    if not isinstance(schema, str) or not schema.startswith("v13.a5.") or len(schema) > 96:
        raise A5AdmissionError("INVALID_SCHEMA")
    if packet.get("action_authority") is not False or packet.get("learning_authority") is not False:
        raise A5AdmissionError("UNTRUSTED_AUTHORITY")
    if packet.get("status") not in ("FINAL", "PROVISIONAL"):
        raise A5AdmissionError("INVALID_STATUS")
    try:
        raw = json.dumps(packet, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise A5AdmissionError("UNSERIALIZABLE_PACKET") from exc
    if len(raw) > 65536:
        raise A5AdmissionError("SOURCE_PACKET_TOO_LARGE")
    # Do not put raw observations or transcript in a model prompt.
    envelope = {
        "schema": "v13.a5.admission/1",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_id_sha256": hashlib.sha256(source_id.encode()).hexdigest()[:16],
        "modality": source.get("modality") if source.get("modality") in ("audio", "visual", "ui") else "unknown",
        "status": packet["status"],
        "requires_source_lookup": True,
        "action_authority": False,
        "learning_authority": False,
    }
    encoded = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    if len(encoded) > max_bytes:
        raise A5AdmissionError("ENVELOPE_OVER_BUDGET")
    return envelope
