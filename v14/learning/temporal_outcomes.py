"""V14 temporal outcome ledger with explicit success, mismatch and omission semantics.

This records source-bound prediction outcomes. It does not authenticate a producer
or grant optimizer permission; callers must provide those boundaries separately.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import json
import math
import os
import tempfile


@dataclass
class Expectation:
    id: str
    source: str
    owner: str
    outcome: str
    opened_at: float
    earliest: float
    deadline: float
    probability: float
    status: str = "PENDING"
    evidence: str = ""
    observed_at: float | None = None
    error: float | None = None
    observed_outcome: str | None = None


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _label(value, name, maximum):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError(name)


class TemporalOutcomes:
    def __init__(self, path, max_pending=512):
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError("max_pending")
        self.path = Path(path)
        self.max_pending = max_pending
        self.records = {}
        if self.path.exists():
            data = json.loads(self.path.read_text())
            if data.get("schema") != 1 or not isinstance(data.get("records"), list):
                raise ValueError("schema")
            self.records = {x["id"]: Expectation(**x) for x in data["records"]}
            if len(self.records) != len(data["records"]):
                raise ValueError("duplicate persisted id")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".outcomes-")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"schema": 1, "records": [asdict(x) for x in self.records.values()]}, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def expect(self, r):
        if not isinstance(r, Expectation):
            raise TypeError("Expectation required")
        _label(r.id, "id", 128)
        _label(r.source, "source", 256)
        _label(r.owner, "owner", 64)
        _label(r.outcome, "outcome", 128)
        if not all(_finite_number(x) for x in (r.opened_at, r.earliest, r.deadline, r.probability)):
            raise ValueError("numeric fields")
        if not r.opened_at <= r.earliest <= r.deadline:
            raise ValueError("time")
        if not 0 <= r.probability <= 1 or r.status != "PENDING":
            raise ValueError("probability/status")
        if r.evidence != "" or r.observed_at is not None or r.error is not None or r.observed_outcome is not None:
            raise ValueError("initial state")
        if r.id in self.records:
            raise ValueError("duplicate")
        if sum(x.status == "PENDING" for x in self.records.values()) >= self.max_pending:
            raise OverflowError("pending budget")
        before = self.records
        self.records = {**before, r.id: replace(r)}
        try:
            self.save()
        except Exception:
            self.records = before
            raise

    def resolve(self, id, *, at, observed, evidence="", observed_outcome=None,
                observation_complete=False, cancelled=False):
        _label(id, "id", 128)
        if type(at) not in (int, float) or not math.isfinite(at):
            raise ValueError("time")
        if type(observed) is not bool or type(observation_complete) is not bool or type(cancelled) is not bool:
            raise ValueError("boolean fields")
        if type(evidence) is not str or len(evidence) > 512:
            raise ValueError("evidence")
        if observed_outcome is not None:
            _label(observed_outcome, "observed outcome", 128)
        r = self.records[id]
        if r.status != "PENDING" or at < r.opened_at:
            raise ValueError("state/time")
        if cancelled and (observed or observation_complete or observed_outcome is not None):
            raise ValueError("cancelled outcome conflict")
        if observed and (observed_outcome is None or not evidence):
            raise ValueError("observed outcome/evidence required")
        if not observed and observed_outcome is not None:
            raise ValueError("unexpected observed outcome")
        if not cancelled and not observed and at < r.deadline:
            # An incomplete early observation is not a terminal outcome.
            return asdict(r)

        next_r = replace(r)
        if cancelled:
            next_r.status = "CANCELLED"
        elif observed:
            next_r.observed_outcome = observed_outcome
            if observed_outcome != r.outcome:
                next_r.status = "MISMATCHED"
                next_r.error = -r.probability
            elif at < r.earliest:
                next_r.status = "EARLY"
                next_r.error = -r.probability
            elif at > r.deadline:
                next_r.status = "DELAYED"
                next_r.error = -r.probability
            else:
                next_r.status = "OBSERVED"
                next_r.error = 1 - r.probability
        elif observation_complete and at >= r.deadline and evidence:
            next_r.status = "OMITTED"
            next_r.error = -r.probability
        else:
            next_r.status = "CENSORED"
        next_r.observed_at = at
        next_r.evidence = evidence
        before = self.records
        self.records = {**before, id: next_r}
        try:
            self.save()
        except Exception:
            self.records = before
            raise
        return asdict(next_r)

    def learning_intent(self, id):
        r = self.records[id]
        if r.error is None:
            return None
        return {"source": r.source, "evidence": r.evidence, "owner": r.owner,
                "expected_outcome": r.outcome, "observed_outcome": r.observed_outcome,
                "prediction_error": r.error, "target": "WORLD_TEMPORAL",
                "requires_optimizer_permission": True}
