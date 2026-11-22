"""Verify one-shot signed Android microphone results and feed the existing RAW EAR Runtime.

This module is a Termux-side consumer only. It does not request permissions, open
AudioRecord, fetch data, persist PCM, transcribe, identify speakers, or grant learning
or action authority. Core/QA must provide the separate visible Android capture provider.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .android_companion_ecdsa import ECDSAReceiptVerifier, _verify
from .audio_input import submit_audio_only

REQUEST_SCHEMA = "v14.android-audio-capture-request/1"
RESULT_SCHEMA = "v14.android-audio-capture-result/1"
RECEIPT_SCHEMA = "v14.android-audio-capture-receipt/1"
PURPOSE = "RAW_EAR_ACOUSTIC_CONTEXT"
SOURCE_ID = "android.mic"
SAMPLE_RATE = 16000
MAX_DURATION_MS = 1000

_REQUEST_FIELDS = frozenset({
    "schema", "request_id", "issued_at", "expires_at", "duration_ms",
    "sample_rate", "channels", "encoding", "purpose", "permission_bypass",
    "model_authority", "digest",
})
_RESULT_FIELDS = frozenset({"schema", "status", "request_id", "pcm16_base64", "receipt"})
_RECEIPT_FIELDS = frozenset({
    "schema", "nonce", "request_id", "request_digest", "source_id",
    "generation_id", "start_monotonic_ns", "end_monotonic_ns", "sample_rate",
    "channels", "sample_count", "encoding", "audio_source",
    "permission_granted", "os_permission_status", "consent_result",
    "local_consent", "finality", "pcm_sha256", "issued_at", "expires_at",
    "key_id", "key_storage_status",
})
_HEX32 = re.compile(r"[0-9a-f]{32}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class AudioCaptureDenied(PermissionError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _finite_time(value) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _valid_hex(value, pattern) -> bool:
    return type(value) is str and pattern.fullmatch(value) is not None


def audio_capture_request_digest(request: dict) -> str:
    if type(request) is not dict:
        raise AudioCaptureDenied("request must be an object")
    body = {key: value for key, value in request.items() if key != "digest"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def build_audio_capture_request(
    *, request_id: str | None = None, now: float | None = None, ttl_s: int = 30
) -> dict:
    """Build a bounded request; this does not contact Android or request permission."""
    if now is not None and type(now) not in (int, float):
        raise ValueError("invalid audio request clock or TTL")
    try:
        current = float(time.time() if now is None else now)
    except (OverflowError, ValueError):
        raise ValueError("invalid audio request clock or TTL") from None
    if not math.isfinite(current) or type(ttl_s) is not int or not 1 <= ttl_s <= 60:
        raise ValueError("invalid audio request clock or TTL")
    request_id = secrets.token_hex(16) if request_id is None else request_id
    if not _valid_hex(request_id, _HEX32):
        raise ValueError("request_id must be 32 lowercase hex characters")
    request = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "issued_at": int(current),
        "expires_at": int(current) + ttl_s,
        "duration_ms": MAX_DURATION_MS,
        "sample_rate": SAMPLE_RATE,
        "channels": 1,
        "encoding": "pcm_s16le",
        "purpose": PURPOSE,
        "permission_bypass": False,
        "model_authority": False,
    }
    request["digest"] = audio_capture_request_digest(request)
    return request


def _validate_request(request: dict, now: float) -> None:
    if type(request) is not dict or set(request) != _REQUEST_FIELDS:
        raise AudioCaptureDenied("audio request fields mismatch")
    if request["schema"] != REQUEST_SCHEMA or not _valid_hex(request["request_id"], _HEX32):
        raise AudioCaptureDenied("invalid audio request identity")
    if (
        type(request["issued_at"]) not in (int, float)
        or type(request["expires_at"]) not in (int, float)
        or not _finite_time(request["issued_at"])
        or not _finite_time(request["expires_at"])
    ):
        raise AudioCaptureDenied("invalid audio request time")
    if (
        not request["issued_at"] <= now <= request["expires_at"]
        or request["expires_at"] - request["issued_at"] > 60
    ):
        raise AudioCaptureDenied("audio request expired")
    if (
        type(request["duration_ms"]) is not int
        or not 1 <= request["duration_ms"] <= MAX_DURATION_MS
        or type(request["sample_rate"]) is not int
        or request["sample_rate"] != SAMPLE_RATE
        or type(request["channels"]) is not int
        or request["channels"] != 1
        or request["encoding"] != "pcm_s16le"
        or request["purpose"] != PURPOSE
        or request["permission_bypass"] is not False
        or request["model_authority"] is not False
    ):
        raise AudioCaptureDenied("unsupported audio request configuration")
    if (
        not _valid_hex(request["digest"], _HEX64)
        or audio_capture_request_digest(request) != request["digest"]
    ):
        raise AudioCaptureDenied("audio request digest mismatch")


@dataclass(frozen=True)
class VerifiedAudioCapture:
    request_id: str
    generation_id: str
    source_id: str
    start_ms: int
    sample_rate: int
    sample_count: int
    audio_source: str
    pcm_sha256: str
    receipt_ref: str
    pcm16: bytes = field(repr=False)
    finality: str = "FINAL"
    learning_authority: bool = False
    speaker_identity_authority: bool = False
    action_authority: bool = False


class AudioCaptureReceiptVerifier:
    """P-256 verifier reusing the companion's pinned key and durable nonce ledger."""

    def __init__(
        self,
        path: str | Path,
        public_key_sec1: bytes,
        expected_key_id: str,
        *,
        clock: Callable[[], float] | None = None,
    ):
        self._base = ECDSAReceiptVerifier(
            path, public_key_sec1, expected_key_id, clock=clock
        )
        self._base.start()
        with self._base.lock:
            self._base.db.execute(
                "CREATE TABLE IF NOT EXISTS used_audio_requests "
                "(request_id TEXT PRIMARY KEY, nonce TEXT UNIQUE NOT NULL)"
            )
            self._base.db.commit()

    def verify(
        self,
        request: dict,
        result: dict,
        *,
        expected_generation: str,
        consent_check: Callable,
    ) -> VerifiedAudioCapture:
        with self._base.lock:
            if self._base.stopped:
                raise AudioCaptureDenied("audio receipt verifier stopped")
            if not callable(consent_check):
                raise AudioCaptureDenied("live consent preflight is required")
            now = float(self._base.clock())
            _validate_request(request, now)
            if (
                type(expected_generation) is not str
                or not expected_generation
                or len(expected_generation) > 128
            ):
                raise AudioCaptureDenied("expected Runtime generation is required")
            if type(result) is not dict or set(result) != _RESULT_FIELDS:
                raise AudioCaptureDenied("audio result fields mismatch")
            if (
                result["schema"] != RESULT_SCHEMA
                or result["status"] != "CAPTURED"
                or result["request_id"] != request["request_id"]
            ):
                raise AudioCaptureDenied("audio result is not the requested capture")
            if (
                type(result["pcm16_base64"]) is not str
                or len(result["pcm16_base64"]) > 44000
            ):
                raise AudioCaptureDenied("audio PCM encoding is invalid or too large")
            try:
                pcm = base64.b64decode(result["pcm16_base64"], validate=True)
            except Exception as exc:
                raise AudioCaptureDenied("audio PCM base64 is invalid") from exc
            if not pcm or len(pcm) % 2 or len(pcm) > SAMPLE_RATE * 2:
                raise AudioCaptureDenied("audio PCM exceeds the one-second mono bound")

            receipt = result["receipt"]
            if type(receipt) is not dict or set(receipt) != {"body", "key_id", "signature"}:
                raise AudioCaptureDenied("audio receipt envelope is invalid")
            body = receipt["body"]
            if type(body) is not dict or set(body) != _RECEIPT_FIELDS:
                raise AudioCaptureDenied("audio receipt fields mismatch")
            for key in (
                "schema", "nonce", "request_id", "request_digest", "source_id",
                "generation_id", "encoding", "audio_source", "os_permission_status",
                "consent_result", "finality", "pcm_sha256", "key_id", "key_storage_status",
            ):
                if type(body[key]) is not str:
                    raise AudioCaptureDenied("audio receipt field type mismatch")
            if (
                body["schema"] != RECEIPT_SCHEMA
                or not _valid_hex(body["nonce"], _HEX32)
                or body["request_id"] != request["request_id"]
                or body["request_digest"] != request["digest"]
                or body["source_id"] != SOURCE_ID
                or body["generation_id"] != expected_generation
            ):
                raise AudioCaptureDenied(
                    "audio receipt source, generation or request binding mismatch"
                )
            if (
                type(body["start_monotonic_ns"]) is not int
                or body["start_monotonic_ns"] < 0
                or type(body["end_monotonic_ns"]) is not int
                or body["end_monotonic_ns"] <= body["start_monotonic_ns"]
                or body["end_monotonic_ns"] - body["start_monotonic_ns"]
                > request["duration_ms"] * 1_000_000
            ):
                raise AudioCaptureDenied("audio receipt monotonic window invalid")
            if (
                type(body["sample_rate"]) is not int
                or body["sample_rate"] != request["sample_rate"]
                or type(body["channels"]) is not int
                or body["channels"] != 1
                or type(body["sample_count"]) is not int
                or body["sample_count"]
                != request["sample_rate"] * request["duration_ms"] // 1000
                or body["encoding"] != request["encoding"]
                or len(pcm) != body["sample_count"] * 2
            ):
                raise AudioCaptureDenied("audio sample geometry mismatch")
            expected_duration_ns = (
                body["sample_count"] * 1_000_000_000 // body["sample_rate"]
            )
            if (
                body["end_monotonic_ns"] - body["start_monotonic_ns"]
                < expected_duration_ns * 3 // 4
            ):
                raise AudioCaptureDenied(
                    "audio capture duration is too short for its sample count"
                )
            if (
                body["audio_source"] not in {"UNPROCESSED", "MIC"}
                or body["permission_granted"] is not True
                or body["os_permission_status"] != "GRANTED_RECORD_AUDIO"
                or body["consent_result"] != "CAPTURED"
                or body["local_consent"] is not True
                or body["finality"] != "FINAL"
            ):
                raise AudioCaptureDenied("audio capture consent or finality invalid")
            if (
                not _valid_hex(body["pcm_sha256"], _HEX64)
                or hashlib.sha256(pcm).hexdigest() != body["pcm_sha256"]
            ):
                raise AudioCaptureDenied("audio PCM digest mismatch")
            if (
                not _finite_time(body["issued_at"])
                or not _finite_time(body["expires_at"])
                or not body["issued_at"] <= now <= body["expires_at"]
                or body["expires_at"] - body["issued_at"] > 60
                or body["issued_at"] < request["issued_at"]
                or body["expires_at"] > request["expires_at"]
            ):
                raise AudioCaptureDenied("audio receipt expired or outside request lifetime")
            if (
                body["key_storage_status"]
                not in {
                    "ANDROID_KEYSTORE_SOFTWARE_BACKED",
                    "ANDROID_KEYSTORE_HARDWARE_BACKED",
                }
                or body["key_id"] != self._base.key_id
                or receipt["key_id"] != self._base.key_id
            ):
                raise AudioCaptureDenied(
                    "audio receipt key is not the explicitly pinned companion key"
                )
            if type(receipt["signature"]) is not str or len(receipt["signature"]) > 256:
                raise AudioCaptureDenied("audio receipt signature invalid")
            try:
                signature = base64.b64decode(receipt["signature"], validate=True)
                valid = _verify(self._base.public_point, _canonical(body), signature)
            except Exception as exc:
                raise AudioCaptureDenied("audio receipt signature invalid") from exc
            if not valid:
                raise AudioCaptureDenied("audio receipt signature mismatch")

            receipt_ref = hashlib.sha256(_canonical(body)).hexdigest()
            try:
                authorized = consent_check(SOURCE_ID, receipt_ref)
            except Exception as exc:
                raise AudioCaptureDenied("live audio consent preflight failed") from exc
            if authorized is not True:
                raise AudioCaptureDenied("live audio consent is not active")
            try:
                with self._base.db:
                    self._base.db.execute(
                        "INSERT INTO used_receipts(nonce, action_id) VALUES (?,?)",
                        (body["nonce"], body["request_id"]),
                    )
                    self._base.db.execute(
                        "INSERT INTO used_audio_requests(request_id, nonce) VALUES (?,?)",
                        (body["request_id"], body["nonce"]),
                    )
            except sqlite3.IntegrityError as exc:
                raise AudioCaptureDenied("audio receipt replay") from exc
            return VerifiedAudioCapture(
                request_id=body["request_id"],
                generation_id=body["generation_id"],
                source_id=body["source_id"],
                start_ms=body["start_monotonic_ns"] // 1_000_000,
                sample_rate=body["sample_rate"],
                sample_count=body["sample_count"],
                audio_source=body["audio_source"],
                pcm_sha256=body["pcm_sha256"],
                receipt_ref=receipt_ref,
                pcm16=pcm,
            )

    def close(self):
        self._base.close()


def verifier_from_pinned_controller(controller) -> AudioCaptureReceiptVerifier:
    """Reuse the existing explicitly trusted companion key and receipt database."""
    pinned = getattr(controller, "_pinned_key", None)
    path = getattr(controller, "verifier_path", None)
    clock = getattr(controller, "clock", None)
    if not callable(pinned) or path is None or not callable(clock):
        raise AudioCaptureDenied("existing pinned Android companion controller is required")
    try:
        trust, public_key_sec1, _info = pinned()
    except Exception as exc:
        raise AudioCaptureDenied("pinned companion trust lookup failed") from exc
    if type(trust) is not dict or type(public_key_sec1) is not bytes:
        raise AudioCaptureDenied("companion trust record is invalid")
    key_id = trust.get("key_id")
    if (
        not _valid_hex(key_id, _HEX64)
        or hashlib.sha256(public_key_sec1).hexdigest() != key_id
    ):
        raise AudioCaptureDenied("companion key is not explicitly pinned")
    return AudioCaptureReceiptVerifier(path, public_key_sec1, key_id, clock=clock)


def submit_verified_audio_capture(
    runtime,
    request: dict,
    result: dict,
    *,
    verifier: AudioCaptureReceiptVerifier,
    expected_generation: str,
    consent_check: Callable,
    consent_guard: Callable,
    consent_revocation_subscribe: Callable,
):
    """Consume one signed capture exactly once through the existing RAW EAR Runtime path."""
    if not isinstance(verifier, AudioCaptureReceiptVerifier):
        raise TypeError("a pinned AudioCaptureReceiptVerifier is required")
    if not all(
        callable(value)
        for value in (consent_check, consent_guard, consent_revocation_subscribe)
    ):
        raise AudioCaptureDenied(
            "live consent check, linearizable guard and two-phase revocation are required"
        )
    capture = verifier.verify(
        request,
        result,
        expected_generation=expected_generation,
        consent_check=consent_check,
    )
    window = {
        "pcm16": capture.pcm16,
        "sample_rate": capture.sample_rate,
        "start_ms": capture.start_ms,
        "source_id": capture.source_id,
        "consent_receipt": capture.receipt_ref,
        "consent_check": consent_check,
        "consent_guard": consent_guard,
        "consent_revocation_subscribe": consent_revocation_subscribe,
        "finality": "FINAL",
    }
    runtime_result = submit_audio_only(runtime, window)
    return {
        "status": "SUBMIT_RETURNED",
        "request_id": capture.request_id,
        "generation_id": capture.generation_id,
        "source_id": capture.source_id,
        "audio_source": capture.audio_source,
        "sample_rate": capture.sample_rate,
        "sample_count": capture.sample_count,
        "pcm_sha256": capture.pcm_sha256,
        "receipt_ref": capture.receipt_ref,
        "finality": "FINAL",
        "learning_authority": False,
        "speaker_identity_authority": False,
        "action_authority": False,
        "runtime_result": runtime_result,
    }
