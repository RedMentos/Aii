"""Opt-in Android action outcome -> bounded, source-bound T8 episode inbox.

Only consumes an in-memory settled outcome plus a matching durable journal row.
It never grants Android permissions, trains models, or treats a receipt as proof
of an Android OS action. Caller must use the independently verified dispatcher.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = "v13.android_t8.verified_outcome_inbox.v1"


def ingest_verified_outcome(registry, journal, request_id: str, episode_db: str | Path):
    """Persist one SUCCESS as a source-bound T8 candidate, exactly once.

    Registry and journal must belong to the live audited dispatch session.
    This function cannot re-authenticate a companion after restart. Never pass
    a simulated transport as proof of native execution.
    """
    if type(request_id) is not str or not 1 <= len(request_id) <= 128:
        raise ValueError("invalid request id")
    outcome = registry.outcome_for(request_id)
    if outcome is None or getattr(getattr(outcome, "status", None), "value", None) != "SUCCESS":
        raise ValueError("no settled successful outcome")
    receipt = getattr(outcome, "companion_receipt", None)
    if type(receipt) is not str or not receipt:
        raise ValueError("missing verified receipt")
    matches = [r for r in journal.attempts() if r.get("request_id") == request_id]
    if (len(matches) != 1 or matches[0].get("state") != "REPORTED_SUCCESS"
            or matches[0].get("receipt_present") != 1
            or matches[0].get("capability") != outcome.capability.value):
        raise ValueError("no matching verified journal outcome")
    # No raw receipt, action target, user text, or screen content is retained.
    digest = hashlib.sha256(receipt.encode("utf-8")).hexdigest()
    record = {"schema": SCHEMA, "action_id": request_id,
              "capability": outcome.capability.value,
              "outcome": "SUCCESS", "receipt_sha256": digest,
              "source": "IN_SESSION_VERIFIED_COMPANION_RECEIPT",
              "training_authority": "SHADOW_ONLY", "android_device_verified": False}
    serialized = json.dumps(record, sort_keys=True, separators=(",", ":"))
    db = sqlite3.connect(str(episode_db))
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS android_t8_episode_inbox "
                   "(action_id TEXT PRIMARY KEY, episode_json TEXT NOT NULL, ingested_at REAL NOT NULL)")
        try:
            db.execute("INSERT INTO android_t8_episode_inbox VALUES (?,?,?)",
                       (request_id, serialized, time.time()))
            db.commit()
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise ValueError("duplicate episode") from exc
    finally:
        db.close()
    return record
