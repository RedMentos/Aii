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
import subprocess

from . import source_updater as updates
from . import lifecycle

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
    except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
            subprocess.TimeoutExpired):
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
    key = (commit, name)
    if key not in tested_commits:
        tested_commits[key] = updates.ci_passed(commit, scope=name)
    if not tested_commits[key]:
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


def run_cycle(*, force=False, now=None, manual=False, target="all"):
    """CI-gated fetch -> managed graceful stop -> update -> auto-restart.

    When an exact trusted commit passes tests, an active UI-managed V13 chat
    is stopped (with bounded acknowledgement), source is updated, then the UI
    restarts its chat from the durable local state. A foreign/unmanaged V13
    process is NOT killed; its update is deferred.
    """
    if target not in ("all", "runtime", "dashboard"):
        raise ValueError("unknown V13 update target")
    _private()
    if not manual and not enabled():
        return snapshot()
    clock = int(time.time() if now is None else now)
    previous = _state_raw()
    if not force and clock - int(previous.get("last_check_utc", 0)) < INTERVAL:
        return snapshot()
    if LOCK.is_symlink():
        raise RuntimeError("unsafe pipeline lock")
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    was_running = False
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**snapshot(), "last_result": "BUSY"}
        previous = _state_raw()
        if not force and clock - int(previous.get("last_check_utc", 0)) < INTERVAL:
            return snapshot()
        state = {"last_check_utc": clock, "last_success_utc": int(previous.get("last_success_utc", 0)),
                 "last_result": "CHECKING", "runtime": "NOT_YET_CHECKED",
                 "dashboard": "NOT_YET_CHECKED", "last_error": "NONE",
                 "updated_commit": previous.get("updated_commit", "")}
        _atomic(STATE, state)
        roots = {"runtime": Path.home() / "V13-Phone",
                 "dashboard": Path.home() / ".v13-agent-source"}
        selected = ("runtime", "dashboard") if target == "all" else (target,)
        tested_commits = {}
        try:
            busy = updates._runtime_active()
            # Fetch/check CI BEFORE asking to interrupt a running chat; if CI
            # isn't green, keep V13 running and show CI_WAIT, not fake progress.
            should_stop = False
            if busy:
                for name in selected:
                    report, unavailable = _try_repo(roots[name])
                    if unavailable or report["status"] != "UPDATE_AVAILABLE":
                        continue
                    sha = report["available"]
                    key = (sha, name)
                    if key not in tested_commits:
                        tested_commits[key] = updates.ci_passed(sha, scope=name)
                    if tested_commits[key]:
                        should_stop = True
                if should_stop:
                    try:
                        was_running = lifecycle.request_stop(timeout=35,
                                                              runtime_active=updates._runtime_active)
                    except lifecycle.LifecycleError:
                        state["last_error"] = "RUNNING"
                    busy = updates._runtime_active()
            for name in selected:
                _do_update(name, roots[name], state,
                           runtime_busy=busy, tested_commits=tested_commits)
                _atomic(STATE, state)
            values = {state[name] for name in selected}
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
        except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
                lifecycle.LifecycleError, subprocess.TimeoutExpired) as exc:
            state["last_result"] = "ERROR"
            state["last_error"] = ("RUNNING" if isinstance(exc,lifecycle.LifecycleError)
                                   else "UPDATE")
        finally:
            # Restart the UI-managed V13 chat whether an update succeeded or
            # failed. This cannot restart arbitrary Termux programs.
            if was_running:
                try:
                    lifecycle.request_resume(reason="UPDATED" if state["last_result"]=="UPDATED"
                                             else "RESTORE")
                except (OSError, ValueError, lifecycle.LifecycleError):
                    state["last_error"] = "STATE"
                    state["last_result"] = "ERROR"
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
