"""Android-local control boundary. No OS operations are performed by this module.

The Android companion must obtain OS permissions independently, present the user
with each request, and supply an authenticated local transport. Model text never
issues grants. This broker defaults to dry-run and refuses replayed approvals.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import threading
import time

CAPABILITIES = frozenset({"launch_app", "observe_ui", "tap", "swipe", "type_text", "back"})
MAX_TEXT = 256
MAX_PACKAGE = 180


class ControlDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Proposal:
    action_id: str
    capability: str
    args: dict
    expires_at: float
    digest: str


def _canonical(capability, args):
    if capability not in CAPABILITIES or type(args) is not dict:
        raise ControlDenied("unsupported action")
    keys = {
        "launch_app": {"package"}, "observe_ui": set(),
        "tap": {"x", "y"}, "swipe": {"x1", "y1", "x2", "y2", "duration_ms"},
        "type_text": {"text"}, "back": set()
    }[capability]
    if set(args) != keys:
        raise ControlDenied("invalid action arguments")
    if capability == "launch_app":
        pkg = args["package"]
        if not isinstance(pkg, str) or not 1 <= len(pkg) <= MAX_PACKAGE or not all(
            c.isascii() and (c.isalnum() or c in "._") for c in pkg
        ) or "." not in pkg:
            raise ControlDenied("invalid package")
    if capability == "type_text":
        t = args["text"]
        if not isinstance(t, str) or not 1 <= len(t) <= MAX_TEXT or any(ord(c) < 32 for c in t):
            raise ControlDenied("invalid text")
    if capability == "tap":
        if any(type(v) is not int or not 0 <= v <= 10000 for v in args.values()):
            raise ControlDenied("invalid coordinates")
    if capability == "swipe":
        for k, v in args.items():
            if type(v) is not int or not (50 <= v <= 3000 if k == "duration_ms" else 0 <= v <= 10000):
                raise ControlDenied("invalid swipe")
    return json.dumps({"capability": capability, "args": args}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _private_audit_db_path(db_path):
    """Create/open one private regular audit DB without following a final symlink.

    This protects the dry-run audit from accidental symlink/hardlink redirection
    and makes stored typed text private by default. It is not an OS sandbox or
    a defense against a malicious same-UID process racing the subsequent SQLite
    open; the native companion must still own authenticated consent and storage.
    """
    try:
        path = Path(os.path.abspath(os.path.expanduser(os.fspath(db_path))))
    except (TypeError, ValueError, OSError) as exc:
        raise ControlDenied("invalid audit database path") from exc
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise ControlDenied("safe audit storage unavailable")
    try:
        if not path.parent.is_dir():
            raise ControlDenied("audit database parent must already exist")
        for component in reversed(path.parents):
            if stat.S_ISLNK(component.lstat().st_mode):
                raise ControlDenied("symlinked audit directory")
        flags = os.O_RDWR | nofollow | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ControlDenied("audit database must be a private regular file")
            os.fchmod(fd, 0o600)
            current = path.lstat()
            if (not stat.S_ISREG(current.st_mode)
                    or current.st_dev != info.st_dev or current.st_ino != info.st_ino):
                raise ControlDenied("audit database path changed")
            os.fsync(fd)
        finally:
            os.close(fd)
    except ControlDenied:
        raise
    except OSError as exc:
        raise ControlDenied("unsafe audit database path") from exc
    return path


class AndroidControlBroker:
    """Per-action approval broker; transport and user-confirmation UI are separate.

    A trusted operator UI calls approve(), never the model or an untrusted tool.
    execute() returns a signed-off command envelope, not a claim of Android execution.
    """
    def __init__(self, db_path, *, clock=None):
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db_path = _private_audit_db_path(db_path)
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS control_audit (id INTEGER PRIMARY KEY, action_id TEXT, event TEXT NOT NULL, digest TEXT, at REAL NOT NULL)")
        self.db.commit()
        self.pending = {}
        self.approved = {}
        self.stopped = True

    def _audit(self, action_id, event, digest=None):
        self.db.execute("INSERT INTO control_audit(action_id,event,digest,at) VALUES (?,?,?,?)",
                        (action_id, event, digest, self.clock()))
        self.db.commit()

    def start(self):
        """Only a trusted local operator control may call this."""
        with self.lock:
            self.stopped = False
            self._audit(None, "operator_start")

    def stop(self):
        with self.lock:
            self.stopped = True
            self.pending.clear()
            self.approved.clear()
            self._audit(None, "operator_stop")

    def propose(self, capability, args, *, ttl=30):
        with self.lock:
            payload = _canonical(capability, args)
            if type(ttl) not in (int, float) or not 1 <= ttl <= 60:
                raise ControlDenied("invalid TTL")
            action_id = secrets.token_hex(16)
            digest = hashlib.sha256(payload.encode()).hexdigest()
            p = Proposal(action_id, capability, dict(args), self.clock() + ttl, digest)
            self.pending[action_id] = p
            self._audit(action_id, "proposed", digest)
            return p

    def approve(self, action_id, *, confirmed_by_local_ui=False):
        with self.lock:
            p = self.pending.pop(action_id, None)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "approval_denied")
                raise ControlDenied("approval unavailable")
            if confirmed_by_local_ui is not True:
                self._audit(action_id, "approval_denied", p.digest)
                raise ControlDenied("local confirmation required")
            self.approved[action_id] = p
            self._audit(action_id, "approved", p.digest)

    def execute(self, action_id, *, dry_run=True):
        with self.lock:
            p = self.approved.pop(action_id, None)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "execution_denied")
                raise ControlDenied("not approved or expired")
            if dry_run is not True:
                self._audit(action_id, "live_transport_unavailable", p.digest)
                raise ControlDenied("live Android companion not connected")
            self._audit(action_id, "dry_run", p.digest)
            return {"action_id": p.action_id, "capability": p.capability,
                    "args": dict(p.args), "digest": p.digest, "status": "DRY_RUN_ONLY"}

    def events(self):
        with self.lock:
            return list(self.db.execute("SELECT action_id,event,digest,at FROM control_audit ORDER BY id"))

    def close(self):
        with self.lock:
            self.stop()
            self.db.close()
