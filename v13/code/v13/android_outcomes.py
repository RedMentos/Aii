"""Typed fail-closed Android action outcome boundary for C5/JEF.

Software-only: a DRY_RUN is never an observed Android transition and must
never be promoted into T8 learning evidence. The OS companion remains OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Mapping
import time

from .android_control import AndroidControlBroker, ControlDenied


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
