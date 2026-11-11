"""Connect Core's approved dry-run operator to the persistent fake Android world.

This is a *simulation-only* integration adapter. No Android IPC or native
permissions. It must not be used to synthesize human consent on a real device.
"""
from __future__ import annotations

from .android_control import ControlDenied
from .android_operator_loop import AndroidOperatorLoop, SimulatedCompanion, ActionOutcome
from .android_companion_registry import CapabilityRegistry, CompanionTransport
from .behavior_governor import neutral_signals, review_behavior


class PersistentWorldCompanion(SimulatedCompanion):
    """Apply exactly one broker-approved synthetic envelope to SQLite world."""
    def __init__(self, world):
        self.world = world
        self.last_receipt = None

    def dispatch(self, envelope):
        # Validate BEFORE mutating the world.
        validated = super().dispatch(envelope)
        if validated.status != "SIMULATED" or validated.source != "SIMULATED_COMPANION":
            raise ControlDenied("invalid synthetic companion outcome")
        receipt = self.world.apply(envelope)
        if (receipt.get("native_android_executed") is not False
                or receipt.get("simulation_applied") is not True):
            raise ControlDenied("world did not prove simulation-only execution")
        self.last_receipt = receipt
        return validated


def synthetic_operator_action(broker, world, capability, args):
    """One brain-like proposal -> synthetic fixture consent -> persisted outcome.

    The local_confirmation=True here is test-fixture consent only, never an
    authenticated human approval. A native implementation MUST replace this
    path with a separate trusted Android UI/OS capability broker.
    """
    verdict = review_behavior(neutral_signals(), has_external_effect=False)
    if verdict.guidance != "NO_OBJECTION_IN_ADVISORY_REVIEW":
        raise ControlDenied("synthetic behavior requires independent review")
    companion = PersistentWorldCompanion(world)
    typed_transport = CompanionTransport(CapabilityRegistry(), simulator=companion)
    operator = AndroidOperatorLoop(broker, companion=typed_transport)
    proposal = operator.run_from_brain(capability, args)
    if proposal.status != "AWAITING_LOCAL_APPROVAL":
        raise ControlDenied("brain action unexpectedly approved")
    outcome = operator.approved_simulation(proposal.action_id, local_confirmation=True)
    if (outcome.action_id != proposal.action_id
            or outcome.status != "SIMULATED"
            or outcome.source != "SIMULATED_COMPANION"
            or companion.last_receipt is None):
        raise ControlDenied("missing matching synthetic action outcome")
    return companion.last_receipt
