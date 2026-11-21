"""Android-local control boundary. No OS operations are performed by this module.

The Android companion must obtain OS permissions independently, present the user
with each request, and supply an authenticated local transport. Model text never
issues grants. This Python broker is only a test scaffold: its local-UI boolean is
caller-asserted, not authenticated evidence. It performs no OS operation.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets
import sqlite3
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
    event_id: str | None = None
    source_ref: dict | None = None


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


class AndroidControlBroker:
    """Per-action approval broker; transport and user-confirmation UI are separate.

    The caller is expected to be a trusted operator UI, but this module cannot
    authenticate that caller; confirmed_by_local_ui is only a test assertion.
    Production approval must be enforced by the separate Android companion.
    execute() returns a command envelope, not a claim of Android execution.
    """
    def __init__(self, db_path, *, clock=None):
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS control_audit (id INTEGER PRIMARY KEY, action_id TEXT, event TEXT NOT NULL, digest TEXT, at REAL NOT NULL)")
        self.db.commit()
        self.pending = {}
        self.approved = {}
        self.dispatched = {}
        self.stopped = True

    def _audit(self, action_id, event, digest=None):
        self.db.execute("INSERT INTO control_audit(action_id,event,digest,at) VALUES (?,?,?,?)",
                        (action_id, event, digest, self.clock()))
        self.db.commit()

    def start(self):
        """Test-scaffold gate only; caller identity is not authenticated here."""
        with self.lock:
            self.stopped = False
            self._audit(None, "operator_start")

    def stop(self):
        with self.lock:
            self.stopped = True
            self.pending.clear()
            self.approved.clear()
            self.dispatched.clear()
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
            p = Proposal(action_id, capability, dict(args), self.clock() + ttl, digest,
                         event_id, dict(source_ref) if source_ref is not None else None)
            self.pending[action_id] = p
            self._audit(action_id, "proposed", digest)
            return p

    def approve(self, action_id, *, confirmed_by_local_ui=False):
        """Accept a caller-asserted test flag; never treat it as Android consent proof."""
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

    def dispatch_approved(self, action_id):
        """Export one locally approved request for a separately consented companion."""
        with self.lock:
            p = self.approved.pop(action_id, None)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "dispatch_denied")
                raise ControlDenied("approved action unavailable")
            if action_id in self.dispatched:
                self._audit(action_id, "dispatch_replay_denied", p.digest)
                raise ControlDenied("action already dispatched")
            self.dispatched[action_id] = p
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
                "android_os_permission_required": True,
                "permission_bypass": False,
                "model_authority": False,
            }

    def consume_dispatched(self, action_id):
        """Consume a dispatched request once before verifying its companion receipt."""
        with self.lock:
            p = self.dispatched.pop(action_id, None)
            if p is None or self.stopped or self.clock() > p.expires_at:
                self._audit(action_id, "companion_receipt_denied")
                raise ControlDenied("dispatched action unavailable")
            self._audit(action_id, "companion_receipt_pending", p.digest)
            return p

    def record_companion_receipt(self, action_id, digest, *, verified):
        if type(verified) is not bool:
            raise ControlDenied("invalid receipt result")
        with self.lock:
            self._audit(action_id, "companion_receipt_verified" if verified else
                        "companion_receipt_rejected", digest)

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
