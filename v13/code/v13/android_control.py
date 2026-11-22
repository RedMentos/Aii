"""Android-local control boundary.

The Python broker persists source-bound proposals and signed companion receipt state,
but it performs no Android OS operation. The separate native companion owns OS
permissions, caller pairing, visible per-action consent, and the Keystore signing key.
The legacy local-UI boolean remains a caller assertion, never Android consent proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType
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
_ACTIVE_STATES = ("PROPOSED", "APPROVED", "DISPATCHED", "SUBMIT_UNCERTAIN", "RECEIPT_CONSUMED")


class ControlDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Proposal:
    action_id: str
    capability: str
    args: Mapping
    expires_at: float
    digest: str
    event_id: str | None = None
    source_ref: dict | None = None

    def __post_init__(self):
        # frozen=True does not freeze a nested dict. Keep the action payload
        # immutable because this exact object is retained through approval.
        object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


def _verify_proposal_digest(proposal):
    """Bind the immutable approved arguments to the digest shown at proposal."""
    payload = _canonical(proposal.capability, dict(proposal.args))
    actual = hashlib.sha256(payload.encode()).hexdigest()
    if not hmac.compare_digest(actual, proposal.digest):
        raise ControlDenied("proposal integrity changed")


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


# Legacy compatibility only: some Android releases expose this exact mapping as a symlink.
# AOSP Android 13 sets /data to system:system 0771 and bind-mounts /data/data
# onto /data/user/0; only that exact 0771 root (plus legacy /data/data) is exempted.
_ANDROID_PLATFORM_SYMLINKS = ((Path("/data/user/0"), Path("/data/data")),)
_ANDROID_DATA_ROOT = Path("/data")
_ANDROID_SYSTEM_UID = 1000
_ANDROID_SYSTEM_GID = 1000


def _trusted_android_data_group_write(path, info):
    """Allow only exact AOSP system:system 0771 directories, including verified bind mount."""
    exact_system_mode = (
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == _ANDROID_SYSTEM_UID
        and info.st_gid == _ANDROID_SYSTEM_GID
        and stat.S_IMODE(info.st_mode) == 0o771
    )
    if path in {_ANDROID_DATA_ROOT, _ANDROID_DATA_ROOT / "data"}:
        return exact_system_mode

    # Android 13 bind-mounts /data/data onto /data/user/0. Unlike a legacy
    # symlink, lstat() sees a directory at /data/user/0, so its exception must
    # be proven by the mounted directory's device/inode identity, not pathname
    # or owner/mode alone.
    if path == _ANDROID_DATA_ROOT / "user" / "0" and exact_system_mode:
        try:
            target = (_ANDROID_DATA_ROOT / "data").lstat()
        except OSError:
            return False
        return (
            stat.S_ISDIR(target.st_mode)
            and target.st_uid == _ANDROID_SYSTEM_UID
            and target.st_gid == _ANDROID_SYSTEM_GID
            and stat.S_IMODE(target.st_mode) == 0o771
            and (info.st_dev, info.st_ino) == (target.st_dev, target.st_ino)
        )
    return False


def _reject_unapproved_symlink_ancestors(parent, uid):
    """Validate the original path before resolving the exact Android data alias."""
    absolute = Path(os.path.abspath(os.fspath(parent)))
    parts = absolute.parts
    current = Path(parts[0])
    for component in parts[1:]:
        current = current / component
        try:
            info = current.lstat()
        except OSError as exc:
            raise ControlDenied("unsafe audit database ancestor") from exc
        under_android_data = (
            current == _ANDROID_DATA_ROOT or _ANDROID_DATA_ROOT in current.parents
        )
        if stat.S_ISLNK(info.st_mode):
            resolved = Path(os.path.realpath(os.fspath(current)))
            allowed = any(
                current == Path(alias) and resolved == Path(target)
                for alias, target in _ANDROID_PLATFORM_SYMLINKS
            )
            allowed_owners = {0, uid}
            if under_android_data:
                allowed_owners.add(_ANDROID_SYSTEM_UID)
            if not allowed or info.st_uid not in allowed_owners:
                raise ControlDenied("unapproved symlink in audit database path")
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise ControlDenied("audit database ancestor must be a directory")
        if current == absolute:
            if info.st_uid != uid or info.st_mode & 0o022:
                raise ControlDenied("audit database parent must be owner-controlled")
            continue
        allowed_owners = {0, uid}
        if under_android_data:
            allowed_owners.add(_ANDROID_SYSTEM_UID)
        if info.st_uid not in allowed_owners:
            raise ControlDenied("untrusted audit database ancestor owner")
        if info.st_mode & 0o022 and not (info.st_mode & stat.S_ISVTX):
            if not _trusted_android_data_group_write(current, info):
                raise ControlDenied("group/world-writable audit database ancestor")
    return Path(os.path.realpath(os.fspath(absolute)))


def _validate_audit_parent_ancestry(parent, uid):
    """Reject ancestors another UID could rename to redirect the audit database.

    The immediate parent must belong to this process and not be group/world writable.
    Higher ancestors must be root- or caller-owned and non-writable, except sticky
    shared directories (for example /tmp). Under /data, only the exact AOSP
    system:system 0771 /data root (and legacy /data/data target) may be group-writable.
    """
    resolved = Path(os.path.realpath(os.fspath(parent)))
    if not resolved.is_absolute():
        raise ControlDenied("audit database parent must be absolute")
    under_android_data = (
        resolved == _ANDROID_DATA_ROOT or _ANDROID_DATA_ROOT in resolved.parents
    )
    try:
        parent_info = resolved.lstat()
    except OSError as exc:
        raise ControlDenied("unsafe audit database parent") from exc
    if (
        not stat.S_ISDIR(parent_info.st_mode)
        or parent_info.st_uid != uid
        or parent_info.st_mode & 0o022
    ):
        raise ControlDenied("audit database parent must be owner-controlled")
    for directory in reversed(resolved.parents):
        try:
            info = directory.lstat()
        except OSError as exc:
            raise ControlDenied("unsafe audit database ancestor") from exc
        if not stat.S_ISDIR(info.st_mode):
            raise ControlDenied("audit database ancestor must be a directory")
        allowed_owners = {0, uid}
        if under_android_data and (
            directory == _ANDROID_DATA_ROOT or _ANDROID_DATA_ROOT in directory.parents
        ):
            allowed_owners.add(_ANDROID_SYSTEM_UID)
        if info.st_uid not in allowed_owners:
            raise ControlDenied("untrusted audit database ancestor owner")
        if info.st_mode & 0o022:
            sticky = bool(info.st_mode & stat.S_ISVTX)
            if not sticky and not _trusted_android_data_group_write(directory, info):
                raise ControlDenied("group/world-writable audit database ancestor")
    return resolved


def _private_audit_db_path(db_path):
    """Create/open one private regular audit DB without following a final symlink.

    This rejects final-file, caller-controlled symlink, hardlink, and cross-UID
    writable-ancestor redirection. The sole ancestor alias exception is the exact
    Android platform mapping /data/user/0 -> /data/data. The only group-writable
    ancestor exception is exact mode 0771 with system:system ownership on /data
    (or the legacy /data/data target); world-write and writable child ancestors
    remain rejected. Sticky shared ancestors such as /tmp retain their normal
    sticky-bit rule. This is not an OS sandbox or a defense against a malicious
    same-UID process racing the subsequent SQLite open; the native companion
    must still own authenticated consent and storage.
    """
    try:
        raw_path = Path(os.path.abspath(os.path.expanduser(os.fspath(db_path))))
        getuid = getattr(os, "getuid", None)
        if getuid is None:
            raise ControlDenied("safe audit storage unavailable")
        uid = getuid()
        canonical_parent = _reject_unapproved_symlink_ancestors(raw_path.parent, uid)
        parent = _validate_audit_parent_ancestry(canonical_parent, uid)
        path = parent / raw_path.name
    except ControlDenied:
        raise
    except (TypeError, ValueError, OSError) as exc:
        raise ControlDenied("invalid audit database path") from exc
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise ControlDenied("safe audit storage unavailable")
    try:
        if not path.parent.is_dir():
            raise ControlDenied("audit database parent must already exist")
        if stat.S_ISLNK(path.parent.lstat().st_mode):
            raise ControlDenied("symlinked audit parent")
        parent_info = path.parent.stat()
        if parent_info.st_uid != getuid() or parent_info.st_mode & 0o022:
            raise ControlDenied("audit database parent must be owner-controlled")
        flags = (os.O_RDWR | nofollow | getattr(os, "O_CLOEXEC", 0)
                 | getattr(os, "O_NONBLOCK", 0))
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
    """Source-bound one-shot action broker with restart-safe dispatch records.

    Only non-sensitive action arguments are persisted. `type_text` remains
    process-local and is dropped on restart. A dispatched action can be resumed
    after a Termux restart, but a companion receipt is still non-authoritative.
    """
    def __init__(self, db_path, *, clock=None):
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db_path = _private_audit_db_path(db_path)
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS control_audit (id INTEGER PRIMARY KEY, action_id TEXT, event TEXT NOT NULL, digest TEXT, at REAL NOT NULL)")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS control_actions ("
            "action_id TEXT PRIMARY KEY, capability TEXT NOT NULL, args_json TEXT, "
            "expires_at REAL NOT NULL, digest TEXT NOT NULL, event_id TEXT, "
            "source_ref_json TEXT, state TEXT NOT NULL)"
        )
        self.db.commit()
        self.pending = {}
        self.approved = {}
        self.dispatched = {}
        self.consumed = {}
        self.stopped = True
        self._restore_actions()

    def _audit(self, action_id, event, digest=None):
        self.db.execute("INSERT INTO control_audit(action_id,event,digest,at) VALUES (?,?,?,?)",
                        (action_id, event, digest, self.clock()))
        self.db.commit()

    def _restore_actions(self):
        self.pending.clear()
        self.approved.clear()
        self.dispatched.clear()
        self.consumed.clear()
        rows = list(self.db.execute(
            "SELECT action_id,capability,args_json,expires_at,digest,event_id,source_ref_json,state "
            "FROM control_actions WHERE state IN ('PROPOSED','APPROVED','DISPATCHED','SUBMIT_UNCERTAIN','RECEIPT_CONSUMED')"
        ))
        for action_id, capability, args_json, expires_at, digest, event_id, source_json, state in rows:
            if expires_at < self.clock():
                self.db.execute("UPDATE control_actions SET state='EXPIRED' WHERE action_id=?", (action_id,))
                self._audit(action_id, "expired_on_restore", digest)
                continue
            if args_json is None:
                self.db.execute("UPDATE control_actions SET state='DROPPED_ON_RESTART' WHERE action_id=?", (action_id,))
                self._audit(action_id, "sensitive_args_dropped_on_restart", digest)
                continue
            try:
                args = json.loads(args_json)
                source_ref = json.loads(source_json) if source_json else None
                proposal = Proposal(action_id, capability, args, float(expires_at), digest, event_id, source_ref)
            except Exception:
                self.db.execute("UPDATE control_actions SET state='INVALID_ON_RESTORE' WHERE action_id=?", (action_id,))
                self._audit(action_id, "invalid_state_on_restore", digest)
                continue
            if state == "PROPOSED":
                self.pending[action_id] = proposal
            elif state == "APPROVED":
                self.approved[action_id] = proposal
            elif state in ("DISPATCHED", "SUBMIT_UNCERTAIN"):
                self.dispatched[action_id] = proposal
            elif state == "RECEIPT_CONSUMED":
                self.consumed[action_id] = proposal
        self.db.commit()

    def _set_state(self, action_id, state, expected=None):
        if expected is None:
            self.db.execute("UPDATE control_actions SET state=? WHERE action_id=?", (state, action_id))
        else:
            self.db.execute(
                "UPDATE control_actions SET state=? WHERE action_id=? AND state=?",
                (state, action_id, expected),
            )
        self.db.commit()

    def start(self):
        """Open the local operator gate and restore durable non-sensitive actions."""
        with self.lock:
            self.stopped = False
            self._audit(None, "operator_start")

    def stop(self):
        with self.lock:
            self.stopped = True
            # Local-only proposals can be cancelled. A request already sent to
            # Android, or a receipt awaiting durable Store commit, must remain
            # recoverable until remote cancellation or signed receipt is proven.
            for action_id in set(self.pending) | set(self.approved):
                self._audit(action_id, "operator_stop_cancelled")
            for action_id, proposal in list(self.dispatched.items()):
                row = self.db.execute(
                    "SELECT state FROM control_actions WHERE action_id=?", (action_id,)
                ).fetchone()
                if row is not None and row[0] == "DISPATCHED":
                    self._set_state(action_id, "SUBMIT_UNCERTAIN", expected="DISPATCHED")
                self._audit(action_id, "operator_stop_preserved_uncertain", proposal.digest)
            for action_id, proposal in self.consumed.items():
                self._audit(action_id, "operator_stop_preserved_receipt", proposal.digest)
            self.db.execute(
                "UPDATE control_actions SET state='CANCELLED' WHERE state IN ('PROPOSED','APPROVED')"
            )
            self.db.commit()
            self.pending.clear()
            self.approved.clear()
            # Keep dispatched/uncertain and consumed maps for in-process retry.
            self._audit(None, "operator_stop")

    def propose(self, capability, args, *, ttl=30, event_id=None, source_ref=None):
        with self.lock:
            payload = _canonical(capability, args)
            if (event_id is None) != (source_ref is None):
                raise ControlDenied("event and source reference must be supplied together")
            if event_id is not None:
                if type(event_id) is not str or not 1 <= len(event_id) <= 128:
                    raise ControlDenied("invalid source event")
                if (type(source_ref) is not dict
                        or type(source_ref.get("source_id")) is not str
                        or type(source_ref.get("sha256")) is not str
                        or len(source_ref["sha256"]) != 64
                        or any(ch not in "0123456789abcdef" for ch in source_ref["sha256"])
                        or type(source_ref.get("char_start")) is not int
                        or type(source_ref.get("char_end")) is not int
                        or source_ref["char_start"] < 0
                        or source_ref["char_end"] <= source_ref["char_start"]
                        or type(source_ref.get("modality")) is not str):
                    raise ControlDenied("invalid source binding")
            if type(ttl) not in (int, float) or not 1 <= ttl <= 60:
                raise ControlDenied("invalid TTL")
            action_id = secrets.token_hex(16)
            digest = hashlib.sha256(payload.encode()).hexdigest()
            expires_at = self.clock() + ttl
            p = Proposal(action_id, capability, dict(args), expires_at, digest,
                         event_id, dict(source_ref) if source_ref is not None else None)
            self.pending[action_id] = p
            # Never persist raw typed text. The native companion currently accepts
            # launch_app only; other non-sensitive action types remain restart-safe.
            args_json = None if capability == "type_text" else json.dumps(
                args, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            source_json = json.dumps(source_ref, sort_keys=True, separators=(",", ":")) if source_ref is not None else None
            self.db.execute(
                "INSERT INTO control_actions(action_id,capability,args_json,expires_at,digest,event_id,source_ref_json,state) "
                "VALUES (?,?,?,?,?,?,?,'PROPOSED')",
                (action_id, capability, args_json, expires_at, digest, event_id, source_json),
            )
            self.db.commit()
            self._audit(action_id, "proposed", digest)
            return p

    def approve(self, action_id, *, confirmed_by_local_ui=False):
        """Accept a caller assertion from the local operator; companion UI still confirms."""
        with self.lock:
            p = self.pending.get(action_id)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "approval_denied")
                if p is not None and self.clock() > p.expires_at:
                    self.pending.pop(action_id, None)
                    self._set_state(action_id, "EXPIRED")
                raise ControlDenied("approval unavailable")
            if confirmed_by_local_ui is not True:
                self._audit(action_id, "approval_denied", p.digest)
                raise ControlDenied("local confirmation required")
            try:
                _verify_proposal_digest(p)
            except ControlDenied:
                self._audit(action_id, "approval_denied", p.digest)
                raise
            self.pending.pop(action_id, None)
            self.approved[action_id] = p
            self._set_state(action_id, "APPROVED", expected="PROPOSED")
            self._audit(action_id, "approved", p.digest)

    def dispatch_approved(self, action_id):
        """Export one locally approved request for a separately consented companion."""
        with self.lock:
            p = self.approved.get(action_id)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "dispatch_denied")
                raise ControlDenied("approved action unavailable")
            if action_id in self.dispatched:
                self._audit(action_id, "dispatch_replay_denied", p.digest)
                raise ControlDenied("action already dispatched")
            self.approved.pop(action_id, None)
            self.dispatched[action_id] = p
            self._set_state(action_id, "DISPATCHED", expected="APPROVED")
            self._audit(action_id, "dispatched", p.digest)
            return {
                "schema": "v14.android-action-request/1",
                "action_id": p.action_id,
                "capability": p.capability,
                "args": dict(p.args),
                "digest": p.digest,
                "expires_at": p.expires_at,
                "local_approval": "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION",
                "companion_local_consent_required": True,
                "android_os_permission_required": False,
                "permission_bypass": False,
                "model_authority": False,
            }

    def mark_submit_uncertain(self, action_id):
        """Retain a dispatched action when the remote submit/cancel result is ambiguous."""
        with self.lock:
            proposal = self.dispatched.get(action_id)
            row = self.db.execute(
                "SELECT state FROM control_actions WHERE action_id=?", (action_id,)
            ).fetchone()
            if proposal is None or row is None or row[0] not in ("DISPATCHED", "SUBMIT_UNCERTAIN"):
                raise ControlDenied("action is not an unresolved dispatch")
            if row[0] == "DISPATCHED":
                self._set_state(action_id, "SUBMIT_UNCERTAIN", expected="DISPATCHED")
            self._audit(action_id, "submit_uncertain", proposal.digest)
            return True

    def consume_dispatched(self, action_id):
        """Consume a dispatched or uncertain request once before verifying its receipt."""
        with self.lock:
            p = self.consumed.get(action_id) or self.dispatched.get(action_id)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "companion_receipt_denied")
                raise ControlDenied("dispatched action unavailable")
            if action_id in self.dispatched:
                row = self.db.execute(
                    "SELECT state FROM control_actions WHERE action_id=?", (action_id,)
                ).fetchone()
                expected = row[0] if row and row[0] in ("DISPATCHED", "SUBMIT_UNCERTAIN") else None
                if expected is None:
                    raise ControlDenied("dispatch state cannot be consumed")
                self.dispatched.pop(action_id, None)
                self._set_state(action_id, "RECEIPT_CONSUMED", expected=expected)
                self.consumed[action_id] = p
            self._audit(action_id, "companion_receipt_pending", p.digest)
            return p

    def record_companion_receipt(self, action_id, digest, *, verified):
        if type(verified) is not bool:
            raise ControlDenied("invalid receipt result")
        with self.lock:
            p = self.consumed.get(action_id)
            if p is None or p.digest != digest:
                raise ControlDenied("receipt is not bound to a consumed dispatch")
            self.consumed.pop(action_id, None)
            self._set_state(action_id, "RECEIPT_VERIFIED" if verified else "RECEIPT_REJECTED",
                            expected="RECEIPT_CONSUMED")
            self._audit(action_id, "companion_receipt_verified" if verified else
                        "companion_receipt_rejected", digest)

    def cancel(self, action_id):
        with self.lock:
            p = (self.pending.pop(action_id, None) or self.approved.pop(action_id, None)
                 or self.dispatched.pop(action_id, None) or self.consumed.pop(action_id, None))
            row = self.db.execute("SELECT state,digest FROM control_actions WHERE action_id=?", (action_id,)).fetchone()
            if p is None and (row is None or row[0] not in _ACTIVE_STATES):
                raise ControlDenied("action is not cancellable")
            digest = p.digest if p is not None else row[1]
            self._set_state(action_id, "CANCELLED")
            self._audit(action_id, "cancelled", digest)
            return True

    def execute(self, action_id, *, dry_run=True):
        with self.lock:
            p = self.approved.get(action_id)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "execution_denied")
                raise ControlDenied("not approved or expired")
            try:
                _verify_proposal_digest(p)
            except ControlDenied:
                self._audit(action_id, "execution_denied", p.digest)
                raise
            if dry_run is not True:
                self._audit(action_id, "live_transport_unavailable", p.digest)
                raise ControlDenied("live Android companion not connected")
            self.approved.pop(action_id, None)
            self._set_state(action_id, "DRY_RUN", expected="APPROVED")
            self._audit(action_id, "dry_run", p.digest)
            return {"action_id": p.action_id, "capability": p.capability,
                    "args": dict(p.args), "digest": p.digest, "status": "DRY_RUN_ONLY"}

    def action_state(self, action_id):
        with self.lock:
            row = self.db.execute(
                "SELECT state FROM control_actions WHERE action_id=?", (action_id,)
            ).fetchone()
            return row[0] if row else None

    def events(self):
        with self.lock:
            return list(self.db.execute("SELECT action_id,event,digest,at FROM control_audit ORDER BY id"))

    def close(self):
        with self.lock:
            # Process shutdown preserves durable dispatched actions for restart recovery.
            self.stopped = True
            self._audit(None, "operator_close")
            self.db.close()
