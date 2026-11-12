"""Opt-in read-only diagnostic command processor for a PRIVATE outbound relay.

The transport MUST separately authenticate author, verify private-repository
visibility and enforce Android-side consent. This module has no shell/network API.
"""
import hashlib
import fcntl
import json
import os
import re
import tempfile
import time
from pathlib import Path

COMMANDS = {
    "HEALTH": {"ready", "uptime_s", "queue_depth", "stop_latched"},
    "LEARNING_STATUS": {"age", "updates", "pending", "rollback_available"},
    "DIAGNOSTICS_REDACTED": {"error_count", "error_code", "organ", "dropped_events"},
}
IDENT = re.compile(r"^[A-Za-z0-9_-]{12,80}$")


def safe_value(value):
    if type(value) is bool:
        return value
    if type(value) is int and 0 <= value <= 1000000000:
        return value
    if type(value) is str and len(value) <= 40 and re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return value
    return None


class DiagnosticBridge:
    """No device commands; durable request dedup before metric collection."""

    def __init__(self, state_path, *, allowed_authors, metrics, enabled=False, max_seen=512):
        self.path = Path(state_path)
        self.authors = frozenset(allowed_authors)
        self.metrics = metrics
        self.enabled = enabled
        self.max_seen = max(1, min(max_seen, 4096))
        self.seen = self._load()

    def _load(self):
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or len(data) > 4096:
            raise ValueError("invalid bridge state")
        if any(not IDENT.fullmatch(k) or not isinstance(v, str) or
               not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in data.items()):
            raise ValueError("invalid bridge state entries")
        return data

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".bridge-", dir=str(self.path.parent))
        os.fchmod(fd, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.seen, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def handle(self, envelope, *, private_relay, authenticated_author, now=None):
        if not self.enabled or not private_relay or authenticated_author not in self.authors:
            return {"status": "DENIED"}
        if not isinstance(envelope, dict) or set(envelope) != {"id", "command", "expires_at", "author"}:
            return {"status": "INVALID"}
        request_id, command = envelope["id"], envelope["command"]
        if not isinstance(request_id, str) or not IDENT.fullmatch(request_id) or not isinstance(command, str) or command not in COMMANDS:
            return {"status": "INVALID"}
        if envelope["author"] != authenticated_author:
            return {"status": "DENIED"}
        current = int(time.time()) if now is None else now
        expires = envelope["expires_at"]
        if type(expires) is not int or expires < current or expires > current + 300:
            return {"status": "EXPIRED"}
        digest = hashlib.sha256(json.dumps(envelope, sort_keys=True).encode()).hexdigest()
        # Cross-process exclusion: re-read the durable journal under one lock.
        # Never evict unexpired/unknown legacy IDs: reject at capacity instead.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with open(lock_path, "a+b") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                self.seen = self._load()
                if request_id in self.seen:
                    return {"status": "DUPLICATE" if self.seen[request_id] == digest else "REPLAY_CONFLICT", "id": request_id}
                if len(self.seen) >= self.max_seen:
                    return {"status": "CAPACITY", "id": request_id}
                self.seen[request_id] = digest
                self._save()
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        try:
            raw = self.metrics[command]()
            if not hasattr(raw, "items"):
                raise ValueError("invalid metrics")
            filtered = {}
            for key, value in raw.items():
                if key in COMMANDS[command]:
                    safe = safe_value(value)
                    if safe is not None:
                        filtered[key] = safe
            return {"status": "OK", "id": request_id, "command": command, "metrics": filtered}
        except Exception:
            return {"status": "METRICS_UNAVAILABLE", "id": request_id}
