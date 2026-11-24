"""Typed fail-closed Android action outcome boundary for C5/JEF.

Software-only: a DRY_RUN is never an observed Android transition and must
never be promoted into T8 learning evidence. The OS companion remains OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Mapping
import math
import time

from .android_control import AndroidControlBroker, ControlDenied
from .contracts import packet
from .common import dumps, now


class InvalidOutcome(ValueError):
    pass


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    status: str
    observed: bool
    evidence_level: str
    timestamp: float
    details: Mapping[str, object]

    def to_event(self) -> dict:
        return asdict(self)


def execute_approved_dry_run(
    broker: AndroidControlBroker,
    action_id: str,
    *,
    on_outcome: Callable[[ActionOutcome], None] | None = None,
    clock: Callable[[], float] = time.time,
) -> ActionOutcome:
    """Consume an approved action once, with no Android API execution.

    The trusted local UI, not model text, must approve the action. The sink
    receives only a non-observation event. Sink failure cannot replay it.
    """
    if not isinstance(action_id, str) or not action_id:
        raise ControlDenied("invalid action identifier")
    envelope = broker.execute(action_id, dry_run=True)
    outcome = ActionOutcome(
        action_id=envelope["action_id"],
        capability=envelope["capability"],
        status="DRY_RUN_ONLY",
        observed=False,
        evidence_level="SOFTWARE_SIMULATION",
        timestamp=float(clock()),
        details={"digest": envelope["digest"]},
    )
    if on_outcome is not None:
        on_outcome(outcome)
    return outcome


def trusted_transition_eligible(outcome: ActionOutcome) -> bool:
    """No Android-native learning evidence before verified companion auth."""
    return False


def accept_companion_receipt(
    broker: AndroidControlBroker,
    verifier,
    action_id: str,
    receipt: dict,
    *,
    on_outcome: Callable[[ActionOutcome], None] | None = None,
    clock: Callable[[], float] = time.time,
    finalize_broker: bool = True,
) -> ActionOutcome:
    """Consume a dispatched request using an authenticated companion receipt.

    The broker dispatch is consumed before verification; malformed, stale,
    replayed or unauthenticated receipts fail closed. The combined persistence
    path may defer successful broker finalization until the source-bound
    ActionOutcome and nonce are durably committed. A valid receipt remains only
    a companion attestation, not independent device observation or T8 authority.
    """
    if not isinstance(action_id, str) or not action_id:
        raise ControlDenied("invalid action identifier")
    proposal = broker.consume_dispatched(action_id)
    envelope = {
        "action_id": proposal.action_id,
        "capability": proposal.capability,
        "digest": proposal.digest,
    }
    try:
        attestation = verifier.verify(envelope, receipt, consume_nonce=False)
        if (type(attestation) is not dict
                or attestation.get("status") not in {
                    "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
                    "COMPANION_USER_DENIED",
                    "COMPANION_DISPATCH_FAILED",
                    "COMPANION_OUTCOME_UNKNOWN",
                }
                or attestation.get("t8_authoritative") is not False):
            raise InvalidOutcome("companion verifier returned an unsupported authority level")
        with broker.lock:
            if broker.stopped:
                raise ControlDenied("broker stopped during companion verification")
    except Exception:
        broker.record_companion_receipt(action_id, proposal.digest, verified=False)
        raise
    verified_at = float(clock())
    details = {
        "digest": proposal.digest,
        "receipt_schema": attestation["schema"],
        "auth_scheme": attestation["auth_scheme"],
        "receipt_nonce": attestation["nonce"],
        "companion_local_consent_claim": attestation.get("companion_local_consent_claim", True),
        "receipt_status": attestation.get("receipt_status", "EXECUTED"),
        "local_approval_evidence": attestation.get(
            "local_approval_evidence", "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
        ),
        "android_os_permission_status": attestation.get(
            "android_os_permission_status", "REQUIRED_NOT_VERIFIED"
        ),
        "key_storage_status": attestation["key_storage_status"],
        "t8_authoritative": False,
        "world_learning_eligible": False,
        "event_id": proposal.event_id,
        "source_ref": dict(proposal.source_ref) if proposal.source_ref is not None else None,
    }
    if attestation["auth_scheme"] == "ECDSA_P256_SHA256_ANDROID_KEYSTORE":
        # Keep the exact authenticated envelope with the derived ActionOutcome.
        # Recovery can then re-check the signature without asking the companion
        # to redispatch or trusting mutable status fields in SQLite.
        details["signed_receipt"] = {
            "body": dict(receipt["body"]),
            "key_id": receipt["key_id"],
            "signature": receipt["signature"],
        }
        details["receipt_verified_at"] = verified_at
    outcome = ActionOutcome(
        action_id=proposal.action_id,
        capability=proposal.capability,
        status=attestation["status"],
        observed=False,
        evidence_level="COMPANION_RECEIPT_ONLY",
        timestamp=verified_at,
        details=details,
    )
    if finalize_broker:
        broker.record_companion_receipt(action_id, proposal.digest, verified=True)
    if on_outcome is not None:
        on_outcome(outcome)
    return outcome


def persist_companion_outcome(store, outcome: ActionOutcome) -> dict:
    """Atomically persist one source-bound, non-authoritative companion receipt.

    The receipt nonce is committed in the same SQLite transaction as its
    canonical ActionOutcome packet. Repeating the same outcome is idempotent;
    a nonce or action-id collision with different content is rejected. This
    audit record is never a WorldAction or a T8 learning transition.
    """
    if (not isinstance(outcome, ActionOutcome)
            or outcome.status not in {
                "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
                "COMPANION_USER_DENIED",
                "COMPANION_DISPATCH_FAILED",
                "COMPANION_OUTCOME_UNKNOWN",
            }
            or outcome.observed is not False
            or outcome.evidence_level != "COMPANION_RECEIPT_ONLY"
            or not isinstance(outcome.details, Mapping)
            or outcome.details.get("t8_authoritative") is not False
            or outcome.details.get("world_learning_eligible") is not False):
        raise InvalidOutcome("only non-authoritative companion receipts may be persisted here")
    event_id = outcome.details.get("event_id")
    source_ref = outcome.details.get("source_ref")
    nonce = outcome.details.get("receipt_nonce")
    digest = outcome.details.get("digest")
    if type(event_id) is not str or type(source_ref) is not dict:
        raise InvalidOutcome("source-bound event required before persistence")
    auth_scheme = outcome.details.get("auth_scheme")
    consent_claim = outcome.details.get("companion_local_consent_claim")
    receipt_status = outcome.details.get("receipt_status")
    common_invalid = (
        type(nonce) is not str or len(nonce) != 32
        or any(ch not in "0123456789abcdef" for ch in nonce)
        or type(digest) is not str or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
        or outcome.details.get("receipt_schema") != "v14.android-companion-receipt/1"
        or type(consent_claim) is not bool
    )
    legacy_hmac_invalid = (
        auth_scheme == "HMAC_SHA256_PER_INSTALL"
        and (
            outcome.details.get("local_approval_evidence") != "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
            or outcome.details.get("android_os_permission_status") != "REQUIRED_NOT_VERIFIED"
            or outcome.details.get("key_storage_status") != "UNVERIFIED"
        )
    )
    android_keystore_invalid = (
        auth_scheme == "ECDSA_P256_SHA256_ANDROID_KEYSTORE"
        and (
            outcome.details.get("android_os_permission_status") != "NOT_REQUIRED_FOR_LAUNCH_APP"
            or outcome.details.get("key_storage_status") not in {
                "ANDROID_KEYSTORE_SOFTWARE_BACKED", "ANDROID_KEYSTORE_HARDWARE_BACKED"
            }
            or (
                outcome.status == "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
                and (consent_claim is not True
                     or receipt_status != "DISPATCHED_UNVERIFIED"
                     or outcome.details.get("local_approval_evidence") != "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION")
            )
            or (
                outcome.status == "COMPANION_USER_DENIED"
                and (consent_claim is not False
                     or receipt_status != "USER_DENIED"
                     or outcome.details.get("local_approval_evidence") != "ANDROID_COMPANION_USER_DENIAL")
            )
            or (
                outcome.status == "COMPANION_DISPATCH_FAILED"
                and (consent_claim is not True
                     or receipt_status != "FAILED_TO_DISPATCH"
                     or outcome.details.get("local_approval_evidence") != "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION")
            )
            or (
                outcome.status == "COMPANION_OUTCOME_UNKNOWN"
                and (consent_claim is not True
                     or receipt_status != "OUTCOME_UNKNOWN"
                     or outcome.details.get("local_approval_evidence") != "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION")
            )
        )
    )
    ecdsa_envelope_invalid = False
    signed_receipt = outcome.details.get("signed_receipt")
    receipt_verified_at = outcome.details.get("receipt_verified_at")
    if auth_scheme == "ECDSA_P256_SHA256_ANDROID_KEYSTORE":
        if (type(signed_receipt) is not dict
                or set(signed_receipt) != {"body", "key_id", "signature"}):
            ecdsa_envelope_invalid = True
        else:
            body = signed_receipt.get("body")
            if (type(body) is not dict
                    or set(body) != {
                        "schema", "nonce", "action_id", "capability", "digest",
                        "issued_at", "expires_at", "status", "local_consent",
                        "observed", "os_permission_status", "key_storage_status", "key_id",
                    }):
                ecdsa_envelope_invalid = True
            else:
                issued_at = body.get("issued_at")
                expires_at = body.get("expires_at")
                numeric_times = (
                    type(issued_at) in (int, float)
                    and type(expires_at) in (int, float)
                    and type(receipt_verified_at) in (int, float)
                    and (type(issued_at) is int or math.isfinite(issued_at))
                    and (type(expires_at) is int or math.isfinite(expires_at))
                    and (type(receipt_verified_at) is int or math.isfinite(receipt_verified_at))
                )
                ecdsa_envelope_invalid = (
                    not numeric_times
                    or type(signed_receipt.get("key_id")) is not str
                    or signed_receipt.get("key_id") != body.get("key_id")
                    or type(signed_receipt.get("signature")) is not str
                    or not signed_receipt.get("signature")
                    or len(signed_receipt.get("signature", "")) > 256
                    or body.get("schema") != "v14.android-companion-receipt/1"
                    or body.get("nonce") != nonce
                    or body.get("action_id") != outcome.action_id
                    or body.get("capability") != outcome.capability
                    or body.get("digest") != digest
                    or body.get("status") != receipt_status
                    or body.get("local_consent") is not consent_claim
                    or body.get("observed") is not False
                    or body.get("os_permission_status") != outcome.details.get("android_os_permission_status")
                    or body.get("key_storage_status") != outcome.details.get("key_storage_status")
                    or (numeric_times and (
                        expires_at < issued_at
                        or expires_at - issued_at > 60
                        or not issued_at <= receipt_verified_at <= expires_at
                    ))
                )
    if common_invalid or legacy_hmac_invalid or android_keystore_invalid or ecdsa_envelope_invalid or auth_scheme not in {
        "HMAC_SHA256_PER_INSTALL", "ECDSA_P256_SHA256_ANDROID_KEYSTORE"
    }:
        raise InvalidOutcome("companion receipt metadata is incomplete")
    row = store.one("SELECT packet FROM events WHERE id=?", (event_id,))
    if not row:
        raise InvalidOutcome("source event missing")
    import json
    event = json.loads(row["packet"])
    if event.get("source_ref") != source_ref:
        raise InvalidOutcome("source event binding mismatch")
    store.read_source(source_ref)
    actual = {
        "outcome_kind": "ANDROID_COMPANION_RECEIPT",
        "capability": outcome.capability,
        "observed": False,
        "evidence_level": "COMPANION_RECEIPT_ONLY",
        "receipt_schema": outcome.details["receipt_schema"],
        "auth_scheme": outcome.details["auth_scheme"],
        "digest": digest,
        "receipt_nonce": nonce,
        "companion_local_consent_claim": consent_claim,
        "receipt_status": receipt_status,
        "local_approval_evidence": outcome.details["local_approval_evidence"],
        "android_os_permission_status": outcome.details["android_os_permission_status"],
        "key_storage_status": outcome.details["key_storage_status"],
        "t8_authoritative": False,
        "world_learning_eligible": False,
        "trusted_transition_eligible": False,
    }
    if auth_scheme == "ECDSA_P256_SHA256_ANDROID_KEYSTORE":
        actual["signed_receipt"] = signed_receipt
        actual["receipt_verified_at"] = float(receipt_verified_at)
    p = packet(
        "ActionOutcome", "C5_ANDROID_COMPANION", event_id,
        event["brain_generation_id"], [source_ref],
        action_id=outcome.action_id, status=outcome.status, actual=actual,
    )
    # BEGIN IMMEDIATE serializes competing writers. The nonce is scoped to
    # the installation key, not to an event, so replay detection must scan all
    # companion receipts while the packet insert is in the same transaction.
    with store.tx() as c:
        rows = c.execute(
            "SELECT payload FROM packets WHERE kind=?",
            ("ActionOutcome",),
        ).fetchall()
        for prior_row in rows:
            prior = json.loads(prior_row["payload"])
            prior_actual = prior.get("actual")
            if (prior.get("producer_component") != "C5_ANDROID_COMPANION"
                    or not isinstance(prior_actual, dict)
                    or prior_actual.get("outcome_kind") != "ANDROID_COMPANION_RECEIPT"):
                continue
            if prior_actual.get("receipt_nonce") == nonce:
                if (prior.get("action_id") == outcome.action_id
                        and prior.get("event_id") == event_id
                        and prior_actual.get("digest") == digest):
                    return prior
                raise InvalidOutcome("receipt nonce replay")
            if prior.get("action_id") == outcome.action_id:
                raise InvalidOutcome("action already has a different companion receipt")
        c.execute(
            "INSERT INTO packets VALUES (?,?,?,?,?,?)",
            (p["packet_id"], "ActionOutcome", event_id,
             event["brain_generation_id"], dumps(p), now()),
        )
    return p


def accept_and_persist_companion_receipt(
    store,
    broker: AndroidControlBroker,
    verifier,
    action_id: str,
    receipt: dict,
    *,
    on_outcome: Callable[[ActionOutcome], None] | None = None,
    clock: Callable[[], float] | None = None,
):
    """One C5 receipt-consumer call: authenticate, persist, then notify downstream.

    When the caller does not supply a clock, reuse the verifier's clock so
    signature validity and the persisted verification timestamp share one
    time source (important for deterministic clocks and bounded receipt windows).
    """
    if clock is None:
        verifier_clock = getattr(verifier, "clock", None)
        clock = verifier_clock if callable(verifier_clock) else time.time
    outcome = accept_companion_receipt(
        broker, verifier, action_id, receipt, on_outcome=None, clock=clock,
        finalize_broker=False,
    )
    try:
        packet_value = persist_companion_outcome(store, outcome)
    except InvalidOutcome:
        # A permanent provenance/replay rejection is terminal; transient Store
        # failures leave RECEIPT_CONSUMED so the exact signed receipt can retry.
        broker.record_companion_receipt(action_id, outcome.details["digest"], verified=False)
        raise
    # Store transaction commits the nonce and ActionOutcome together. Only
    # then may the broker make this receipt terminal; a failed write stays
    # RECEIPT_CONSUMED and can be retried idempotently.
    broker.record_companion_receipt(action_id, outcome.details["digest"], verified=True)
    if on_outcome is not None:
        on_outcome(outcome)
    return outcome, packet_value
