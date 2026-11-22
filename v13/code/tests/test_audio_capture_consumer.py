import base64
import copy
import hashlib
import json
import sqlite3
from contextlib import contextmanager

import pytest

from v13.audio_capture_consumer import (
    AudioCaptureDenied,
    AudioCaptureReceiptVerifier,
    RECEIPT_SCHEMA,
    RESULT_SCHEMA,
    SOURCE_ID,
    SAMPLE_RATE,
    build_audio_capture_request,
    submit_verified_audio_capture,
    verifier_from_pinned_controller,
)
from v13.audio_input import AUDIO_ONLY_SOURCE_TEXT

PUBLIC_KEY = bytes.fromhex(
    "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
    "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
)
KEY_ID = "698bea63dc44a344663ff1429aea10842df27b6b991ef25866b2c6c02cdcc5be"
SIGNATURE = "MEYCIQCwdMS6664bv7iiLI0JUVBbNEPrDCNUlrlJzFB0T1VAqQIhANwyqrAXHmSn6Yu2qkQd6x4USn+vrSHnM0zz4NUPbx94"
GENERATION = "gen_" + "b" * 32


class RuntimeStub:
    def __init__(self):
        self.calls = []

    def submit(self, text, *, audio_window=None):
        self.calls.append((text, audio_window))
        return "turn-audio-1"


def make_pair():
    request = build_audio_capture_request(request_id="a" * 32, now=1000, ttl_s=20)
    pcm = b"\x00\x00" * SAMPLE_RATE
    body = {
        "schema": RECEIPT_SCHEMA,
        "nonce": "c" * 32,
        "request_id": request["request_id"],
        "request_digest": request["digest"],
        "source_id": SOURCE_ID,
        "generation_id": GENERATION,
        "start_monotonic_ns": 1_000_000_000,
        "end_monotonic_ns": 2_000_000_000,
        "sample_rate": SAMPLE_RATE,
        "channels": 1,
        "sample_count": SAMPLE_RATE,
        "encoding": "pcm_s16le",
        "audio_source": "UNPROCESSED",
        "permission_granted": True,
        "os_permission_status": "GRANTED_RECORD_AUDIO",
        "consent_result": "CAPTURED",
        "local_consent": True,
        "finality": "FINAL",
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "issued_at": 1001,
        "expires_at": 1010,
        "key_id": KEY_ID,
        "key_storage_status": "ANDROID_KEYSTORE_SOFTWARE_BACKED",
    }
    result = {
        "schema": RESULT_SCHEMA,
        "status": "CAPTURED",
        "request_id": request["request_id"],
        "pcm16_base64": base64.b64encode(pcm).decode("ascii"),
        "receipt": {"body": body, "key_id": KEY_ID, "signature": SIGNATURE},
    }
    return request, result, pcm


def make_verifier(path, clock=lambda: 1005.0):
    return AudioCaptureReceiptVerifier(path, PUBLIC_KEY, KEY_ID, clock=clock)


def receipt_ref(result):
    body = result["receipt"]["body"]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def consent_callbacks(expected_ref):
    def check(source, receipt):
        return source == SOURCE_ID and receipt == expected_ref

    @contextmanager
    def guard(source, receipt):
        if not check(source, receipt):
            raise PermissionError("revoked")
        yield True

    def subscribe(*_args):
        return lambda: None

    return check, guard, subscribe


def test_signed_one_shot_result_reaches_existing_raw_ear_runtime(tmp_path):
    request, result, pcm = make_pair()
    verifier = make_verifier(tmp_path / "receipts.sqlite")
    runtime = RuntimeStub()
    ref = receipt_ref(result)
    callbacks = consent_callbacks(ref)

    submitted = submit_verified_audio_capture(
        runtime, request, result, verifier=verifier, expected_generation=GENERATION,
        consent_check=callbacks[0], consent_guard=callbacks[1],
        consent_revocation_subscribe=callbacks[2],
    )

    assert request["sample_rate"] == SAMPLE_RATE == 44100
    assert len(result["pcm16_base64"]) == 117600
    assert submitted["status"] == "SUBMIT_RETURNED"
    assert submitted["runtime_result"] == "turn-audio-1"
    assert submitted["source_id"] == SOURCE_ID
    assert submitted["finality"] == "FINAL"
    assert submitted["learning_authority"] is False
    assert submitted["speaker_identity_authority"] is False
    assert submitted["action_authority"] is False
    assert "pcm16" not in submitted and "pcm16_base64" not in submitted
    assert len(runtime.calls) == 1
    text, window = runtime.calls[0]
    assert text == AUDIO_ONLY_SOURCE_TEXT
    assert window["pcm16"] == pcm
    assert window["sample_rate"] == SAMPLE_RATE
    assert window["start_ms"] == 1000
    assert window["source_id"] == SOURCE_ID
    assert window["consent_receipt"] == ref
    assert window["finality"] == "FINAL"
    assert window["consent_check"] is callbacks[0]
    assert window["consent_guard"] is callbacks[1]
    assert window["consent_revocation_subscribe"] is callbacks[2]
    verifier.close()


def test_signature_tampering_is_rejected_before_runtime_submit(tmp_path):
    request, result, _ = make_pair()
    result["receipt"]["signature"] = base64.b64encode(b"not-an-ecdsa-signature").decode("ascii")
    verifier = make_verifier(tmp_path / "bad-signature.sqlite")
    runtime = RuntimeStub()
    callbacks = consent_callbacks(receipt_ref(make_pair()[1]))
    with pytest.raises(AudioCaptureDenied, match="signature"):
        submit_verified_audio_capture(
            runtime, request, result, verifier=verifier, expected_generation=GENERATION,
            consent_check=callbacks[0], consent_guard=callbacks[1],
            consent_revocation_subscribe=callbacks[2],
        )
    assert runtime.calls == []
    verifier.close()


def test_pcm_digest_and_short_read_controls_are_rejected(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "pcm.sqlite")
    bad_pcm = copy.deepcopy(result)
    bad_pcm["pcm16_base64"] = base64.b64encode(b"\x01\x00" * SAMPLE_RATE).decode("ascii")
    check = consent_callbacks(receipt_ref(result))[0]
    with pytest.raises(AudioCaptureDenied, match="digest"):
        verifier.verify(request, bad_pcm, expected_generation=GENERATION, consent_check=check)

    short = copy.deepcopy(result)
    short["receipt"]["body"]["sample_count"] = SAMPLE_RATE - 1
    with pytest.raises(AudioCaptureDenied, match="geometry"):
        verifier.verify(request, short, expected_generation=GENERATION, consent_check=check)
    verifier.close()


@pytest.mark.parametrize("field,value,match", [
    ("source_id", "android.camera", "source"),
    ("generation_id", "gen_" + "d" * 32, "generation"),
    ("permission_granted", False, "consent"),
    ("os_permission_status", "DENIED", "consent"),
    ("consent_result", "DENIED", "consent"),
    ("finality", "PROVISIONAL", "consent"),
])
def test_source_generation_permission_and_finality_are_bound(tmp_path, field, value, match):
    request, result, _ = make_pair()
    result["receipt"]["body"][field] = value
    verifier = make_verifier(tmp_path / (field + ".sqlite"))
    with pytest.raises(AudioCaptureDenied, match=match):
        verifier.verify(
            request, result, expected_generation=GENERATION,
            consent_check=consent_callbacks(receipt_ref(result))[0],
        )
    verifier.close()


def test_request_digest_expiry_and_extra_fields_fail_closed(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "request.sqlite")
    check = consent_callbacks(receipt_ref(result))[0]
    with pytest.raises(AudioCaptureDenied, match="digest"):
        verifier.verify(dict(request, duration_ms=500), result, expected_generation=GENERATION, consent_check=check)
    with pytest.raises(AudioCaptureDenied, match="fields"):
        verifier.verify(dict(request, allow_background=True), result, expected_generation=GENERATION, consent_check=check)
    verifier.close()

    expired = make_verifier(tmp_path / "expired.sqlite", clock=lambda: 1021.0)
    with pytest.raises(AudioCaptureDenied, match="expired"):
        expired.verify(request, result, expected_generation=GENERATION, consent_check=check)
    expired.close()


def test_receipt_nonce_and_request_id_are_both_single_use(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "replay.sqlite")
    check = consent_callbacks(receipt_ref(result))[0]
    verifier.verify(request, result, expected_generation=GENERATION, consent_check=check)
    with pytest.raises(AudioCaptureDenied, match="replay"):
        verifier.verify(request, result, expected_generation=GENERATION, consent_check=check)
    verifier.close()


def test_revoked_preflight_does_not_consume_one_shot_receipt(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "revoked.sqlite")
    runtime = RuntimeStub()
    callbacks = consent_callbacks(receipt_ref(result))
    with pytest.raises(AudioCaptureDenied, match="not active"):
        submit_verified_audio_capture(
            runtime, request, result, verifier=verifier, expected_generation=GENERATION,
            consent_check=lambda *_: False, consent_guard=callbacks[1],
            consent_revocation_subscribe=callbacks[2],
        )
    assert runtime.calls == []
    verifier.verify(
        request, result, expected_generation=GENERATION,
        consent_check=consent_callbacks(receipt_ref(result))[0],
    )
    verifier.close()


def test_missing_revocation_contract_is_rejected_before_nonce_consumption(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "missing-guard.sqlite")
    runtime = RuntimeStub()
    callbacks = consent_callbacks(receipt_ref(result))
    with pytest.raises(AudioCaptureDenied, match="two-phase revocation"):
        submit_verified_audio_capture(
            runtime, request, result, verifier=verifier, expected_generation=GENERATION,
            consent_check=callbacks[0], consent_guard=callbacks[1],
            consent_revocation_subscribe=None,
        )
    assert runtime.calls == []
    verifier.verify(
        request, result, expected_generation=GENERATION,
        consent_check=consent_callbacks(receipt_ref(result))[0],
    )
    verifier.close()


def test_short_monotonic_capture_is_rejected(tmp_path):
    request, result, _ = make_pair()
    result["receipt"]["body"]["end_monotonic_ns"] = 1_000_000_001
    verifier = make_verifier(tmp_path / "short-time.sqlite")
    with pytest.raises(AudioCaptureDenied, match="too short"):
        verifier.verify(
            request, result, expected_generation=GENERATION,
            consent_check=consent_callbacks(receipt_ref(make_pair()[1]))[0],
        )
    verifier.close()


def test_zero_or_wrong_sample_rate_is_rejected_without_arithmetic_error(tmp_path):
    request, result, _ = make_pair()
    result["receipt"]["body"]["sample_rate"] = 0
    verifier = make_verifier(tmp_path / "bad-rate.sqlite")
    with pytest.raises(AudioCaptureDenied, match="geometry"):
        verifier.verify(
            request, result, expected_generation=GENERATION,
            consent_check=consent_callbacks(receipt_ref(make_pair()[1]))[0],
        )
    verifier.close()


def test_non_finite_and_overflow_times_fail_closed(tmp_path):
    request, result, _ = make_pair()
    request["issued_at"] = 10**10000
    verifier = make_verifier(tmp_path / "overflow-time.sqlite")
    with pytest.raises(AudioCaptureDenied, match="request time"):
        verifier.verify(
            request, result, expected_generation=GENERATION,
            consent_check=consent_callbacks(receipt_ref(make_pair()[1]))[0],
        )
    verifier.close()


def test_request_builder_rejects_boolean_clock():
    with pytest.raises(ValueError, match="clock"):
        build_audio_capture_request(request_id="a" * 32, now=True)


def test_verified_capture_repr_does_not_expose_raw_pcm(tmp_path):
    request, result, _ = make_pair()
    verifier = make_verifier(tmp_path / "repr.sqlite")
    capture = verifier.verify(
        request, result, expected_generation=GENERATION,
        consent_check=consent_callbacks(receipt_ref(result))[0],
    )
    assert "pcm16" not in repr(capture)
    assert "\\x00\\x00" not in repr(capture)
    verifier.close()


def test_replay_ledger_contains_only_nonce_and_request_metadata(tmp_path):
    request, result, _ = make_pair()
    path = tmp_path / "private-receipts.sqlite"
    verifier = make_verifier(path)
    verifier.verify(
        request, result, expected_generation=GENERATION,
        consent_check=consent_callbacks(receipt_ref(result))[0],
    )
    verifier.close()
    db = sqlite3.connect(path)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"used_receipts", "used_audio_requests"}
    columns = {
        table: {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        for table in tables
    }
    assert columns["used_receipts"] == {"nonce", "action_id"}
    assert columns["used_audio_requests"] == {"request_id", "nonce"}
    db.close()


def test_verifier_factory_reuses_only_the_existing_pinned_companion(tmp_path):
    class Controller:
        verifier_path = tmp_path / "shared-receipts.sqlite"
        clock = staticmethod(lambda: 1005.0)

        def _pinned_key(self):
            return ({"key_id": KEY_ID}, PUBLIC_KEY, {"schema": "v14.android-companion-public-key/1"})

    verifier = verifier_from_pinned_controller(Controller())
    assert verifier._base.key_id == KEY_ID
    verifier.close()

    class UntrustedController:
        verifier_path = tmp_path / "untrusted.sqlite"
        clock = staticmethod(lambda: 1005.0)

        def _pinned_key(self):
            return ({"key_id": "0" * 64}, PUBLIC_KEY, {})

    with pytest.raises(AudioCaptureDenied, match="not explicitly pinned"):
        verifier_from_pinned_controller(UntrustedController())
