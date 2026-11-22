"""Verify per-install HMAC-authenticated Android receipts; no Android action execution.

This is a protocol prototype, not an asymmetric Android Keystore signature or
proof of OS permission state. The caller must supply a per-install secret.
"""
import hashlib
import hmac
import json
import sqlite3
import time
import threading

SCHEMA = "v14.android-companion-receipt/1"

class CompanionDenied(PermissionError):
    pass

def sign_fixture(secret, body):
    """Fixture signer; real signing belongs to the Android companion."""
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()

class ReceiptVerifier:
    """Fail-closed, durable replay check for independent Android-side consent receipts."""
    def __init__(self, path, secret, *, clock=None):
        if type(secret) is not bytes or len(secret) < 32:
            raise ValueError("per-installation secret must have >=32 bytes")
        self.secret = secret
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
        """Verify a receipt; defer nonce commit only when a caller commits it with its outcome.

        Normal callers keep the default durable verifier ledger. The C5 Store
        consumer uses consume_nonce=False so nonce and packet share one SQLite
        transaction; callers must not discard that verified nonce.
        """
        if type(consume_nonce) is not bool:
            raise CompanionDenied("invalid nonce policy")
        with self.lock:
            return self._verify_locked(envelope, receipt, consume_nonce=consume_nonce)

    def _verify_locked(self, envelope, receipt, *, consume_nonce=True):
        if self.stopped:
            raise CompanionDenied("stopped")
        if type(envelope) is not dict or type(receipt) is not dict or set(receipt) != {"body", "mac"}:
            raise CompanionDenied("invalid receipt")
        b = receipt["body"]
        fields = {"schema", "nonce", "action_id", "capability", "digest", "issued_at",
                  "expires_at", "status", "local_consent"}
        if type(b) is not dict or set(b) != fields:
            raise CompanionDenied("invalid fields")
        if any(type(b[k]) is not str for k in ("schema", "nonce", "action_id", "capability", "digest", "status")):
            raise CompanionDenied("invalid types")
        if b["schema"] != SCHEMA or b["status"] != "EXECUTED" or b["local_consent"] is not True:
            raise CompanionDenied("no confirmed execution")
        if len(b["nonce"]) != 32 or any(c not in "0123456789abcdef" for c in b["nonce"]):
            raise CompanionDenied("invalid nonce")
        if type(b["issued_at"]) not in (int, float) or type(b["expires_at"]) not in (int, float):
            raise CompanionDenied("invalid time")
        now = self.clock()
        if not b["issued_at"] <= now <= b["expires_at"] or b["expires_at"] - b["issued_at"] > 60:
            raise CompanionDenied("expired receipt")
        if any(b[k] != envelope.get(k) for k in ("action_id", "capability", "digest")):
            raise CompanionDenied("scope mismatch")
        if type(receipt["mac"]) is not str or not hmac.compare_digest(sign_fixture(self.secret, b), receipt["mac"]):
            raise CompanionDenied("invalid authentication")
        if consume_nonce:
            try:
                with self.db:
                    self.db.execute("INSERT INTO used_receipts VALUES (?,?)", (b["nonce"], b["action_id"]))
            except sqlite3.IntegrityError as exc:
                raise CompanionDenied("replay") from exc
        return {"schema": SCHEMA, "action_id": b["action_id"],
                "nonce": b["nonce"],
                "status": "COMPANION_ATTESTED_NOT_DEVICE_VERIFIED",
                "auth_scheme": "HMAC_SHA256_PER_INSTALL",
                "key_storage_status": "UNVERIFIED",
                "t8_authoritative": False}

    def close(self):
        with self.lock:
            self.stopped = True
            self.db.close()
