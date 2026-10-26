"""Lossless local chat export, independent of the bounded model context window.

The export is a user-requested backup, never an automatic upload. Messages
are read in small id-ordered pages up to the high-water mark observed when
the command begins. The completed file replaces the prior export atomically.
"""
import contextlib
import hashlib
import os
from pathlib import Path
import re
import tempfile

from .common import dumps

PAGE_SIZE = 256
SAFE_SESSION = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def _filename(session, fmt):
    if not isinstance(session, str) or not session:
        raise ValueError("Invalid chat session")
    # Legacy/imported session IDs can be arbitrary database text. They must
    # never become relative paths, separators, or control characters.
    name = session if SAFE_SESSION.fullmatch(session) else (
        "chat-" + hashlib.sha256(session.encode("utf-8")).hexdigest()[:32])
    return name + "." + fmt


def export_chat(store, session, fmt="json", page_size=PAGE_SIZE):
    """Return local export path; no truncation, model call, or network effect."""
    if fmt not in ("json", "md"):
        raise ValueError("Export format: json|md")
    if type(page_size) is not int or not 1 <= page_size <= 4096:
        raise ValueError("Invalid export page size")
    if not store.one("SELECT id FROM sessions WHERE id=?", (session,)):
        raise ValueError("Chat-ID unbekannt")

    bound = store.one(
        "SELECT COALESCE(MAX(id),0) AS high FROM messages WHERE session_id=?",
        (session,))["high"]
    target = Path(store.home) / "exports" / _filename(session, fmt)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending-chat-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
            cursor = 0
            first = True
            if fmt == "json":
                out.write("[")
            while True:
                rows = store.rows(
                    "SELECT * FROM messages WHERE session_id=? AND id>? "
                    "AND id<=? ORDER BY id LIMIT ?",
                    (session, cursor, bound, page_size))
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
        os.replace(tmp, target)
        with contextlib.suppress(OSError):
            d = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(d)
            finally:
                os.close(d)
        return str(target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
