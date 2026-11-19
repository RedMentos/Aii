"""V14 temporal outcome ledger: observed outcomes and censored omissions.

No reward is inferred merely because a deadline passed. An explicit trusted
observation-window closure is required before recording an omission.
This is a local learning-data organ, not a permission or model-weight authority.
"""
import json
import math
import sqlite3
import threading
import time
import uuid


class ExpectationError(ValueError):
    pass


class TemporalOutcomes:
    def __init__(self, path, *, clock=None):
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("PRAGMA busy_timeout=3000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS v14_expectations (
            id TEXT PRIMARY KEY, source_ref TEXT NOT NULL, owner TEXT NOT NULL,
            outcome TEXT NOT NULL, probability REAL NOT NULL,
            earliest REAL NOT NULL, deadline REAL NOT NULL,
            status TEXT NOT NULL, observed_at REAL, evidence TEXT,
            error REAL, created_at REAL NOT NULL)""")
        self.db.commit()

    def predict(self, *, source_ref, owner, outcome, probability, earliest, deadline):
        if not all(isinstance(x, str) and 0 < len(x) <= 256
                   for x in (source_ref, owner, outcome)):
            raise ExpectationError("source, owner and outcome required")
        if owner not in ("WORLD", "SELF", "ACTION", "B1", "B2"):
            raise ExpectationError("invalid owner")
        if not all(type(x) in (float, int) and math.isfinite(x)
                   for x in (probability, earliest, deadline)):
            raise ExpectationError("nonfinite expectation")
        if not (0 <= probability <= 1 and earliest <= deadline and deadline >= self.clock()):
            raise ExpectationError("invalid probability or time window")
        key = uuid.uuid4().hex
        with self.lock:
            self.db.execute("INSERT INTO v14_expectations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (key, source_ref, owner, outcome, float(probability),
                             float(earliest), float(deadline), "PENDING", None, None,
                             None, self.clock()))
            self.db.commit()
        return key

    def resolve(self, key, *, observed, evidence_ref, observation_complete=False, at=None):
        """Resolve only with positive evidence; no-evidence -> censored.

        observed=True requires evidence of the predicted outcome.
        observed=False + observation_complete=True requires evidence of
        continuous, authoritative monitoring of the expected outcome window.
        """
        if type(observed) is not bool or type(observation_complete) is not bool:
            raise ExpectationError("boolean flags required")
        if not isinstance(evidence_ref, str) or not (1 <= len(evidence_ref) <= 256):
            raise ExpectationError("source-bound evidence required")
        at = self.clock() if at is None else at
        if type(at) not in (float, int) or not math.isfinite(at):
            raise ExpectationError("invalid observation time")
        with self.lock:
            row = self.db.execute(
                "SELECT probability,earliest,deadline,status FROM v14_expectations WHERE id=?",
                (key,)).fetchone()
            if row is None:
                raise ExpectationError("unknown expectation")
            p, earliest, deadline, status = row
            if status != "PENDING":
                raise ExpectationError("expectation already resolved")
            if at < earliest:
                raise ExpectationError("outcome window not started")
            if observed:
                new_status = "OBSERVED" if at <= deadline else "DELAYED"
                error = 1.0 - p
            elif observation_complete and at >= deadline:
                new_status = "OMITTED"
                error = -p
            else:
                new_status = "CENSORED"
                error = None
            self.db.execute("""UPDATE v14_expectations
                SET status=?,observed_at=?,evidence=?,error=? WHERE id=? AND status='PENDING'""",
                (new_status, float(at), evidence_ref, error, key))
            self.db.commit()
            return {"id": key, "status": new_status, "prediction_error": error,
                    "evidence_ref": evidence_ref}

    def pending(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ExpectationError("invalid limit")
        with self.lock:
            rows = self.db.execute("""SELECT id,source_ref,owner,outcome,probability,
                earliest,deadline FROM v14_expectations WHERE status='PENDING'
                ORDER BY deadline,id LIMIT ?""", (limit,)).fetchall()
        return [dict(zip(("id","source_ref","owner","outcome","probability",
                          "earliest","deadline"), row)) for row in rows]

    def close(self):
        with self.lock:
            self.db.close()
