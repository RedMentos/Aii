"""V14 source-bound temporal outcome ledger; no automatic weight edits."""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import json, os, tempfile

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

class TemporalOutcomes:
    def __init__(self, path, max_pending=512):
        self.path = Path(path)
        self.max_pending = max_pending
        self.records = {}
        if self.path.exists():
            data = json.loads(self.path.read_text())
            if data.get("schema") != 1: raise ValueError("schema")
            self.records = {x["id"]: Expectation(**x) for x in data["records"]}

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
            if os.path.exists(name): os.unlink(name)

    def expect(self, r):
        if not all((r.id, r.source, r.owner, r.outcome)): raise ValueError("missing provenance")
        if not r.opened_at <= r.earliest <= r.deadline: raise ValueError("time")
        if not 0 <= r.probability <= 1 or r.status != "PENDING": raise ValueError("probability/status")
        if r.id in self.records: raise ValueError("duplicate")
        if sum(x.status == "PENDING" for x in self.records.values()) >= self.max_pending:
            raise OverflowError("pending budget")
        before = self.records
        self.records = {**before, r.id: replace(r)}
        try:
            self.save()
        except Exception:
            self.records = before
            raise

    def resolve(self, id, *, at, observed, evidence="", observation_complete=False, cancelled=False):
        r = self.records[id]
        if r.status != "PENDING" or at < r.opened_at: raise ValueError("state/time")
        if not cancelled and not observed and at < r.deadline:
            # An incomplete early observation is not a terminal outcome.
            return asdict(r)
        next_r = replace(r)
        if cancelled:
            next_r.status = "CANCELLED"
        elif observed:
            if not evidence: raise ValueError("outcome evidence")
            next_r.status = "OBSERVED" if at <= r.deadline else "DELAYED"
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
        if r.error is None: return None
        return {"source": r.source, "evidence": r.evidence, "owner": r.owner,
                "prediction_error": r.error, "target": "WORLD_TEMPORAL",
                "requires_optimizer_permission": True}
