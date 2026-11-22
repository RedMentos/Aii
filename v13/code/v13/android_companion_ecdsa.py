"""Pinned P-256 verifier for the native Android Keystore companion.

The public key must be paired and pinned out of band. The receipt only attests
that the companion UI approved a request and dispatched an API call; it never
proves foreground observation or grants T8 learning authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import threading
import time

from .android_companion_protocol import CompanionDenied, SCHEMA

_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_A = _P - 3
_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_G = (
    0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
    0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
)
_FIELDS = {
    "schema", "nonce", "action_id", "capability", "digest", "issued_at",
    "expires_at", "status", "local_consent", "observed",
    "os_permission_status", "key_storage_status", "key_id",
}


def _point_add(left, right):
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if left == right:
        slope = ((3 * x1 * x1 + _A) * pow(2 * y1, -1, _P)) % _P
    else:
        slope = ((y2 - y1) * pow((x2 - x1) % _P, -1, _P)) % _P
    x3 = (slope * slope - x1 - x2) % _P
    y3 = (slope * (x1 - x3) - y1) % _P
    return x3, y3


def _point_mul(scalar, point):
    result = None
    addend = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1
    return result


def _decode_der_signature(data):
    """Decode the short DER SEQUENCE of two positive ECDSA integers."""
    raw = memoryview(data)
    if len(raw) < 8 or raw[0] != 0x30:
        raise ValueError("invalid ECDSA DER sequence")

    def read_length(pos):
        first = raw[pos]
        pos += 1
        if first < 0x80:
            return first, pos
        count = first & 0x7F
        if count == 0 or count > 2 or pos + count > len(raw):
            raise ValueError("invalid DER length")
        if raw[pos] == 0:
            raise ValueError("non-minimal DER length")
        length = int.from_bytes(raw[pos:pos + count], "big")
        if length < 0x80:
            raise ValueError("non-minimal DER long length")
        return length, pos + count

    total, pos = read_length(1)
    if pos + total != len(raw):
        raise ValueError("DER sequence length mismatch")
    values = []
    for _ in range(2):
        if pos >= len(raw) or raw[pos] != 0x02:
            raise ValueError("missing DER integer")
        length, pos = read_length(pos + 1)
        if length < 1 or pos + length > len(raw):
            raise ValueError("invalid DER integer length")
        integer_bytes = bytes(raw[pos:pos + length])
        pos += length
        if integer_bytes[0] & 0x80 or (len(integer_bytes) > 1 and integer_bytes[0] == 0 and not integer_bytes[1] & 0x80):
            raise ValueError("non-canonical DER integer")
        values.append(int.from_bytes(integer_bytes, "big"))
    if pos != len(raw):
        raise ValueError("trailing DER bytes")
    r, s = values
    if not (1 <= r < _N and 1 <= s < _N):
        raise ValueError("ECDSA scalar out of range")
    return r, s


def _verify(public_point, message, signature_der):
    r, s = _decode_der_signature(signature_der)
    z = int.from_bytes(hashlib.sha256(message).digest(), "big")
    inverse = pow(s, -1, _N)
    candidate = _point_add(
        _point_mul((z * inverse) % _N, _G),
        _point_mul((r * inverse) % _N, public_point),
    )
    return candidate is not None and candidate[0] % _N == r


class ECDSAReceiptVerifier:
    """Verify AndroidKeyStore P-256 receipts with a previously pinned public key."""

    def __init__(self, path, public_key_sec1: bytes, expected_key_id: str, *, clock=None):
        if type(public_key_sec1) is not bytes or len(public_key_sec1) != 65 or public_key_sec1[0] != 4:
            raise ValueError("expected uncompressed P-256 SEC1 public key")
        x = int.from_bytes(public_key_sec1[1:33], "big")
        y = int.from_bytes(public_key_sec1[33:], "big")
        if x >= _P or y >= _P or (y * y - (x * x * x + _A * x + _B)) % _P:
            raise ValueError("public key is not on P-256")
        actual_key_id = hashlib.sha256(public_key_sec1).hexdigest()
        if type(expected_key_id) is not str or actual_key_id != expected_key_id:
            raise ValueError("pinned public-key fingerprint mismatch")
        self.public_point = (x, y)
        self.key_id = actual_key_id
        self.clock = clock or time.time
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.RLock()
        self.db.execute("CREATE TABLE IF NOT EXISTS used_receipts (nonce TEXT PRIMARY KEY, action_id TEXT NOT NULL)")
        self.db.commit()
        self.stopped = True

    def start(self):
        with self.lock:
            self.stopped = False

    def stop(self):
        with self.lock:
            self.stopped = True

    def verify(self, envelope, receipt, *, consume_nonce=True):
        if type(consume_nonce) is not bool:
            raise CompanionDenied("invalid nonce policy")
        with self.lock:
            if self.stopped:
                raise CompanionDenied("stopped")
            if type(envelope) is not dict or type(receipt) is not dict or set(receipt) != {"body", "key_id", "signature"}:
                raise CompanionDenied("invalid receipt")
            body = receipt["body"]
            if type(body) is not dict or set(body) != _FIELDS:
                raise CompanionDenied("invalid fields")
            if len(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)) > 4096:
                raise CompanionDenied("receipt too large")
            for key in ("schema", "nonce", "action_id", "capability", "digest", "status",
                        "os_permission_status", "key_storage_status", "key_id"):
                if type(body[key]) is not str:
                    raise CompanionDenied("invalid types")
            status_map = {
                "DISPATCHED_UNVERIFIED": (True, "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
                                          "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"),
                "USER_DENIED": (False, "COMPANION_USER_DENIED",
                                "ANDROID_COMPANION_USER_DENIAL"),
                "FAILED_TO_DISPATCH": (True, "COMPANION_DISPATCH_FAILED",
                                       "ANDROID_COMPANION_SIGNED_UI_CONFIRMATION"),
                "OUTCOME_UNKNOWN": (True, "COMPANION_DISPATCH_UNKNOWN",
                                    "ANDROID_COMPANION_RECOVERY_UNKNOWN"),
            }
            mapped = status_map.get(body["status"])
            if (body["schema"] != SCHEMA or mapped is None
                    or body["local_consent"] is not mapped[0] or body["observed"] is not False):
                raise CompanionDenied("invalid signed action outcome")
            if len(body["nonce"]) != 32 or any(c not in "0123456789abcdef" for c in body["nonce"]):
                raise CompanionDenied("invalid nonce")
            if (len(body["action_id"]) != 32 or any(c not in "0123456789abcdef" for c in body["action_id"])
                    or len(body["digest"]) != 64 or any(c not in "0123456789abcdef" for c in body["digest"])):
                raise CompanionDenied("invalid action scope")
            if body["capability"] != "launch_app" or body["os_permission_status"] != "NOT_REQUIRED_FOR_LAUNCH_APP":
                raise CompanionDenied("unsupported capability receipt")
            if body["key_storage_status"] not in {"ANDROID_KEYSTORE_SOFTWARE_BACKED", "ANDROID_KEYSTORE_HARDWARE_BACKED"}:
                raise CompanionDenied("unknown key storage status")
            if type(body["issued_at"]) not in (int, float) or type(body["expires_at"]) not in (int, float):
                raise CompanionDenied("invalid time")
            now = self.clock()
            if not body["issued_at"] <= now <= body["expires_at"] or body["expires_at"] - body["issued_at"] > 60:
                raise CompanionDenied("expired receipt")
            if any(body[k] != envelope.get(k) for k in ("action_id", "capability", "digest")):
                raise CompanionDenied("scope mismatch")
            if body["key_id"] != self.key_id or receipt["key_id"] != self.key_id:
                raise CompanionDenied("untrusted public key")
            if type(receipt["signature"]) is not str:
                raise CompanionDenied("invalid signature type")
            try:
                signature = base64.b64decode(receipt["signature"], validate=True)
                message = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
                valid = _verify(self.public_point, message, signature)
            except Exception as exc:
                raise CompanionDenied("invalid signature") from exc
            if not valid:
                raise CompanionDenied("invalid signature")
            if consume_nonce:
                try:
                    with self.db:
                        self.db.execute("INSERT INTO used_receipts VALUES (?,?)",
                                        (body["nonce"], body["action_id"]))
                except sqlite3.IntegrityError as exc:
                    raise CompanionDenied("replay") from exc
            return {
                "schema": SCHEMA,
                "action_id": body["action_id"],
                "nonce": body["nonce"],
                "status": mapped[1],
                "receipt_status": body["status"],
                "companion_local_consent_claim": body["local_consent"],
                "observed": False,
                "auth_scheme": "ECDSA_P256_SHA256_ANDROID_KEYSTORE",
                "key_storage_status": body["key_storage_status"],
                "android_os_permission_status": body["os_permission_status"],
                "local_approval_evidence": mapped[2],
                "t8_authoritative": False,
            }

    def close(self):
        with self.lock:
            self.stopped = True
            self.db.close()
