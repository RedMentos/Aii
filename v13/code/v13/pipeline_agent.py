"""V13 Redmi continuous GitHub -> CI -> phone source update -> private status loop.

This agent never executes issue text, GitHub-provided commands, arbitrary shell,
or model-generated actions. It ONLY fast-forwards the user's two preexisting,
pinned Git checkouts when the exact commit passed trusted V13 GitHub CI and
no V13 runtime is active. All updates are opt-in and crash-safe.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import time
import tempfile

from . import source_updater as updates

PRIVATE = Path.home() / ".v13-private"
ENABLED = PRIVATE / "auto-source-update.enabled"
STATE = PRIVATE / "pipeline-status.json"
LOCK = PRIVATE / "pipeline-status.lock"
UI_REFRESH = PRIVATE / "pipeline-ui-refresh"
BRIDGE_REFRESH = PRIVATE / "pipeline-bridge-refresh"
INTERVAL = 900
MAX_STATE_BYTES = 8192


def _private():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_uid != os.getuid() or PRIVATE.stat().st_mode & 0o077:
        raise RuntimeError("private pipeline directory is not owner-only")


def enabled():
    if ENABLED.is_symlink():
        return False
    try:
        return ENABLED.is_file() and ENABLED.read_text(encoding="ascii").strip() == "yes"
    except (OSError, UnicodeError):
        return False


def _atomic(path, value):
    _private()
    if path.is_symlink():
        raise RuntimeError("unsafe pipeline state symlink")
    fd, name = tempfile.mkstemp(prefix=".v13-pipeline-", dir=str(PRIVATE))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, sort_keys=True, ensure_ascii=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _state_raw():
    try:
        if STATE.is_symlink() or not STATE.is_file() or STATE.stat().st_size > MAX_STATE_BYTES:
            return {}
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def snapshot():
    """Only safe enums/short commit identifiers; no log, paths, user inputs."""
    data = _state_raw()
    result = {"schema": "v13.pipeline-status/1", "auto_enabled": enabled(),
              "last_check_utc": data.get("last_check_utc", 0),
              "last_success_utc": data.get("last_success_utc", 0),
              "last_result": data.get("last_result", "NOT_YET_RUN"),
              "runtime": data.get("runtime", "NOT_YET_CHECKED"),
              "dashboard": data.get("dashboard", "NOT_YET_CHECKED"),
              "last_error": data.get("last_error", "NONE"),
              "updated_commit": data.get("updated_commit", "")}
    if not isinstance(result["last_check_utc"], int):
        result["last_check_utc"] = 0
    if not isinstance(result["last_success_utc"], int):
        result["last_success_utc"] = 0
    allowed = {
        "last_result": {"NOT_YET_RUN", "AUTO_OFF", "UP_TO_DATE", "UPDATED", "CI_WAIT",
                        "BUSY", "BLOCKED_RUNNING", "PARTIAL", "ERROR", "CHECKING"},
        "runtime": {"NOT_YET_CHECKED", "UP_TO_DATE", "UPDATED", "CI_WAIT",
                    "BLOCKED_RUNNING", "NOT_INSTALLED", "ERROR"},
        "dashboard": {"NOT_YET_CHECKED", "UP_TO_DATE", "UPDATED", "CI_WAIT",
                      "BLOCKED_RUNNING", "NOT_INSTALLED", "ERROR"},
        "last_error": {"NONE", "GITHUB", "CI", "GIT", "RUNNING", "UPDATE", "STATE"}
    }
    for field, choices in allowed.items():
        if result[field] not in choices:
            result[field] = "ERROR" if field != "last_error" else "STATE"
    commit = result["updated_commit"]
    if not isinstance(commit, str) or not updates.SHA.fullmatch(commit):
        result["updated_commit"] = ""
    return result


def _try_repo(root):
    try:
        if not root.is_dir():
            return None, "NOT_INSTALLED"
        return updates.status(root), None
    except (OSError, ValueError, TimeoutError):
        return None, "ERROR"


def _do_update(name, root, state, *, runtime_busy, tested_commits):
    probe, unavailable = _try_repo(root)
    if unavailable:
        state[name] = unavailable
        return
    if probe["status"] == "UP_TO_DATE":
        state[name] = "UP_TO_DATE"
        return
    if runtime_busy:
        state[name] = "BLOCKED_RUNNING"
        return
    commit = probe["available"]
    if commit not in tested_commits:
        tested_commits[commit] = updates.ci_passed(commit)
    if not tested_commits[commit]:
        state[name] = "CI_WAIT"
        return
    if name == "runtime":
        updated = updates.apply(root, expected_tip=commit)
    else:
        updated = updates.apply_dashboard(root, expected_tip=commit)
    state[name] = "UPDATED" if updated["status"] == "UPDATED" else "UP_TO_DATE"
    if state[name] == "UPDATED":
        state["updated_commit"] = commit
        state["last_success_utc"] = int(time.time())
        if name == "dashboard":
            _atomic(UI_REFRESH, {"commit": commit})
            _atomic(BRIDGE_REFRESH, {"commit": commit})


def run_cycle(*, force=False, now=None):
    """Try both source checkouts, without clobbering active model processes."""
    _private()
    if not enabled():
        return snapshot()
    clock = int(time.time() if now is None else now)
    previous = _state_raw()
    if not force and clock - int(previous.get("last_check_utc", 0)) < INTERVAL:
        return snapshot()
    if LOCK.is_symlink():
        raise RuntimeError("unsafe pipeline lock")
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**snapshot(), "last_result": "BUSY"}
        # Double-check after acquiring the lock; bridge and UI may coexist.
        previous = _state_raw()
        if not force and clock - int(previous.get("last_check_utc", 0)) < INTERVAL:
            return snapshot()
        state = {"last_check_utc": clock, "last_success_utc": int(previous.get("last_success_utc", 0)),
                 "last_result": "CHECKING", "runtime": "NOT_YET_CHECKED",
                 "dashboard": "NOT_YET_CHECKED", "last_error": "NONE",
                 "updated_commit": previous.get("updated_commit", "")}
        _atomic(STATE, state)
        try:
            busy = updates._runtime_active()
            tested_commits = {}
            _do_update("runtime", Path.home() / "V13-Phone", state,
                       runtime_busy=busy, tested_commits=tested_commits)
            _atomic(STATE, state)
            _do_update("dashboard", Path.home() / ".v13-agent-source", state,
                       runtime_busy=busy, tested_commits=tested_commits)
            values = {state["runtime"], state["dashboard"]}
            if "UPDATED" in values:
                state["last_result"] = "UPDATED"
            elif "CI_WAIT" in values:
                state["last_result"] = "CI_WAIT"
            elif "BLOCKED_RUNNING" in values:
                state["last_result"] = "BLOCKED_RUNNING"
            elif "ERROR" in values or "NOT_INSTALLED" in values:
                state["last_result"] = "PARTIAL"
            else:
                state["last_result"] = "UP_TO_DATE"
        except (OSError, ValueError, TimeoutError) as exc:
            state["last_result"] = "ERROR"
            # Error class only; no secrets/paths/arguments in persisted state.
            state["last_error"] = "CI" if "CI" in type(exc).__name__ else "UPDATE"
        finally:
            _atomic(STATE, state)
        return snapshot()
    finally:
        os.close(fd)


def refresh_requested(which):
    name = UI_REFRESH if which == "ui" else BRIDGE_REFRESH
    return name.is_file() and not name.is_symlink()


def acknowledge_refresh(which):
    name = UI_REFRESH if which == "ui" else BRIDGE_REFRESH
    if name.is_symlink():
        return False
    try:
        name.unlink()
        return True
    except FileNotFoundError:
        return False
