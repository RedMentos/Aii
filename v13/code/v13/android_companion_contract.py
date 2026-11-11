"""Typed Android companion boundary; no Android OS action is implemented here.

The model cannot create consent or promote a simulated result into native proof.
A future Android application must authenticate its channel and independently
check platform permissions and foreground/background restrictions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol
import hashlib
import json
import time

from .android_control import CAPABILITIES, ControlDenied, _canonical


class CapabilityState(str, Enum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    TESTED = "TESTED"
    ANDROID_VERIFIED = "ANDROID_VERIFIED"


@dataclass(frozen=True)
class Capability:
    name: str
    state: CapabilityState
    android_permission: str | None
    channel: str


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    capability: str
    args: Mapping[str, object]
    approved_digest: str
    expires_at: float


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    status: str
    source: str
    observed_at: float
    detail: str = ""


class CompanionTransport(Protocol):
    """Native companion implements this after OS-granted permissions."""
    def dispatch(self, request: ActionRequest) -> ActionOutcome: ...


class CapabilityRegistry:
    """Default deny: all native paths OFF until separately verified and enabled."""
    def __init__(self):
        self._caps = {
            name: Capability(name, CapabilityState.OFF,
                "android.permission.BIND_ACCESSIBILITY_SERVICE" if name in
                {"tap", "swipe", "type_text", "back"} else
                "user-approved MediaProjection or Accessibility observation" if name == "observe_ui"
                else None, "native_companion")
            for name in CAPABILITIES
        }

    def get(self, name: str) -> Capability:
        if name not in self._caps:
            raise ControlDenied("unknown Android capability")
        return self._caps[name]

    def status(self) -> dict[str, str]:
        return {k: v.state.value for k, v in sorted(self._caps.items())}


class AndroidCompanionGateway:
    """Reject native dispatch until a trusted companion is integrated.

    A broker's dry-run envelope is intentionally NOT an approval token for live
    dispatch. An authenticated, single-use native consent binding is still
    required; until implemented this gateway cannot perform live operations.
    """
    def __init__(self, registry: CapabilityRegistry | None = None, *, clock=None):
        self.registry = registry or CapabilityRegistry()
        self.clock = clock or time.time

    def dispatch(self, request: ActionRequest, transport: CompanionTransport | None = None) -> ActionOutcome:
        _canonical(request.capability, dict(request.args))
        if not request.action_id or not request.approved_digest:
            raise ControlDenied("missing action identity")
        if request.expires_at <= self.clock():
            raise ControlDenied("expired action")
        if self.registry.get(request.capability).state is CapabilityState.OFF:
            raise ControlDenied("native Android capability OFF")
        # No trusted Android consent verifier exists yet. Never call transport.
        raise ControlDenied("native companion consent verifier unavailable")

    def preview(self, request: ActionRequest) -> ActionOutcome:
        payload = _canonical(request.capability, dict(request.args))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if request.approved_digest != digest or request.expires_at <= self.clock():
            raise ControlDenied("invalid or expired preview")
        self.registry.get(request.capability)
        return ActionOutcome(request.action_id, request.capability, "DRY_RUN_ONLY",
                             "synthetic_preview", self.clock(),
                             "No Android API or UI action executed")
