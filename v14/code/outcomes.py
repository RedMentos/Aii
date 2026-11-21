"""Persistent outcome/omission observation contract. No action authority or model mutation."""
import math
import sqlite3
import time
from dataclasses import dataclass

@dataclass(frozen=True)
class OutcomeError:
    expectation_id: str
    status: str
    error: float | None
    source_ref: str | None

class OutcomeTracker:
    def __init__(self, db_path, clock=None):
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS v14_expectations (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL, condition_ref TEXT NOT NULL,
          predicted TEXT NOT NULL, probability REAL NOT NULL, deadline REAL NOT NULL,
          status TEXT NOT NULL, outcome_ref TEXT, observed_at REAL)""")
        self.db.commit()
        self.clock = clock or time.time

    def expect(self, eid, owner, condition_ref, predicted, probability, deadline):
        if not all(isinstance(x, str) and 0 < len(x) <= 256 for x in (eid, owner, condition_ref, predicted)):
            raise ValueError("invalid provenance or identifier")
        if not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("invalid probability")
        now = self.clock()
        if not isinstance(deadline, (int, float)) or not math.isfinite(deadline) or not now < deadline <= now + 86400 * 30:
            raise ValueError("invalid finite deadline")
        with self.db:
            self.db.execute("INSERT INTO v14_expectations VALUES (?,?,?,?,?,?,?,NULL,NULL)",
                            (eid, owner, condition_ref, predicted, probability, deadline, "PENDING"))

    def settle(self, eid, *, observed=False, source_ref=None, window_complete=False, cancelled=False):
        now = self.clock()
        with self.db:
            row = self.db.execute("SELECT probability,deadline,status FROM v14_expectations WHERE id=?", (eid,)).fetchone()
            if row is None:
                raise KeyError(eid)
            p, deadline, status = row
            if status != "PENDING":
                return OutcomeError(eid, status, None, None)
            if cancelled:
                new, err = "CANCELLED", None
            elif observed:
                if not isinstance(source_ref, str) or not source_ref or len(source_ref) > 256:
                    raise ValueError("observation needs source reference")
                new, err = "OBSERVED", 1.0 - p
            elif now < deadline:
                return OutcomeError(eid, "PENDING", None, None)
            elif window_complete and isinstance(source_ref, str) and source_ref:
                new, err = "OMITTED", -p
            else:
                new, err = "CENSORED", None
            self.db.execute("UPDATE v14_expectations SET status=?,outcome_ref=?,observed_at=? WHERE id=?",
                            (new, source_ref, now, eid))
            return OutcomeError(eid, new, err, source_ref)

    def pending(self, limit=128):
        if type(limit) is not int or not 1 <= limit <= 1024:
            raise ValueError("invalid limit")
        return self.db.execute("SELECT id,deadline FROM v14_expectations WHERE status=? ORDER BY deadline LIMIT ?",
                               ("PENDING", limit)).fetchall()

    def close(self):
        self.db.close()
