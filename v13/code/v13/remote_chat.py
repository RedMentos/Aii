"""Bounded owner-authorized private GitHub ↔ running V13 chat session.

Only the actual V13 daemon gets normal user messages. Never arbitrary
Termux shell, arbitrary file paths or model-generated tool calls. The owner
requested remote chat visibility; both text and reply live in a PRIVATE repo.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time

from . import chat_service

ROOT = Path.home() / ".v13-private"
JOBS = ROOT / "remote-chat-jobs"
LOGS = ROOT / "console-logs"
ID = re.compile(r"[a-f0-9]{32}\Z")
SESSION = re.compile(r"v13-session-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}\.log\Z")
MAX_TEXT_BYTES = 1400
MAX_READ_BYTES = 9000
SAFE_OPERATOR_COMMANDS = frozenset({
    ":status", ":help", ":doctor", ":models", ":gates summary", ":objectives",
    ":sleep status", ":learning status", ":notaus status",
    ":probe jef-modes", ":probe step12",
    ":scheduler lab summary", ":scheduler lab now"
})
JOB_TTL_SECONDS = 21600
TOKEN_PATTERN = re.compile(r"(?:gh[pousr]_[a-zA-Z0-9_]{10,}|github_pat_[a-zA-Z0-9_]{10,})")


class ChatDenied(ValueError):
    pass


def _dir():
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ROOT.is_symlink() or ROOT.stat().st_uid != os.getuid() or ROOT.stat().st_mode & 0o077:
        raise ChatDenied("unsafe private chat root")
    JOBS.mkdir(mode=0o700, parents=True, exist_ok=True)
    if JOBS.is_symlink() or JOBS.stat().st_uid != os.getuid() or JOBS.stat().st_mode & 0o077:
        raise ChatDenied("unsafe private chat jobs")


def _path(ident):
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ChatDenied("invalid remote chat request ID")
    return JOBS / (ident + ".json")


def _get(ident):
    name = _path(ident)
    if name.is_symlink() or not name.is_file() or name.stat().st_size > 1200:
        return None
    if name.stat().st_mode & 0o077:
        raise ChatDenied("unsafe chat job permissions")
    value = json.loads(name.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("id") != ident:
        raise ChatDenied("invalid chat job")
    return value


def _write(ident, record):
    _dir()
    name = _path(ident)
    if name.exists() or name.is_symlink():
        raise ChatDenied("duplicate chat request")
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as writer:
        json.dump(record, writer, sort_keys=True)
        writer.flush()
        os.fsync(writer.fileno())


def _update(ident, record):
    """Persist the send outcome without ever removing its single-use marker."""
    name = _path(ident)
    if name.is_symlink() or not name.is_file():
        raise ChatDenied("unsafe chat job update")
    fd, temporary = tempfile.mkstemp(prefix=".chat-job-", dir=JOBS)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            os.fchmod(writer.fileno(), 0o600)
            json.dump(record, writer, sort_keys=True)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, name)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _logfile(session):
    if not isinstance(session, str) or not SESSION.fullmatch(session):
        raise ChatDenied("unrecognized V13 session")
    p = LOGS / session
    if p.is_symlink() or not p.is_file() or p.stat().st_uid != os.getuid():
        raise ChatDenied("V13 chat session unavailable")
    return p


def _safe_output(s):
    # Display V13 response only, never its user's already included text.
    s = TOKEN_PATTERN.sub("[TOKEN_REDACTED]", s)
    return "".join(ch for ch in s if ch in "\n\t" or ord(ch) >= 32)


def send(ident, text, *, operator=False):
    """Queue normal text, or an exact allowlisted diagnostic operator query."""
    _dir()
    if (not isinstance(text, str) or not text.strip() or
            len(text.encode("utf-8")) > MAX_TEXT_BYTES or
            any(ch in text for ch in ("\x00", "\n", "\r"))):
        raise ChatDenied("invalid bounded chat message")
    # Operator commands can modify state or invoke future tools. Remote
    # operator access is therefore a separate exact diagnostic allowlist.
    if operator:
        if text.strip() not in SAFE_OPERATOR_COMMANDS:
            raise ChatDenied("operator command not in diagnostic allowlist")
    elif text.strip().startswith(":"):
        raise ChatDenied("operator commands require a separate approved scope")
    p = _path(ident)
    if p.exists() or p.is_symlink():
        raise ChatDenied("repeated chat request")
    state = chat_service.call("state")
    if state.get("running") is not True:
        return {"status": "NOT_RUNNING", "request_id": ident}
    # Persist a single-use marker BEFORE submitting. A replay or crash is
    # never permitted to send the same message twice.
    record = {"id": ident, "created": int(time.time()), "state": "RESERVED",
              "operator":operator,
              "input_digest":hashlib.sha256(text.strip().encode("utf-8")).hexdigest()}
    _write(ident, record)
    try:
        response = chat_service.call("send", line=text)
    except (OSError, RuntimeError, ValueError, TimeoutError):
        # The daemon may have accepted it before the connection failed. A
        # later unrelated chat must not be attributed to this reservation.
        record["state"] = "SEND_UNCONFIRMED"
        _update(ident, record)
        return {"status": "SEND_UNCONFIRMED", "request_id": ident}
    if response.get("status") != "SENT":
        record["state"] = "REJECTED"
        _update(ident, record)
        return {"status": "REJECTED", "request_id": ident}
    session, offset = response.get("session"), response.get("offset")
    if (response.get("input_logged") is not True or
            not isinstance(session, str) or not SESSION.fullmatch(session) or
            type(offset) is not int or offset < 0):
        # An older daemon can still send, but its status-only reply has no
        # reliable output binding. Never fall back to the earlier snapshot.
        record["state"] = "CORRELATION_UNAVAILABLE"
        _update(ident, record)
        return {"status": "CORRELATION_UNAVAILABLE", "request_id": ident}
    record.update(state="SENT", session=session, offset=offset)
    _update(ident, record)
    return {"status": "SENT", "request_id": ident,
            "response": "Use CHAT_RESULT to retrieve actual model output."}


def result(ident):
    _dir()
    item = _get(ident)
    if not item:
        return {"status": "NO_SUCH_REQUEST"}
    age = int(time.time()) - int(item.get("created", 0))
    if age < 0 or age > JOB_TTL_SECONDS:
        return {"status": "EXPIRED"}
    state = item.get("state")
    if state != "SENT":
        # RESERVED also covers a process crash before the receipt was saved.
        status = (state if state in {"REJECTED", "SEND_UNCONFIRMED",
                                     "CORRELATION_UNAVAILABLE"} else "SEND_UNCONFIRMED")
        return {"status":status, "request_id":ident, "complete":False}
    p = _logfile(item.get("session"))
    offset = item.get("offset")
    if type(offset) is not int or offset < 0:
        raise ChatDenied("invalid remote chat byte offset")
    length = p.stat().st_size - offset
    if length < 0:
        return {"status": "SESSION_ROTATED"}
    if length == 0:
        return {"status": "WAITING"}
    with p.open("rb") as file:
        file.seek(offset)
        data = file.read(MAX_READ_BYTES + 1)
    text = data.decode("utf-8", "replace")
    # Skip echo of submitted prompt. Do not include subsequent turns.
    lines = text.splitlines()
    output = []
    got_input = False
    end = False
    for line in lines:
        if line.startswith("[du> "):
            if got_input:
                end = True
                break
            if (not line.endswith("]") or
                    hashlib.sha256(line[5:-1].encode("utf-8")).hexdigest() != item.get("input_digest")):
                return {"status":"CORRELATION_UNAVAILABLE", "request_id":ident,
                        "complete":False}
            got_input = True
            continue
        if line.strip() == "du>":
            # The Termux prompt appears immediately after the input was
            # QUEUED, *before* V13 asynchronously generates its answer.
            # It does not signal completion. Never truncate the answer here.
            continue
        if got_input:
            output.append(line)
    from .phone_monitor import classify_output, SYSTEM_REPORT
    chat, error = classify_output(output)
    visible = _safe_output("\n".join(output).strip())[-4000:]
    correlation = {"correlation":"ATOMIC_INPUT_WINDOW", "complete":False}
    if chat == "CHAT_ERROR":
        # Runtime diagnostics quote exact user sources and prior corrections.
        # A failed native turn exports only its technical enum here.
        if SYSTEM_REPORT in "\n".join(output):
            visible = ""
        return {"status": "MODEL_ERROR", "request_id": ident,
                "output": visible, "error_code":error, **correlation}
    if end:
        # The plain UI queues another input before the earlier turn finishes.
        # A subsequent echo is neither completion nor a trustworthy boundary
        # for assigning asynchronously arriving assistant output.
        return {"status":"AMBIGUOUS_TURN", "request_id":ident, **correlation}
    if len(data) > MAX_READ_BYTES:
        return {"status": "TRUNCATED", "request_id": ident,
                "output": visible, **correlation}
    if chat == "CHAT_RESPONDED" and not item.get("operator"):
        # This proves only text is visible in the input's atomic log window;
        # the frozen plain UI supplies no final status or runtime turn ID.
        return {"status": "ANSWER_VISIBLE", "request_id": ident,
                "output": visible, **correlation}
    return {"status": "GENERATING", "request_id": ident,
            "output": visible, **correlation}
