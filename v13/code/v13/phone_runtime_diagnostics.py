"""Fixed, read-only last-turn telemetry; never export chat or database rows."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import time

DATA_HOME = Path.home() / "v13"
MAX_METADATA_BYTES = 256 * 1024
READ_TIMEOUT_SECONDS = .15
READ_BUDGET_SECONDS = .3
MAX_VM_STEPS = 100_000
SCHEMA = "v13.phone-last-turn/1"
STATUSES = frozenset({"DRAFT", "OUTPUT_COMMITTED", "STREAMING", "FINAL",
                      "CANCELLED", "DEADLINE", "ERROR", "INTERRUPTED"})
STAGES = ("ingress", "policy_check", "perception_and_state", "memory_recall",
          "routing", "preanswer_observers", "focal_loop", "output_prepare",
          "native_answer", "finished")
ERROR_CLASSES = frozenset({"Limits", "Unavailable", "Cancelled", "TimeoutError",
                          "FileNotFoundError", "MemoryError", "PermissionError",
                          "ImportError", "ModuleNotFoundError", "OSError",
                          "RuntimeError", "ValueError", "TypeError", "KeyError",
                          "AttributeError", "OperationalError", "DatabaseError"})
CONFIG_BOUNDS = {
    "deadline_seconds": (0, 3600), "observer_seconds": (0, 3600),
    "control_seconds": (0, 3600), "retrieval_seconds": (0, 3600),
    "output_adapter_seconds": (0, 3600), "threads": (1, 128),
    "context_tokens": (1, 131072), "answer_tokens": (1, 16384),
    "observer_tokens": (1, 16384), "history_turns": (0, 256),
    "body_residency_mb": (0, 65536),
}
RUNNER_BOUNDS = {
    "duration_s": (0, 86400), "ttft_s": (0, 86400),
    "elapsed_in_last_phase_s": (0, 86400),
    "generated_tokens": (0, 10_000_000), "prompt_tokens": (0, 10_000_000),
    "requested_tokens": (0, 10_000_000), "input_message_count": (0, 65536),
}
RUNNER_STAGES = ("load_s", "template_s", "prefill_to_first_token_s", "stream_s")
ADMISSION_STATES = frozenset({"ADMITTED", "PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET"})
ADMISSION_OMISSIONS = frozenset({
    "C3_LAYER_TASK_CONTEXT", "C3_LAYER_DIGEST", "C3_LAYER_USER_MODEL",
    "OLD_NATIVE_HISTORY", "BODY_SOURCE_ADDRESS_METADATA",
    "BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS", "BODY_NON_SOURCE_STATE_DETAIL",
    "BODY_DUPLICATE_EXACT_DETAIL_WINDOWS",
})
# No text, session/event identifiers or source references are selected. The
# substr cap applies before metadata crosses the SQLite/Python boundary.
LAST_ASSISTANT_SQL = """SELECT substr(CAST(status AS BLOB),1,33),
    typeof(metadata), length(CAST(metadata AS BLOB)),
    substr(CAST(metadata AS BLOB),1,?) FROM messages
    WHERE role='assistant' ORDER BY id DESC LIMIT 1"""


def _unavailable(reason):
    return {"schema": SCHEMA, "availability": "UNAVAILABLE", "reason": reason}


def _numbers(source, bounds):
    if not isinstance(source, dict):
        return {}
    return {name: value for name, (low, high) in bounds.items()
            if type(value := source.get(name)) in (int, float)
            and low <= value <= high and math.isfinite(value)}


def _reject_constant(_):
    raise ValueError("nonfinite JSON")


def _project(status, metadata):
    out = {"schema": SCHEMA, "availability": "AVAILABLE", "status": status}
    error = metadata.get("error")
    if isinstance(error, str) and error in ERROR_CLASSES:
        out["error_class"] = error
    if status == "DEADLINE" or error == "TimeoutError":
        kind = "MODEL_TIMEOUT"
    elif status == "CANCELLED" or error == "Cancelled":
        kind = "CANCELLED"
    else:
        kind = {"FileNotFoundError": "MISSING_FILE", "MemoryError": "OUT_OF_MEMORY",
                "PermissionError": "PERMISSION", "ImportError": "IMPORT_ERROR",
                "ModuleNotFoundError": "IMPORT_ERROR", "Limits": "LIMIT_REACHED",
                "Unavailable": "MODEL_UNAVAILABLE"}.get(error if isinstance(error, str) else "")
        kind = kind or ("OTHER_EXCEPTION" if error or status in {"ERROR", "INTERRUPTED"} else "NONE")
    out["error_kind"] = kind
    for name in ("failure_stage", "turn_stage"):
        if metadata.get(name) in STAGES:
            out[name] = metadata[name]
    out.update(_numbers(metadata, {"duration_s": (0, 86400)}))
    out["stage_marks_s"] = _numbers(metadata.get("stage_marks_s"),
                                    {name: (0, 86400) for name in STAGES})
    out["effective_config"] = _numbers(metadata.get("effective_config"), CONFIG_BOUNDS)
    source = metadata.get("runner")
    if isinstance(source, dict):
        runner = _numbers(source, RUNNER_BOUNDS)
        if source.get("last_phase") in ("load", "template", "prefill", "stream"):
            runner["last_phase"] = source["last_phase"]
        if isinstance(source.get("status"), str) and source["status"] in STATUSES:
            runner["status"] = source["status"]
        runner["stage_durations_s"] = _numbers(source.get("stage_durations_s"),
                                               {name: (0, 86400) for name in RUNNER_STAGES})
        admission=source.get("prompt_admission")
        if isinstance(admission, dict) and admission.get("revision") == "v13.native-prompt-admission/1":
            native={"revision":"v13.native-prompt-admission/1"}
            if admission.get("status") in ADMISSION_STATES:
                native["status"]=admission["status"]
            native.update(_numbers(admission,{
                "target_tokens":(0,131072),
                "original_prompt_tokens":(0,10_000_000),
                "prompt_tokens":(0,10_000_000),
            }))
            raw_omissions=admission.get("removed_layers")
            if isinstance(raw_omissions,list):
                native["removed_layers"]=[x for x in raw_omissions[:12]
                    if type(x) is str and x in ADMISSION_OMISSIONS]
            if type(admission.get("source_text_rewritten")) is bool:
                native["source_text_rewritten"]=admission["source_text_rewritten"]
            runner["prompt_admission"]=native
        out["runner"] = runner
    return out


def _authorizer(action, arg1, arg2, database, source):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if (action == sqlite3.SQLITE_READ and database == "main" and source is None
            and arg1 == "messages" and arg2 in {"id", "role", "status", "metadata"}):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and arg2 in {"substr", "typeof", "length"}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def last_turn():
    """Read one bounded assistant metadata record from the fixed local store.

    Read-only SQLite participates in existing WAL shared-memory reader locks;
    it never updates database/WAL contents. No arbitrary path or SQL API exists.
    """
    path = DATA_HOME / "data/db/brain.sqlite3"
    try:
        for component in (DATA_HOME, DATA_HOME / "data", path.parent, path):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
                return _unavailable("UNSAFE_PATH")
        if not stat.S_ISREG(info.st_mode):
            return _unavailable("UNSAFE_PATH")
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = path.with_name(path.name + suffix)
            if sidecar.is_symlink():
                return _unavailable("UNSAFE_PATH")
        with path.open("rb") as source:
            header = source.read(20)
        if not header.startswith(b"SQLite format 3\x00") or len(header) != 20:
            return _unavailable("INVALID_DATABASE")
        # SQLite mode=ro can otherwise create missing WAL coordination files.
        # Fail explicitly instead of changing a stopped WAL-mode store.
        if header[18:20] == b"\x02\x02" and not all(
                path.with_name(path.name + suffix).is_file() for suffix in ("-wal", "-shm")):
            return _unavailable("WAL_COORDINATION_UNAVAILABLE")
    except FileNotFoundError:
        return _unavailable("DATABASE_MISSING")
    except PermissionError:
        return _unavailable("ACCESS_DENIED")
    except OSError:
        return _unavailable("DATABASE_UNREADABLE")

    deadline = time.monotonic() + READ_BUDGET_SECONDS
    steps = 0
    def progress():
        nonlocal steps
        steps += 1000
        return int(steps >= MAX_VM_STEPS or time.monotonic() >= deadline)
    connection = None
    try:
        connection = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True,
                                     timeout=READ_TIMEOUT_SECONDS, isolation_level=None)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.set_authorizer(_authorizer)
        connection.set_progress_handler(progress, 1000)
        row = connection.execute(LAST_ASSISTANT_SQL, (MAX_METADATA_BYTES + 1,)).fetchone()
    except sqlite3.Error as exc:
        code = getattr(exc, "sqlite_errorcode", 0) & 255
        reason = ("DATABASE_BUSY" if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                  else "READ_LIMIT" if code == sqlite3.SQLITE_INTERRUPT
                  else "INVALID_DATABASE")
        return _unavailable(reason)
    finally:
        if connection is not None:
            connection.close()
    if row is None:
        return _unavailable("NO_ASSISTANT_MESSAGES")
    raw_status, metadata_type, size, raw = row
    if metadata_type != "text" or size is None:
        return _unavailable("INVALID_METADATA")
    if size > MAX_METADATA_BYTES:
        return _unavailable("METADATA_TOO_LARGE")
    try:
        status = raw_status.decode("utf-8")
        if status not in STATUSES:
            return _unavailable("INVALID_STATUS")
        metadata = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
        if not isinstance(metadata, dict):
            return _unavailable("INVALID_METADATA")
        return _project(status, metadata)
    except (ValueError, UnicodeError, TypeError, AttributeError, RecursionError):
        return _unavailable("INVALID_METADATA")
