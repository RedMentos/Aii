"""Owner-consented, outbound-only V13 observation and remote-test policy.

One private GitHub issue is updated in place, never a stream of issues. State
survives a restarted phone relay; no arbitrary shell, file browsing, source
change, weight edit, raw user prompts, authentication secrets or local paths.
The owner's separately authorized chat-test commands remain bounded in
remote_chat.py. All three consent toggles default OFF.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
import tempfile
import threading
import time


ROOT = Path.home() / ".v13-private"
SETTINGS = ROOT / "remote-observation-consent.json"
STATE = ROOT / "remote-observation-state.json"
SCHEMA = "v13.remote-observation/1"
REPORT_SCHEMA = "v13.remote-observation-report/1"
OPTIONS = ("observe", "remote_tests", "include_console")
INTERVAL = 900
_LOCK = threading.RLock()


def _root():
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    st = ROOT.lstat()
    if ROOT.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("private V13 consent directory is unsafe")


def _read(path):
    if path.is_symlink():
        raise RuntimeError("unsafe V13 observation state symlink")
    if not path.is_file():
        return {}
    st = path.stat()
    if st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_size > 8192:
        raise RuntimeError("unsafe V13 observation state")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("invalid V13 observation state")
    return obj


def _save(path, obj):
    _root()
    if path.is_symlink():
        raise RuntimeError("unsafe observation state path")
    fd, name = tempfile.mkstemp(prefix=".v13-observe-", dir=str(ROOT))
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as output:
            json.dump(obj,output,sort_keys=True,ensure_ascii=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def consent():
    with _LOCK:
        data = _read(SETTINGS)
        if data and (data.get("schema") != SCHEMA or
                     any(type(data.get(k)) is not bool for k in OPTIONS) or
                     set(data) != {"schema", *OPTIONS}):
            raise ValueError("invalid observation consent schema")
        return {key: data.get(key, False) for key in OPTIONS}


def set_consent(key, value):
    if key not in OPTIONS or type(value) is not bool:
        raise ValueError("unknown consent toggle")
    with _LOCK:
        _root()
        try:
            settings = consent()
        except ValueError:
            # An explicit owner toggle may recover a syntactically corrupt,
            # still owner-only settings file. Recovery starts from ALL OFF,
            # never from a guessed previous remote permission.
            settings = {field:False for field in OPTIONS}
        settings[key] = value
        # The console switch is independently effective only when observe is ON.
        _save(SETTINGS,{"schema":SCHEMA, **settings})
        if consent()[key] != value:
            raise RuntimeError("observation consent not persisted")
        return settings


def permits(command):
    """Checks both locally persisted consent and the relay's own author/command permissions."""
    tests = {"CHAT_SEND","CHAT_RESULT","CHAT_OPERATOR"}
    if command not in tests:
        return True
    try:
        return consent()["remote_tests"]
    except (OSError, ValueError, RuntimeError):
        return False


def status(*, now=None):
    clock = int(time.time() if now is None else now)
    try:
        c = consent()
    except (ValueError, RuntimeError):
        c = {field:False for field in OPTIONS}
    try:
        state = _read(STATE)
    except (OSError, ValueError, RuntimeError):
        state = {}
    last_poll = state.get("last_poll",0)
    last_upload = state.get("last_upload",0)
    if type(last_poll) is not int or last_poll < 0 or last_poll > clock + 90:
        last_poll = 0
    if type(last_upload) is not int or last_upload < 0 or last_upload > clock + 90:
        last_upload = 0
    result = state.get("last_result")
    if result not in {"NEVER","PUBLISHED","NOT_DUE","FAILED","DISABLED"}:
        result = "NEVER"
    return {
        "schema":SCHEMA, **c,
        "relay_recently_polled": bool(last_poll and clock-last_poll <= 300),
        "last_poll_utc":last_poll,
        "last_upload_utc":last_upload,
        "last_result":result,
    }


def heartbeat(*, now=None):
    """Observed actual successful GitHub relay polling, not a UI/browser liveness claim."""
    clock=int(time.time() if now is None else now)
    with _LOCK:
        _root()
        data = _read(STATE)
        if clock-int(data.get("last_poll",0)) < 90:
            return False
        data["last_poll"] = clock
        _save(STATE,data)
        return True


def report():
    """Fixed shape of bounded, private technical metadata, no V13 chat content."""
    from .pipeline_agent import snapshot
    from .mobile_dashboard import summary
    from .phone_offer_delivery_audit import connect_readonly, audit
    data = {"schema":REPORT_SCHEMA,"pipeline":snapshot(),"device":summary(),
            "body_delivery":{"status":"UNAVAILABLE"}}
    try:
        with connect_readonly(Path.home() / "v13") as conn:
            details = audit(conn,5)
        data["body_delivery"]={
            "status":"LOCAL_METADATA_ONLY",
            "turn_count":details["turn_count"],
            "roles":details["roles"],
            "turns":details["turns"][:3],
        }
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        pass
    # Explicit, separate opt-in to sharing a bounded saved console excerpt.
    c = consent()
    if c["observe"] and c["include_console"]:
        from .mobile_dashboard import remote_full_console
        data["console_excerpt"] = remote_full_console()
    return data


def note_failure(*, now=None):
    """Retain an honest local outcome without exporting exception text."""
    with _LOCK:
        try:
            state = _read(STATE)
            state.update(last_result="FAILED",
                         last_failure=int(time.time() if now is None else now))
            _save(STATE,state)
        except (OSError, ValueError, RuntimeError):
            pass


def publish_once(client, cfg, *, now=None):
    """15-minute bounded status update to ONE private relay issue.

    Reuses its remote issue ID across restarts. No GitHub access whatsoever
    unless the owner actively enabled observation. Errors leave the marker
    unchanged so the next poll can retry.
    """
    clock=int(time.time() if now is None else now)
    with _LOCK:
        if not consent()["observe"]:
            return {"status":"DISABLED"}
        _root()
        state = _read(STATE)
        last = state.get("last_upload",0)
        if type(last) is int and 0 <= clock-last < INTERVAL:
            return {"status":"NOT_DUE"}
        client.check_private()
        repo = cfg["relay_repo"]
        if repo != getattr(client,"repository",repo):
            raise ValueError("observation relay repository mismatch")
        body = json.dumps(report(),ensure_ascii=True,sort_keys=True)
        if len(body.encode("utf-8")) > 16000:
            raise ValueError("observation exceeds bound")
        number = state.get("issue_number")
        if type(number) is int and 0 < number < 1_000_000_000:
            client.request("PATCH","/repos/"+repo+"/issues/"+str(number),
                           {"body":body})
        else:
            result=client.request("POST","/repos/"+repo+"/issues",
                                  {"title":"V13OBS: Live-Gerätestatus (nur privat)",
                                   "body":body})
            number=result.get("number") if isinstance(result,dict) else None
            if type(number) is not int or not 0 < number < 1_000_000_000:
                raise ValueError("private observation issue not acknowledged")
        state.update(last_upload=clock,last_result="PUBLISHED",issue_number=number)
        _save(STATE,state)
        return {"status":"PUBLISHED","issue_number":number}
