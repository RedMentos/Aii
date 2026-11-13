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
from . import runtime_deploy

PRIVATE = Path.home() / ".v13-private"
ENABLED = PRIVATE / "auto-source-update.enabled"
STATE = PRIVATE / "pipeline-status.json"
LOCK = PRIVATE / "pipeline-status.lock"
UI_REFRESH = PRIVATE / "pipeline-ui-refresh"
BRIDGE_REFRESH = PRIVATE / "pipeline-bridge-refresh"
AI_REFRESH = PRIVATE / "pipeline-ai-refresh"
UPDATE_REQUEST = PRIVATE / "pipeline-manual-request.json"
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


def set_enabled(value):
    """One authority for auto-update consent: atomic, durable and idempotent.

    Both the WebView button and the independent relay update worker consume
    this exact marker. A UI acknowledgement is made only after the persisted
    state is re-read. Never clear a symlink or change directory permissions.
    """
    if type(value) is not bool:
        raise ValueError("auto-update enabled must be a boolean")
    _private()
    if ENABLED.is_symlink():
        raise RuntimeError("unsafe auto-update consent symlink")
    if value:
        fd, tmp = tempfile.mkstemp(prefix=".v13-auto-optin-", dir=str(PRIVATE))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as f:
                f.write("yes\\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, ENABLED)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    else:
        ENABLED.unlink(missing_ok=True)
    if enabled() != value:
        raise RuntimeError("auto-update consent not persisted")
    return value


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
    # A partial single-target check may have left a failed sibling in state.
    # Never tell the owner that *both* installed components are current then.
    if result["last_result"] in ("UPDATED", "UP_TO_DATE"):
        if any(result[name] not in ("UPDATED", "UP_TO_DATE")
               for name in ("runtime", "dashboard")):
            result["last_result"] = "PARTIAL"
    if result["last_error"] == "NONE" and (
            result["runtime"] == "ERROR" or result["dashboard"] == "ERROR"):
        result["last_error"] = "UPDATE"
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


def pending_updates(*, fetch=True):
    """Inspect the SAME two checkouts used by the one-click updater.

    This intentionally does NOT check the obsolete ~/V13-Phone directory.
    Git source updated != installed runtime updated: independently verify the
    active launcher snapshot, too. No code is installed by this read-only call.
    """
    roots = {"runtime": Path.home() / ".v13-runtime-source",
             "dashboard": Path.home() / ".v13-agent-source"}
    result = {"schema": "v13.pipeline-pending/1",
              "status": "UP_TO_DATE", "pending_files": 0,
              "runtime": "UNKNOWN", "dashboard": "UNKNOWN",
              "runtime_activation_pending": False,
              "auto_enabled": enabled(), "branches": {}}
    for name, root in roots.items():
        if not root.is_dir():
            result[name] = "NOT_INSTALLED"
            result["status"] = "NOT_INSTALLED"
            continue
        try:
            info = updates.status(root, fetch=fetch)
            source_state = info["status"]
            if source_state not in ("UP_TO_DATE", "UPDATE_AVAILABLE"):
                raise ValueError("Unexpected update state")
            pending = info.get("changed_files", 0)
            if type(pending) is not int or pending < 0:
                raise ValueError("Invalid changed file count")
            result["pending_files"] += pending
            result["branches"][name] = {
                "current": info.get("current", "")[:12],
                "available": info.get("available", "")[:12],
                "pending_files": pending
            }
            if name == "runtime" and source_state == "UP_TO_DATE":
                if runtime_deploy.needs_deploy(root):
                    result["runtime_activation_pending"] = True
                    source_state = "ACTIVATION_PENDING"
            result[name] = source_state
            if source_state != "UP_TO_DATE" and result["status"] == "UP_TO_DATE":
                result["status"] = "UPDATE_AVAILABLE"
        except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
                runtime_deploy.RuntimeDeployError, subprocess.TimeoutExpired):
            result[name] = "ERROR"
            result["status"] = "ERROR"
    # An unreachable or uninstalled side is never reported as 0 verified.
    result["verified_current"] = (
        result["status"] == "UP_TO_DATE" and
        result["runtime"] == result["dashboard"] == "UP_TO_DATE" and
        result["pending_files"] == 0 and
        not result["runtime_activation_pending"]
    )
    return result


def _do_update(name, root, state, *, runtime_busy, tested_commits):
    probe, unavailable = _try_repo(root)
    if unavailable:
        state[name] = unavailable
        if unavailable == "ERROR":
            state["last_error"] = "GIT"
        return
    if probe["status"] == "UP_TO_DATE" and name != "runtime":
        updates.ensure_sparse_phone_modules(root)
        state[name] = "UP_TO_DATE"
        return
    must_deploy = name == "runtime" and runtime_deploy.needs_deploy(root)
    if probe["status"] == "UP_TO_DATE" and not must_deploy:
        state[name] = "UP_TO_DATE"
        return
    commit = probe.get("available") or probe.get("current")
    if not commit or not updates.SHA.fullmatch(commit):
        state[name] = "ERROR"
        return
    key = (commit, name)
    if key not in tested_commits:
        tested_commits[key] = updates.ci_passed(commit, scope=name)
    if not tested_commits[key]:
        state[name] = "CI_WAIT"
        return
    if runtime_busy:
        state[name] = "BLOCKED_RUNNING"
        return
    if probe["status"] != "UP_TO_DATE":
        if name == "runtime":
            updated = updates.apply(root, expected_tip=commit)
        else:
            updated = updates.apply_dashboard(root, expected_tip=commit)
    else:
        updated = {"status":"UP_TO_DATE"}
    activated = False
    if name == "runtime":
        # A Git checkout update is NOT a runtime update. Stage a complete
        # code snapshot, check source/Canon, and atomically switch bin/v13.
        activated = runtime_deploy.deploy(root, ci_verified=True)["status"] == "DEPLOYED"
    state[name] = "UPDATED" if updated["status"] == "UPDATED" or activated else "UP_TO_DATE"
    if state[name] == "UPDATED":
        state["updated_commit"] = commit
        state["last_success_utc"] = int(time.time())
        if name == "dashboard":
            _atomic(UI_REFRESH, {"commit": commit})
            _atomic(BRIDGE_REFRESH, {"commit": commit})
            _atomic(AI_REFRESH, {"commit": commit})
        else:
            _atomic(AI_REFRESH, {"commit": commit})


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
        prior_status = snapshot()
        state = {"last_check_utc": clock, "last_success_utc": int(previous.get("last_success_utc", 0)),
                 "last_result": "CHECKING", "runtime": prior_status["runtime"],
                 "dashboard": prior_status["dashboard"], "last_error": "NONE",
                 "updated_commit": previous.get("updated_commit", "")}
        _atomic(STATE, state)
        roots = {"runtime": Path.home() / ".v13-runtime-source",
                 "dashboard": Path.home() / ".v13-agent-source"}
        selected = ("runtime", "dashboard") if target == "all" else (target,)
        for name in selected:
            state[name] = "NOT_YET_CHECKED"
        tested_commits = {}
        try:
            failed = set()
            if "runtime" in selected:
                try:
                    # Old phone installs only had the dashboard Git clone.
                    # Prepare the fixed runtime source as part of Update all;
                    # activation below still requires CI and a stopped model.
                    runtime_deploy.prepare_source(roots["runtime"])
                except (OSError, ValueError, TimeoutError,
                        runtime_deploy.RuntimeDeployError, subprocess.TimeoutExpired):
                    state["runtime"] = "ERROR"
                    state["last_error"] = "UPDATE"
                    failed.add("runtime")
            busy = updates._runtime_active()
            # Fetch/check CI BEFORE asking to interrupt a running chat; if CI
            # isn't green, keep V13 running and show CI_WAIT, not fake progress.
            should_stop = False
            if busy:
                for name in selected:
                    if name in failed:
                        continue
                    report, unavailable = _try_repo(roots[name])
                    if unavailable:
                        continue
                    try:
                        if report["status"] != "UPDATE_AVAILABLE":
                            if name != "runtime" or not runtime_deploy.needs_deploy(roots[name]):
                                continue
                    except runtime_deploy.RuntimeDeployError:
                        state[name] = "ERROR"
                        state["last_error"] = "UPDATE"
                        failed.add(name)
                        continue
                    sha = report["available"]
                    key = (sha, name)
                    try:
                        if key not in tested_commits:
                            tested_commits[key] = updates.ci_passed(sha, scope=name)
                    except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
                            subprocess.TimeoutExpired):
                        state[name] = "ERROR"
                        state["last_error"] = "CI"
                        failed.add(name)
                        continue
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
                if name in failed:
                    continue
                try:
                    _do_update(name, roots[name], state,
                               runtime_busy=busy, tested_commits=tested_commits)
                except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
                        runtime_deploy.RuntimeDeployError, subprocess.TimeoutExpired):
                    # A broken runtime install must not strand CHECKING or
                    # prevent the independent control panel repairing itself.
                    state[name] = "ERROR"
                    state["last_error"] = "UPDATE"
                _atomic(STATE, state)
            values = {state[name] for name in selected}
            if values == {"ERROR"}:
                state["last_result"] = "ERROR"
            elif "ERROR" in values or "NOT_INSTALLED" in values:
                state["last_result"] = "PARTIAL"
            elif "UPDATED" in values:
                state["last_result"] = ("UPDATED" if values <= {"UPDATED", "UP_TO_DATE"}
                                        else "PARTIAL")
            elif "CI_WAIT" in values:
                state["last_result"] = "CI_WAIT"
            elif "BLOCKED_RUNNING" in values:
                state["last_result"] = "BLOCKED_RUNNING"
            else:
                state["last_result"] = "UP_TO_DATE"
            # A targeted runtime update is not a successful phone-wide update
            # while the *other* installed component is broken or unchecked.
            if state["last_result"] in ("UP_TO_DATE", "UPDATED"):
                if any(state[name] not in ("UP_TO_DATE", "UPDATED")
                       for name in ("runtime", "dashboard")):
                    state["last_result"] = "PARTIAL"
            if state["last_error"] == "NONE" and (
                    state["runtime"] == "ERROR" or state["dashboard"] == "ERROR"):
                state["last_error"] = "UPDATE"
        except (OSError, ValueError, TimeoutError, updates.UpdateDenied,
                lifecycle.LifecycleError, runtime_deploy.RuntimeDeployError,
                subprocess.TimeoutExpired) as exc:
            state["last_result"] = "ERROR"
            state["last_error"] = ("RUNNING" if isinstance(exc,lifecycle.LifecycleError)
                                   else "UPDATE")
        except Exception:
            # Preserve a terminal, sanitized state even for an unexpected
            # Python/import error; the supervising worker can log its class.
            state["last_result"] = "ERROR"
            state["last_error"] = "UPDATE"
            raise
        finally:
            # Restart the UI-managed V13 chat whether an update succeeded or
            # failed. This cannot restart arbitrary Termux programs.
            if was_running:
                try:
                    lifecycle.request_resume(reason="UPDATED" if any(state[n] == "UPDATED" for n in selected)
                                             else "RESTORE")
                except (OSError, ValueError, lifecycle.LifecycleError):
                    state["last_error"] = "STATE"
                    state["last_result"] = "ERROR"
            _atomic(STATE, state)
        return snapshot()
    finally:
        os.close(fd)


def schedule_update(request_id):
    """Owner-triggered source update, queued for the existing pipeline worker.

    No raw shell code or arbitrary paths are accepted. The worker enforces
    the exact-commit CI gate and honors the V13 graceful stop/restart.
    """
    import re
    if not isinstance(request_id, str) or re.fullmatch(r"[a-f0-9]{32}", request_id) is None:
        raise ValueError("invalid update request ID")
    _private()
    if UPDATE_REQUEST.is_symlink():
        raise RuntimeError("unsafe update queue")
    if UPDATE_REQUEST.is_file():
        existing = json.loads(UPDATE_REQUEST.read_text(encoding="utf-8"))
        if int(existing.get("expires",0)) > time.time():
            return {"status":"ALREADY_QUEUED"}
    _atomic(UPDATE_REQUEST, {"request_id":request_id, "expires":int(time.time()) + 900})
    return {"status":"QUEUED","request_id":request_id,
            "next":"PIPELINE_STATUS confirms the actual result"}


def claim_scheduled_update():
    """Consume once, atomically, before any source checkout modification."""
    _private()
    if UPDATE_REQUEST.is_symlink() or not UPDATE_REQUEST.is_file():
        return False
    data=json.loads(UPDATE_REQUEST.read_text(encoding="utf-8"))
    UPDATE_REQUEST.unlink()
    return type(data.get("expires")) is int and data["expires"]>=time.time()


def refresh_requested(which):
    name = {"ui": UI_REFRESH, "bridge": BRIDGE_REFRESH, "ai": AI_REFRESH}.get(which)
    if name is None:
        raise ValueError("invalid refresh target")
    return name.is_file() and not name.is_symlink()


def acknowledge_refresh(which):
    name = {"ui": UI_REFRESH, "bridge": BRIDGE_REFRESH, "ai": AI_REFRESH}.get(which)
    if name is None:
        raise ValueError("invalid refresh target")
    if name.is_symlink():
        return False
    try:
        name.unlink()
        return True
    except FileNotFoundError:
        return False


def main(argv=None):
    """Correct standalone Termux update entry point for BOTH installed roots.

    The former v13-update shell command invoked source_updater's obsolete
    ~/V13-Phone default. That can report a persistent file count without
    touching either .v13-runtime-source or .v13-agent-source, and it never
    deployed the pinned ~/v13/bin/v13 launcher. Use the same CI-gated,
    stop/deploy/resume transaction as the phone UI instead.
    """
    import argparse
    parser = argparse.ArgumentParser(description="V13 installed runtime + dashboard update")
    parser.add_argument("action", nargs="?", default="apply",
                        choices=("check", "apply", "auto", "status", "rollback"))
    parser.add_argument("--target", choices=("all", "runtime", "dashboard"), default="all")
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            report = snapshot()
            ok = report["last_result"] in ("UPDATED", "UP_TO_DATE")
        elif args.action == "check":
            report = pending_updates(fetch=True)
            ok = report["status"] in ("UP_TO_DATE", "UPDATE_AVAILABLE")
        elif args.action == "rollback":
            # The legacy rollback restored a Git tree only, not the installed
            # launcher. Never falsely report a runtime rollback as complete.
            report = {"status": "REFUSED",
                      "reason": "A launcher-safe runtime rollback is not yet implemented"}
            ok = False
        elif args.action == "auto" and not enabled():
            report = {"status": "AUTO_OFF", "auto_enabled": False}
            ok = False
        else:
            report = run_cycle(force=True, manual=args.action == "apply",
                               target=args.target)
            ok = report["last_result"] in ("UPDATED", "UP_TO_DATE")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if ok else 2
    except (OSError, RuntimeError, ValueError, TimeoutError,
            subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "REFUSED", "error_code": type(exc).__name__},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
