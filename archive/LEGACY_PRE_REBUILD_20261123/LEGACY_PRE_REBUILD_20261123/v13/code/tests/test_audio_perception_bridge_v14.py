"""Canonical PCM16 -> A5 PerceptPacket -> real A4/SQLite and C3 admission tests."""
import struct
from types import SimpleNamespace

import pytest

from v13.audio_ear import observe_pcm16
from v13.audio_percept_contract import audio_percept_packet
from v13.audio_perception_bridge import (
    admit_audio_packet,
    consume_audio_packet,
    consume_pcm16_window,
)
from v13.store import Store


PCM = struct.pack("<" + "h" * 80, *([1000, -1000] * 40))
SOURCE_ID = "fixture:pcm16"
RECEIPT = "fixture:current-consent"


def make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("audio bridge test")
    event = store.event(session, "audio bridge fixture")
    runtime = SimpleNamespace(home=tmp_path, store=store)
    return runtime, event


def make_packet(runtime, event, *, finality="FINAL"):
    raw = observe_pcm16(
        PCM, 8000, 1234, consent=True, source_id=SOURCE_ID, max_seconds=1
    )
    segment = raw["segments"][0]
    return audio_percept_packet(
        event_id=event["event_id"],
        generation_id=event["brain_generation_id"],
        source_id=SOURCE_ID,
        source_sha256=raw["source_ref"]["sha256"],
        start_ms=segment["start_ms"],
        end_ms=segment["end_ms"],
        rms=segment["acoustic"]["rms"],
        zcr=segment["acoustic"]["zero_crossing_rate"],
        finality=finality,
        consent_receipt=RECEIPT,
    )


def consent_ok(source_id, receipt):
    return source_id == SOURCE_ID and receipt == RECEIPT


def count_packets(store, event_id):
    return store.one(
        "SELECT COUNT(*) AS n FROM packets WHERE event_id=?", (event_id,)
    )["n"]


def count_attention(store, event_id):
    return store.one(
        "SELECT COUNT(*) AS n FROM telemetry WHERE kind='attention_gain' AND event_id=?",
        (event_id,),
    )["n"]


def test_pcm16_reaches_canonical_a5_real_a4_and_c3_admission(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_window(
            runtime, PCM, sample_rate=8000, start_ms=1234,
            event_id=event["event_id"],
            generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, token_budget=512,
        )
        assert result["status"] == "SYNTHETIC_PCM16_A5_A4_C3_ADMISSION"
        assert result["packet"]["modality"] == "audio"
        assert result["packet"]["segments"][0]["end_ms"] == 1244
        assert result["a4"]["attention"]["truth_authority"] == 0
        assert result["a4"]["learning_authority"] is False
        assert result["a4"]["action_authority"] is False
        assert result["c3_admission"].status == "ADMITTED"
        assert result["c3_admission"].selected[0].modality == "audio"
        assert count_packets(runtime.store, event["event_id"]) == 1
        assert count_attention(runtime.store, event["event_id"]) == 1
        # The PCM bytes are represented by a digest and bounded features only.
        audio_hash = result["packet"]["source_ref"]["sha256"]
        assert not (tmp_path / "data" / "blobs" / audio_hash).exists()
    finally:
        runtime.store.close()


def test_revoked_consent_before_capture_has_no_consumer_side_effect(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        with pytest.raises(PermissionError):
            consume_pcm16_window(
                runtime, PCM, sample_rate=8000, start_ms=1234,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=lambda source, receipt: False,
            )
        assert count_packets(runtime.store, event["event_id"]) == 0
        assert count_attention(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_revocation_before_a4_is_rechecked_after_packet_store(tmp_path):
    runtime, event = make_runtime(tmp_path)
    calls = [0]

    def revoke_before_a4(source, receipt):
        calls[0] += 1
        return calls[0] < 3

    try:
        with pytest.raises(PermissionError):
            consume_pcm16_window(
                runtime, PCM, sample_rate=8000, start_ms=1234,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=revoke_before_a4,
            )
        assert calls[0] == 3
        assert count_packets(runtime.store, event["event_id"]) == 1
        assert count_attention(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_revocation_between_a4_and_c3_blocks_c3_admission(tmp_path):
    runtime, event = make_runtime(tmp_path)
    calls = [0]

    def revoke_before_c3(source, receipt):
        calls[0] += 1
        return calls[0] < 4

    try:
        with pytest.raises(PermissionError):
            consume_pcm16_window(
                runtime, PCM, sample_rate=8000, start_ms=1234,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=revoke_before_c3,
            )
        assert calls[0] == 4
        assert count_packets(runtime.store, event["event_id"]) == 1
        assert count_attention(runtime.store, event["event_id"]) == 1
    finally:
        runtime.store.close()


def test_forged_authority_and_provenance_are_rejected_before_a4(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        packet = make_packet(runtime, event)
        packet["segments"][0]["action_authority"] = True
        with pytest.raises(PermissionError):
            consume_audio_packet(runtime, event["event_id"], packet, consent_check=consent_ok)
        assert count_packets(runtime.store, event["event_id"]) == 0
        assert count_attention(runtime.store, event["event_id"]) == 0

        packet = make_packet(runtime, event)
        packet["provenance"] = [{"source_id": "forged"}]
        with pytest.raises(ValueError):
            consume_audio_packet(runtime, event["event_id"], packet, consent_check=consent_ok)
        assert count_packets(runtime.store, event["event_id"]) == 0
        assert count_attention(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_stale_generation_and_missing_receipt_are_rejected(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        packet = make_packet(runtime, event)
        packet["brain_generation_id"] = "stale-generation"
        with pytest.raises(ValueError):
            consume_audio_packet(runtime, event["event_id"], packet, consent_check=consent_ok)

        packet = make_packet(runtime, event)
        packet["segments"][0]["consent_receipt_ref"] = ""
        with pytest.raises(PermissionError):
            admit_audio_packet(
                runtime, event["event_id"], packet,
                consent_check=consent_ok, token_budget=512,
            )
        assert count_packets(runtime.store, event["event_id"]) == 0
        assert count_attention(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()


def test_provisional_audio_can_modulate_a4_but_is_not_admitted_to_c3(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        result = consume_pcm16_window(
            runtime, PCM, sample_rate=8000, start_ms=1234,
            event_id=event["event_id"],
            generation_id=event["brain_generation_id"],
            source_id=SOURCE_ID, consent_receipt=RECEIPT,
            consent_check=consent_ok, finality="PROVISIONAL",
        )
        assert result["a4"]["finality"] == "PROVISIONAL"
        assert count_attention(runtime.store, event["event_id"]) == 1
        assert result["c3_admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["c3_admission"].selected == ()
    finally:
        runtime.store.close()


def test_consent_provider_exception_fails_closed(tmp_path):
    runtime, event = make_runtime(tmp_path)
    try:
        def broken_provider(source, receipt):
            raise RuntimeError("private provider details")

        with pytest.raises(PermissionError):
            consume_pcm16_window(
                runtime, PCM, sample_rate=8000, start_ms=1234,
                event_id=event["event_id"],
                generation_id=event["brain_generation_id"],
                source_id=SOURCE_ID, consent_receipt=RECEIPT,
                consent_check=broken_provider,
            )
        assert count_packets(runtime.store, event["event_id"]) == 0
        assert count_attention(runtime.store, event["event_id"]) == 0
    finally:
        runtime.store.close()
