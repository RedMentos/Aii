"""V14 Core: typed Android capability-to-outcome pipeline, simulation-only.

This composes existing approved action envelopes, persistent synthetic Android
world and typed outcomes. It does not grant Android OS permissions or expose a
native transport. An independent, authenticated Android companion is required
before any production executor can be registered.
"""
from __future__ import annotations

from dataclasses import dataclass
from .android_control import AndroidControlBroker, CAPABILITIES, ControlDenied
from .android_control_sim import SimulatedAndroidWorld
from .android_outcome import receipt

SCHEMA = "v14.capability-registry/1"
SIMULATED = "SIMULATED_ONLY"
UNAVAILABLE = "OFF"


@dataclass(frozen=True)
class CapabilityStatus:
    capability: str
    mode: str
    android_verified: bool
    consent_required: bool

    def as_record(self):
        return {"capability": self.capability, "mode": self.mode,
                "android_verified": self.android_verified,
                "consent_required": self.consent_required}


class CapabilityRegistry:
    """Fail-closed runtime capability view; never derives OS authority from Age."""

    def __init__(self, *, simulator=None):
        self.simulator = simulator

    def status(self):
        mode = SIMULATED if self.simulator is not None else UNAVAILABLE
        return {"schema": SCHEMA, "native_transport": UNAVAILABLE,
                "capabilities": [CapabilityStatus(c, mode, False, True).as_record()
                                 for c in sorted(CAPABILITIES)]}

    def execute_approved(self, broker: AndroidControlBroker, action_id: str):
        """Consume exactly one local-UI-approved envelope and commit a simulated outcome.

        Native operations are deliberately not exposed here. An invalid or
        replayed approval cannot mutate the simulator. The simulator itself
        transactionally deduplicates action IDs across restarts.
        """
        if self.simulator is None:
            raise ControlDenied("no authenticated Android companion or simulator")
        if type(action_id) is not str:
            raise ControlDenied("invalid action id")
        envelope = broker.execute(action_id, dry_run=True)
        result = self.simulator.apply(envelope)
        outcome = receipt(envelope)
        return {"schema": "v14.android-control-result/1",
                "outcome": outcome.as_record(),
                "transition": result,
                "authority": "LOCAL_UI_APPROVAL_SIMULATION_ONLY",
                "native_android_executed": False}

    def close(self):
        if self.simulator is not None:
            self.simulator.close()


def simulated_registry(home):
    """Explicit test-only factory; never used by the default Android runtime."""
    return CapabilityRegistry(simulator=SimulatedAndroidWorld(home))
