"""Local, owner-only V13 lifecycle handoff during verified source upgrades.

The bridge and installer can request a shutdown of the *managed* V13 chat,
wait for confirmation, and ask the new UI to start a fresh session. No remote
arbitrary process control. All files are private and contain no chat content.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time

PRIVATE = Path.home() / ".v13-private"
STOP_REQUEST = PRIVATE / "v13-lifecycle-stop.json"
STOP_ACK = PRIVATE / "v13-lifecycle-stop-ack.json"
RESUME = PRIVATE / "v13-lifecycle-resume.json"
MAX_BYTES = 1024
NONCE = re.compile(r"[0-9a-f]{32}\Z")


class LifecycleError(RuntimeError):
    pass


def _private():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    st = PRIVATE.lstat()
    if PRIVATE.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise LifecycleError("V13 lifecycle state directory is not private")


def _write(path, payload):
    _private()
    if path.is_symlink():
        raise LifecycleError("V13 lifecycle symlink refused")
    fd, tmp = tempfile.mkstemp(prefix=".v13-lifecycle-", dir=str(PRIVATE))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(payload, out, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        item = json.loads(path.read_text(encoding="utf-8"))
        return item if isinstance(item, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def _discard(path):
    if path.is_symlink():
        raise LifecycleError("V13 lifecycle symlink refused")
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def request_stop(*, timeout=35, runtime_active=None):
    """Request a managed session stop; fail closed for unmanageable processes.

    Returns True only when a managed V13 session was running and has exited.
    Returns False if no V13 was running. Never signals unrelated processes.
    """
    if runtime_active is None:
        from .source_updater import _runtime_active as runtime_active
    if not runtime_active():
        return False
    _private()
    if STOP_REQUEST.is_file():
        current = _read(STOP_REQUEST)
        if current and current.get("expires", 0) > time.time():
            raise LifecycleError("Another V13 restart is already requested")
    nonce = secrets.token_hex(16)
    _discard(STOP_ACK)
    _write(STOP_REQUEST, {"schema":"v13.lifecycle.stop/1", "nonce":nonce,
                          "expires":int(time.time()) + int(timeout) + 5})
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            item = _read(STOP_ACK)
            if item and item.get("nonce") == nonce:
                if item.get("status") != "STOPPED":
                    raise LifecycleError("Managed V13 refused a safe stop")
                if runtime_active():
                    raise LifecycleError("Other V13 processes still active after managed stop")
                return item.get("was_running") is True
            time.sleep(.2)
        raise LifecycleError("V13 did not confirm graceful shutdown; no update applied")
    finally:
        current = _read(STOP_REQUEST)
        if current and current.get("nonce") == nonce:
            _discard(STOP_REQUEST)


def service_stop(console, *, shutdown_wait=12, interrupt_wait=6):
    """Called only by the local UI, not by a GitHub command handler."""
    item = _read(STOP_REQUEST)
    if not item or item.get("schema") != "v13.lifecycle.stop/1":
        return False
    nonce = item.get("nonce")
    if not isinstance(nonce, str) or not NONCE.fullmatch(nonce):
        return False
    if type(item.get("expires")) is not int or item["expires"] < time.time():
        return False
    ack = _read(STOP_ACK)
    if ack and ack.get("nonce") == nonce:
        return True
    was_running = console.state()["running"]
    stopped = not was_running
    if was_running:
        try:
            console.shutdown()  # let V13 save and close its own state
        except (OSError, ValueError, RuntimeError, BrokenPipeError):
            pass
        deadline = time.monotonic() + shutdown_wait
        while time.monotonic() < deadline and console.state()["running"]:
            time.sleep(.1)
        if console.state()["running"]:
            try:
                console.cancel()  # SIGINT to the isolated managed process group
            except (OSError, ValueError, RuntimeError, ProcessLookupError):
                pass
            deadline = time.monotonic() + interrupt_wait
            while time.monotonic() < deadline and console.state()["running"]:
                time.sleep(.1)
        stopped = not console.state()["running"]
    _write(STOP_ACK, {"nonce":nonce, "status":"STOPPED" if stopped else "BUSY",
                      "was_running":was_running, "created":int(time.time())})
    return True


def request_resume(*, reason="UPDATED"):
    """One-shot local marker consumed only by the UI's managed chat launcher."""
    if reason not in ("UPDATED", "RESTORE", "INSTALL"):
        raise ValueError("invalid V13 resume reason")
    _write(RESUME, {"schema":"v13.lifecycle.resume/1", "reason":reason,
                    "expires":int(time.time())+900})


def service_resume(console):
    """Called by UI AFTER an update transaction and possible UI re-exec."""
    item = _read(RESUME)
    if not item or item.get("schema") != "v13.lifecycle.resume/1":
        return False
    if type(item.get("expires")) is not int or item["expires"] < time.time():
        _discard(RESUME)
        return False
    if console.state()["running"]:
        _discard(RESUME)
        return True
    try:
        result = console.start()
        if result.get("status") not in ("STARTED", "ALREADY_RUNNING"):
            return False
    except (OSError, RuntimeError):
        return False  # keep the marker for a subsequent local UI boot
    _discard(RESUME)
    return True
