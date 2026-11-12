"""Persistent C3 text speech intents; not an audio renderer or Android permission grant."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import sqlite3
import threading
import time
import uuid

class SpeechIntentError(ValueError):
    pass

@dataclass(frozen=True)
class SpeechIntent:
    intent_id: str
    text: str
    source_id: str
    created_at: float
    status: str
    digest: str

class SpeechIntentQueue:
    """Bounded text-to-speech handoff; completion requires renderer acknowledgement."""
    def __init__(self, path, *, clock=None, max_pending=16):
        if type(max_pending) is not int or not 1 <= max_pending <= 128:
            raise ValueError("invalid capacity")
        self.clock = clock or time.time
        self.max_pending = max_pending
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS speech_intents (intent_id TEXT PRIMARY KEY, text TEXT NOT NULL, source_id TEXT NOT NULL, created_at REAL NOT NULL, status TEXT NOT NULL, digest TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS speech_events (id INTEGER PRIMARY KEY, intent_id TEXT, event TEXT NOT NULL, at REAL NOT NULL)")
        self.db.commit()

    def recover_uncertain(self):
        """Explicit cold-start recovery, only when no renderer process is active.

        Never invoke from a second live queue connection: it could invalidate
        an in-flight receipt and allow another process to start playback.
        The operator must first stop/confirm all renderer processes are gone.
        Uncertain speech is interrupted, never replayed automatically.
        """
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                ids = [row[0] for row in self.db.execute(
                    "SELECT intent_id FROM speech_intents WHERE status='RENDERING'"
                )]
                for intent_id in ids:
                    self.db.execute(
                        "UPDATE speech_intents SET status='INTERRUPTED' WHERE intent_id=? AND status='RENDERING'",
                        (intent_id,),
                    )
                    self._event(intent_id, "RECOVERED_UNCERTAIN")
                self.db.commit()
                return len(ids)
            except BaseException:
                self.db.rollback()
                raise

    def _event(self, intent_id, event):
        self.db.execute("INSERT INTO speech_events(intent_id,event,at) VALUES (?,?,?)", (intent_id, event, self.clock()))

    def submit(self, text, *, source_id):
        if not isinstance(text, str) or not 1 <= len(text) <= 2048 or any(ord(c) < 32 and c not in "\n\t" for c in text):
            raise SpeechIntentError("invalid text")
        if not isinstance(source_id, str) or not 1 <= len(source_id) <= 128 or not all(c.isascii() and (c.isalnum() or c in "-_:.") for c in source_id):
            raise SpeechIntentError("invalid source")
        with self.lock:
            count = self.db.execute("SELECT count(*) FROM speech_intents WHERE status IN ('QUEUED','RENDERING')").fetchone()[0]
            if count >= self.max_pending:
                raise SpeechIntentError("queue full")
            intent_id = uuid.uuid4().hex
            at = self.clock()
            digest = hashlib.sha256(json.dumps([text, source_id], ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
            self.db.execute("INSERT INTO speech_intents VALUES (?,?,?,?,?,?)", (intent_id, text, source_id, at, "QUEUED", digest))
            self._event(intent_id, "QUEUED")
            self.db.commit()
            return SpeechIntent(intent_id, text, source_id, at, "QUEUED", digest)

    def claim(self):
        with self.lock:
            # Serialize claim across independent Termux processes, not just
            # threads sharing this queue instance. The write lock is acquired
            # before checking for another active renderer.
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if self.db.execute("SELECT 1 FROM speech_intents WHERE status='RENDERING'").fetchone():
                    self.db.commit()
                    return None
                row = self.db.execute("SELECT intent_id,text,source_id,created_at,status,digest FROM speech_intents WHERE status='QUEUED' ORDER BY created_at,intent_id LIMIT 1").fetchone()
                if row is None:
                    self.db.commit()
                    return None
                self.db.execute("UPDATE speech_intents SET status='RENDERING' WHERE intent_id=? AND status='QUEUED'", (row[0],))
                self._event(row[0], "RENDERING")
                self.db.commit()
                return SpeechIntent(*row[:4], "RENDERING", row[5])
            except BaseException:
                self.db.rollback()
                raise

    def acknowledge(self, intent_id, *, digest, rendered=False):
        """Commit a trusted receipt atomically against concurrent stop/recovery.

        The Android companion still has to authenticate and verify the receipt;
        this SQLite transaction only protects the state transition.
        """
        if rendered is not True:
            raise SpeechIntentError("unverified renderer acknowledgement")
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                updated = self.db.execute(
                    "UPDATE speech_intents SET status='RENDERED' "
                    "WHERE intent_id=? AND digest=? AND status='RENDERING'",
                    (intent_id, digest),
                ).rowcount
                if updated != 1:
                    raise SpeechIntentError("unverified renderer acknowledgement")
                self._event(intent_id, "RENDERED")
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    def interrupt(self):
        """Atomically stop queued/active intents; companion must stop actual audio."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                ids = [r[0] for r in self.db.execute(
                    "SELECT intent_id FROM speech_intents "
                    "WHERE status IN ('QUEUED','RENDERING')"
                )]
                for intent_id in ids:
                    self.db.execute(
                        "UPDATE speech_intents SET status='INTERRUPTED' "
                        "WHERE intent_id=? AND status IN ('QUEUED','RENDERING')",
                        (intent_id,),
                    )
                    self._event(intent_id, "INTERRUPTED")
                self.db.commit()
                return len(ids)
            except BaseException:
                self.db.rollback()
                raise

    def interrupt_one(self, intent_id):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                updated = self.db.execute(
                    "UPDATE speech_intents SET status='INTERRUPTED' "
                    "WHERE intent_id=? AND status IN ('QUEUED','RENDERING')",
                    (intent_id,),
                ).rowcount
                if updated:
                    self._event(intent_id, "INTERRUPTED")
                self.db.commit()
                return updated == 1
            except BaseException:
                self.db.rollback()
                raise

    def status(self, intent_id):
        row = self.db.execute("SELECT status FROM speech_intents WHERE intent_id=?", (intent_id,)).fetchone()
        return row[0] if row else None

    def close(self):
        with self.lock:
            self.db.close()
