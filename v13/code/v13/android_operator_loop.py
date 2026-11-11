"""Android operator loop: brain proposal -> local approval -> companion outcome.

Simulation is useful for wiring and tests, not evidence of Android execution.
The caller must keep the local confirmation UI outside model-controlled code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping
import time

from .android_control import AndroidControlBroker, ControlDenied


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    status: str
    observed_at: float
    source: str
    detail: str = ""


class SimulatedCompanion:
    """No Android APIs, no filesystem writes, no side effects."""
    def dispatch(self, envelope: Mapping[str, object]) -> ActionOutcome:
        if envelope.get("status") != "DRY_RUN_ONLY":
            raise ControlDenied("simulation accepts dry-run envelopes only")
        return ActionOutcome(str(envelope["action_id"]), str(envelope["capability"]),
                             "SIMULATED", time.time(), "SIMULATED_COMPANION")


class AndroidOperatorLoop:
    """The only current executor is simulation; live execution stays OFF.

    confirm is invoked by a trusted local operator integration, never by C3/JEF
    or model-generated input. This Python boundary is not an OS permission gate.
    """
    def __init__(self, broker: AndroidControlBroker, companion=None):
        self.broker = broker
        self.companion = companion or SimulatedCompanion()

    def propose(self, capability: str, args: dict):
        return self.broker.propose(capability, args)

    def approved_simulation(self, action_id: str, *, local_confirmation: bool = False) -> ActionOutcome:
        self.broker.approve(action_id, confirmed_by_local_ui=local_confirmation)
        envelope = self.broker.execute(action_id, dry_run=True)
        return self.companion.dispatch(envelope)

    def run_from_brain(self, capability: str, args: dict) -> ActionOutcome:
        """Brain requests are never self-approved; return a pending state."""
        proposal = self.propose(capability, args)
        return ActionOutcome(proposal.action_id, capability, "AWAITING_LOCAL_APPROVAL",
                             time.time(), "BRAIN_PROPOSAL")
