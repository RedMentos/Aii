import base64
import hashlib
import json
from types import SimpleNamespace

import pytest

from v13.android_companion_ecdsa import _G, _N, _point_mul
from v13.android_companion_ui_frames import (
    AndroidCompanionFrameProvider,
    ECDSAUIFrameReceiptVerifier,
    FrameReceiptDenied,
)


def _der_integer(value):
    raw = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return b"\x02" + bytes([len(raw)]) + raw


def _sign(body, private=1, nonce_scalar=2):
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    z = int.from_bytes(hashlib.sha256(encoded).digest(), "big")
    point = _point_mul(nonce_scalar, _G)
    r = point[0] % _N
    s = (pow(nonce_scalar, -1, _N) * (z + r * private)) % _N
    payload = _der_integer(r) + _der_integer(s)
    der = b"\x30" + bytes([len(payload)]) + payload
    x, y = _G
    sec1 = b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")
    key_id = hashlib.sha256(sec1).hexdigest()
    return sec1, key_id, {
        "body": body,
        "key_id": key_id,
        "signature": base64.b64encode(der).decode("ascii"),
    }


def _body(frame, *, issued=1000, expires=1030):
    nonce = "a" * 32
    return {
        "schema": "v14.android-ui-frame-receipt/1",
        "nonce": nonce,
        "frame_token": "b" * 32,
        "source_id": "ui-" + nonce,
        "capture_session_id": "mp-" + nonce,
        "consent_receipt_ref": "mp-" + nonce,
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "api_level": 33,
        "clock": "ELAPSED_REALTIME",
        "event_kind": "SCREEN_FRAME_AVAILABLE",
        "start_ms": 100,
        "end_ms": 120,
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
        "frame_bytes": len(frame),
        "frame_width": 2,
        "frame_height": 2,
        "frame_format": "image/jpeg",
        "issued_at": issued,
        "expires_at": expires,
        "key_storage_status": "ANDROID_KEYSTORE_SOFTWARE_BACKED",
        "key_id": "",
    }


def _verifier(tmp_path, frame, clock=lambda: 1001):
    body = _body(frame)
    sec1, key_id, _ = _sign(body)
    body["key_id"] = key_id
    sec1, key_id, receipt = _sign(body)
    verifier = ECDSAUIFrameReceiptVerifier(tmp_path / "receipts.sqlite", sec1, key_id, clock=clock)
    verifier.start()
    return verifier, receipt, key_id


def test_signed_frame_receipt_verifies_and_nonce_is_one_use(tmp_path):
    frame = b"jpeg"
    verifier, receipt, _ = _verifier(tmp_path, frame)
    try:
        body = verifier.verify(receipt)
        assert body["frame_sha256"] == hashlib.sha256(frame).hexdigest()
        assert body["action_authority"] is False
        assert body["learning_authority"] is False
        assert body["raw_capture_persisted"] is False
        with pytest.raises(FrameReceiptDenied, match="replay"):
            verifier.verify(receipt)
        assert verifier.verify(receipt, consume_nonce=False)["frame_token"] == "b" * 32
    finally:
        verifier.close()


def test_tampered_or_authority_bearing_receipts_are_rejected(tmp_path):
    frame = b"jpeg"
    verifier, receipt, _ = _verifier(tmp_path, frame)
    try:
        tampered = json.loads(json.dumps(receipt))
        tampered["body"]["frame_sha256"] = "c" * 64
        with pytest.raises(FrameReceiptDenied, match="signature"):
            verifier.verify(tampered, consume_nonce=False)

        bad_body = dict(receipt["body"])
        bad_body["learning_authority"] = True
        _, _, bad_receipt = _sign(bad_body)
        with pytest.raises(FrameReceiptDenied, match="authority"):
            verifier.verify(bad_receipt, consume_nonce=False)
    finally:
        verifier.close()


def test_expired_receipt_and_wrong_public_key_fail_closed(tmp_path):
    frame = b"jpeg"
    body = _body(frame, issued=1000, expires=1030)
    sec1, key_id, _ = _sign(body)
    body["key_id"] = key_id
    sec1, key_id, receipt = _sign(body)
    verifier = ECDSAUIFrameReceiptVerifier(tmp_path / "expired.sqlite", sec1, key_id, clock=lambda: 1031)
    verifier.start()
    try:
        with pytest.raises(FrameReceiptDenied, match="expired"):
            verifier.verify(receipt, consume_nonce=False)
    finally:
        verifier.close()

    with pytest.raises(ValueError, match="fingerprint"):
        ECDSAUIFrameReceiptVerifier(tmp_path / "wrong.sqlite", sec1, "0" * 64)


class FakeTransport:
    def __init__(self, frame, receipt, token="b" * 32, status="FRAME_READY", enabled=True):
        self.frame = frame
        self.receipt = receipt
        self.token = token
        self.status_value = status
        self.enabled = enabled
        self.read_calls = 0

    def capabilities(self):
        return {
            "enabled": self.enabled,
            "termux_paired": True,
            "capabilities": [{
                "capability": "screen_capture",
                "status": "READY_WITH_PER_SESSION_OS_CONSENT",
            }],
        }

    def screen_frame_status(self):
        if self.status_value != "FRAME_READY":
            return {"status": self.status_value}
        return {
            "status": "FRAME_READY",
            "receipt": self.receipt,
            "frame_uri": "content://com.redmentos.v14.companion/ui-frame/" + self.token,
            "expires_in_ms": 15000,
        }

    def read_frame(self, uri, *, max_bytes):
        self.read_calls += 1
        assert uri.endswith(self.token)
        assert len(self.frame) <= max_bytes
        return self.frame


def test_provider_returns_only_exact_signed_frame_and_metadata(tmp_path):
    frame = b"jpeg"
    body = _body(frame)
    sec1, key_id, _ = _sign(body)
    body["key_id"] = key_id
    sec1, key_id, receipt = _sign(body)
    verifier = ECDSAUIFrameReceiptVerifier(tmp_path / "provider.sqlite", sec1, key_id, clock=lambda: 1001)
    transport = FakeTransport(frame, receipt)
    provider = AndroidCompanionFrameProvider(transport, verifier)
    try:
        bundle = provider.read_once()
        assert bundle["observation"]["capture_method"] == "MEDIA_PROJECTION"
        assert bundle["observation"]["raw_capture_persisted"] is False
        assert bundle["observation"]["learning_authority"] is False
        assert bundle["observation"]["action_authority"] is False
        assert bundle["frame_buffer"] == bytearray(frame)
        assert bundle["verify_frame"](bundle["observation"], hashlib.sha256(frame).hexdigest(), len(frame))
        assert not bundle["verify_frame"](bundle["observation"], "0" * 64, len(frame))
        assert transport.read_calls == 1
    finally:
        provider.close()


def test_provider_refuses_disabled_companion_or_unbound_frame_uri(tmp_path):
    frame = b"jpeg"
    body = _body(frame)
    sec1, key_id, _ = _sign(body)
    body["key_id"] = key_id
    sec1, key_id, receipt = _sign(body)
    verifier = ECDSAUIFrameReceiptVerifier(tmp_path / "provider-deny.sqlite", sec1, key_id, clock=lambda: 1001)
    disabled = AndroidCompanionFrameProvider(FakeTransport(frame, receipt, enabled=False), verifier)
    try:
        with pytest.raises(FrameReceiptDenied, match="enabled"):
            disabled.read_once()
    finally:
        disabled.close()

    verifier = ECDSAUIFrameReceiptVerifier(tmp_path / "provider-uri.sqlite", sec1, key_id, clock=lambda: 1001)
    transport = FakeTransport(frame, receipt, token="c" * 32)
    provider = AndroidCompanionFrameProvider(transport, verifier)
    try:
        with pytest.raises(FrameReceiptDenied, match="URI"):
            provider.read_once()
    finally:
        provider.close()


def test_runtime_turn_frame_lease_fails_closed_without_raw_eye_consumer(tmp_path):
    frame = bytearray(b"frame")
    observation = {
        "source_id": "ui-" + "a" * 32,
        "capture_session_id": "mp-" + "a" * 32,
        "consent_receipt_ref": "mp-" + "a" * 32,
    }
    provider = AndroidCompanionFrameProvider(
        transport=None,
        verifier=SimpleNamespace(close=lambda: None),
    )
    provider.read_once = lambda: {
        "observation": observation,
        "frame_buffer": frame,
        "receipt_body": {},
        "verify_frame": lambda *_: True,
    }
    runtime = SimpleNamespace(
        current="turn",
        turn_event={"brain_generation_id": "generation-1"},
    )
    try:
        with pytest.raises(FrameReceiptDenied, match="A5 UI lease consumer"):
            with provider.open_current_turn(runtime):
                pass
        assert frame == bytearray(b"\x00" * 5)
    finally:
        provider.close()
