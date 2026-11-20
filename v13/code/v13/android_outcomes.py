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
        attestation = verifier.verify(envelope, receipt)
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
            "companion_local_consent": True,
            "android_os_permission_independently_required": True,
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
    """Persist a source-bound audit packet; never create a WorldAction transition."""
    if (not isinstance(outcome, ActionOutcome)
            or outcome.status != "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED"
            or outcome.observed is not False
            or outcome.evidence_level != "COMPANION_RECEIPT_ONLY"
            or outcome.details.get("t8_authoritative") is not False
            or outcome.details.get("world_learning_eligible") is not False):
        raise InvalidOutcome("only non-authoritative companion receipts may be persisted here")
    event_id = outcome.details.get("event_id")
    source_ref = outcome.details.get("source_ref")
    if type(event_id) is not str or type(source_ref) is not dict:
        raise InvalidOutcome("source-bound event required before persistence")
    row = store.one("SELECT packet FROM events WHERE id=?", (event_id,))
    if not row:
        raise InvalidOutcome("source event missing")
    import json
    event = json.loads(row["packet"])
    if event.get("source_ref") != source_ref:
        raise InvalidOutcome("source event binding mismatch")
    store.read_source(source_ref)
    p = packet(
        "AndroidActionOutcome", "C5_ANDROID_COMPANION", event_id,
        event["brain_generation_id"], [source_ref],
        action_id=outcome.action_id, capability=outcome.capability,
        status=outcome.status, observed=False,
        evidence_level="COMPANION_RECEIPT_ONLY",
        receipt_schema=outcome.details["receipt_schema"],
        auth_scheme=outcome.details["auth_scheme"],
        digest=outcome.details["digest"],
        companion_local_consent=True,
        android_os_permission_independently_required=True,
        t8_authoritative=False, world_learning_eligible=False,
        trusted_transition_eligible=False,
    )
    store.add_packet("AndroidActionOutcome", p)
    return p
