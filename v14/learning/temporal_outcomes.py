"""V14 temporal outcome ledger with explicit success, mismatch and omission semantics.

This records source-bound prediction outcomes. It does not authenticate a producer
or grant optimizer permission; callers must provide those boundaries separately.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from contextlib import contextmanager
import fcntl
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
    def __init__(self, path, max_pending=512, max_records=4096):
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError("max_pending")
        if type(max_records) is not int or max_records < max_pending:
            raise ValueError("max_records")
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.max_pending = max_pending
        self.max_records = max_records
        self.records = {}
        self._refresh()

    @contextmanager
    def _locked(self, exclusive):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _load_unlocked(self):
        if not self.path.exists():
            self.records = {}
            return
        data = json.loads(self.path.read_text())
        if (data.get("schema") != 1 or not isinstance(data.get("records"), list)
                or len(data["records"]) > self.max_records):
            raise ValueError("schema")
        loaded = {x["id"]: Expectation(**x) for x in data["records"]}
        if len(loaded) != len(data["records"]):
            raise ValueError("duplicate persisted id")
        self.records = loaded

    def _refresh(self):
        with self._locked(False):
            self._load_unlocked()

    def _save_unlocked(self):
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".outcomes-")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"schema": 1, "records": [asdict(x) for x in self.records.values()]}, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
            dfd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def save(self):
        # Mutations are committed by expect/resolve. This only republishes the
        # latest locked state and cannot overwrite another instance's changes.
        with self._locked(True):
            self._load_unlocked()
            self._save_unlocked()

    def get(self, id):
        with self._locked(False):
            self._load_unlocked()
            record = self.records.get(id)
            return asdict(record) if record else None

    def count(self):
        with self._locked(False):
            self._load_unlocked()
            return len(self.records)

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
        with self._locked(True):
            self._load_unlocked()
            if r.id in self.records:
                raise ValueError("duplicate")
            if sum(x.status == "PENDING" for x in self.records.values()) >= self.max_pending:
                raise OverflowError("pending budget")
            before = self.records
            candidate = {**before, r.id: replace(r)}
            if len(candidate) > self.max_records:
                for old_id, old in list(candidate.items()):
                    if len(candidate) <= self.max_records:
                        break
                    if old.status != "PENDING" and old_id != r.id:
                        del candidate[old_id]
            if len(candidate) > self.max_records:
                raise OverflowError("record budget")
            self.records = candidate
            try:
                self._save_unlocked()
            except Exception:
                self.records = before
                raise

    def resolve(self, id, *, at, observed, evidence="", observed_outcome=None,
                observation_complete=False, cancelled=False, censored=False):
        _label(id, "id", 128)
        if type(at) not in (int, float) or not math.isfinite(at):
            raise ValueError("time")
        if (type(observed) is not bool or type(observation_complete) is not bool
                or type(cancelled) is not bool or type(censored) is not bool):
            raise ValueError("boolean fields")
        if type(evidence) is not str or len(evidence) > 512:
            raise ValueError("evidence")
        if observed_outcome is not None:
            _label(observed_outcome, "observed outcome", 128)
        with self._locked(True):
            self._load_unlocked()
            r = self.records[id]
            if r.status != "PENDING" or at < r.opened_at:
                raise ValueError("state/time")
            if cancelled and censored:
                raise ValueError("cancelled/censored conflict")
            if (cancelled or censored) and (observed or observation_complete or observed_outcome is not None):
                raise ValueError("non-observed outcome conflict")
            if censored and not evidence:
                raise ValueError("censored evidence required")
            if observed and (observed_outcome is None or not evidence):
                raise ValueError("observed outcome/evidence required")
            if not observed and observed_outcome is not None:
                raise ValueError("unexpected observed outcome")
            if not cancelled and not censored and not observed and at < r.deadline:
                return asdict(r)
            next_r = replace(r)
            if cancelled:
                next_r.status = "CANCELLED"
            elif censored:
                next_r.status = "CENSORED"
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
                self._save_unlocked()
            except Exception:
                self.records = before
                raise
            return asdict(next_r)

    def learning_intent(self, id):
        with self._locked(False):
            self._load_unlocked()
            r = self.records[id]
            if r.error is None:
                return None
            return {"source": r.source, "evidence": r.evidence, "owner": r.owner,
                    "expected_outcome": r.outcome, "observed_outcome": r.observed_outcome,
                    "prediction_error": r.error, "target": "WORLD_TEMPORAL",
                    "requires_optimizer_permission": True}
