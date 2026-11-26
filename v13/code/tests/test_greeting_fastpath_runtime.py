import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock

from v13.greeting_fastpath import RULE_ID, match
from v13.runtime import Runtime


def _text_event(**extra):
    event = {
        "source_ref": {
            "source_id": "src_" + "a" * 32,
            "sha256": "a" * 64,
            "char_start": 0,
            "char_end": 2,
            "modality": "text",
        },
        "modalities": ["text"],
    }
    event.update(extra)
    return event


def _resources():
    return {
        "wall_time": time.time(),
        "mem_available_bytes": 8 * 1024**3,
        "mem_total_bytes": 8 * 1024**3,
        "free_disk_bytes": 20 * 1024**3,
        "battery_temperature_c": 25.0,
        "battery_percent": 80.0,
        "charging": True,
        "processes": [],
        "own_peak_rss_bytes": 0,
    }


def _wait_idle(runtime):
    until = time.monotonic() + 8
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle()


def test_greeting_match_is_exact_bounded_and_text_only():
    result = match("  HI!!  ", event=_text_event())
    assert result is not None
    assert result["rule_id"] == RULE_ID
    assert result["reply"] == "Hi."
    assert result["model_generated"] is False
    assert result["native_models_invoked"] is False

    assert match("hi, how are you?", event=_text_event()) is None
    assert match("hi", event=_text_event(source_ref={"modality": "audio"})) is None
    assert match("hi", event=_text_event(modalities=["text", "image"])) is None
    assert match("hi", event=_text_event(raw_audio=b"not-empty")) is None
    assert match("hi\nthere", event=_text_event()) is None
    assert match("hi" * 40, event=_text_event()) is None


def test_runtime_answers_exact_greeting_without_native_body_or_c3_calls():
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Runtime(Path(tmp))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            runtime.resources = _resources
            runtime.guard.update(runtime.resources())
            runtime.pool.get = Mock(side_effect=AssertionError("C3 must not run for exact greeting"))
            runtime.cognition.offer = Mock(side_effect=AssertionError("B1/B2 must not run for exact greeting"))
            runtime.cognition.percept = Mock(side_effect=AssertionError("exact text greeting uses the bounded A5 source packet"))

            runtime.submit("Hi there!")
            _wait_idle(runtime)

            row = runtime.last_answer()
            assert row is not None
            assert row["status"] == "FINAL"
            assert row["text"].strip() == "Hi."
            meta = json.loads(row["metadata"])
            assert meta["greeting_fastpath"]["rule_id"] == RULE_ID
            assert meta["greeting_fastpath"]["native_models_invoked"] is False
            assert meta["model_generated"] is False
            assert meta["output_policy"]["rule_id"] == RULE_ID
            assert meta["output_authority"] == "APPROVED_FIXED_RULE"
            assert "B_OBSERVERS" in meta["skipped_native_stages"]
            assert "C3_DECODE" in meta["skipped_native_stages"]
            runtime.pool.get.assert_not_called()
            runtime.cognition.offer.assert_not_called()
            runtime.cognition.percept.assert_not_called()
        finally:
            runtime.close()


def test_non_greeting_question_falls_through_to_perception():
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Runtime(Path(tmp))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            runtime.resources = _resources
            runtime.guard.update(runtime.resources())
            runtime.cognition.percept = Mock(side_effect=RuntimeError("test fallthrough sentinel"))

            runtime.submit("Hi, how are you?")
            _wait_idle(runtime)

            row = runtime.last_answer()
            assert row is not None
            meta = json.loads(row["metadata"])
            assert "greeting_fastpath" not in meta
            runtime.cognition.percept.assert_called_once()
        finally:
            runtime.close()
