"""Typed Android action outcome contract. Simulation only; no OS control."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
import hashlib
import json
import time

class Capability(str, Enum):
    LAUNCH_APP = "launch_app"
    OBSERVE_UI = "observe_ui"
    TAP = "tap"
    SWIPE = "swipe"
    TYPE_TEXT = "type_text"
    BACK = "back"
    SPEAK_TEXT = "speak_text"

class ExecutionStatus(str, Enum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    DENIED = "DENIED"
    EXECUTED = "EXECUTED"

@dataclass(frozen=True)
class CapabilitySpec:
    capability: Capability
    android_permission: str | None
    native_verified: bool = False

SPECS = {c: CapabilitySpec(c, "android.accessibilityservice.AccessibilityService"
         if c in {Capability.OBSERVE_UI, Capability.TAP, Capability.SWIPE,
                  Capability.TYPE_TEXT, Capability.BACK} else None) for c in Capability}

@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    capability: Capability
    args: Mapping[str, object]
    source_event_id: str
    expires_at: float

@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: Capability
    source_event_id: str
    status: ExecutionStatus
    at: float
    request_digest: str
    error_code: str

    def t8_record(self) -> dict:
        """No raw screen, speech text, app arguments or credentials in telemetry."""
        return {"action_id": self.action_id, "capability": self.capability.value,
                "source_event_id": self.source_event_id, "status": self.status.value,
                "at": self.at, "request_digest": self.request_digest,
                "error_code": self.error_code}

class CapabilityRegistry:
    """Default OFF; shadow enablement is not an Android OS grant."""
    def __init__(self):
        self._enabled = set()
        self._stopped = True

    def describe(self, capability: Capability) -> CapabilitySpec:
        return SPECS[Capability(capability)]

    def status(self, capability: Capability) -> ExecutionStatus:
        return (ExecutionStatus.SHADOW if not self._stopped
                and capability in self._enabled else ExecutionStatus.OFF)

    def enable_shadow_for_test(self, capability: Capability):
        self._enabled.add(Capability(capability))
        self._stopped = False

    def stop(self):
        self._stopped = True
        self._enabled.clear()

class AndroidActionBridge:
    """C5/JEF simulation consumer. No caller can enable live execution.

    Live requests must be independently authenticated and authorized inside
    a separate Android companion. A model-provided approval flag is not proof.
    """
    def __init__(self, registry: CapabilityRegistry, *, clock=time.time):
        self.registry = registry
        self.clock = clock
        self._seen = set()

    def submit(self, request: ActionRequest) -> ActionOutcome:
        if not request.action_id or not request.source_event_id:
            raise ValueError("missing identity")
        payload = json.dumps({"id": request.action_id, "capability": request.capability.value,
                              "args": dict(request.args), "source": request.source_event_id,
                              "expires": request.expires_at}, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        now = self.clock()
        if request.action_id in self._seen:
            status, error = ExecutionStatus.DENIED, "REPLAY"
        elif type(request.expires_at) not in (int, float) or not now < request.expires_at <= now + 60:
            status, error = ExecutionStatus.DENIED, "EXPIRED_OR_TTL"
        else:
            self._seen.add(request.action_id)
            status = self.registry.status(request.capability)
            error = ("NATIVE_COMPANION_UNVERIFIED" if status is ExecutionStatus.SHADOW
                     else "CAPABILITY_OFF")
        return ActionOutcome(request.action_id, request.capability, request.source_event_id,
                             status, now, digest, error)
