"""Bounded owner-authorized private GitHub ↔ running V13 chat session.

Only the actual V13 daemon gets normal user messages. Never arbitrary
Termux shell, arbitrary file paths or model-generated tool calls. The owner
requested remote chat visibility; both text and reply live in a PRIVATE repo.
"""
from __future__ import annotations

import hashlib
import json
import math
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
# The only parameterized remote operator is a one-shot native receiver probe.
# Exact role allowlists plus --last-source and --confirm prevent shell/flag injection.
NATIVE_RECEIVER_PROBE_COMMAND = re.compile(
    r":callosum native-probe (B1_DETAIL|B2_GIST) "
    r"(B1_DETAIL|B2_GIST|C3_LANGUAGE) --last-source --confirm",
    re.ASCII,
)


def is_safe_operator_command(command):
    """Accept fixed diagnostics or the exact owner-confirmed native probe form."""
    if not isinstance(command, str) or command != command.strip():
        return False
    if command in SAFE_OPERATOR_COMMANDS:
        return True
    match = NATIVE_RECEIVER_PROBE_COMMAND.fullmatch(command)
    return bool(match and match.group(1) != match.group(2))



def _native_receiver_probe_summary(lines, sender, receiver):
    """Return only bounded, source-free fields from one completed native probe."""
    from .phone_monitor import ANSWER_PREFIXES
    cleaned = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        for prefix in ANSWER_PREFIXES:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
                break
        cleaned.append(value)
    try:
        value = json.loads("\n".join(cleaned))
    except (TypeError, ValueError):
        return None
    if (not isinstance(value, dict) or value.get("completed") is not True
            or value.get("queued") is not False
            or value.get("requires_explicit_confirmation") is not True
            or value.get("sender_role") != sender
            or value.get("receiver_role") != receiver):
        return None
    if (value.get("production_route") is not False
            or value.get("semantic_use_proven") is not False
            or type(value.get("training_authority")) is not int
            or value["training_authority"] != 0
            or type(value.get("native_receiver_authority")) is not int
            or value["native_receiver_authority"] != 0):
        return None
    try:
        from .native_latent_receiver import EFFECT_EPSILON, PINNED_LLAMA_REVISION, POSITION_MODE
    except (ImportError, AttributeError):
        return None
    if value.get("runner_revision") != PINNED_LLAMA_REVISION:
        return None
    if value.get("position_mode") != POSITION_MODE:
        return None
    if value.get("status") not in {
            "NATIVE_INPUT_EFFECT", "NATIVE_DECODE_NO_EFFECT", "DIMENSION_MISMATCH"}:
        return None
    for key in ("sender_model_sha256", "receiver_model_sha256", "input_sha256"):
        digest = value.get(key)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return None
    for key in ("sender_model_revision", "receiver_model_revision", "sender_tap_id", "llama_version"):
        item = value.get(key)
        if not isinstance(item, str) or not item or len(item) > 128:
            return None
    tokenizer_revision = value.get("tokenizer_revision")
    if tokenizer_revision is not None and (
            not isinstance(tokenizer_revision, str) or not tokenizer_revision or len(tokenizer_revision) > 128):
        return None
    rows, dim = value.get("input_rows"), value.get("input_dim")
    receiver_dim, output_dim = value.get("receiver_input_dim"), value.get("output_dim")
    decode_status = value.get("decode_status")
    if (type(rows) is not int or not 1 <= rows <= 64
            or type(dim) is not int or not 1 <= dim <= 8192
            or type(receiver_dim) is not int or not 1 <= receiver_dim <= 8192
            or type(output_dim) is not int or not 1 <= output_dim <= 8192
            or type(decode_status) is not int):
        return None
    positions = value.get("position_ids")
    if (not isinstance(positions, list) or len(positions) != rows
            or any(type(pos) is not int for pos in positions)
            or positions != list(range(rows))):
        return None
    if type(value.get("native_input_consumed")) is not bool or type(value.get("input_effect_detected")) is not bool:
        return None
    if type(value.get("row_shuffle_control_applicable")) is not bool:
        return None
    def finite_number(item, *, cosine=False):
        return (isinstance(item, (int, float)) and not isinstance(item, bool)
                and math.isfinite(float(item))
                and (not cosine or -1.00001 <= float(item) <= 1.00001))
    for key in ("output_norm", "input_effect_rms"):
        if not finite_number(value.get(key)) or float(value[key]) < 0:
            return None
    for key in ("zero_control_cosine", "shuffle_control_cosine",
                "row_shuffle_control_cosine", "repeat_cosine"):
        item = value.get(key)
        if item is not None and not finite_number(item, cosine=True):
            return None
    status = value["status"]
    if status == "DIMENSION_MISMATCH":
        if (receiver_dim == dim or decode_status != -100
                or value["row_shuffle_control_applicable"]
                or value.get("row_shuffle_control_cosine") is not None):
            return None
    else:
        if rows >= 2:
            if value["row_shuffle_control_applicable"] is not True:
                return None
        elif (value["row_shuffle_control_applicable"] is not False
                or value.get("row_shuffle_control_cosine") is not None):
            return None
    consumed, effect = value["native_input_consumed"], value["input_effect_detected"]
    effect_rms = float(value["input_effect_rms"])
    if status == "DIMENSION_MISMATCH":
        if consumed or effect:
            return None
    elif (receiver_dim != dim or decode_status != 0 or not consumed
          or effect != (status == "NATIVE_INPUT_EFFECT")
          or (effect and effect_rms <= EFFECT_EPSILON)
          or (not effect and effect_rms > EFFECT_EPSILON)):
        return None
    # Never forward source_ref, event/session IDs, tap packet IDs, input hashes,
    # raw position arrays, vectors, prompts, or arbitrary command output.
    return {
        "sender_role": sender,
        "receiver_role": receiver,
        "sender_model_revision": value["sender_model_revision"],
        "sender_model_sha256": value["sender_model_sha256"],
        "sender_tap_id": value["sender_tap_id"],
        "tokenizer_revision": tokenizer_revision,
        "receiver_model_revision": value["receiver_model_revision"],
        "receiver_model_sha256": value["receiver_model_sha256"],
        "runner_revision": PINNED_LLAMA_REVISION,
        "llama_version": value["llama_version"],
        "input_rows": rows,
        "input_dim": dim,
        "position_count": len(positions),
        "position_mode": POSITION_MODE,
        "receiver_input_dim": receiver_dim,
        "output_dim": output_dim,
        "decode_status": decode_status,
        "output_norm": float(value["output_norm"]),
        "input_effect_rms": effect_rms,
        "zero_control_cosine": value.get("zero_control_cosine"),
        "shuffle_control_cosine": value.get("shuffle_control_cosine"),
        "row_shuffle_control_cosine": value.get("row_shuffle_control_cosine"),
        "row_shuffle_control_applicable": value["row_shuffle_control_applicable"],
        "repeat_cosine": value.get("repeat_cosine"),
        "native_input_consumed": consumed,
        "input_effect_detected": effect,
        "status": status,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


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
        if not is_safe_operator_command(text):
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
    input_text = None
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
            input_text = line[5:-1]
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
    if item.get("operator") and input_text:
        match = NATIVE_RECEIVER_PROBE_COMMAND.fullmatch(input_text)
        if match and chat == "CHAT_RESPONDED":
            summary = _native_receiver_probe_summary(output, match.group(1), match.group(2))
            if summary is None:
                return {"status": "OPERATOR_RESULT_INVALID", "request_id": ident,
                        "error_code": "INVALID_NATIVE_RECEIVER_RESULT",
                        "complete": False, **correlation}
            return {"status": "OPERATOR_RESULT_VISIBLE", "request_id": ident,
                    "operator": "NATIVE_RECEIVER_PROBE", "result": summary,
                    "command_complete": True, **correlation}
    if chat == "CHAT_RESPONDED" and not item.get("operator"):
        # This proves only text is visible in the input's atomic log window;
        # the frozen plain UI supplies no final status or runtime turn ID.
        return {"status": "ANSWER_VISIBLE", "request_id": ident,
                "output": visible, **correlation}
    return {"status": "GENERATING", "request_id": ident,
            "output": visible, **correlation}
