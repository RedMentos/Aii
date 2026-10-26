"""Coherent, bounded-memory local chat export from a read-only WAL snapshot.

The independent SQLite read connection keeps a stable view while the runtime
writes on its own connection. The user-requested export is never uploaded.
"""
import contextlib
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from .common import dumps

PAGE_SIZE = 256
SAFE_SESSION = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def _filename(session, fmt):
    if not isinstance(session, str) or not session:
        raise ValueError("Invalid chat session")
    name = session if SAFE_SESSION.fullmatch(session) else (
        "chat-" + hashlib.sha256(session.encode("utf-8")).hexdigest()[:32])
    return name + "." + fmt


def _page(conn, session, cursor, bound, page_size):
    """One bounded page from the same read transaction, not Store's writer."""
    return [dict(row) for row in conn.execute(
        "SELECT * FROM messages WHERE session_id=? AND id>? "
        "AND id<=? ORDER BY id LIMIT ?",
        (session, cursor, bound, page_size))]


def export_chat(store, session, fmt="json", page_size=PAGE_SIZE):
    """Export one stable SQLite snapshot to a local, atomically replaced file."""
    if fmt not in ("json", "md"):
        raise ValueError("Export format: json|md")
    if type(page_size) is not int or not 1 <= page_size <= 4096:
        raise ValueError("Invalid export page size")
    name = _filename(session, fmt)
    db_path = (Path(store.home) / "data/db/brain.sqlite3").resolve()
    # A separate mode=ro connection is required: multiple SELECTs on Store's
    # writer connection do not form a snapshot when a turn updates rows.
    uri = db_path.as_uri() + "?mode=ro"
    target = Path(store.home) / "exports" / name
    tmp = None
    try:
        with contextlib.closing(sqlite3.connect(
                uri, uri=True, isolation_level=None, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            try:
                if not conn.execute("SELECT id FROM sessions WHERE id=?",
                                    (session,)).fetchone():
                    raise ValueError("Chat-ID unbekannt")
                bound = conn.execute(
                    "SELECT COALESCE(MAX(id),0) AS high FROM messages WHERE session_id=?",
                    (session,)).fetchone()["high"]
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(prefix=".pending-chat-", dir=target.parent)
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
                    cursor = 0
                    first = True
                    if fmt == "json":
                        out.write("[")
                    while True:
                        rows = _page(conn, session, cursor, bound, page_size)
                        if not rows:
                            break
                        for row in rows:
                            if not first:
                                out.write("," if fmt == "json" else "\n\n")
                            if fmt == "json":
                                out.write(dumps(row))
                            else:
                                out.write("**" + row["role"] + " · " + row["status"]
                                          + "**\n\n" + row["text"])
                            first = False
                            cursor = row["id"]
                    if fmt == "json":
                        out.write("]")
                    out.flush()
                    os.fsync(out.fileno())
            finally:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")  # release WAL read snapshot
        os.replace(tmp, target)
        with contextlib.suppress(OSError):
            d = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(d)
            finally:
                os.close(d)
        return str(target)
    finally:
        if tmp is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
