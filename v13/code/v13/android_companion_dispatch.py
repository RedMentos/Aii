"""Fail-closed Android action dispatcher. Native companion remains a separate OS trust boundary.

The injected transport must be implemented by an Android companion with its own
OS-granted permissions and local user approval. This Python module cannot grant
those permissions or authenticate the Android app by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import time

from .android_capability_contract import (
    ActionOutcome, ActionRequest, Capability, CapabilityRegistry, OutcomeStatus,
)


class CompanionTransport(Protocol):
    def execute(self, request: ActionRequest) -> ActionOutcome:
        """Native companion must independently authorize and execute each request."""


class ReceiptVerifier(Protocol):
    def verify(self, request: ActionRequest, outcome: ActionOutcome) -> bool:
        """Validate authenticated companion provenance, not just a receipt string."""


@dataclass(frozen=True)
class DispatchResult:
    request: ActionRequest
    outcome: ActionOutcome


class AndroidDispatcher:
    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        transport: CompanionTransport | None = None,
        verifier: ReceiptVerifier | None = None,
        max_age_seconds: float = 30.0,
    ):
        if not 0 < max_age_seconds <= 300:
            raise ValueError("invalid action expiry")
        self.registry = registry
        self.transport = transport
        self.verifier = verifier
        self.max_age_seconds = max_age_seconds

    def dispatch(self, capability: Capability, target: str, *, dry_run: bool = True) -> DispatchResult:
        request = self.registry.request(capability, target, dry_run=dry_run)
        if dry_run:
            outcome = ActionOutcome(request.request_id, capability, OutcomeStatus.DRY_RUN, None, time.time())
            self.registry.settle(outcome)
            return DispatchResult(request, outcome)

        # No native transport and independently authenticated receipt verifier = OFF.
        if self.transport is None or self.verifier is None:
            outcome = ActionOutcome(request.request_id, capability, OutcomeStatus.DENIED, None, time.time())
            self.registry.settle(outcome)
            return DispatchResult(request, outcome)

        if time.monotonic() - request.created_monotonic > self.max_age_seconds:
            outcome = ActionOutcome(request.request_id, capability, OutcomeStatus.CANCELLED, None, time.time())
            self.registry.settle(outcome)
            return DispatchResult(request, outcome)

        try:
            response = self.transport.execute(request)
            if not isinstance(response, ActionOutcome):
                raise ValueError("invalid native outcome")
            if response.request_id != request.request_id or response.capability != request.capability:
                raise ValueError("native outcome request mismatch")
            if response.status == OutcomeStatus.SUCCESS:
                if not response.companion_receipt or not self.verifier.verify(request, response):
                    raise PermissionError("unverified companion receipt")
            if time.monotonic() - request.created_monotonic > self.max_age_seconds:
                raise TimeoutError("native response expired")
            self.registry.settle(response)
            return DispatchResult(request, response)
        except Exception:
            # Do not report SUCCESS when the transport, authentication, or
            # response handling fails. A native action might already have
            # occurred; callers must not automatically retry ambiguous outcomes.
            outcome = ActionOutcome(request.request_id, capability, OutcomeStatus.FAILED, None, time.time())
            self.registry.settle(outcome)
            return DispatchResult(request, outcome)
