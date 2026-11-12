"""Privacy-safe autonomous V13 phone health checks for the owner's private relay.

This detects a failed *real local chat* from session logs and compares it with
the independently running AI process, without submitting fake chat prompts.
Only coarse enums and counts are sent to private GitHub; never user messages,
model text, traceback lines, blob hashes, absolute paths or secrets.
"""
from __future__ import annotations
import hashlib
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
SYSTEM_REPORT = "[SOURCE_SYSTEM_REPORT"
ANSWER_PREFIXES = ("[Antwort]", "[V13 Antwort]", "assistant>", "model>")
ERROR_PREFIXES = ("[Fehler]", "[V13 Fehler]")
SESSION = re.compile(r"v13-session-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}\.log\Z")


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


def classify_output(lines):
    """Classify one captured turn without returning any of its private text.

    A runtime failure is also rendered with the assistant role. Its explicit
    source-system-report marker is diagnostic evidence, never a model answer.
    Error evidence wins over any other output in the same turn.
    """
    answer = []
    in_answer = False
    report_reason = None
    report_seen = False
    for line in lines:
        line = line.strip()
        if line.startswith(ERROR_PREFIXES):
            return "CHAT_ERROR", _error_kind(line)
        for prefix in ANSWER_PREFIXES:
            if line.startswith(prefix):
                line = line[len(prefix):].lstrip()
                in_answer = True
                break
        if in_answer and line.startswith(SYSTEM_REPORT):
            report_seen = True
            continue
        if report_seen and report_reason is None and line:
            report_reason = line
        if in_answer and line and line != "du>":
            if line.startswith(("[V13]", "[V13 exited", "[V13 local log", "[console capture error:")):
                continue
            answer.append(line)
    content = "\n".join(answer).strip()
    if report_seen:
        # Only the report's reason is an error source; quoted user messages
        # and recalled corrections below it cannot choose the incident code.
        return "CHAT_ERROR", _error_kind(report_reason or "")
    if content and not SYSTEM_REPORT.startswith(content):
        return "CHAT_RESPONDED", "NONE"
    return "CHAT_PENDING", "NONE"


def _latest_session(preferred=None):
    if LOGS.is_symlink() or not LOGS.is_dir():
        return None
    if isinstance(preferred,str) and SESSION.fullmatch(preferred):
        path=LOGS/preferred
        return (path if path.is_file() and not path.is_symlink()
                and path.stat().st_uid==os.getuid() else None)
    items = sorted((p for p in LOGS.glob("v13-session-*.log")
                    if p.is_file() and not p.is_symlink()
                    and p.stat().st_uid == os.getuid()),
                   key=lambda p: p.name, reverse=True)
    return items[0] if items else None


def check():
    """Read actual model process and most recent recorded turn; no model prompts."""
    result = {"schema":"v13.phone-health/1","checked_at":int(time.time()),
              "ai":"AI_OFFLINE","chat":"NO_CHAT_YET",
              "error":"NONE","failures":0,"recent_messages":0,
              "response_observation":None}
    session=None
    try:
        from .chat_service import call
        state = call("state")
        result["ai"] = "MODEL_RUNNING" if state.get("running") is True else "MODEL_STOPPED"
        session=state.get("last_session")
    except (OSError, RuntimeError, ValueError, TimeoutError):
        pass
    path = _latest_session(session)
    if path is None:
        return result
    try:
        with path.open("rb") as fh:
            start=max(0,path.stat().st_size-MAX_TAIL)
            inode=path.stat().st_ino
            fh.seek(start)
            raw=fh.read(MAX_TAIL)
    except (OSError,UnicodeError):
        return result
    # Captured input is enclosed in [du> ...]; never retain the contents.
    # Inspect only the operator-command prefix; never serialize user text.
    latest=None
    message_count=0
    output=[]
    turn_start=None
    active=False

    def finish():
        nonlocal latest
        if not active:
            return
        latest,error=classify_output(output)
        result["error"]=error
        if latest=="CHAT_ERROR":
            result["failures"]+=1
        elif latest=="CHAT_RESPONDED":
            # Opaque local checkpoint, not a prompt/model/blob hash. Alerts
            # never serialize it. The same old answer cannot recover an
            # offline incident just because the daemon became reachable.
            observation=f"{path.name}:{inode}:{turn_start}"
            result["response_observation"]=hashlib.sha256(observation.encode()).hexdigest()

    position=start
    for index,chunk in enumerate(raw.splitlines(keepends=True)):
        line=chunk.decode("utf-8","replace").strip()
        line_start=position
        position+=len(chunk)
        if start and index==0:
            # A tail beginning inside a line is never independent evidence.
            continue
        if line.startswith("[du> "):
            finish()
            output=[]
            active=not line[5:].lstrip().startswith(":")
            if not active:
                continue
            message_count+=1
            latest="CHAT_PENDING"
            result["error"]="NONE"
            turn_start=line_start
            continue
        if active:
            output.append(line)
    finish()
    result["recent_messages"]=min(message_count,100)
    if latest is not None:
        result["chat"]=latest
    if result["ai"]!="MODEL_RUNNING" and result["chat"]=="CHAT_PENDING":
        result["chat"]="CHAT_ERROR"
        result["error"]="OTHER_EXCEPTION"
    return result


def safe_incident(report):
    """Safe status-only incident, with no identifying run-path/hash/chat data."""
    ai=report.get("ai")
    if ai not in ("MODEL_RUNNING","MODEL_STOPPED","AI_OFFLINE"):
        ai="AI_OFFLINE"
    if report["chat"]=="CHAT_ERROR":
        error=report.get("error")
        if error not in KINDS:
            error="OTHER_EXCEPTION"
        return {"schema":"v13.phone-incident/1","severity":"ERROR",
                "component":"CHAT","code":error,"ai":ai}
    if ai=="AI_OFFLINE":
        return {"schema":"v13.phone-incident/1","severity":"ERROR",
                "component":"AI_DAEMON","code":"SERVICE_OFFLINE",
                "ai":"AI_OFFLINE"}
    if ai=="MODEL_STOPPED":
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
