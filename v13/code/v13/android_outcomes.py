"""Typed fail-closed Android action outcome boundary for C5/JEF.

Software-only: a DRY_RUN is never an observed Android transition and must
never be promoted into T8 learning evidence. The OS companion remains OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Mapping
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
) -> ActionOutcome:
    """Consume a dispatched request using an authenticated companion receipt.

    The broker approval is consumed before verification; any malformed, stale,
    replayed or unauthenticated receipt therefore fails closed and requires a
    new local approval. A valid receipt is still only a companion attestation,
    not independent device observation or T8 learning authority.
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
                or attestation.get("status") != "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
                or attestation.get("t8_authoritative") is not False):
            raise InvalidOutcome("companion verifier returned an unsupported authority level")
        with broker.lock:
            if broker.stopped:
                raise ControlDenied("broker stopped during companion verification")
            broker.record_companion_receipt(action_id, proposal.digest, verified=True)
    except Exception:
        broker.record_companion_receipt(action_id, proposal.digest, verified=False)
        raise
    outcome = ActionOutcome(
        action_id=proposal.action_id,
        capability=proposal.capability,
        status="COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
        observed=False,
        evidence_level="COMPANION_RECEIPT_ONLY",
        timestamp=float(clock()),
        details={
            "digest": proposal.digest,
            "receipt_schema": attestation["schema"],
            "auth_scheme": attestation["auth_scheme"],
            "receipt_nonce": attestation["nonce"],
            "companion_local_consent_claim": True,
            "local_approval_evidence": "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION",
            "android_os_permission_status": "REQUIRED_NOT_VERIFIED",
            "key_storage_status": attestation["key_storage_status"],
            "t8_authoritative": False,
            "world_learning_eligible": False,
            "event_id": proposal.event_id,
            "source_ref": dict(proposal.source_ref) if proposal.source_ref is not None else None,
        },
    )
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
            or outcome.status != "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
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
    if (type(nonce) is not str or len(nonce) != 32
            or any(ch not in "0123456789abcdef" for ch in nonce)
            or type(digest) is not str or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or outcome.details.get("receipt_schema") != "v14.android-companion-receipt/1"
            or outcome.details.get("auth_scheme") != "HMAC_SHA256_PER_INSTALL"
            or outcome.details.get("companion_local_consent_claim") is not True
            or outcome.details.get("local_approval_evidence") != "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION"
            or outcome.details.get("android_os_permission_status") != "REQUIRED_NOT_VERIFIED"
            or outcome.details.get("key_storage_status") != "UNVERIFIED"):
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
        "companion_local_consent_claim": True,
        "local_approval_evidence": "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION",
        "android_os_permission_status": "REQUIRED_NOT_VERIFIED",
        "key_storage_status": "UNVERIFIED",
        "t8_authoritative": False,
        "world_learning_eligible": False,
        "trusted_transition_eligible": False,
    }
    p = packet(
        "ActionOutcome", "C5_ANDROID_COMPANION", event_id,
        event["brain_generation_id"], [source_ref],
        action_id=outcome.action_id, status=outcome.status, actual=actual,
    )
    # BEGIN IMMEDIATE serializes competing writers. The uniqueness check and
    # packet insert therefore commit together, without a second replay ledger.
    with store.tx() as c:
        rows = c.execute(
            "SELECT payload FROM packets WHERE kind=? AND event_id=?",
            ("ActionOutcome", event_id),
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
    clock: Callable[[], float] = time.time,
):
    """One C5 receipt-consumer call: authenticate, persist, then notify downstream."""
    outcome = accept_companion_receipt(
        broker, verifier, action_id, receipt, on_outcome=None, clock=clock
    )
    packet_value = persist_companion_outcome(store, outcome)
    if on_outcome is not None:
        on_outcome(outcome)
    return outcome, packet_value
