"""Privacy-safe autonomous V13 phone health checks for the owner's private relay.

This detects a failed *real local chat* from session logs and compares it with
the independently running AI process, without submitting fake chat prompts.
Only coarse enums and counts are sent to private GitHub; never user messages,
model text, traceback lines, blob hashes, absolute paths or secrets.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import time

PRIVATE = Path.home() / ".v13-private"
LOGS = PRIVATE / "console-logs"
REPORT = PRIVATE / "ai-health-status.json"
MAX_TAIL = 16 * 1024
KINDS = ("MISSING_FILE", "OUT_OF_MEMORY", "MODEL_TIMEOUT", "IMPORT_ERROR",
         "PERMISSION", "OTHER_EXCEPTION")
_STATUS = {"MODEL_RUNNING", "MODEL_STOPPED", "AI_OFFLINE", "NO_CHAT_YET",
           "CHAT_ERROR", "CHAT_PENDING", "CHAT_RESPONDED"}


def _error_kind(line):
    if re.search(r"\b(?:FileNotFoundError|No such file or directory|Errno 2)\b", line):
        return "MISSING_FILE"
    if re.search(r"\b(?:MemoryError|out of memory|ENOMEM|OOM)\b", line, re.I):
        return "OUT_OF_MEMORY"
    if re.search(r"\b(?:Zeitbudget erreicht|TimeoutError|deadline exceeded)\b", line, re.I):
        return "MODEL_TIMEOUT"
    if re.search(r"\b(?:ImportError|ModuleNotFoundError)\b", line):
        return "IMPORT_ERROR"
    if re.search(r"\b(?:PermissionError|Permission denied)\b", line):
        return "PERMISSION"
    return "OTHER_EXCEPTION"


def _latest_session():
    if LOGS.is_symlink() or not LOGS.is_dir():
        return None
    items = sorted((p for p in LOGS.glob("v13-session-*.log")
                    if p.is_file() and not p.is_symlink()
                    and p.stat().st_uid == os.getuid()),
                   key=lambda p: p.name, reverse=True)
    return items[0] if items else None


def check():
    """Read actual model process and most recent recorded turn; no model prompts."""
    result = {"schema":"v13.phone-health/1","checked_at":int(time.time()),
              "ai":"AI_OFFLINE","chat":"NO_CHAT_YET",
              "error":"NONE","failures":0,"recent_messages":0}
    try:
        from .chat_service import call
        state = call("state")
        result["ai"] = "MODEL_RUNNING" if state.get("running") is True else "MODEL_STOPPED"
    except (OSError, RuntimeError, ValueError, TimeoutError):
        pass
    path = _latest_session()
    if path is None:
        return result
    try:
        with path.open("rb") as fh:
            fh.seek(max(0,path.stat().st_size-MAX_TAIL))
            raw=fh.read(MAX_TAIL).decode("utf-8","replace")
    except (OSError,UnicodeError):
        return result
    # Captured input is enclosed in [du> ...]; never retain the contents.
    # Only count, not read or serialize user text.
    lines=raw.splitlines()
    latest=None
    message_count=0
    for line in lines:
        line=line.strip()
        if line.startswith("[du> "):
            message_count+=1
            latest="CHAT_PENDING"
            continue
        if latest is None:
            continue
        if line.startswith("[Fehler]") or line.startswith("[V13 Fehler]"):
            result["failures"]+=1
            result["error"]=_error_kind(line)
            latest="CHAT_ERROR"
        elif (line.startswith("[Antwort]") or line.startswith("[V13 Antwort]")
              or line.startswith("assistant>")):
            latest="CHAT_RESPONDED"
            result["error"]="NONE"
    result["recent_messages"]=min(message_count,100)
    if latest is not None:
        result["chat"]=latest
    if result["ai"]!="MODEL_RUNNING" and result["chat"]=="CHAT_PENDING":
        result["chat"]="CHAT_ERROR"
        result["error"]="OTHER_EXCEPTION"
    return result


def safe_incident(report):
    """Safe status-only incident, with no identifying run-path/hash/chat data."""
    if report["chat"]=="CHAT_ERROR":
        return {"schema":"v13.phone-incident/1","severity":"ERROR",
                "component":"CHAT","code":report["error"],
                "ai":report["ai"]}
    if report["ai"]=="AI_OFFLINE":
        return {"schema":"v13.phone-incident/1","severity":"ERROR",
                "component":"AI_DAEMON","code":"SERVICE_OFFLINE",
                "ai":"AI_OFFLINE"}
    if report["ai"]=="MODEL_STOPPED":
        return {"schema":"v13.phone-incident/1","severity":"WARNING",
                "component":"AI_RUNTIME","code":"MODEL_STOPPED",
                "ai":"MODEL_STOPPED"}
    return None


def persist_status(report):
    """Private local machine-readable health snapshot, no prompts or log text."""
    if REPORT.is_symlink():
        raise ValueError("unsafe monitor status symlink")
    PRIVATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077:
        raise ValueError("unsafe private monitor directory")
    from .common import atomic_write
    atomic_write(REPORT,json.dumps(report,sort_keys=True,separators=(",",":")))
    REPORT.chmod(0o600)
