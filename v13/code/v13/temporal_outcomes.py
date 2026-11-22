"""V14 temporal outcome ledger. Standard-library only; no automatic model updates.

The ledger distinguishes an absent observation from evidence of an absent outcome.
Only an explicitly trusted, coverage-complete outcome may yield a learning signal.
Callers must separately enforce capability and optimizer approval.
"""
import json
import math
import sqlite3
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS expectations (
  id TEXT PRIMARY KEY, source_ref TEXT NOT NULL, owner TEXT NOT NULL,
  expected TEXT NOT NULL, earliest REAL NOT NULL, deadline REAL NOT NULL,
  probability REAL NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
  outcome_ref TEXT, error REAL, updated_at REAL NOT NULL
)"""

class OutcomeLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.execute(SCHEMA)
        self.db.commit()

    def expect(self, *, event_id, source_ref, owner, expected, earliest, deadline, probability):
        if not all(isinstance(v, str) and v.strip() for v in (event_id, source_ref, owner, expected)):
            raise ValueError("Missing source-bound identity")
        if owner not in ("WORLD", "SELF", "ACTION", "B1", "B2"):
            raise ValueError("Invalid owner")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (earliest, deadline, probability)):
            raise ValueError("Nonfinite expectation")
        if not earliest <= deadline or not 0 <= probability <= 1:
            raise ValueError("Invalid expectation window or probability")
        with self.db:
            self.db.execute(
                "INSERT INTO expectations(id,source_ref,owner,expected,earliest,deadline,probability,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (event_id, source_ref, owner, expected, earliest, deadline, probability, earliest)
            )

    def resolve(self, event_id, *, now, observation_ref=None, observed=None,
                coverage_complete=False, trusted=False, cancelled=False):
        """observed=True/False means verified presence/absence; None means unknown.

        No omission signal without explicit trusted complete coverage after deadline.
        A negative observation before deadline remains pending. Cancelled/censored
        records never produce a training label.
        """
        if not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("Invalid clock")
        row = self.db.execute(
            "SELECT deadline,probability,status FROM expectations WHERE id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise KeyError(event_id)
        deadline, p, status = row
        if status != "PENDING":
            raise ValueError("Terminal expectation")
        if cancelled:
            state, error = "CANCELLED", None
        elif observed is True:
            if not (trusted and observation_ref):
                raise ValueError("Positive outcome requires trusted source")
            state, error = ("OBSERVED" if now <= deadline else "DELAYED"), 1.0 - p
        elif observed is False and now >= deadline and coverage_complete and trusted and observation_ref:
            state, error = "OMITTED", -p
        elif now >= deadline:
            state, error = "CENSORED", None
        else:
            return {"status": "PENDING", "error": None, "trainable": False}
        with self.db:
            self.db.execute(
                "UPDATE expectations SET status=?,outcome_ref=?,error=?,updated_at=? WHERE id=? AND status='PENDING'",
                (state, observation_ref if trusted else None, error, now, event_id)
            )
        return {"status": state, "error": error, "trainable": error is not None}

    def read(self, event_id):
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM expectations WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None

    def close(self):
        self.db.close()
