"""Durable local action-attempt journal for an injected Android companion transport.

This is a Termux-side audit boundary, NOT an Android permission or authentication
mechanism. A native companion must enforce grants, local approval and its own log.
An interrupted attempt remains UNKNOWN and must never be retried automatically.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .android_capability_contract import ActionRequest, ActionOutcome, OutcomeStatus
from .android_companion_dispatch import CompanionTransport


class AuditUnavailable(RuntimeError):
    pass


class DurableCompanionTransport:
    """Write a durable intent before invoking any external transport.

    Only one instance may own a journal file; callers must enforce a single
    process owner. Never store action target or typed text in the audit DB.
    """

    def __init__(self, path: str | Path, transport: CompanionTransport, verifier=None):
        self._transport = transport
        self._verifier = verifier
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""CREATE TABLE IF NOT EXISTS android_action_audit (
            request_id TEXT PRIMARY KEY, capability TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('IN_FLIGHT','REPORTED_SUCCESS','FAILED','UNKNOWN')),
            started_at REAL NOT NULL, finished_at REAL,
            receipt_present INTEGER NOT NULL DEFAULT 0
        )""")

    def execute(self, request: ActionRequest) -> ActionOutcome:
        if request.dry_run:
            raise PermissionError("dry-run must not reach companion transport")
        with self._lock:
            try:
                self._db.execute(
                    "INSERT INTO android_action_audit(request_id,capability,state,started_at) VALUES (?,?,?,?)",
                    (request.request_id, request.capability.value, "IN_FLIGHT", time.time()),
                )
            except sqlite3.Error as exc:
                raise AuditUnavailable("cannot durably reserve action") from exc
            # Holding the lock serializes external execution and avoids a second
            # in-process action overtaking an unresolved attempt.
            try:
                outcome = self._transport.execute(request)
            except BaseException:
                self._finish(request.request_id, "UNKNOWN", False)
                raise
            if not isinstance(outcome, ActionOutcome):
                self._finish(request.request_id, "UNKNOWN", False)
                raise ValueError("invalid companion outcome")
            # The transport's claimed SUCCESS is not evidence of execution.
            # Verify before recording any success-like terminal journal state.
            if outcome.status == OutcomeStatus.SUCCESS:
                try:
                    valid = (self._verifier is not None
                             and outcome.request_id == request.request_id
                             and outcome.capability == request.capability
                             and bool(outcome.companion_receipt)
                             and bool(self._verifier.verify(request, outcome)))
                except Exception:
                    valid = False
                if not valid:
                    self._finish(request.request_id, "FAILED", False)
                    return outcome  # Dispatcher independently rejects the forged receipt.
            state = ("REPORTED_SUCCESS" if outcome.status == OutcomeStatus.SUCCESS
                     else "FAILED" if outcome.status in (OutcomeStatus.DENIED, OutcomeStatus.FAILED, OutcomeStatus.CANCELLED)
                     else "UNKNOWN")
            self._finish(request.request_id, state, bool(outcome.companion_receipt))
            return outcome

    def _finish(self, request_id: str, state: str, receipt: bool) -> None:
        try:
            self._db.execute(
                "UPDATE android_action_audit SET state=?,finished_at=?,receipt_present=? WHERE request_id=?",
                (state, time.time(), int(receipt), request_id),
            )
        except sqlite3.Error as exc:
            raise AuditUnavailable("cannot persist terminal action outcome") from exc

    def attempts(self) -> tuple[dict, ...]:
        with self._lock:
            rows = self._db.execute(
                "SELECT request_id,capability,state,receipt_present FROM android_action_audit ORDER BY rowid"
            ).fetchall()
            return tuple(dict(zip(("request_id", "capability", "state", "receipt_present"), row)) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._db.close()


def build_audited_dispatcher(registry, path: str | Path, transport: CompanionTransport, verifier):
    """Opt-in wiring: dispatcher still requires independent receipt verification.

    Returns (dispatcher, journal); owner must close journal during shutdown.
    No native transport is created here, and no Android capability is enabled.
    """
    from .android_companion_dispatch import AndroidDispatcher

    if verifier is None:
        raise ValueError("authenticated native receipt verifier required")
    journal = DurableCompanionTransport(path, transport, verifier=verifier)
    return AndroidDispatcher(registry, transport=journal, verifier=verifier), journal
