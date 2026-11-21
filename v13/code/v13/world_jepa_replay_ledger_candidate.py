"""Persistent G13 replay cursor bound to a verified WorldJEPA checkpoint.

This ledger is not a trainer or a substitute for the existing G13 authority.
Caller must first durably save the optimizer checkpoint, then commit its
receipt here; on restart the receipt must match the checkpoint bytes.
"""
import hashlib
from pathlib import Path
import sqlite3


class ReplayLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS replay_cursor (
            stream TEXT PRIMARY KEY, source_sha TEXT NOT NULL,
            cursor INTEGER NOT NULL CHECK(cursor >= 0),
            checkpoint_sha TEXT NOT NULL, revision INTEGER NOT NULL
        )""")

    def close(self):
        self.db.close()

    @staticmethod
    def digest(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def read(self, stream, source_sha, checkpoint_path):
        row = self.db.execute(
            "SELECT source_sha,cursor,checkpoint_sha,revision FROM replay_cursor WHERE stream=?",
            (stream,)).fetchone()
        if row is None:
            return None
        if row[0] != source_sha or not Path(checkpoint_path).is_file():
            raise ValueError("REPLAY_SOURCE_OR_CHECKPOINT_MISSING")
        if self.digest(checkpoint_path) != row[2]:
            raise ValueError("REPLAY_CHECKPOINT_MISMATCH")
        return {"cursor": row[1], "checkpoint_sha": row[2], "revision": row[3]}

    def commit(self, stream, source_sha, old_cursor, new_cursor, checkpoint_path, *, previous_checkpoint_path=None):
        if (not isinstance(stream, str) or not 1 <= len(stream) <= 96
                or not isinstance(source_sha, str) or len(source_sha) != 64
                or any(c not in "0123456789abcdef" for c in source_sha)
                or type(old_cursor) is not int or type(new_cursor) is not int
                or old_cursor < 0 or new_cursor <= old_cursor):
            raise ValueError("INVALID_REPLAY_ADVANCE")
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.is_file():
            raise ValueError("CHECKPOINT_REQUIRED_BEFORE_CURSOR")
        digest = self.digest(checkpoint_path)
        # A checkpoint is immutable once receipted. Never advance from a
        # overwritten/missing predecessor: a crash could otherwise skip T8 rows.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT source_sha,cursor,checkpoint_sha,revision FROM replay_cursor WHERE stream=?",
                (stream,)).fetchone()
            if row is None:
                if old_cursor != 0:
                    raise ValueError("CURSOR_INITIALIZATION_MISMATCH")
                if previous_checkpoint_path is not None:
                    raise ValueError("UNEXPECTED_PREVIOUS_CHECKPOINT")
                revision = 1
                self.db.execute(
                    "INSERT INTO replay_cursor VALUES (?,?,?,?,?)",
                    (stream, source_sha, new_cursor, digest, revision))
            else:
                if row[0] != source_sha or row[1] != old_cursor:
                    raise ValueError("CURSOR_CAS_OR_SOURCE_MISMATCH")
                if previous_checkpoint_path is None or not Path(previous_checkpoint_path).is_file():
                    raise ValueError("PREVIOUS_CHECKPOINT_REQUIRED")
                if self.digest(previous_checkpoint_path) != row[2]:
                    raise ValueError("PREVIOUS_CHECKPOINT_MISMATCH")
                if Path(previous_checkpoint_path).resolve() == checkpoint_path.resolve():
                    raise ValueError("CHECKPOINT_GENERATION_REQUIRED")
                revision = row[3] + 1
                self.db.execute(
                    "UPDATE replay_cursor SET cursor=?,checkpoint_sha=?,revision=? WHERE stream=?",
                    (new_cursor, digest, revision, stream))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return {"cursor": new_cursor, "checkpoint_sha": digest, "revision": revision}
