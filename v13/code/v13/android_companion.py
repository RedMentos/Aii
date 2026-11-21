"""Fail-closed client for a separately permissioned Android companion.

The Python/Termux process never performs Android OS actions. It can only send a
single typed request to a user-paired loopback HTTPS companion. The companion
must independently check its OS permissions and show a local confirmation for
every action. No config means OFF. A successful HTTP response is not learning
evidence unless it carries a byte-exact Store SourceRef for an observed result.

Protocol v1 endpoints:
  GET  /v1/capabilities
  POST /v1/actions

The companion server and Android app are not included here; this is the Termux
client contract and remains OFF until a real companion is paired and tested.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import ssl
import stat
import time

from .android_control import CAPABILITIES, ControlDenied, _canonical, _private_audit_db_path

CONFIG_NAME = "android_companion.json"
NONCE_DB_NAME = "android_companion_receipts.sqlite"
CAPABILITY_SCHEMA = "v13.android-companion-capabilities/1"
ACTION_REQUEST_SCHEMA = "v13.android-companion-action-request/1"
ACTION_OUTCOME_SCHEMA = "v13.android-companion-action-outcome/1"
MAX_RESPONSE_BYTES = 64 * 1024
MAX_GRANT_TTL_S = 300.0
ACTION_TTL_S = 30.0
HEX32 = re.compile(r"[0-9a-f]{32}\\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\\Z")
PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\\.[A-Za-z0-9_]+)+\\Z")
SAFE_DETAIL_KEYS = frozenset({"package", "screen_id", "elapsed_ms", "api", "state", "display_size"})


class CompanionUnavailable(RuntimeError):
    pass


class CompanionProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompanionConfig:
    host: str
    port: int
    certificate_sha256: str
    companion_id: str
    timeout_s: float


@dataclass(frozen=True)
class CompanionActionOutcome:
    action_id: str
    capability: str
    status: str
    observed: bool
    evidence_level: str
    timestamp: float
    companion_id: str
    request_digest: str
    source_ref: dict
    user_confirmed: bool
    os_permission_granted: bool
    error_code: str
    details: dict

    def as_record(self):
        return {
            "schema": ACTION_OUTCOME_SCHEMA,
            "action_id": self.action_id,
            "capability": self.capability,
            "status": self.status,
            "observed": self.observed,
            "evidence_level": self.evidence_level,
            "timestamp": self.timestamp,
            "companion_id": self.companion_id,
            "request_digest": self.request_digest,
            "source_ref": dict(self.source_ref),
            "user_confirmed": self.user_confirmed,
            "os_permission_granted": self.os_permission_granted,
            "error_code": self.error_code,
            "details": dict(self.details),
        }


def _load_config(home) -> CompanionConfig:
    root = Path(home)
    permissions = root / "permissions"
    if not permissions.exists():
        raise CompanionUnavailable("COMPANION_OFF")
    try:
        uid_fn = getattr(os, "getuid", None)
        if uid_fn is None or permissions.is_symlink():
            raise CompanionProtocolError("UNSAFE_COMPANION_CONFIG")
        pinfo = permissions.lstat()
        if (not stat.S_ISDIR(pinfo.st_mode) or pinfo.st_uid != uid_fn()
                or stat.S_IMODE(pinfo.st_mode) & 0o077):
            raise CompanionProtocolError("UNSAFE_COMPANION_CONFIG")
        path = permissions / CONFIG_NAME
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid_fn()
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise CompanionProtocolError("UNSAFE_COMPANION_CONFIG")
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CompanionUnavailable("COMPANION_OFF") from exc
    except CompanionProtocolError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise CompanionProtocolError("UNSAFE_COMPANION_CONFIG") from exc
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise CompanionProtocolError("INVALID_COMPANION_CONFIG") from exc
    if type(obj) is not dict or set(obj) != {
        "enabled", "host", "port", "certificate_sha256", "companion_id", "timeout_s"
    }:
        raise CompanionProtocolError("INVALID_COMPANION_CONFIG")
    if obj["enabled"] is not True:
        raise CompanionUnavailable("COMPANION_OFF")
    if obj["host"] != "127.0.0.1":
        raise CompanionProtocolError("COMPANION_MUST_BIND_LOOPBACK")
    if (type(obj["port"]) is not int or not 1024 <= obj["port"] <= 65535
            or type(obj["timeout_s"]) not in (int, float)
            or not 0.2 <= float(obj["timeout_s"]) <= 5.0
            or type(obj["certificate_sha256"]) is not str
            or not HEX64.fullmatch(obj["certificate_sha256"])
            or type(obj["companion_id"]) is not str
            or not HEX32.fullmatch(obj["companion_id"])):
        raise CompanionProtocolError("INVALID_COMPANION_CONFIG")
    return CompanionConfig(
        host=obj["host"], port=obj["port"],
        certificate_sha256=obj["certificate_sha256"],
        companion_id=obj["companion_id"], timeout_s=float(obj["timeout_s"]),
    )


def encode_action_args(args):
    if type(args) is not dict:
        raise ControlDenied("invalid Android action arguments")
    raw = json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_action_args(encoded):
    if type(encoded) is not str or not 1 <= len(encoded) <= 2048:
        raise ControlDenied("invalid Android action argument envelope")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, TypeError) as exc:
        raise ControlDenied("invalid Android action argument envelope") from exc
    if type(value) is not dict:
        raise ControlDenied("invalid Android action arguments")
    return value


def _valid_source_ref(ref):
    return (
        type(ref) is dict
        and set(ref) == {"source_id", "sha256", "char_start", "char_end", "modality"}
        and type(ref.get("source_id")) is str and 1 <= len(ref["source_id"]) <= 128
        and type(ref.get("sha256")) is str and bool(HEX64.fullmatch(ref["sha256"]))
        and type(ref.get("char_start")) is int and type(ref.get("char_end")) is int
        and 0 <= ref["char_start"] <= ref["char_end"]
        and ref.get("modality") == "text"
    )


def trusted_transition_eligible(outcome, store):
    """Only a companion-confirmed observed result with a live exact SourceRef may reach T8."""
    if type(outcome) is not dict or outcome.get("schema") != ACTION_OUTCOME_SCHEMA:
        return False
    try:
        cfg = _load_config(store.home)
        if (outcome.get("companion_id") != cfg.companion_id
                or outcome.get("status") != "SUCCEEDED"
                or outcome.get("observed") is not True
                or outcome.get("evidence_level") != "ANDROID_OS_CONFIRMED"
                or outcome.get("user_confirmed") is not True
                or outcome.get("os_permission_granted") is not True):
            return False
        ref = outcome.get("source_ref")
        if not _valid_source_ref(ref):
            return False
        text = store.read_source(ref)
        return isinstance(text, str) and bool(text)
    except (CompanionUnavailable, CompanionProtocolError, ControlDenied,
            KeyError, TypeError, ValueError, OSError, UnicodeError):
        return False


class CapabilityRegistry:
    """Fresh companion-owned per-capability grants; no local model can write grants."""

    def __init__(self, transport):
        self.transport = transport

    def read(self, config):
        obj = self.transport._request(config, "GET", "/v1/capabilities")
        now = time.time()
        if (type(obj) is not dict
                or obj.get("schema") != CAPABILITY_SCHEMA
                or obj.get("companion_id") != config.companion_id
                or type(obj.get("issued_at")) not in (int, float)
                or type(obj.get("expires_at")) not in (int, float)
                or obj["issued_at"] > now + 15
                or obj["expires_at"] < now
                or obj["expires_at"] - obj["issued_at"] > MAX_GRANT_TTL_S
                or type(obj.get("capabilities")) is not list
                or len(obj["capabilities"]) > len(CAPABILITIES)):
            raise CompanionProtocolError("INVALID_CAPABILITY_REGISTRY")
        grants = {}
        for grant in obj["capabilities"]:
            if type(grant) is not dict or set(grant) != {
                "name", "enabled", "user_granted", "os_permission_granted",
                "expires_at", "package_allowlist", "max_text_chars"
            }:
                raise CompanionProtocolError("INVALID_CAPABILITY_GRANT")
            name = grant["name"]
            if (name not in CAPABILITIES or name in grants
                    or type(grant["enabled"]) is not bool
                    or type(grant["user_granted"]) is not bool
                    or type(grant["os_permission_granted"]) is not bool
                    or type(grant["expires_at"]) not in (int, float)
                    or grant["expires_at"] > obj["expires_at"]
                    or type(grant["package_allowlist"]) is not list
                    or len(grant["package_allowlist"]) > 128
                    or any(type(p) is not str or not PACKAGE.fullmatch(p)
                           for p in grant["package_allowlist"])
                    or type(grant["max_text_chars"]) is not int
                    or not 0 <= grant["max_text_chars"] <= 256):
                raise CompanionProtocolError("INVALID_CAPABILITY_GRANT")
            grants[name] = grant
        return grants

    @staticmethod
    def allows(name, args, grants):
        grant = grants.get(name)
        if (not grant or grant["enabled"] is not True
                or grant["user_granted"] is not True
                or grant["os_permission_granted"] is not True
                or grant["expires_at"] < time.time()):
            return False
        if name == "launch_app":
            return args.get("package") in grant["package_allowlist"]
        if name == "type_text":
            return len(args.get("text", "")) <= grant["max_text_chars"]
        return True


class AndroidCompanionTransport:
    """Pinned-loopback HTTPS client. The Android companion remains the only OS executor."""

    def __init__(self, home, *, connection_factory=None, id_factory=None, nonce_factory=None):
        self.home = Path(home)
        self.connection_factory = connection_factory or self._connection
        self.id_factory = id_factory or (lambda: secrets.token_hex(16))
        self.nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self.registry = CapabilityRegistry(self)

    @staticmethod
    def _connection(config):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return http.client.HTTPSConnection(
            config.host, config.port, context=context, timeout=config.timeout_s
        )

    def _request(self, config, method, path, payload=None):
        if path not in {"/v1/capabilities", "/v1/actions"}:
            raise CompanionProtocolError("INVALID_COMPANION_ENDPOINT")
        conn = self.connection_factory(config)
        try:
            conn.connect()
            if conn.sock is None:
                raise CompanionUnavailable("COMPANION_UNAVAILABLE")
            cert = conn.sock.getpeercert(binary_form=True)
            fingerprint = hashlib.sha256(cert).hexdigest()
            if fingerprint != config.certificate_sha256:
                raise CompanionProtocolError("COMPANION_CERT_PIN_MISMATCH")
            body = None if payload is None else json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            headers = {"Accept": "application/json", "Connection": "close"}
            if body is not None:
                headers["Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                raise CompanionUnavailable("COMPANION_HTTP_" + str(response.status))
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise CompanionProtocolError("COMPANION_RESPONSE_TOO_LARGE")
            obj = json.loads(raw.decode("utf-8"))
            if type(obj) is not dict:
                raise CompanionProtocolError("INVALID_COMPANION_RESPONSE")
            return obj
        except (CompanionUnavailable, CompanionProtocolError):
            raise
        except (OSError, ValueError, UnicodeError, http.client.HTTPException) as exc:
            raise CompanionUnavailable("COMPANION_UNAVAILABLE") from exc
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _record_request(self, request_id, nonce):
        db_path = _private_audit_db_path(self.home / "permissions" / NONCE_DB_NAME)
        db = sqlite3.connect(str(db_path))
        try:
            db.execute(
                "CREATE TABLE IF NOT EXISTS used_requests ("
                "request_id TEXT PRIMARY KEY, nonce TEXT UNIQUE NOT NULL, created REAL NOT NULL)"
            )
            with db:
                db.execute(
                    "INSERT INTO used_requests(request_id,nonce,created) VALUES (?,?,?)",
                    (request_id, nonce, time.time()),
                )
        except sqlite3.IntegrityError as exc:
            raise CompanionProtocolError("COMPANION_REQUEST_REPLAY") from exc
        finally:
            db.close()

    def _unavailable(self, capability, digest, status="UNAVAILABLE", error="COMPANION_OFF"):
        return CompanionActionOutcome(
            action_id=self.id_factory(), capability=capability, status=status,
            observed=False, evidence_level="NONE", timestamp=time.time(),
            companion_id="", request_digest=digest, source_ref={},
            user_confirmed=False, os_permission_granted=False,
            error_code=error, details={},
        )

    def execute(self, capability, args):
        try:
            canonical = _canonical(capability, args)
        except ControlDenied:
            raise
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        try:
            config = _load_config(self.home)
        except CompanionUnavailable:
            return self._unavailable(capability, digest)
        grants = self.registry.read(config)
        if not self.registry.allows(capability, args, grants):
            return self._unavailable(
                capability, digest, status="DENIED", error="CAPABILITY_NOT_GRANTED"
            )
        request_id, nonce = self.id_factory(), self.nonce_factory()
        if not HEX32.fullmatch(request_id) or not HEX32.fullmatch(nonce):
            raise CompanionProtocolError("INVALID_LOCAL_REQUEST_ID")
        self._record_request(request_id, nonce)
        now = time.time()
        payload = {
            "schema": ACTION_REQUEST_SCHEMA,
            "companion_id": config.companion_id,
            "request_id": request_id,
            "nonce": nonce,
            "capability": capability,
            "args": args,
            "args_sha256": digest,
            "issued_at": now,
            "expires_at": now + ACTION_TTL_S,
            "user_confirmation_required": True,
            "os_permission_recheck_required": True,
        }
        response = self._request(config, "POST", "/v1/actions", payload)
        required = {
            "schema", "companion_id", "request_id", "nonce", "capability",
            "args_sha256", "status", "observed", "evidence_level",
            "user_confirmed", "os_permission_granted", "timestamp",
            "source_ref", "error_code", "details"
        }
        if type(response) is not dict or set(response) != required:
            raise CompanionProtocolError("INVALID_ACTION_OUTCOME_SCHEMA")
        if (response["schema"] != ACTION_OUTCOME_SCHEMA
                or response["companion_id"] != config.companion_id
                or response["request_id"] != request_id
                or response["nonce"] != nonce
                or response["capability"] != capability
                or response["args_sha256"] != digest):
            raise CompanionProtocolError("ACTION_OUTCOME_BINDING_MISMATCH")
        status = response["status"]
        if status not in {"SUCCEEDED", "DENIED", "FAILED", "CANCELLED"}:
            raise CompanionProtocolError("INVALID_ACTION_STATUS")
        if (type(response["observed"]) is not bool
                or type(response["user_confirmed"]) is not bool
                or type(response["os_permission_granted"]) is not bool
                or response["evidence_level"] not in {"ANDROID_OS_CONFIRMED", "ACTION_ACK_ONLY", "NONE"}
                or type(response["timestamp"]) not in (int, float)
                or abs(float(response["timestamp"]) - time.time()) > 120
                or type(response["error_code"]) is not str
                or len(response["error_code"]) > 64
                or not response["error_code"].isascii()
                or type(response["details"]) is not dict
                or set(response["details"]) - SAFE_DETAIL_KEYS):
            raise CompanionProtocolError("INVALID_ACTION_OUTCOME_FIELDS")
        source_ref = response["source_ref"]
        if response["observed"]:
            if (status != "SUCCEEDED"
                    or response["evidence_level"] != "ANDROID_OS_CONFIRMED"
                    or response["user_confirmed"] is not True
                    or response["os_permission_granted"] is not True
                    or not _valid_source_ref(source_ref)):
                raise CompanionProtocolError("UNVERIFIED_OBSERVATION")
        elif source_ref is not None:
            raise CompanionProtocolError("UNEXPECTED_ACTION_SOURCE")
        return CompanionActionOutcome(
            action_id=request_id, capability=capability, status=status,
            observed=response["observed"], evidence_level=response["evidence_level"],
            timestamp=float(response["timestamp"]), companion_id=config.companion_id,
            request_digest=digest, source_ref=source_ref or {},
            user_confirmed=response["user_confirmed"],
            os_permission_granted=response["os_permission_granted"],
            error_code=response["error_code"], details=response["details"],
        )


def make_tool(store):
    """Create the ToolRegistry executor; no config or companion means a typed OFF outcome."""
    transport = AndroidCompanionTransport(store.home)

    def execute(capability, args_b64):
        args = decode_action_args(args_b64)
        outcome = transport.execute(capability, args)
        return outcome.as_record()

    return execute


def preview_tool(capability, args_b64):
    """Non-effecting approval preview; never reveals typed text."""
    args = decode_action_args(args_b64)
    _canonical(capability, args)
    if capability == "launch_app":
        target = args["package"]
    elif capability == "type_text":
        target = "focused input field (text hidden until local approval)"
    else:
        target = capability
    return {
        "effect": "Android companion request; local per-call and companion confirmation required",
        "target": target,
        "native_android_executed": False,
    }
