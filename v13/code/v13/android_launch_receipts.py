"""Verify native-companion launch receipts before treating them as trusted events.

Evidence adapter only: native Android app must independently enforce permissions,
consent, stop switch and signature verification. Python is not the OS boundary.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Callable

class ReceiptRejected(ValueError):
    pass

@dataclass(frozen=True)
class LaunchOutcome:
    action_id: str
    package: str
    status: str
    source: str = "ANDROID_COMPANION_ATTESTED"

def canonical_receipt(data: dict) -> bytes:
    if type(data) is not dict or set(data) != {"action_id", "package", "status", "request_digest", "nonce"}:
        raise ReceiptRejected("receipt fields")
    action_id, package, status, digest, nonce = (data[k] for k in ("action_id", "package", "status", "request_digest", "nonce"))
    if any(type(x) is not str for x in (action_id, package, status, digest, nonce)):
        raise ReceiptRejected("receipt types")
    if not (len(action_id) == 32 and all(c in '0123456789abcdef' for c in action_id)):
        raise ReceiptRejected("action id")
    if not (1 <= len(package) <= 180 and '.' in package and all(c.isascii() and (c.isalnum() or c in '._') for c in package)):
        raise ReceiptRejected("package")
    if status not in ("LAUNCHED", "DENIED", "FAILED"):
        raise ReceiptRejected("status")
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ReceiptRejected("digest")
    if not (16 <= len(nonce) <= 128 and nonce.isascii() and nonce.isalnum()):
        raise ReceiptRejected("nonce")
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

class NativeLaunchReceiptInbox:
    """Only accepts native-verifier-backed, approved-request-bound receipts."""
    def __init__(self, db_path, verify_native: Callable[[bytes, str], bool]):
        if not callable(verify_native):
            raise TypeError("native signature verifier required")
        self.verify_native = verify_native
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("CREATE TABLE IF NOT EXISTS native_launch_receipts (action_id TEXT PRIMARY KEY, nonce TEXT UNIQUE NOT NULL, payload_sha256 TEXT NOT NULL, status TEXT NOT NULL)")
        self.db.commit()

    def accept(self, receipt: dict, signature: str, expected_request: dict) -> LaunchOutcome:
        payload = canonical_receipt(receipt)
        if type(signature) is not str or not signature or len(signature) > 4096:
            raise ReceiptRejected("signature")
        if type(expected_request) is not dict or set(expected_request) != {"action_id", "package", "request_digest"}:
            raise ReceiptRejected("expected request")
        if any(receipt[k] != expected_request[k] for k in expected_request):
            raise ReceiptRejected("request mismatch")
        if self.db.execute("SELECT 1 FROM native_launch_receipts WHERE action_id=? OR nonce=?", (receipt['action_id'], receipt['nonce'])).fetchone():
            raise ReceiptRejected("replayed receipt")
        try:
            verified = self.verify_native(payload, signature)
        except Exception as exc:
            raise ReceiptRejected("native verifier failed") from exc
        if verified is not True:
            raise ReceiptRejected("unverified native receipt")
        try:
            self.db.execute("INSERT INTO native_launch_receipts VALUES (?,?,?,?)", (receipt['action_id'], receipt['nonce'], hashlib.sha256(payload).hexdigest(), receipt['status']))
            self.db.commit()
        except sqlite3.IntegrityError as exc:
            raise ReceiptRejected("replayed receipt") from exc
        return LaunchOutcome(receipt['action_id'], receipt['package'], receipt['status'])

    def close(self):
        self.db.close()
