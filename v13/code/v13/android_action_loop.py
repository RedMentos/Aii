"""C5 Android action/outcome bridge. Native transport is intentionally OFF.

A local OS-permissioned companion must independently authenticate requests and
provide verified device receipts before any outcome may be marked observed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from .android_control import AndroidControlBroker, ControlDenied


@dataclass(frozen=True)
class ActionOutcome:
    action_id: str
    capability: str
    status: str
    observed_at: float
    source: str
    request_digest: str

    def to_event(self):
        return asdict(self)


class AndroidActionLoop:
    """Model may propose; only trusted local UI may approve; live is unavailable."""

    def __init__(self, broker: AndroidControlBroker, sink, *, clock=None):
        self.broker = broker
        self.sink = sink
        self.clock = clock or time.time

    def propose(self, capability, args):
        return self.broker.propose(capability, args)

    def approve_local(self, action_id, *, local_confirmation=False):
        self.broker.approve(action_id, confirmed_by_local_ui=local_confirmation)

    def dry_run(self, action_id):
        result = self.broker.execute(action_id, dry_run=True)
        if result.get("status") != "DRY_RUN_ONLY":
            raise ControlDenied("unexpected broker result")
        outcome = ActionOutcome(
            action_id=result["action_id"], capability=result["capability"],
            status="SIMULATED_NOT_EXECUTED", observed_at=float(self.clock()),
            source="LOCAL_DRY_RUN", request_digest=result["digest"])
        self.sink(outcome.to_event())
        return outcome

    def dispatch_live(self, action_id):
        raise ControlDenied("native companion and OS capability gate unavailable")
