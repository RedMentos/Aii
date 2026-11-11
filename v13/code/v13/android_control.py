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

    A trusted operator UI calls approve(), never the model or an untrusted tool.
    execute() returns a signed-off command envelope, not a claim of Android execution.
    """
    def __init__(self, db_path, *, clock=None):
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
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

    def record_simulated_outcome(self, envelope, outcome):
        """Persist verified simulation result, distinct from command issuance."""
        with self.lock:
            action_id = envelope.get("action_id")
            digest = envelope.get("digest")
            if (envelope.get("status") != "DRY_RUN_ONLY"
                    or not isinstance(action_id, str)
                    or not isinstance(digest, str)
                    or not any(row[0] == action_id and row[1] == "dry_run" and row[2] == digest
                               for row in self.events())):
                raise ControlDenied("unissued simulation outcome")
            if (outcome.action_id != action_id
                    or outcome.capability != envelope.get("capability")
                    or outcome.status != "SIMULATED"
                    or outcome.source != "SIMULATED_COMPANION"):
                self._audit(action_id, "outcome_rejected", digest)
                raise ControlDenied("simulation outcome mismatch")
            if any(row[0] == action_id and row[1] == "simulated_outcome" for row in self.events()):
                raise ControlDenied("duplicate simulation outcome")
            self._audit(action_id, "simulated_outcome", digest)

    def record_simulated_failure(self, envelope):
        """Dispatch failure is not evidence of an Android action."""
        with self.lock:
            self._audit(envelope["action_id"], "simulation_dispatch_failed", envelope["digest"])

    def events(self):
        with self.lock:
            return list(self.db.execute("SELECT action_id,event,digest,at FROM control_audit ORDER BY id"))

    def close(self):
        with self.lock:
            self.stop()
            self.db.close()
