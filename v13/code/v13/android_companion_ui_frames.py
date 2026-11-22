"""Verified one-shot Android MediaProjection frame transport.

The companion remains the sole Android capture provider. This module verifies
its pinned P-256 receipt, reads the one-use ContentProvider pipe, checks the
exact signed byte count/hash, and returns a bounded in-memory frame bundle.
It does not call C3, persist screenshots, grant action authority, or enable
learning. Runtime/Perception integration must keep the UI lease open through
all downstream consumers.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from .android_companion_ecdsa import _A, _B, _P, _verify
from .android_companion_transport import (
    AndroidCompanionTransport,
    CompanionTransportError,
    MAX_FRAME_BYTES,
)

MAX_FRAME_PIXELS = 4_000_000
_RECEIPT_SCHEMA = "v14.android-ui-frame-receipt/1"
_FRAME_URI = re.compile(
    r"content://com\.redmentos\.v14\.companion/ui-frame/([0-9a-f]{32})\Z"
)
_NONCE = re.compile(r"[0-9a-f]{32}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {
    "schema", "nonce", "frame_token", "source_id", "capture_session_id",
    "consent_receipt_ref", "capture_method", "capture_scope", "api_level",
    "clock", "event_kind", "start_ms", "end_ms", "finality",
    "action_authority", "learning_authority", "raw_capture_persisted",
    "frame_sha256", "frame_bytes", "frame_width", "frame_height",
    "frame_format", "issued_at", "expires_at", "key_storage_status", "key_id",
}


class FrameReceiptDenied(PermissionError):
    pass


class ECDSAUIFrameReceiptVerifier:
    """Pinned P-256 verifier with durable one-use nonce/token replay protection."""

    def __init__(self, path, public_key_sec1: bytes, expected_key_id: str, *, clock=None):
        if type(public_key_sec1) is not bytes or len(public_key_sec1) != 65 or public_key_sec1[0] != 4:
            raise ValueError("expected uncompressed P-256 SEC1 public key")
        x = int.from_bytes(public_key_sec1[1:33], "big")
        y = int.from_bytes(public_key_sec1[33:], "big")
        if (x >= _P or y >= _P
                or (y * y - (x * x * x - 3 * x + _B)) % _P):
            raise ValueError("public key is not on P-256")
        actual_key_id = hashlib.sha256(public_key_sec1).hexdigest()
        if type(expected_key_id) is not str or actual_key_id != expected_key_id:
            raise ValueError("pinned public-key fingerprint mismatch")
        self.public_point = (x, y)
        self.key_id = actual_key_id
        self.clock = clock or time.time
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS used_ui_frame_receipts ("
            "nonce TEXT PRIMARY KEY, frame_token TEXT NOT NULL UNIQUE, "
            "frame_sha256 TEXT NOT NULL, expires_at INTEGER NOT NULL)"
        )
        self.db.commit()
        self.lock = threading.RLock()
        self.stopped = True

    def start(self):
        with self.lock:
            self.stopped = False

    def stop(self):
        with self.lock:
            self.stopped = True

    def verify(self, receipt: dict, *, consume_nonce=True) -> dict:
        if type(consume_nonce) is not bool:
            raise FrameReceiptDenied("invalid nonce policy")
        with self.lock:
            if self.stopped:
                raise FrameReceiptDenied("frame receipt verifier is stopped")
            if type(receipt) is not dict or set(receipt) != {"body", "key_id", "signature"}:
                raise FrameReceiptDenied("invalid signed frame receipt envelope")
            body = receipt["body"]
            if type(body) is not dict or set(body) != _FIELDS:
                raise FrameReceiptDenied("frame receipt fields are incomplete or unexpected")
            if receipt.get("key_id") != self.key_id or body.get("key_id") != self.key_id:
                raise FrameReceiptDenied("frame receipt key does not match the pinned companion")
            try:
                encoded_body = json.dumps(
                    body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                ).encode("ascii")
                signature = base64.b64decode(receipt["signature"], validate=True)
            except Exception as exc:
                raise FrameReceiptDenied("invalid frame receipt encoding") from exc
            if len(encoded_body) > 4096 or not _verify(self.public_point, encoded_body, signature):
                raise FrameReceiptDenied("invalid frame receipt signature")

            nonce = body["nonce"]
            token = body["frame_token"]
            if (body["schema"] != _RECEIPT_SCHEMA
                    or type(nonce) is not str or not _NONCE.fullmatch(nonce)
                    or type(token) is not str or not _NONCE.fullmatch(token)):
                raise FrameReceiptDenied("invalid frame receipt identity")
            if (body["source_id"] != "ui-" + nonce
                    or body["capture_session_id"] != "mp-" + nonce
                    or body["consent_receipt_ref"] != "mp-" + nonce):
                raise FrameReceiptDenied("frame receipt source/session binding mismatch")
            if (body["capture_method"] != "MEDIA_PROJECTION"
                    or body["capture_scope"] != "FULL_DISPLAY"
                    or body["clock"] != "ELAPSED_REALTIME"
                    or body["event_kind"] != "SCREEN_FRAME_AVAILABLE"
                    or body["finality"] != "FINAL"):
                raise FrameReceiptDenied("unsupported MediaProjection frame contract")
            if (body["action_authority"] is not False
                    or body["learning_authority"] is not False
                    or body["raw_capture_persisted"] is not False):
                raise FrameReceiptDenied("frame receipt attempted to grant authority or persistence")
            if (type(body["api_level"]) is not int or not 21 <= body["api_level"] <= 99
                    or type(body["start_ms"]) is not int or type(body["end_ms"]) is not int
                    or body["start_ms"] < 0 or body["end_ms"] <= body["start_ms"]
                    or body["end_ms"] - body["start_ms"] > 5000):
                raise FrameReceiptDenied("invalid monotonic capture interval")
            if (type(body["frame_sha256"]) is not str or not _SHA256.fullmatch(body["frame_sha256"])
                    or type(body["frame_bytes"]) is not int
                    or not 1 <= body["frame_bytes"] <= MAX_FRAME_BYTES
                    or type(body["frame_width"]) is not int or type(body["frame_height"]) is not int
                    or body["frame_width"] < 1 or body["frame_height"] < 1
                    or body["frame_width"] * body["frame_height"] > MAX_FRAME_PIXELS
                    or body["frame_format"] != "image/jpeg"):
                raise FrameReceiptDenied("invalid signed frame dimensions or encoding")
            if (type(body["issued_at"]) is not int or type(body["expires_at"]) is not int
                    or body["expires_at"] <= body["issued_at"]
                    or body["expires_at"] - body["issued_at"] > 30
                    or not body["issued_at"] <= self.clock() <= body["expires_at"]):
                raise FrameReceiptDenied("frame receipt expired or has an invalid lifetime")
            if (type(body["key_storage_status"]) is not str
                    or not body["key_storage_status"] or len(body["key_storage_status"]) > 64):
                raise FrameReceiptDenied("invalid companion key-storage status")

            if consume_nonce:
                try:
                    with self.db:
                        self.db.execute(
                            "INSERT INTO used_ui_frame_receipts "
                            "(nonce,frame_token,frame_sha256,expires_at) VALUES (?,?,?,?)",
                            (nonce, token, body["frame_sha256"], body["expires_at"]),
                        )
                except sqlite3.IntegrityError as exc:
                    raise FrameReceiptDenied("frame receipt replay") from exc
            return dict(body)

    def close(self):
        with self.lock:
            self.stopped = True
            self.db.close()


class AndroidCompanionFrameProvider:
    """Read and verify a single user-approved frame from the paired companion."""

    def __init__(self, transport: AndroidCompanionTransport,
                 verifier: ECDSAUIFrameReceiptVerifier):
        self.transport = transport
        self.verifier = verifier

    def _capability_ready(self):
        capabilities = self.transport.capabilities()
        if (type(capabilities) is not dict
                or capabilities.get("enabled") is not True
                or capabilities.get("termux_paired") is not True):
            raise FrameReceiptDenied("companion must be paired and explicitly enabled")
        items = capabilities.get("capabilities")
        if type(items) is not list:
            raise FrameReceiptDenied("companion capability registry is unavailable")
        screen = next((item for item in items
                       if type(item) is dict and item.get("capability") == "screen_capture"), None)
        if not screen or screen.get("status") != "READY_WITH_PER_SESSION_OS_CONSENT":
            raise FrameReceiptDenied("one-shot screen capture is not available")

    def status(self) -> dict:
        """Verify current frame metadata without consuming its one-use nonce or bytes."""
        self._capability_ready()
        response = self.transport.screen_frame_status()
        if response.get("status") != "FRAME_READY":
            return {"status": response.get("status", "UNAVAILABLE")}
        self.verifier.start()
        body = self.verifier.verify(response.get("receipt"), consume_nonce=False)
        uri = response.get("frame_uri")
        match = _FRAME_URI.fullmatch(uri) if isinstance(uri, str) else None
        if not match or match.group(1) != body["frame_token"]:
            raise FrameReceiptDenied("frame URI is not bound to the signed token")
        return {
            "status": "FRAME_READY",
            "source_id": body["source_id"],
            "capture_session_id": body["capture_session_id"],
            "capture_method": body["capture_method"],
            "capture_scope": body["capture_scope"],
            "api_level": body["api_level"],
            "frame_bytes": body["frame_bytes"],
            "frame_width": body["frame_width"],
            "frame_height": body["frame_height"],
            "frame_sha256_prefix": body["frame_sha256"][:12],
            "expires_in_ms": response.get("expires_in_ms"),
            "action_authority": False,
            "learning_authority": False,
            "raw_capture_persisted": False,
        }

    def read_once(self) -> dict:
        """Consume the signed one-use pipe and return a mutable, hash-bound frame bundle."""
        self._capability_ready()
        response = self.transport.screen_frame_status()
        if response.get("status") != "FRAME_READY":
            raise FrameReceiptDenied("no current one-shot frame is available")
        self.verifier.start()
        body = self.verifier.verify(response.get("receipt"), consume_nonce=True)
        uri = response.get("frame_uri")
        match = _FRAME_URI.fullmatch(uri) if isinstance(uri, str) else None
        if not match or match.group(1) != body["frame_token"]:
            raise FrameReceiptDenied("frame URI is not bound to the signed token")
        raw = self.transport.read_frame(uri, max_bytes=body["frame_bytes"])
        frame = bytearray(raw)
        digest = hashlib.sha256(frame).hexdigest()
        if len(frame) != body["frame_bytes"] or digest != body["frame_sha256"]:
            frame[:] = b"\x00" * len(frame)
            raise FrameReceiptDenied("one-shot frame bytes do not match the signed receipt")

        observation = {
            "schema": "v14.a5.ui-observation/1",
            "modality": "ui",
            "source_id": body["source_id"],
            "capture_session_id": body["capture_session_id"],
            "consent_receipt_ref": body["consent_receipt_ref"],
            "capture_method": body["capture_method"],
            "capture_scope": body["capture_scope"],
            "api_level": body["api_level"],
            "clock": body["clock"],
            "event_kind": body["event_kind"],
            "start_ms": body["start_ms"],
            "end_ms": body["end_ms"],
            "finality": body["finality"],
            "action_authority": False,
            "learning_authority": False,
            "raw_capture_persisted": False,
        }

        def verify_frame(candidate_observation, candidate_sha256, candidate_size):
            return bool(
                type(candidate_observation) is dict
                and candidate_observation == observation
                and candidate_sha256 == body["frame_sha256"]
                and type(candidate_size) is int
                and candidate_size == body["frame_bytes"]
            )

        return {
            "observation": observation,
            "frame_buffer": frame,
            "receipt_body": body,
            "verify_frame": verify_frame,
            "frame_verifier": None,
            "perception_contract": (
                "After the V14 RAW EYE module is present, issue its one-shot "
                "ProviderFrameVerifier from this verified observation and verify_frame callback."
            ),
        }

    def close(self):
        self.verifier.stop()



class _UIFrameGrantState:
    """Local mirror of the companion's short-lived, revocable one-frame lease."""

    def __init__(self, observation, transport, verifier, receipt_body):
        self.observation = observation
        self.transport = transport
        self.verifier = verifier
        self.receipt_body = receipt_body
        self.lock = threading.RLock()
        self.active = True
        self.subscribers = []
        self.stop_event = threading.Event()
        self.thread = None

    def _matches(self, source_id, receipt, session_id, operation, method, scope, api_level):
        obs = self.observation
        return (
            source_id == obs["source_id"]
            and receipt == obs["consent_receipt_ref"]
            and session_id == obs["capture_session_id"]
            and operation == "observe_ui"
            and method == obs["capture_method"]
            and scope == obs["capture_scope"]
            and api_level == obs["api_level"]
        )

    def consent_check(self, *args):
        with self.lock:
            return self.active is True and self._matches(*args)

    @contextmanager
    def consent_guard(self, *args):
        with self.lock:
            yield self.active is True and self._matches(*args)

    def revocation_subscribe(
        self, source_id, receipt, session_id, operation, method, scope, api_level,
        on_revoke_requested, on_revoked,
    ):
        if (not self._matches(source_id, receipt, session_id, operation, method, scope, api_level)
                or not callable(on_revoke_requested) or not callable(on_revoked)):
            raise FrameReceiptDenied("invalid UI frame revocation subscription")
        entry = (on_revoke_requested, on_revoked)
        with self.lock:
            if not self.active:
                raise FrameReceiptDenied("UI frame grant is already revoked")
            self.subscribers.append(entry)

        def unsubscribe():
            with self.lock:
                if entry in self.subscribers:
                    self.subscribers.remove(entry)

        return unsubscribe

    def revoke(self):
        # First phase runs before acquiring the same lock used by consent_guard.
        with self.lock:
            if not self.active:
                return False
            callbacks = list(self.subscribers)
        for request_cancel, _ in callbacks:
            try:
                request_cancel()
            except Exception:
                pass
        with self.lock:
            if not self.active:
                return False
            self.active = False
            callbacks = list(self.subscribers)
            self.subscribers.clear()
        # Second phase runs after releasing the provider lock.
        for _, cleanup in callbacks:
            try:
                cleanup()
            except Exception:
                pass
        return True

    def finish(self):
        """Normal turn completion: release cache/subscription without cancelling the finished turn."""
        self.stop_event.set()
        with self.lock:
            if not self.active:
                return
            self.active = False
            callbacks = list(self.subscribers)
            self.subscribers.clear()
        for _, cleanup in callbacks:
            try:
                cleanup()
            except Exception:
                pass

    def start_polling(self):
        if self.thread is not None:
            return
        expected = self.receipt_body

        def poll():
            while not self.stop_event.wait(0.5):
                try:
                    status = self.transport.screen_frame_status()
                    if status.get("status") not in {"FRAME_READY", "FRAME_CONSUMED"}:
                        self.revoke()
                        return
                    receipt = status.get("receipt")
                    body = self.verifier.verify(receipt, consume_nonce=False)
                    if (body.get("nonce") != expected["nonce"]
                            or body.get("frame_token") != expected["frame_token"]
                            or body.get("frame_sha256") != expected["frame_sha256"]
                            or body.get("source_id") != expected["source_id"]
                            or type(status.get("expires_in_ms")) is not int
                            or status["expires_in_ms"] <= 0):
                        self.revoke()
                        return
                except Exception:
                    # An unavailable/ambiguous provider status is revocation, not permission.
                    self.revoke()
                    return

        self.thread = threading.Thread(target=poll, name="v14-ui-frame-revocation", daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        thread = self.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self.finish()


class UIFrameGrant:
    """Frame and lease held together while the active Runtime turn consumes C3 context."""

    def __init__(self, bundle, lease, state):
        self.bundle = bundle
        self.observation = bundle["observation"]
        self.lease = lease
        self.state = state
        self._consumed = False

    def consume(self, runtime, *, current_source, goal="", token_budget=512,
                context_budget_chars=320, priority=0, cfg=None):
        if self._consumed:
            raise FrameReceiptDenied("one-shot UI frame was already consumed")
        if not self.lease.active_for(
            runtime, runtime.turn_event.get("brain_generation_id")
        ):
            raise FrameReceiptDenied("UI frame lease is no longer active")
        try:
            from .vision_ui_frame_ingress import (
                _issue_provider_frame_verifier,
                consume_projected_frame,
            )
        except Exception as exc:
            raise FrameReceiptDenied(
                "the V14 RAW EYE consumer is not installed in this checkout"
            ) from exc
        verifier = _issue_provider_frame_verifier(
            self.observation, self.bundle["verify_frame"]
        )
        self._consumed = True
        return consume_projected_frame(
            runtime,
            self.observation,
            self.bundle["frame_buffer"],
            consent_lease=self.lease,
            frame_verifier=verifier,
            current_source=current_source,
            goal=goal,
            token_budget=token_budget,
            context_budget_chars=context_budget_chars,
            priority=priority,
            cfg=cfg,
        )


@contextmanager
def _open_current_turn(provider, runtime):
    bundle = provider.read_once()
    observation = bundle["observation"]
    event = getattr(runtime, "turn_event", None)
    if (type(event) is not dict or type(event.get("brain_generation_id")) is not str
            or getattr(runtime, "current", None) != "turn"):
        bundle["frame_buffer"][:] = b"\\x00" * len(bundle["frame_buffer"])
        raise FrameReceiptDenied("screen frames can only be consumed inside an active Runtime turn")
    try:
        from .a5_ui_admission_bridge import A5UIRuntimeAdapter
    except Exception as exc:
        bundle["frame_buffer"][:] = b"\\x00" * len(bundle["frame_buffer"])
        raise FrameReceiptDenied("the V14 A5 UI lease consumer is not installed in this checkout") from exc

    state = _UIFrameGrantState(
        observation, provider.transport, provider.verifier, bundle["receipt_body"]
    )
    adapter = A5UIRuntimeAdapter(runtime)
    try:
        with adapter.lease(
            observation, state.consent_check, state.consent_guard, state.revocation_subscribe
        ) as lease:
            state.start_polling()
            yield UIFrameGrant(bundle, lease, state)
    finally:
        state.close()
        # If decoding did not already overwrite the mutable caller buffer, erase it now.
        frame = bundle.get("frame_buffer")
        if type(frame) is bytearray and frame:
            frame[:] = b"\\x00" * len(frame)


AndroidCompanionFrameProvider.open_current_turn = _open_current_turn
