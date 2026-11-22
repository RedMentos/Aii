"""Read-only C3 context for recent authenticated Android companion receipts.

A companion receipt proves only what the paired companion attested. It is not
independent Android UI observation, a WorldTransition, or T8 learning authority.
"""
from __future__ import annotations

import json
import math
import re
import time

_ACTION_ID = re.compile(r"[A-Za-z0-9_-]{8,128}")
_HEX_32 = re.compile(r"[0-9a-f]{32}")
_HEX_64 = re.compile(r"[0-9a-f]{64}")
_STATUS = {
    "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED": "DISPATCHED_UNVERIFIED",
    "COMPANION_USER_DENIED": "USER_DENIED",
    "COMPANION_DISPATCH_FAILED": "FAILED_TO_DISPATCH",
}
_AUTH_SCHEMES = {
    "HMAC_SHA256_PER_INSTALL",
    "ECDSA_P256_SHA256_ANDROID_KEYSTORE",
}


def recent_companion_receipt_context(
    store,
    session_id: str,
    *,
    now: float | None = None,
    ttl_seconds: float = 300.0,
) -> dict | None:
    """Return one recent, source-bound, non-authoritative receipt for this session.

    The database query selects only the newest companion receipt. If that newest
    receipt is malformed, stale, or source-unbound, the reader fails closed
    instead of resurfacing an older action as if it were current.
    """
    if not isinstance(session_id, str) or not session_id:
        return None
    try:
        current = float(time.time() if now is None else now)
        ttl = float(ttl_seconds)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(current) or not math.isfinite(ttl) or ttl <= 0:
        return None

    row = store.one(
        "SELECT p.payload,p.created,e.id AS source_event_id,e.packet AS event_packet "
        "FROM packets p JOIN events e ON e.id=p.event_id "
        "WHERE p.kind='ActionOutcome' AND e.session_id=? "
        "AND json_extract(p.payload,'$.producer_component')='C5_ANDROID_COMPANION' "
        "AND json_extract(p.payload,'$.actual.outcome_kind')='ANDROID_COMPANION_RECEIPT' "
        "ORDER BY p.created DESC,p.id DESC LIMIT 1",
        (session_id,),
    )
    if not row:
        return None

    try:
        created = float(row["created"])
        packet_value = json.loads(row["payload"])
        event = json.loads(row["event_packet"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return None
    age = current - created
    if not math.isfinite(created) or age < 0 or age > ttl:
        return None

    actual = packet_value.get("actual")
    status = packet_value.get("status")
    expected_receipt_status = _STATUS.get(status)
    action_id = packet_value.get("action_id")
    packet_id = packet_value.get("packet_id")
    source_event_id = packet_value.get("event_id")
    source_refs = packet_value.get("source_refs")

    if (
        packet_value.get("producer_component") != "C5_ANDROID_COMPANION"
        or source_event_id != row["source_event_id"]
        or event.get("event_id") != source_event_id
        or packet_value.get("brain_generation_id") != event.get("brain_generation_id")
        or not isinstance(actual, dict)
        or actual.get("outcome_kind") != "ANDROID_COMPANION_RECEIPT"
        or actual.get("capability") != "launch_app"
        or actual.get("observed") is not False
        or actual.get("evidence_level") != "COMPANION_RECEIPT_ONLY"
        or actual.get("t8_authoritative") is not False
        or actual.get("world_learning_eligible") is not False
        or actual.get("trusted_transition_eligible") is not False
        or expected_receipt_status is None
        or actual.get("receipt_status") != expected_receipt_status
        or actual.get("auth_scheme") not in _AUTH_SCHEMES
        or type(actual.get("companion_local_consent_claim")) is not bool
        or type(action_id) is not str
        or not _ACTION_ID.fullmatch(action_id)
        or type(packet_id) is not str
        or not _ACTION_ID.fullmatch(packet_id)
        or not isinstance(source_refs, list)
        or len(source_refs) != 1
        or not isinstance(event.get("source_ref"), dict)
        or source_refs[0] != event["source_ref"]
    ):
        return None

    consent = actual["companion_local_consent_claim"]
    if status == "COMPANION_USER_DENIED" and consent is not False:
        return None
    if status != "COMPANION_USER_DENIED" and consent is not True:
        return None

    digest = actual.get("digest")
    nonce = actual.get("receipt_nonce")
    if (
        type(digest) is not str
        or not _HEX_64.fullmatch(digest)
        or type(nonce) is not str
        or not _HEX_32.fullmatch(nonce)
    ):
        return None

    auth_scheme = actual["auth_scheme"]
    if auth_scheme == "ECDSA_P256_SHA256_ANDROID_KEYSTORE":
        if (
            actual.get("android_os_permission_status") != "NOT_REQUIRED_FOR_LAUNCH_APP"
            or actual.get("key_storage_status") not in {
                "ANDROID_KEYSTORE_SOFTWARE_BACKED",
                "ANDROID_KEYSTORE_HARDWARE_BACKED",
            }
        ):
            return None
        expected_approval = (
            "ANDROID_COMPANION_USER_DENIAL"
            if status == "COMPANION_USER_DENIED"
            else "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"
        )
        if actual.get("local_approval_evidence") != expected_approval:
            return None
    elif auth_scheme == "HMAC_SHA256_PER_INSTALL":
        if (
            actual.get("android_os_permission_status") != "REQUIRED_NOT_VERIFIED"
            or actual.get("key_storage_status") != "UNVERIFIED"
            or actual.get("local_approval_evidence") != "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
        ):
            return None

    try:
        store.read_source(source_refs[0])
    except (OSError, ValueError, KeyError):
        return None

    if status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED":
        boundary = (
            "The paired Android companion attested that it dispatched the "
            "launch intent after local consent. The app's foreground state "
            "was not independently observed; do not claim that it opened."
        )
    elif status == "COMPANION_USER_DENIED":
        boundary = (
            "The paired Android companion records that the user denied the "
            "request; no launch dispatch occurred."
        )
    else:
        boundary = (
            "The paired Android companion records that launch dispatch failed. "
            "The app's foreground state was not independently observed."
        )

    return {
        "packet_id": packet_id,
        "action_id": action_id,
        "source_event_id": source_event_id,
        "capability": "launch_app",
        "status": status,
        "receipt_status": expected_receipt_status,
        "observed": False,
        "evidence_level": "COMPANION_RECEIPT_ONLY",
        "t8_authoritative": False,
        "world_learning_eligible": False,
        "trusted_transition_eligible": False,
        "claim_boundary": boundary,
        "source_refs": [source_refs[0]],
    }
