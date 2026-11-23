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
)
from v13.audio_voice_cues import audio_consent_lease
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
            assert result["duplex"]["decision"] == "INTERRUPT"
            assert result["duplex"]["relation"] == "AUDIO_BARGE_IN"
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


def test_bridge_rejects_expired_or_wrong_source_lease_before_cancel(tmp_path):
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
