"""Unit and A5/A4 consumer tests for the session-local RAW EAR A3 predictor."""
from array import array
from contextlib import contextmanager
import json
import math
import struct
from types import SimpleNamespace

import pytest

from v13 import audio_voice_cues as audio_voice_module
from v13.audio_event_expectation import AudioEventExpectationRegistry
from v13.audio_temporal_prediction import (
    ATTENTION_GAIN,
    FEATURE_COUNT,
    AudioTemporalPredictionError,
    AudioTemporalPredictionRegistry,
    AudioTemporalPredictor,
    acoustic_feature_vector,
    predictive_attention_novelty,
    predictive_omission_novelty,
    unavailable_prediction,
)
from v13.audio_voice_cues import (
    _runtime_audio_temporal_prediction_registry,
    consume_pcm16_voice_window,
    reset_runtime_temporal_voice_states,
)
from v13.store import Store


SOURCE = "fixture:raw-ear-temporal-prediction"
RECEIPT = "fixture:consented-raw-ear-temporal-prediction"
NEW_RECEIPT = "fixture:rotated-consent-raw-ear-temporal-prediction"


def tone(sample_rate=16000, frequency=140, seconds=1.0, amplitude=6000, phase=0.0):
    count = int(sample_rate * seconds)
    samples = [
        int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate + phase))
        for index in range(count)
    ]
    return struct.pack("<" + "h" * len(samples), *samples)


def make_runtime(tmp_path, *, preserve_generation=False):
    (tmp_path / "data" / "db").mkdir(parents=True, exist_ok=True)
    store = Store(tmp_path)
    if not preserve_generation:
        store.ensure_generation_snapshot({}, {})
    session = store.new_session("RAW EAR temporal prediction test")
    event = store.event(session, "synthetic acoustic-cue prediction fixture")
    return SimpleNamespace(home=tmp_path, store=store), event


def consent_check(source_id, receipt):
    return source_id == SOURCE and receipt in {RECEIPT, NEW_RECEIPT}


def consent_guard(check):
    @contextmanager
    def lease(source_id, receipt):
        yield check(source_id, receipt)
    return lease


def acoustic_cues(activity, *, f0=140.0, f0_range=20.0, energy=10.0,
                  voiced_energy=5.0, voiced_fraction=0.8,
                  confidence=0.9, activity_score=0.8, prosody=0.2):
    return {
        "activity_hint": activity,
        "frame_count": 50,
        "f0_median_hz": f0,
        "f0_range_hz": f0_range,
        "energy_range_db": energy,
        "voiced_energy_range_db": voiced_energy,
        "voiced_fraction": voiced_fraction,
        "voicing_confidence": confidence,
        "activity_score": activity_score,
        "prosody_change_score": prosody,
    }


SILENCE = acoustic_cues(
    "SILENCE", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.0, prosody=0.0,
)
EVENT_SILENCE = acoustic_cues(
    "SILENCE", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.9, prosody=0.0,
)
UNCERTAIN = acoustic_cues(
    "UNCERTAIN", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.0, prosody=0.0,
)
VOICED = acoustic_cues("VOICED")


class CaptureAttention:
    def __init__(self):
        self.calls = []

    def modulate(self, event_id, *, sal):
        values = dict(sal)
        self.calls.append(values)
        return {
            "event_id": event_id,
            "salience": max(values.values()),
            "caution": 0.0,
            "gains": {
                "perceptual": 0.5, "callosum": 0.5, "workspace": 0.5,
                "focal": 0.5, "action": 0.5,
            },
            "interrupt": values.get("external_interrupt", 0.0) >= 0.9,
            "interrupt_reason": None,
            "truth_authority": 0,
        }


def run_consumer_sequence(runtime, event, monkeypatch, sequence, capture,
                          *, receipt=RECEIPT, registry_override=None,
                          event_registry_override=None):
    cues_iter = iter(sequence)

    def fake_extract(_pcm, _sample_rate, backend="python"):
        return dict(next(cues_iter))

    monkeypatch.setattr(audio_voice_module, "extract_voice_cues", fake_extract)
    monkeypatch.setattr(audio_voice_module.attctl, "controller", lambda _runtime: capture)
    if registry_override is not None:
        monkeypatch.setattr(
            audio_voice_module,
            "_runtime_audio_temporal_prediction_registry",
            lambda _runtime: registry_override,
        )
    if event_registry_override is not None:
        monkeypatch.setattr(
            audio_voice_module,
            "_runtime_audio_event_expectation_registry",
            lambda _runtime: event_registry_override,
        )
    results = []
    for index in range(len(sequence)):
        results.append(consume_pcm16_voice_window(
            runtime,
            bytes(32000),
            sample_rate=16000,
            start_ms=100 + index * 1000,
            event_id=event["event_id"],
            generation_id=event["brain_generation_id"],
            source_id=SOURCE,
            consent_receipt=receipt,
            consent_check=consent_check,
            consent_guard=consent_guard(consent_check),
            finality="FINAL",
        ))
    return results


def run_pattern(registry, *, scope="a" * 64):
    sequence = [SILENCE, VOICED, VOICED, SILENCE, SILENCE,
                VOICED, VOICED, SILENCE, SILENCE, VOICED, VOICED, VOICED]
    results = []
    for index, item in enumerate(sequence):
        results.append(registry.update(
            source_id="source-a",
            generation_id="generation-a",
            consent_scope_id=scope,
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            cues=item,
            finality="FINAL",
        ))
    return results


def test_feature_vector_is_fixed_bounded_and_keeps_non_speech_classes():
    vector = acoustic_feature_vector(acoustic_cues(
        "IMPULSIVE", f0=None, f0_range=None, energy=120.0,
        voiced_energy=None, voiced_fraction=0.0, confidence=0.0,
        activity_score=1.0, prosody=1.0,
    ))
    assert len(vector) == FEATURE_COUNT == 13
    assert all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in vector)
    assert vector[11] == 1.0
    assert sum(vector[8:]) == 1.0


def test_predictor_changes_numeric_parameters_and_beats_persistence_on_repeated_pattern():
    results = run_pattern(AudioTemporalPredictionRegistry())
    measured = [item for item in results if item["status"] == "SHADOW_MEASURED"]
    assert measured
    assert measured[-2]["improvement_mae"] > 0
    assert any(item["weight_delta_l2"] > 0 for item in measured)
    assert any(item["parameter_l2"] > 0 for item in measured)
    assert measured[-2]["parameter_count"] == 182
    assert measured[-2]["weight_persistence"] is False
    assert measured[-2]["learning_authority"] is False


def test_unexpected_repeated_state_emits_capped_excess_prediction_error():
    last = run_pattern(AudioTemporalPredictionRegistry())[-1]
    assert last["status"] == "SHADOW_MEASURED"
    assert last["excess_prediction_error"] > 0
    assert 0.0 < predictive_attention_novelty(last) <= ATTENTION_GAIN
    assert last["attention_novelty"] == predictive_attention_novelty(last)


def test_provisional_window_never_creates_or_updates_prediction_state():
    registry = AudioTemporalPredictionRegistry()
    result = registry.update(
        source_id="source-a", generation_id="generation-a",
        consent_scope_id="a" * 64, start_ms=0, end_ms=1000,
        cues=VOICED, finality="PROVISIONAL",
    )
    assert result["status"] == "PROVISIONAL_IGNORED"
    assert result["updates"] == 0
    assert len(registry) == 0


def test_new_consent_scope_resets_old_session_weights():
    registry = AudioTemporalPredictionRegistry()
    run_pattern(registry)
    reset = registry.update(
        source_id="source-a", generation_id="generation-a",
        consent_scope_id="b" * 64, start_ms=12000, end_ms=13000,
        cues=SILENCE, finality="FINAL",
    )
    assert reset["status"] == "RESET_CONSENT_SCOPE"
    assert reset["updates"] == 0
    assert len(registry) == 1


def test_gap_and_backwards_time_reset_instead_of_learning_across_discontinuity():
    registry = AudioTemporalPredictionRegistry()
    first = registry.update(
        source_id="s", generation_id="g", consent_scope_id="c" * 64,
        start_ms=0, end_ms=1000, cues=SILENCE, finality="FINAL",
    )
    assert first["status"] == "WARMUP_FEATURE_BASELINE"
    gap = registry.update(
        source_id="s", generation_id="g", consent_scope_id="c" * 64,
        start_ms=4000, end_ms=5000, cues=VOICED, finality="FINAL",
    )
    assert gap["status"] == "RESET_GAP"
    backwards = registry.update(
        source_id="s", generation_id="g", consent_scope_id="c" * 64,
        start_ms=3000, end_ms=4000, cues=SILENCE, finality="FINAL",
    )
    assert backwards["status"] == "RESET_CHRONOLOGY"


def test_explicit_reset_clears_only_matching_source_generation():
    registry = AudioTemporalPredictionRegistry()
    registry.update(source_id="s1", generation_id="g1", consent_scope_id="1" * 64,
                    start_ms=0, end_ms=1000, cues=SILENCE, finality="FINAL")
    registry.update(source_id="s2", generation_id="g2", consent_scope_id="2" * 64,
                    start_ms=0, end_ms=1000, cues=VOICED, finality="FINAL")
    assert registry.reset(source_id="s1", generation_id="g1") == 1
    assert len(registry) == 1
    assert registry.reset() == 1
    assert len(registry) == 0


def test_invalid_scope_interval_activity_and_nan_fail_closed():
    registry = AudioTemporalPredictionRegistry()
    with pytest.raises(AudioTemporalPredictionError):
        registry.update(source_id="s", generation_id="g", consent_scope_id="short",
                        start_ms=0, end_ms=1000, cues=SILENCE, finality="FINAL")
    with pytest.raises(AudioTemporalPredictionError):
        registry.update(source_id="s", generation_id="g", consent_scope_id="a" * 64,
                        start_ms=0, end_ms=1001, cues=SILENCE, finality="FINAL")
    with pytest.raises(AudioTemporalPredictionError):
        acoustic_feature_vector(dict(VOICED, activity_hint="UNKNOWN"))
    with pytest.raises(AudioTemporalPredictionError):
        acoustic_feature_vector(dict(VOICED, voiced_fraction=float("nan")))


def test_registry_capacity_is_bounded_and_evicts_oldest_stream():
    registry = AudioTemporalPredictionRegistry(max_streams=1)
    registry.update(source_id="s1", generation_id="g1", consent_scope_id="1" * 64,
                    start_ms=0, end_ms=1000, cues=SILENCE, finality="FINAL")
    registry.update(source_id="s2", generation_id="g2", consent_scope_id="2" * 64,
                    start_ms=0, end_ms=1000, cues=VOICED, finality="FINAL")
    assert len(registry) == 1
    assert registry.reset(source_id="s1", generation_id="g1") == 0
    assert registry.reset(source_id="s2", generation_id="g2") == 1


def test_direct_predictor_reports_real_gradient_and_parameter_delta():
    predictor = AudioTemporalPredictor(learning_rate=0.5, warmup_updates=1)
    zeros = [0.0] * FEATURE_COUNT
    ones = [1.0] * FEATURE_COUNT
    predictor.update(zeros)
    result = predictor.update(ones)
    assert result["gradient_l2"] > 0
    assert result["weight_delta_l2"] > 0
    assert result["status"] == "SHADOW_MEASURED"
    assert predictor._parameter_l2() <= math.sqrt(182) * 2.0


def test_real_a5_a4_consumer_uses_predictive_novelty_only_on_a4_novelty(tmp_path, monkeypatch):
    sequence = [SILENCE, UNCERTAIN, UNCERTAIN, SILENCE, SILENCE,
                UNCERTAIN, UNCERTAIN, SILENCE, SILENCE, UNCERTAIN, UNCERTAIN, UNCERTAIN]

    runtime, event = make_runtime(tmp_path / "predictor")
    predictor_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            results = run_consumer_sequence(
                runtime, event, patch, sequence, predictor_attention,
            )
        last = results[-1]
        prediction = last["a4"]["audio_temporal_prediction"]
        assert prediction["status"] == "SHADOW_MEASURED"
        assert last["a4"]["audio_temporal_predictive_novelty"] > 0
        assert last["a4"]["audio_temporal_predictive_novelty"] <= ATTENTION_GAIN
        assert last["a4"]["voice_activity_hint"] == "UNCERTAIN"
        assert last["learning_authority"] is False
        assert last["action_authority"] is False
        assert len(last["c3_admission"].selected) == 1
    finally:
        runtime.store.close()

    class DisabledRegistry:
        def update(self, **_kwargs):
            return unavailable_prediction("DISABLED_CONTROL")

    control_runtime, control_event = make_runtime(tmp_path / "control")
    control_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            control_results = run_consumer_sequence(
                control_runtime, control_event, patch, sequence,
                control_attention, registry_override=DisabledRegistry(),
            )
        control_last = control_results[-1]
        assert control_last["a4"]["audio_temporal_prediction"]["status"] == "DISABLED_CONTROL"
        assert control_attention.calls[-1]["novelty"] < predictor_attention.calls[-1]["novelty"]
        assert control_attention.calls[-1]["external_interrupt"] == pytest.approx(
            predictor_attention.calls[-1]["external_interrupt"]
        )
        assert control_last["c3_admission"].selected[0].source_id == SOURCE
    finally:
        control_runtime.store.close()


def test_actual_provisional_consumer_does_not_train_or_admit(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    capture = CaptureAttention()
    try:
        monkeypatch.setattr(
            audio_voice_module,
            "extract_voice_cues",
            lambda _pcm, _sample_rate, backend="python": dict(VOICED),
        )
        monkeypatch.setattr(audio_voice_module.attctl, "controller", lambda _runtime: capture)
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_check, consent_guard=consent_guard(consent_check),
            finality="PROVISIONAL",
        )
        assert result["a4"]["audio_temporal_prediction"]["status"] == "PROVISIONAL_IGNORED"
        assert result["a4"]["audio_temporal_predictive_novelty"] == 0.0
        assert result["a4"]["audio_temporal_omission_novelty"] == 0.0
        assert result["a4"]["audio_event_expectation"]["status"] == "PROVISIONAL_IGNORED"
        assert result["a4"]["audio_event_omission_novelty"] == 0.0
        assert result["c3_admission"].selected == ()
        assert len(_runtime_audio_temporal_prediction_registry(runtime)) == 0
        assert len(audio_voice_module._runtime_audio_event_expectation_registry(runtime)) == 0
    finally:
        runtime.store.close()


def test_consent_scope_rotation_and_explicit_reset_clear_consumer_state(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    capture = CaptureAttention()
    try:
        monkeypatch.setattr(
            audio_voice_module,
            "extract_voice_cues",
            lambda _pcm, _sample_rate, backend="python": dict(VOICED),
        )
        monkeypatch.setattr(audio_voice_module.attctl, "controller", lambda _runtime: capture)
        consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_check, consent_guard=consent_guard(consent_check),
            finality="FINAL",
        )
        registry = _runtime_audio_temporal_prediction_registry(runtime)
        event_registry = audio_voice_module._runtime_audio_event_expectation_registry(runtime)
        assert len(registry) == 1
        assert len(event_registry) == 1
        reset_runtime_temporal_voice_states(
            runtime, source_id=SOURCE, generation_id=event["brain_generation_id"],
        )
        assert len(registry) == 0
        assert len(event_registry) == 0
        consume_pcm16_voice_window(
            runtime, tone(phase=0.2), sample_rate=16000, start_ms=1100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=NEW_RECEIPT,
            consent_check=consent_check, consent_guard=consent_guard(consent_check),
            finality="FINAL",
        )
        assert len(registry) == 1
        assert len(event_registry) == 1
        assert registry._states[(SOURCE, event["brain_generation_id"])].predictor.updates == 0
    finally:
        runtime.store.close()


def test_opt_in_persistent_weights_survive_runtime_restart_and_revoke(tmp_path, monkeypatch):
    sequence = [SILENCE, UNCERTAIN, UNCERTAIN, SILENCE, SILENCE,
                UNCERTAIN, UNCERTAIN, SILENCE, SILENCE, UNCERTAIN, UNCERTAIN, UNCERTAIN]
    runtime, event = make_runtime(tmp_path)
    runtime.cfg = {"raw_ear_persist_prediction_weights": True}
    capture = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            first = run_consumer_sequence(runtime, event, patch, sequence, capture)
        prediction = first[-1]["a4"]["audio_temporal_prediction"]
        assert prediction["status"] == "SHADOW_MEASURED"
        assert prediction["weight_persistence"] is True
        assert prediction["training_data_persisted"] is False
        state = runtime._raw_ear_prediction_registry._states[(SOURCE, event["brain_generation_id"])]
        before = state.predictor.state_dict()
        assert before["updates"] > 0
        assert any(abs(value) > 0 for row in before["weights"] for value in row)
        rows = runtime.store.rows(
            "SELECT key,payload FROM states WHERE key LIKE ?",
            ("raw_ear_prediction.v1.%",),
        )
        assert len(rows) == 1
        payload, _version = runtime.store.state(rows[0]["key"], None)
        assert set(payload) == {
            "schema", "status", "source_scope_sha256", "generation_scope_sha256",
            "consent_scope_id", "method", "weights", "updates", "last_touched_ns", "state_sha256",
        }
        assert "previous_features" not in payload and "pcm" not in payload and "transcript" not in payload
    finally:
        runtime.store.close()

    restarted, event2 = make_runtime(tmp_path, preserve_generation=True)
    restarted.cfg = {"raw_ear_persist_prediction_weights": True}
    assert event2["brain_generation_id"] == event["brain_generation_id"]
    capture2 = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            second = run_consumer_sequence(restarted, event2, patch, sequence, capture2)
        assert second[-1]["a4"]["audio_temporal_prediction"]["weight_persistence"] is True
        after = restarted._raw_ear_prediction_registry._states[
            (SOURCE, event2["brain_generation_id"])
        ].predictor.state_dict()
        assert after["updates"] > before["updates"]
        assert after["weights"] != before["weights"]

        rotated = restarted._raw_ear_prediction_registry.update(
            source_id=SOURCE,
            generation_id=event2["brain_generation_id"],
            consent_scope_id="b" * 64,
            start_ms=20000,
            end_ms=21000,
            cues=VOICED,
            finality="FINAL",
        )
        assert rotated["status"] == "RESET_CONSENT_SCOPE"
        reset_state = restarted._raw_ear_prediction_registry._states[
            (SOURCE, event2["brain_generation_id"])
        ].predictor.state_dict()
        assert reset_state["updates"] == 0
        assert not any(abs(value) > 0 for row in reset_state["weights"] for value in row)
    finally:
        restarted.store.close()

    # Revocation after restart must clear persisted weights even before a registry exists.
    revoked, _event3 = make_runtime(tmp_path, preserve_generation=True)
    revoked.cfg = {"raw_ear_persist_prediction_weights": True}
    reset_runtime_temporal_voice_states(
        revoked, source_id=SOURCE, generation_id=event["brain_generation_id"]
    )
    assert revoked.store.rows(
        "SELECT key FROM states WHERE key LIKE ?",
        ("raw_ear_prediction.v1.%",),
    ) == []
    revoked.store.close()


def test_persistent_mode_does_not_write_provisional_windows(tmp_path):
    runtime, event = make_runtime(tmp_path)
    runtime.cfg = {"raw_ear_persist_prediction_weights": True}
    try:
        registry = _runtime_audio_temporal_prediction_registry(runtime)
        result = registry.update(
            source_id=SOURCE,
            generation_id=event["brain_generation_id"],
            consent_scope_id="c" * 64,
            start_ms=0,
            end_ms=1000,
            cues=VOICED,
            finality="PROVISIONAL",
        )
        assert result["status"] == "PROVISIONAL_IGNORED"
        assert result["weight_persistence"] is True
        assert runtime.store.rows(
            "SELECT key FROM states WHERE key LIKE ?",
            ("raw_ear_prediction.v1.%",),
        ) == []
    finally:
        runtime.store.close()


def _insert_state_fixture(store, key, payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    with store.tx() as connection:
        connection.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)", (key, 1, encoded))


def test_persistent_pruning_uses_literal_prefix_and_keeps_similar_unrelated_keys(tmp_path):
    runtime, _event = make_runtime(tmp_path)
    registry = AudioTemporalPredictionRegistry(max_streams=1, store=runtime.store)
    unrelated_key = "rawXearYprediction.v1.foreign"
    unrelated_payload = {"last_touched_ns": 0}
    _insert_state_fixture(runtime.store, unrelated_key, unrelated_payload)
    try:
        registry.update(
            source_id="source-a", generation_id="generation-a",
            consent_scope_id="a" * 64, start_ms=0, end_ms=1000,
            cues=SILENCE, finality="FINAL",
        )
        assert runtime.store.state(unrelated_key, None)[0] == unrelated_payload
    finally:
        runtime.store.close()


def test_persistent_reset_uses_literal_prefix_and_keeps_similar_unrelated_keys(tmp_path):
    runtime, _event = make_runtime(tmp_path)
    registry = AudioTemporalPredictionRegistry(store=runtime.store)
    unrelated_key = "rawXearYprediction.v1.foreign"
    unrelated_payload = {
        "source_scope_sha256": registry._scope_hash("source-a"),
        "generation_scope_sha256": registry._scope_hash("generation-other"),
    }
    _insert_state_fixture(runtime.store, unrelated_key, unrelated_payload)
    try:
        assert registry.reset(source_id="source-a") == 0
        assert runtime.store.state(unrelated_key, None)[0] == unrelated_payload
    finally:
        runtime.store.close()


def test_signed_negative_prediction_error_surfaces_an_omitted_expected_cue():
    predictor = AudioTemporalPredictor(learning_rate=0.20, warmup_updates=1)
    repeated_change = (1.0,) * FEATURE_COUNT
    predictor.update(repeated_change)  # temporal warm-up
    for _ in range(8):
        predictor.update(repeated_change)
    omitted = predictor.update((0.0,) * FEATURE_COUNT)
    assert omitted["status"] == "SHADOW_MEASURED"
    assert omitted["omission_prediction_error"] > 0.1
    assert omitted["negative_prediction_error"] < 0.0
    assert omitted["signed_prediction_error"] < 0.0
    assert omitted["commission_prediction_error"] == 0.0
    assert predictive_omission_novelty(omitted) > 0.0
    # This omission can be better than the persistence baseline, so the old
    # positive-only excess-error channel may correctly remain zero.
    assert predictive_attention_novelty(omitted) == 0.0
    assert predictive_omission_novelty(unavailable_prediction("PROVISIONAL_IGNORED")) == 0.0


def test_a4_consumer_routes_audio_omission_to_novelty_not_interrupt(tmp_path, monkeypatch):
    sequence = [
        SILENCE, VOICED, SILENCE, VOICED, SILENCE,
        VOICED, SILENCE, VOICED, VOICED,
    ]
    runtime, event = make_runtime(tmp_path)
    predictor_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            predicted = run_consumer_sequence(runtime, event, patch, sequence, predictor_attention)
        last = predicted[-1]
        prediction = last["a4"]["audio_temporal_prediction"]
        assert prediction["status"] == "SHADOW_MEASURED"
        assert prediction["negative_prediction_error"] < 0.0
        omission_novelty = last["a4"]["audio_temporal_omission_novelty"]
        assert omission_novelty > 0.0
        assert omission_novelty <= ATTENTION_GAIN
        assert predictor_attention.calls[-1]["novelty"] >= omission_novelty
    finally:
        runtime.store.close()

    class DisabledRegistry:
        def update(self, **_kwargs):
            return unavailable_prediction("DISABLED_CONTROL")

    control_runtime, control_event = make_runtime(tmp_path / "control")
    control_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            control = run_consumer_sequence(
                control_runtime, control_event, patch, sequence,
                control_attention, registry_override=DisabledRegistry(),
            )
        assert control[-1]["a4"]["audio_temporal_omission_novelty"] == 0.0
        assert predictor_attention.calls[-1]["external_interrupt"] == pytest.approx(
            control_attention.calls[-1]["external_interrupt"]
        )
        # The predictor contributes through max-fusion; stronger existing voice evidence may dominate it.
        assert predictor_attention.calls[-1]["novelty"] >= control_attention.calls[-1]["novelty"]
    finally:
        control_runtime.store.close()


def test_a4_consumer_routes_timed_event_omission_to_novelty_only(tmp_path, monkeypatch):
    sequence = [
        VOICED, EVENT_SILENCE, VOICED, EVENT_SILENCE, VOICED,
        EVENT_SILENCE, VOICED, EVENT_SILENCE, EVENT_SILENCE,
    ]
    runtime, event = make_runtime(tmp_path)
    predictor_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            predicted = run_consumer_sequence(runtime, event, patch, sequence, predictor_attention)
        last = predicted[-1]
        expectation = last["a4"]["audio_event_expectation"]
        omission_novelty = last["a4"]["audio_event_omission_novelty"]
        assert expectation["status"] == "SHADOW_MEASURED"
        assert expectation["omission_detected"] is True
        assert omission_novelty > 0.0
        assert omission_novelty <= 0.05
        assert last["a4"]["learning_authority"] is False
        assert last["a4"]["action_authority"] is False
    finally:
        runtime.store.close()

    class DisabledEventRegistry:
        def update(self, **_kwargs):
            return audio_voice_module.unavailable_expectation("DISABLED_CONTROL")

    control_runtime, control_event = make_runtime(tmp_path / "event-control")
    control_attention = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            control = run_consumer_sequence(
                control_runtime, control_event, patch, sequence, control_attention,
                event_registry_override=DisabledEventRegistry(),
            )
        assert control[-1]["a4"]["audio_event_omission_novelty"] == 0.0
        assert predictor_attention.calls[-1]["external_interrupt"] == pytest.approx(
            control_attention.calls[-1]["external_interrupt"]
        )
        assert predictor_attention.calls[-1]["novelty"] >= control_attention.calls[-1]["novelty"]
    finally:
        control_runtime.store.close()


def _event_registry_window(registry, activity, start_ms, end_ms, *, activity_score=0.9):
    if activity == "VOICED":
        cues = dict(VOICED)
    elif activity == "UNCERTAIN":
        cues = dict(UNCERTAIN)
    else:
        cues = dict(EVENT_SILENCE)
    cues["activity_score"] = activity_score
    return registry.update(
        source_id="event-expectation-source",
        generation_id="event-expectation-generation",
        consent_scope_id="e" * 64,
        start_ms=start_ms,
        end_ms=end_ms,
        cues=cues,
        finality="FINAL",
    )


def _seed_event_registry(registry):
    for activity, start_ms, end_ms in (
        ("VOICED", 100, 300), ("SILENCE", 1100, 1300),
        ("VOICED", 2100, 2300), ("SILENCE", 3100, 3300),
        ("VOICED", 4100, 4300), ("SILENCE", 5100, 5300),
        ("VOICED", 6100, 6300),
    ):
        _event_registry_window(registry, activity, start_ms, end_ms)


def test_uncertain_window_over_expected_event_breaks_pending_omission(tmp_path, monkeypatch):
    sequence = [
        VOICED, EVENT_SILENCE, VOICED, EVENT_SILENCE, VOICED,
        EVENT_SILENCE, VOICED, EVENT_SILENCE, UNCERTAIN, EVENT_SILENCE,
    ]
    runtime, event = make_runtime(tmp_path)
    capture = CaptureAttention()
    try:
        with monkeypatch.context() as patch:
            results = run_consumer_sequence(runtime, event, patch, sequence, capture)
        assert results[-2]["a4"]["audio_event_expectation"]["status"] == "CENSORED_UNCERTAIN"
        after = results[-1]["a4"]["audio_event_expectation"]
        assert after["omission_detected"] is False
        assert after["expected_events"] == []
        assert results[-1]["a4"]["audio_event_omission_novelty"] == 0.0
    finally:
        runtime.store.close()


def test_low_confidence_silence_is_censored_not_used_as_omission():
    registry = AudioEventExpectationRegistry()
    _seed_event_registry(registry)
    result = _event_registry_window(
        registry, "SILENCE", 8100, 9100, activity_score=0.1,
    )
    assert result["status"] == "CENSORED_LOW_CONFIDENCE"
    assert result["omission_detected"] is False
    assert result["attention_novelty"] == 0.0


def test_late_non_target_window_after_expected_time_does_not_prove_omission():
    registry = AudioEventExpectationRegistry()
    _seed_event_registry(registry)
    _event_registry_window(registry, "SILENCE", 7000, 7200)
    result = _event_registry_window(registry, "SILENCE", 8500, 9500)
    assert result["omission_detected"] is False
    assert result["attention_novelty"] == 0.0


def test_optional_event_registry_failure_does_not_break_raw_ear(tmp_path, monkeypatch):
    runtime, event = make_runtime(tmp_path)
    capture = CaptureAttention()
    try:
        monkeypatch.setattr(
            audio_voice_module,
            "extract_voice_cues",
            lambda _pcm, _sample_rate, backend="python": dict(VOICED),
        )
        monkeypatch.setattr(audio_voice_module.attctl, "controller", lambda _runtime: capture)

        def unavailable_registry(_runtime):
            raise ValueError("runtime cannot retain optional event state")

        monkeypatch.setattr(
            audio_voice_module,
            "_runtime_audio_event_expectation_registry",
            unavailable_registry,
        )
        result = consume_pcm16_voice_window(
            runtime, tone(), sample_rate=16000, start_ms=100,
            event_id=event["event_id"], generation_id=event["brain_generation_id"],
            source_id=SOURCE, consent_receipt=RECEIPT,
            consent_check=consent_check, consent_guard=consent_guard(consent_check),
            finality="FINAL",
        )
        assert result["packet"]["packet_id"]
        assert result["a4"]["voice_cues"]["activity_hint"] == "VOICED"
        assert result["a4"]["audio_event_expectation"]["status"] == "REJECTED"
        assert result["a4"]["audio_event_omission_novelty"] == 0.0
    finally:
        runtime.store.close()


def test_integrated_audio_candidate_pins_all_current_sources():
    import hashlib
    from pathlib import Path

    code_dir = Path(__file__).resolve().parents[1]
    builder_path = code_dir / "scripts" / "integrated_audio_context_candidate_20261121.py"
    namespace = {}
    source = builder_path.read_text(encoding="utf-8")
    exec(compile(source, str(builder_path), "exec"), namespace)
    pins = namespace["SOURCE_BLOBS"]
    assert "v13/audio_voice_cues.py" in pins
    assert "v13/audio_temporal_prediction.py" in pins
    assert "v13/audio_event_expectation.py" in pins
    for relative, expected in pins.items():
        path = code_dir / relative
        assert path.is_file(), relative
        raw = path.read_bytes()
        actual = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        assert actual == expected, relative


def test_a4_temporal_prediction_is_source_bound_into_b1_b2_and_c3_context(tmp_path, monkeypatch):
    import importlib.util
    import sys
    import types
    from pathlib import Path
    from v13.audio_voice_cues import audio_consent_lease

    runtime, event = make_runtime(tmp_path / "cross-organ")
    capture = CaptureAttention()
    code_dir = Path(__file__).resolve().parents[1]
    builder_path = code_dir / "scripts" / "integrated_audio_context_candidate_20261121.py"
    spec = importlib.util.spec_from_file_location("raw_ear_context_candidate", builder_path)
    builder = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(builder)
    sources = {
        relative: (code_dir / relative).read_bytes()
        for relative in ("v13/runtime.py", "v13/cognition.py", "v13/arithmetic_reflex.py")
    }
    candidate = builder.apply_sources(code_dir, sources)
    context_store = types.ModuleType("v13.audio_context_store")
    context_store.__package__ = "v13"
    exec(compile(candidate["v13/audio_context_store.py"], "v13/audio_context_store.py", "exec"),
         context_store.__dict__)
    monkeypatch.setitem(sys.modules, "v13.audio_context_store", context_store)

    cognition = candidate["v13/cognition.py"].decode("utf-8")
    assert "consumer=role" in cognition
    assert "query['audio_context']=audio_context" in cognition
    assert "audio_context_refs" in cognition

    def check(source_id, receipt):
        return source_id == SOURCE and receipt == RECEIPT

    try:
        with audio_consent_lease(
            runtime, SOURCE, event["brain_generation_id"], RECEIPT,
            check, consent_guard(check),
        ) as lease:
            with monkeypatch.context() as patch:
                patch.setattr(
                    audio_voice_module, "extract_voice_cues",
                    lambda _pcm, _rate, backend="python": dict(VOICED),
                )
                patch.setattr(audio_voice_module.attctl, "controller", lambda _runtime: capture)
                result = consume_pcm16_voice_window(
                    runtime, tone(), sample_rate=16000, start_ms=12_100,
                    event_id=event["event_id"], generation_id=event["brain_generation_id"],
                    source_id=SOURCE, consent_receipt=RECEIPT,
                    consent_check=None, consent_guard=None, consent_lease=lease,
                    finality="FINAL",
                )
            window = {
                "source_id": SOURCE, "consent_receipt": RECEIPT,
                "consent_check": check, "_consent_lease": lease,
            }
            assert result["c3_admission"].status == "ADMITTED"
            assert result["c3_admission"].selected
            packet_value = result["packet"]
            assert packet_value["brain_generation_id"] == runtime.store.generation_id
            assert result["a4"]["packet_id"] == packet_value["packet_id"]
            try:
                context_store._a4_temporal_context(
                    result["a4"], packet_value, packet_value["source_ref"],
                    packet_value["segments"][0], event["event_id"], SOURCE,
                )
            except Exception as exc:
                pytest.fail(f"A4 temporal context validation failed: {type(exc).__name__}: {exc}")
            context = context_store.record(runtime, event["event_id"], result, window)
            if context is None:
                row = runtime.store.one(
                    "SELECT metrics FROM telemetry WHERE event_id=? ORDER BY id DESC LIMIT 1",
                    (event["event_id"],),
                )
                pytest.fail(f"audio context record returned None; last telemetry={row}")
            temporal = context["body"]["a4_temporal"]
            assert temporal["schema"] == "v14.raw-ear-a4-temporal-context/1"
            assert temporal["learning_authority"] is False
            assert temporal["action_authority"] is False
            assert temporal["truth_authority"] is False
            assert temporal["temporal_prediction"]["weight_scope"] == "EPHEMERAL_CONSENT_SCOPED_PROCESS"
            assert temporal["temporal_prediction"]["training_data_persisted"] is False
            assert "pcm16" not in json.dumps(context["body"])
            assert context["body"]["transcript"] is None
            assert context["body"]["observations"]
            assert all(len(item["summary"]) <= 256 for item in context["body"]["observations"])
            for role in ("B1_DETAIL", "B2_GIST", "C3"):
                viewed = context_store.view(runtime, event["event_id"], role)
                assert viewed is not None
                assert viewed["a4_temporal"] == temporal
        assert context_store.view(runtime, event["event_id"], "C3") is None
    finally:
        runtime.store.close()
