import json
import math
import struct
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

import pytest

from v13 import duplex
from v13.audio_duplex_bridge import (
    consume_pcm16_voice_window_with_duplex,
    decide_audio_overlap,
    on_audio_input,
    _persist_temporal_voice_receipt,
    _claim_one_use_audio_receipt,
    _REPLAY_MAX_ENTRIES,
    _REPLAY_STATE_KEY,
    _TEMPORAL_RECEIPT_PROCESS_EPOCH,
)
from v13.audio_voice_cues import audio_consent_lease, consume_pcm16_voice_window
from v13.audio_temporal_evidence import TemporalVoiceEvidence
from v13.common import Cancelled
from v13.runtime import Runtime

SOURCE = "fixture:audio-duplex"
RECEIPT = "fixture:consented-audio"


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000):
    count = int(sample_rate * seconds)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
               for i in range(count)]
    return struct.pack("<" + "h" * len(samples), *samples)


def consent_ok(source_id, receipt):
    return source_id == SOURCE and receipt == RECEIPT


@contextmanager
def consent_guard(source_id, receipt):
    yield consent_ok(source_id, receipt)


def make_runtime(tmp_path, mode):
    runtime = Runtime(Path(tmp_path))
    runtime.cfg["duplex_mode"] = mode
    runtime.sleep.cycle.set_policy("enabled", "off")
    started = threading.Event()

    def generate(messages, cancel, deadline, *args, **kwargs):
        for index in range(200):
            if cancel.is_set():
                raise Cancelled("audio barge-in")
            if index == 1:
                started.set()
            yield f"word{index} "
            time.sleep(0.01)

    runtime._route = Mock(return_value=("simple", {"source": "TEST_ROUTE_SEAM"}))
    runtime.pool.get = Mock(return_value=SimpleNamespace(
        role="C3_LANGUAGE", last_metrics={}, generate=generate,
    ))
    runtime.learner.output_delta = Mock(return_value=None)
    return runtime, started


def wait_idle(runtime, timeout=20):
    until = time.monotonic() + timeout
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "runtime did not settle after synthetic audio input"


def answer(runtime, event_id):
    return runtime.store.one(
        "SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
        (event_id,),
    )


def make_audio(runtime, *, start_ms=100):
    event = runtime.store.event(runtime.session, "synthetic caller-supplied audio input")
    generation = event["brain_generation_id"]
    return event, generation, tone(), {
        "sample_rate": 16000,
        "start_ms": start_ms,
        "event_id": event["event_id"],
        "generation_id": generation,
        "source_id": SOURCE,
        "consent_receipt": RECEIPT,
        "consent_check": consent_ok,
        "finality": "PROVISIONAL",
        "token_budget": 512,
    }


def test_decision_modes_keep_auto_non_interrupting_and_require_voice_onset():
    assert decide_audio_overlap("VOICED", True, "auto") == (
        "CONTINUE", "AUDIO_OVERLAP_CANDIDATE",
    )
    assert decide_audio_overlap("VOICED", True, "interrupt") == (
        "INTERRUPT", "AUDIO_BARGE_IN",
    )
    assert decide_audio_overlap("VOICED", True, "off") is None
    assert decide_audio_overlap("SILENCE", True, "interrupt") is None
    assert decide_audio_overlap("UNVOICED_NOISE", True, "interrupt") is None
    assert decide_audio_overlap("IMPULSIVE", True, "interrupt") is None
    assert decide_audio_overlap("VOICED", False, "interrupt") is None
    with pytest.raises(ValueError):
        decide_audio_overlap("VOICED", True, "invalid")


def test_provisional_raw_ear_onset_interrupts_only_in_explicit_interrupt_mode(tmp_path):
    runtime, started = make_runtime(tmp_path, "interrupt")
    try:
        first = runtime.submit("Tell me a long story about the capital of France")
        assert started.wait(10)
        audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window_with_duplex(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            assert result["a4"]["voice_cues"]["activity_hint"] == "VOICED"
            assert result["a4"]["temporal_voice"]["voice_onset"] is True
            persisted = runtime.store.one(
                "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
                (result["packet"]["packet_id"],),
            )
            persisted_packet = json.loads(persisted["payload"])
            assert persisted_packet["segments"][0]["acoustic"]["temporal_voice_receipt"]["evidence"] == result["a4"]["temporal_voice"]
            assert result["a4"]["temporal_receipt_id"] == result["temporal_receipt_id"]
            assert result["duplex"]["decision"] == "INTERRUPT"
            assert result["duplex"]["relation"] == "AUDIO_BARGE_IN"
            assert result["duplex"]["bridge_revision"] == "V14_RAW_EAR_AUDIO_DUPLEX_BRIDGE_V3"
            assert result["learning_authority"] is False
            assert result["action_authority"] is False
        wait_idle(runtime)
        cut = answer(runtime, first)
        assert cut["status"] == "CANCELLED"
        meta = json.loads(cut["metadata"])
        assert meta["duplex"] == {
            "interrupted_by": audio_event["event_id"],
            "relation": "AUDIO_BARGE_IN",
            "provisional": True,
            "authority": "PROVISIONAL_LIVE_NOT_LEARNED",
        }
        from v13.history import native_history
        history, _ = native_history(runtime.store, runtime.session, "evt_none", 8)
        assert first not in [item["event_id"] for item in history]
        assert duplex.status(runtime)["counters"]["INTERRUPT"] == 1
    finally:
        runtime.close()


def test_default_auto_records_overlap_candidate_without_cancelling_answer(tmp_path):
    runtime, started = make_runtime(tmp_path, "auto")
    try:
        first = runtime.submit("Tell me a long story about the capital of Italy")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window_with_duplex(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            assert result["duplex"]["decision"] == "CONTINUE"
            assert result["duplex"]["relation"] == "AUDIO_OVERLAP_CANDIDATE"
            assert not runtime.cancel_event.is_set()
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
        assert duplex.status(runtime)["counters"]["CONTINUE"] == 1
    finally:
        runtime.close()


def test_bridge_rejects_expired_or_wrong_receipt_lease_before_cancel(tmp_path):
    runtime, _started = make_runtime(tmp_path, "interrupt")
    try:
        audio_event, generation, _pcm, _kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            bad_result = {
                "status": "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION",
                "packet": {
                    "modality": "audio", "event_id": audio_event["event_id"],
                    "generation_id": generation,
                    "source_ref": {"source_id": SOURCE, "sha256": "a" * 64},
                    "segments": [{"finality": "PROVISIONAL", "consent_receipt_ref": "wrong"}],
                },
                "a4": {"voice_cues": {"activity_hint": "VOICED"},
                       "temporal_voice": {"voice_onset": True}},
            }
            with pytest.raises(PermissionError):
                on_audio_input(runtime, bad_result, lease)
            assert not runtime.cancel_event.is_set()
        with pytest.raises(PermissionError):
            on_audio_input(runtime, bad_result, lease)
    finally:
        runtime.close()


def test_bridge_rejects_mutated_persisted_audio_packet_before_cancel(tmp_path):
    runtime, _started = make_runtime(tmp_path, "interrupt")
    try:
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            result["packet"]["source_ref"]["sha256"] = "a" * 64
            with pytest.raises(ValueError, match="differs from its persisted"):
                on_audio_input(runtime, result, lease)
            assert not runtime.cancel_event.is_set()
    finally:
        runtime.close()


def test_bridge_rejects_forged_temporal_voice_not_bound_to_persisted_receipt(tmp_path):
    runtime, started = make_runtime(tmp_path, "interrupt")
    try:
        first = runtime.submit("Tell me a long story about the history of Rome")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            _persist_temporal_voice_receipt(runtime, result, lease)
            persisted = runtime.store.one(
                "SELECT payload FROM packets WHERE id=? AND kind='PerceptPacket'",
                (result["packet"]["packet_id"],),
            )
            evidence = json.loads(persisted["payload"])["segments"][0]["acoustic"]["temporal_voice_receipt"]["evidence"]
            forged = dict(result["a4"]["temporal_voice"])
            forged["voice_onset"] = not evidence["voice_onset"]
            result["a4"]["temporal_voice"] = forged
            with pytest.raises(ValueError, match="differs from persisted temporal receipt"):
                on_audio_input(runtime, result, lease)
            assert not runtime.cancel_event.is_set()
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
    finally:
        runtime.close()


@pytest.mark.parametrize(("mode", "expected_decision"), [
    ("interrupt", "INTERRUPT"),
    ("auto", "CONTINUE"),
])
def test_audio_temporal_receipt_is_one_use_across_later_turns_including_continue(
    tmp_path, mode, expected_decision,
):
    runtime, started = make_runtime(tmp_path, mode)
    try:
        first = runtime.submit("Tell me a long story about the history of Greece")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            _persist_temporal_voice_receipt(runtime, result, lease)
            first_decision = on_audio_input(runtime, result, lease)
            assert first_decision["decision"] == expected_decision
            wait_idle(runtime)

            started.clear()
            second = runtime.submit("Tell me a long story about the history of Portugal")
            assert started.wait(10)
            with pytest.raises(ValueError, match="already consumed"):
                on_audio_input(runtime, result, lease)
            assert not runtime.cancel_event.is_set()
            wait_idle(runtime)
            assert answer(runtime, second)["status"] == "FINAL"
            assert duplex.status(runtime)["counters"][expected_decision] == 1
    finally:
        runtime.close()


def test_audio_receipt_is_consumed_even_when_duplex_mode_is_off(tmp_path):
    runtime, started = make_runtime(tmp_path, "off")
    try:
        first = runtime.submit("Tell me a long story about the history of Spain")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            _persist_temporal_voice_receipt(runtime, result, lease)
            assert on_audio_input(runtime, result, lease) is None
            wait_idle(runtime)
            started.clear()
            second = runtime.submit("Tell me a long story about the history of Portugal")
            assert started.wait(10)
            runtime.cfg["duplex_mode"] = "interrupt"
            with pytest.raises(ValueError, match="already consumed"):
                on_audio_input(runtime, result, lease)
            assert not runtime.cancel_event.is_set()
            wait_idle(runtime)
            assert answer(runtime, second)["status"] == "FINAL"
    finally:
        runtime.close()


def test_audio_receipt_claim_is_linearizable_under_concurrent_dispatch(tmp_path):
    runtime, _started = make_runtime(tmp_path, "auto")
    barrier = threading.Barrier(2)
    results = []

    def claim():
        barrier.wait(timeout=5)
        try:
            _claim_one_use_audio_receipt(runtime, "same-event", "same-packet", "a" * 64)
        except ValueError as exc:
            results.append(("rejected", str(exc)))
        else:
            results.append(("claimed", ""))

    threads = [threading.Thread(target=claim) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert all(not thread.is_alive() for thread in threads)
        assert sorted(result[0] for result in results) == ["claimed", "rejected"]
        state, _version = runtime.store.state(_REPLAY_STATE_KEY, {"revision": 1, "entries": []})
        assert len(state["entries"]) == 1
    finally:
        runtime.close()


def test_audio_receipt_replay_guard_fails_closed_at_its_bound(tmp_path):
    runtime, _started = make_runtime(tmp_path, "auto")
    now_ns = time.monotonic_ns()
    entries = [
        {
            "receipt_key": f"{index:064x}",
            "process_epoch": _TEMPORAL_RECEIPT_PROCESS_EPOCH,
            "expires_monotonic_ns": now_ns + 60_000_000_000,
        }
        for index in range(_REPLAY_MAX_ENTRIES)
    ]
    try:
        runtime.store.set_state(
            _REPLAY_STATE_KEY, {"revision": 1, "entries": entries},
        )
        with pytest.raises(RuntimeError, match="replay guard is full"):
            _claim_one_use_audio_receipt(runtime, "new-event", "new-packet", "b" * 64)
        state, _version = runtime.store.state(_REPLAY_STATE_KEY, {})
        assert len(state["entries"]) == _REPLAY_MAX_ENTRIES
    finally:
        runtime.close()



def test_pcm16_duplex_wrapper_forwards_the_same_live_temporal_state(tmp_path):
    runtime, started = make_runtime(tmp_path, "auto")
    try:
        first = runtime.submit("Tell me a long story about the history of Denmark")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        temporal_state = TemporalVoiceEvidence()
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
            temporal_state=temporal_state,
        ) as lease:
            result = consume_pcm16_voice_window_with_duplex(
                runtime, pcm, consent_lease=lease,
                temporal_state=temporal_state, **kwargs,
            )
            assert result["duplex"]["decision"] == "CONTINUE"
            assert result["duplex"]["record_status"] == "RECORDED"
            assert not runtime.cancel_event.is_set()
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
        assert duplex.status(runtime)["counters"]["CONTINUE"] == 1
    finally:
        runtime.close()


def test_bridge_requires_the_same_temporal_state_bound_to_the_consent_lease(tmp_path):
    runtime, started = make_runtime(tmp_path, "interrupt")
    try:
        first = runtime.submit("Tell me a long story about the history of Japan")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        held_state = TemporalVoiceEvidence()
        different_state = TemporalVoiceEvidence()
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
            temporal_state=held_state,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease,
                temporal_state=held_state, **kwargs,
            )
            _persist_temporal_voice_receipt(
                runtime, result, lease, temporal_state=held_state,
            )
            with pytest.raises(PermissionError, match="source-bound consent lease"):
                on_audio_input(
                    runtime, result, lease, temporal_state=different_state,
                )
            assert not runtime.cancel_event.is_set()
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
    finally:
        runtime.close()


def test_audio_event_created_before_active_turn_cannot_interrupt_it(tmp_path):
    runtime, started = make_runtime(tmp_path, "interrupt")
    try:
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        first = runtime.submit("Tell me a long story about the history of Norway")
        assert started.wait(10)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            _persist_temporal_voice_receipt(runtime, result, lease)
            with pytest.raises(ValueError, match="predates the active Runtime turn"):
                on_audio_input(runtime, result, lease)
            assert not runtime.cancel_event.is_set()
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
    finally:
        runtime.close()


def test_audio_generation_must_match_the_active_turn_before_interrupt(tmp_path):
    runtime, started = make_runtime(tmp_path, "interrupt")
    try:
        first = runtime.submit("Tell me a long story about the history of Sweden")
        assert started.wait(10)
        _audio_event, generation, pcm, kwargs = make_audio(runtime)
        with audio_consent_lease(
            runtime, SOURCE, generation, RECEIPT, consent_ok, consent_guard,
        ) as lease:
            result = consume_pcm16_voice_window(
                runtime, pcm, consent_lease=lease, **kwargs,
            )
            _persist_temporal_voice_receipt(runtime, result, lease)
            current = runtime.turn_event
            original_generation = current["brain_generation_id"]
            current["brain_generation_id"] = "generation-mismatch"
            try:
                with pytest.raises(ValueError, match="does not match the active Runtime turn"):
                    on_audio_input(runtime, result, lease)
                assert not runtime.cancel_event.is_set()
            finally:
                current["brain_generation_id"] = original_generation
        wait_idle(runtime)
        assert answer(runtime, first)["status"] == "FINAL"
    finally:
        runtime.close()
