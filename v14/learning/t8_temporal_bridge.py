"""Experimental T8 -> temporal outcome -> numeric receiver bridge.

This is NOT a native B1/B2 adapter, trained JEPA encoder or GGUF optimizer.
Only call with independently authenticated T8 envelopes; a string prefix alone
does not authenticate the producer.
"""
from temporal_outcomes import TemporalOutcomes, Expectation
from temporal_receiver import TemporalReadout


class TemporalT8Bridge:
    def __init__(self, directory, *, learning_enabled=False):
        from pathlib import Path
        root = Path(directory)
        self.ledger = TemporalOutcomes(root / "outcomes.json")
        self.receiver = TemporalReadout(root / "readout.json", learning_enabled=learning_enabled)

    def open(self, *, event_id, source, owner, outcome, opened_at, earliest, deadline, probability, trusted=False):
        if not trusted:
            raise PermissionError("authenticated T8 producer required")
        if not source.startswith("T8:"):
            raise ValueError("T8 source required")
        self.ledger.expect(Expectation(event_id, source, owner, outcome,
                                       opened_at, earliest, deadline, probability))
        return self.ledger.records[event_id].status

    def observe(self, *, event_id, at, observed, evidence, complete=False,
                trusted=False, optimizer_permission=False):
        if not trusted:
            raise PermissionError("authenticated T8 producer required")
        if not isinstance(evidence, str) or (evidence and not evidence.startswith("T8:")):
            raise ValueError("T8 evidence required")
        record = self.ledger.records[event_id]
        if record.status == "PENDING":
            result = self.ledger.resolve(event_id, at=at, observed=observed,
                                         evidence=evidence, observation_complete=complete)
        else:
            # Crash between durable outcome and durable optimizer checkpoint:
            # retry the exact same event, never silently substitute evidence.
            if record.status not in ("OBSERVED", "DELAYED", "OMITTED"):
                raise ValueError("terminal event cannot learn")
            if record.evidence != evidence or (record.status == "OMITTED") != (not observed):
                raise ValueError("conflicting replay")
            result = vars(record).copy()
        intent = self.ledger.learning_intent(event_id)
        if intent is None:
            return {"outcome": result["status"], "updated": False}
        if event_id in self.receiver.seen:
            return {"outcome": result["status"], "updated": False, "duplicate": True}
        if not optimizer_permission:
            return {"outcome": result["status"], "updated": False, "pending_optimizer": True}
        delta = self.receiver.update(intent, event_id, authorized=True)
        return {"outcome": result["status"], "updated": True, "parameter_delta": delta,
                "readout": {role: self.receiver.read(role) for role in ("WORLD", "B1", "B2")}}
