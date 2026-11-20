"""Experimental T8 -> temporal outcome -> numeric receiver bridge.

This is NOT a native B1/B2 adapter, trained JEPA encoder or GGUF optimizer.
Only call with independently authenticated T8 envelopes; a string prefix or
caller-supplied boolean does not authenticate the producer.
"""
from temporal_outcomes import TemporalOutcomes, Expectation
from temporal_receiver import TemporalReadout


class TemporalT8Bridge:
    def __init__(self, directory, *, learning_enabled=False):
        from pathlib import Path
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled")
        root = Path(directory)
        self.ledger = TemporalOutcomes(root / "outcomes.json")
        self.receiver = TemporalReadout(root / "readout.json", learning_enabled=learning_enabled)

    def open(self, *, event_id, source, owner, outcome, opened_at, earliest, deadline,
             probability, trusted=False):
        if trusted is not True:
            raise PermissionError("authenticated T8 producer required")
        if type(source) is not str or not source.startswith("T8:"):
            raise ValueError("T8 source required")
        self.ledger.expect(Expectation(event_id, source, owner, outcome,
                                       opened_at, earliest, deadline, probability))
        return self.ledger.records[event_id].status

    def observe(self, *, event_id, at, observed, evidence, observed_outcome=None,
                complete=False, trusted=False, optimizer_permission=False):
        if trusted is not True:
            raise PermissionError("authenticated T8 producer required")
        if type(optimizer_permission) is not bool:
            raise ValueError("optimizer permission")
        if type(evidence) is not str or (evidence and not evidence.startswith("T8:")):
            raise ValueError("T8 evidence required")
        record = self.ledger.records[event_id]
        if record.status == "PENDING":
            result = self.ledger.resolve(event_id, at=at, observed=observed,
                                         evidence=evidence, observed_outcome=observed_outcome,
                                         observation_complete=complete)
        else:
            terminal = ("OBSERVED", "MISMATCHED", "EARLY", "DELAYED", "OMITTED")
            if record.status not in terminal:
                raise ValueError("terminal event cannot learn")
            if (record.evidence != evidence or record.observed_outcome != observed_outcome
                    or (record.status == "OMITTED") != (not observed)):
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
