"""Android companion capability negotiation, separate from learned brain policy.

No OS privileges are granted here. A native Android companion must independently
enforce its manifest permissions, authenticated caller identity and user consent.
Until native instrumentation exists, this transport is OFF / simulated only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import hashlib
import json

from .android_control import CAPABILITIES, ControlDenied, _canonical
from .android_operator_loop import ActionOutcome, SimulatedCompanion


@dataclass(frozen=True)
class Capability:
    name: str
    backend: str
    permission: str
    enabled: bool = False


class CapabilityRegistry:
    """Immutable declared capabilities; runtime grants never originate in a model."""
    def __init__(self, capabilities=None):
        entries = capabilities if capabilities is not None else (
            Capability("launch_app", "ANDROID_INTENT", "LOCAL_OPERATOR"),
            Capability("observe_ui", "ACCESSIBILITY", "ACCESSIBILITY_SERVICE"),
            Capability("tap", "ACCESSIBILITY", "ACCESSIBILITY_SERVICE"),
            Capability("swipe", "ACCESSIBILITY", "ACCESSIBILITY_SERVICE"),
            Capability("type_text", "ACCESSIBILITY", "ACCESSIBILITY_SERVICE"),
            Capability("back", "ACCESSIBILITY", "ACCESSIBILITY_SERVICE"),
        )
        self._entries = {}
        for item in entries:
            if not isinstance(item, Capability) or item.name not in CAPABILITIES:
                raise ValueError("unsupported capability declaration")
            if item.name in self._entries:
                raise ValueError("duplicate capability")
            self._entries[item.name] = item

    def get(self, name: str) -> Capability:
        try:
            return self._entries[name]
        except (KeyError, TypeError):
            raise ControlDenied("capability not registered") from None

    def report(self) -> tuple[dict, ...]:
        return tuple(dict(name=c.name, backend=c.backend,
                          permission=c.permission, enabled=c.enabled)
                     for c in sorted(self._entries.values(), key=lambda c: c.name))


class CompanionTransport:
    """Typed envelope verifier and simulation-only dispatcher.

    This is not a native Android transport. Live transport must verify Android
    Binder UID/signature or an equivalent OS-backed local identity separately.
    Neither an in-band 'approved' field nor an LLM claim is authentication.
    """
    def __init__(self, registry: CapabilityRegistry, *, simulator=None):
        self.registry = registry
        self.simulator = simulator or SimulatedCompanion()

    def dispatch_simulated(self, envelope: Mapping[str, object]) -> ActionOutcome:
        if not isinstance(envelope, Mapping):
            raise ControlDenied("invalid envelope")
        if set(envelope) != {"action_id", "capability", "args", "digest", "status"}:
            raise ControlDenied("unexpected envelope fields")
        action_id = envelope["action_id"]
        if not isinstance(action_id, str) or len(action_id) != 32 or any(
            c not in "0123456789abcdef" for c in action_id
        ):
            raise ControlDenied("invalid action id")
        capability = envelope["capability"]
        declared = self.registry.get(capability)
        if declared.enabled:
            raise ControlDenied("live-enabled capability cannot use simulation transport")
        if envelope["status"] != "DRY_RUN_ONLY":
            raise ControlDenied("live transport OFF")
        canonical = _canonical(capability, envelope["args"])
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        if envelope["digest"] != digest:
            raise ControlDenied("envelope digest mismatch")
        return self.simulator.dispatch(envelope)

    def dispatch_live(self, envelope: Mapping[str, object]) -> ActionOutcome:
        raise ControlDenied("native Android authenticated companion not installed")
