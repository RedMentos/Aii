"""Deterministic A4 temporal-prediction ablation over synthetic acoustic cues.

This is a source-isolation and online-vs-persistence baseline probe for the
existing RAW EAR A4 consumer. It does not ingest PCM, train a production model,
persist examples, or benchmark Android hardware.
"""
from __future__ import annotations

import hashlib
import json
from statistics import fmean

from v13.audio_temporal_prediction import (
    ATTENTION_GAIN,
    AudioTemporalPredictionRegistry,
    AudioTemporalPredictor,
    acoustic_feature_vector,
    predictive_attention_novelty,
    predictive_omission_novelty,
)
from v13.audio_event_expectation import (
    ATTENTION_GAIN as EVENT_ATTENTION_GAIN,
    AudioEventExpectationRegistry,
    predictive_event_omission_novelty,
)

SCHEMA = "v14.a4.temporal-ablation/1"
METRIC_KEYS = (
    "status", "updates", "prediction_error_mae", "persistence_baseline_mae",
    "improvement_mae", "excess_prediction_error", "signed_prediction_error",
    "negative_prediction_error", "omission_prediction_error",
    "commission_prediction_error", "omission_attention_novelty",
    "attention_novelty", "gradient_l2", "weight_delta_l2", "parameter_l2",
    "weight_persistence", "training_data_persisted", "learning_authority",
    "action_authority", "truth_authority",
)


def _cue(
    activity: str,
    *,
    f0: float | None,
    f0_range: float | None,
    energy: float,
    voiced_energy: float | None,
    voiced_fraction: float,
    confidence: float,
    activity_score: float,
    prosody: float,
) -> dict:
    return {
        "method": "SYNTHETIC_RAW_EAR_CUE_FIXTURE",
        "frame_ms": 40,
        "hop_ms": 20,
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


SILENCE = _cue(
    "SILENCE", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.0, prosody=0.0,
)
VOICED = _cue(
    "VOICED", f0=145.0, f0_range=24.0, energy=18.0, voiced_energy=9.0,
    voiced_fraction=0.82, confidence=0.91, activity_score=0.84, prosody=0.24,
)
UNVOICED_NOISE = _cue(
    "UNVOICED_NOISE", f0=None, f0_range=None, energy=34.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.72, prosody=0.68,
)
EVENT_SILENCE = _cue(
    "SILENCE", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.9, prosody=0.0,
)
EVENT_UNCERTAIN = _cue(
    "UNCERTAIN", f0=None, f0_range=None, energy=0.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=0.0, prosody=0.0,
)

IMPULSIVE = _cue(
    "IMPULSIVE", f0=None, f0_range=None, energy=70.0, voiced_energy=None,
    voiced_fraction=0.0, confidence=0.0, activity_score=1.0, prosody=1.0,
)

# Different deterministic streams; labels are synthetic identifiers, not user data.
PATTERNS = {
    "speech-periodic": (
        SILENCE, VOICED, VOICED, SILENCE, SILENCE, VOICED, VOICED, SILENCE,
        SILENCE, VOICED, VOICED, VOICED, SILENCE, VOICED, VOICED, SILENCE,
    ),
    "non-speech-impulse": (
        SILENCE, IMPULSIVE, SILENCE, UNVOICED_NOISE, SILENCE, IMPULSIVE,
        SILENCE, SILENCE, IMPULSIVE, UNVOICED_NOISE, SILENCE, IMPULSIVE,
        SILENCE, UNVOICED_NOISE, SILENCE, SILENCE,
    ),
    "mixed-activity": (
        SILENCE, VOICED, UNVOICED_NOISE, SILENCE, IMPULSIVE, SILENCE,
        VOICED, VOICED, SILENCE, UNVOICED_NOISE, IMPULSIVE, SILENCE,
        VOICED, SILENCE, UNVOICED_NOISE, SILENCE,
    ),
}


def _scope(source_id: str) -> str:
    return hashlib.sha256(("v14-a4-ablation:" + source_id).encode("utf-8")).hexdigest()


def _feed(registry: AudioTemporalPredictionRegistry, source_id: str, sequence: tuple[dict, ...]) -> list[dict]:
    generation_id = "synthetic-generation:" + source_id
    consent_scope_id = _scope(source_id)
    results = []
    for index, cues in enumerate(sequence):
        results.append(registry.update(
            source_id=source_id,
            generation_id=generation_id,
            consent_scope_id=consent_scope_id,
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            cues=cues,
            finality="FINAL",
        ))
    return results


def _project(results: list[dict]) -> list[dict]:
    return [{key: result.get(key) for key in METRIC_KEYS} for result in results]


def _summarize(results: list[dict]) -> dict:
    measured = [item for item in results if item.get("status") == "SHADOW_MEASURED"]
    if not measured:
        return {
            "observations": len(results),
            "measured_windows": 0,
            "gradient_updates": 0,
            "mean_model_mae": None,
            "mean_persistence_baseline_mae": None,
            "mean_improvement_mae": None,
            "positive_improvement_fraction": 0.0,
            "max_weight_delta_l2": 0.0,
            "max_parameter_l2": 0.0,
            "max_attention_novelty": 0.0,
            "max_omission_attention_novelty": 0.0,
        }
    improvements = [float(item["improvement_mae"]) for item in measured]
    return {
        "observations": len(results),
        "measured_windows": len(measured),
        "gradient_updates": measured[-1]["updates"],
        "mean_model_mae": round(fmean(float(item["prediction_error_mae"]) for item in measured), 8),
        "mean_persistence_baseline_mae": round(fmean(float(item["persistence_baseline_mae"]) for item in measured), 8),
        "mean_improvement_mae": round(fmean(improvements), 8),
        "positive_improvement_fraction": round(sum(value > 0.0 for value in improvements) / len(improvements), 8),
        "max_weight_delta_l2": round(max(float(item["weight_delta_l2"]) for item in measured), 8),
        "max_parameter_l2": round(max(float(item["parameter_l2"]) for item in measured), 8),
        "max_attention_novelty": round(max(predictive_attention_novelty(item) for item in measured), 8),
        "max_omission_attention_novelty": round(max(predictive_omission_novelty(item) for item in measured), 8),
    }




def _feed_direct(sequence: tuple[dict, ...], *, learning_rate: float) -> list[dict]:
    """Run the same registry delta transform with an explicit predictor rate."""
    predictor = AudioTemporalPredictor(learning_rate=learning_rate)
    previous_features = None
    results = []
    for cues in sequence:
        features = acoustic_feature_vector(cues)
        if previous_features is None:
            previous_features = features
            continue
        delta = tuple(abs(features[index] - previous_features[index]) for index in range(len(features)))
        results.append(predictor.update(delta))
        previous_features = features
    return results


def _default_rate_direct_registry_parity() -> bool:
    for source_id, sequence in PATTERNS.items():
        registry_results = _feed(AudioTemporalPredictionRegistry(), source_id, sequence)
        direct_results = _feed_direct(sequence, learning_rate=0.20)
        if _project(registry_results[1:]) != _project(direct_results):
            return False
    return True


def _learning_rate_sweep() -> dict:
    rates = (0.02, 0.05, 0.10, 0.20)
    return {
        source_id: {
            str(rate): _summarize(_feed_direct(sequence, learning_rate=rate))
            for rate in rates
        }
        for source_id, sequence in PATTERNS.items()
    }


def _source_isolation_probe() -> tuple[bool, float]:
    isolated = {}
    for source_id, sequence in PATTERNS.items():
        isolated[source_id] = _project(_feed(AudioTemporalPredictionRegistry(), source_id, sequence))

    shared = AudioTemporalPredictionRegistry()
    interleaved = {source_id: [] for source_id in PATTERNS}
    longest = max(len(sequence) for sequence in PATTERNS.values())
    for index in range(longest):
        for source_id, sequence in PATTERNS.items():
            if index >= len(sequence):
                continue
            generation_id = "synthetic-generation:" + source_id
            interleaved[source_id].append(shared.update(
                source_id=source_id,
                generation_id=generation_id,
                consent_scope_id=_scope(source_id),
                start_ms=index * 1000,
                end_ms=(index + 1) * 1000,
                cues=sequence[index],
                finality="FINAL",
            ))
    projected = {source_id: _project(results) for source_id, results in interleaved.items()}
    equal = projected == isolated
    max_difference = 0.0
    for source_id in PATTERNS:
        for left, right in zip(projected[source_id], isolated[source_id]):
            for key in ("prediction_error_mae", "persistence_baseline_mae", "weight_delta_l2", "parameter_l2"):
                a, b = left[key], right[key]
                if a is not None and b is not None:
                    max_difference = max(max_difference, abs(float(a) - float(b)))
    return equal, round(max_difference, 12)


def _no_context_control(sequence: tuple[dict, ...]) -> dict:
    registry = AudioTemporalPredictionRegistry()
    measured = 0
    max_novelty = 0.0
    for index, cues in enumerate(sequence):
        result = registry.update(
            source_id="synthetic-no-context",
            generation_id="synthetic-no-context-generation",
            consent_scope_id=_scope("synthetic-no-context"),
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            cues=cues,
            finality="FINAL",
        )
        measured += result.get("status") == "SHADOW_MEASURED"
        max_novelty = max(max_novelty, predictive_attention_novelty(result))
        registry.reset(source_id="synthetic-no-context", generation_id="synthetic-no-context-generation")
    return {"measured_windows": measured, "max_attention_novelty": round(max_novelty, 8), "final_stream_count": len(registry)}


def _provisional_control() -> dict:
    registry = AudioTemporalPredictionRegistry()
    result = registry.update(
        source_id="synthetic-provisional",
        generation_id="synthetic-provisional-generation",
        consent_scope_id=_scope("synthetic-provisional"),
        start_ms=0,
        end_ms=1000,
        cues=VOICED,
        finality="PROVISIONAL",
    )
    return {"status": result["status"], "stream_count": len(registry), "updates": result["updates"]}


def _consent_reset_control(sequence: tuple[dict, ...]) -> dict:
    registry = AudioTemporalPredictionRegistry()
    _feed(registry, "synthetic-consent-rotation", sequence[:10])
    result = registry.update(
        source_id="synthetic-consent-rotation",
        generation_id="synthetic-generation:synthetic-consent-rotation",
        consent_scope_id="f" * 64,
        start_ms=10_000,
        end_ms=11_000,
        cues=VOICED,
        finality="FINAL",
    )
    return {
        "status": result["status"],
        "updates": result["updates"],
        "parameter_l2": result.get("parameter_l2"),
        "weight_persistence": result["weight_persistence"],
    }




def _event_sequence(*, missing: bool) -> tuple[dict, ...]:
    sequence = [
        VOICED, EVENT_SILENCE, VOICED, EVENT_SILENCE, VOICED,
        EVENT_SILENCE, VOICED, EVENT_SILENCE,
    ]
    sequence.append(EVENT_SILENCE if missing else VOICED)
    return tuple(sequence)


def _event_feed(registry: AudioEventExpectationRegistry, source_id: str,
                sequence: tuple[dict, ...]) -> list[dict]:
    scope = _scope("event:" + source_id)
    generation_id = "synthetic-event-generation:" + source_id
    results = []
    for index, cues in enumerate(sequence):
        results.append(registry.update(
            source_id=source_id,
            generation_id=generation_id,
            consent_scope_id=scope,
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            cues=cues,
            finality="FINAL",
        ))
    return results


def _event_projection(results: list[dict]) -> list[dict]:
    keys = (
        "status", "observed_activity", "expected_events", "omissions",
        "omission_detected", "timing_confidence_proxy", "attention_novelty",
        "interval_samples", "state_persistence", "training_data_persisted",
        "calibrated_probability", "learning_authority", "action_authority",
        "truth_authority",
    )
    return [{key: item.get(key) for key in keys} for item in results]


def _event_source_isolation_probe() -> bool:
    patterns = {
        "expected": _event_sequence(missing=False),
        "missing": _event_sequence(missing=True),
    }
    isolated = {
        source: _event_projection(_event_feed(AudioEventExpectationRegistry(), source, seq))
        for source, seq in patterns.items()
    }
    shared = AudioEventExpectationRegistry()
    interleaved = {source: [] for source in patterns}
    for index in range(max(len(seq) for seq in patterns.values())):
        for source, seq in patterns.items():
            if index >= len(seq):
                continue
            interleaved[source].append(shared.update(
                source_id=source,
                generation_id="synthetic-event-generation:" + source,
                consent_scope_id=_scope("event:" + source),
                start_ms=index * 1000,
                end_ms=(index + 1) * 1000,
                cues=seq[index],
                finality="FINAL",
            ))
    return {
        source: _event_projection(results)
        for source, results in interleaved.items()
    } == isolated


def _event_expectation_ablation() -> dict:
    expected = _event_feed(
        AudioEventExpectationRegistry(), "expected", _event_sequence(missing=False),
    )[-1]
    missing = _event_feed(
        AudioEventExpectationRegistry(), "missing", _event_sequence(missing=True),
    )[-1]

    uncertain_registry = AudioEventExpectationRegistry()
    _event_feed(uncertain_registry, "uncertain", _event_sequence(missing=True)[:8])
    uncertain = uncertain_registry.update(
        source_id="uncertain",
        generation_id="synthetic-event-generation:uncertain",
        consent_scope_id=_scope("event:uncertain"),
        start_ms=8000,
        end_ms=9000,
        cues=EVENT_UNCERTAIN,
        finality="FINAL",
    )

    provisional_registry = AudioEventExpectationRegistry()
    _event_feed(provisional_registry, "provisional", _event_sequence(missing=True)[:8])
    provisional = provisional_registry.update(
        source_id="provisional",
        generation_id="synthetic-event-generation:provisional",
        consent_scope_id=_scope("event:provisional"),
        start_ms=8000,
        end_ms=9000,
        cues=EVENT_SILENCE,
        finality="PROVISIONAL",
    )
    after_provisional = provisional_registry.update(
        source_id="provisional",
        generation_id="synthetic-event-generation:provisional",
        consent_scope_id=_scope("event:provisional"),
        start_ms=8000,
        end_ms=9000,
        cues=EVENT_SILENCE,
        finality="FINAL",
    )

    consent_registry = AudioEventExpectationRegistry()
    _event_feed(consent_registry, "consent", _event_sequence(missing=True)[:8])
    consent_reset = consent_registry.update(
        source_id="consent",
        generation_id="synthetic-event-generation:consent",
        consent_scope_id="f" * 64,
        start_ms=8000,
        end_ms=9000,
        cues=EVENT_SILENCE,
        finality="FINAL",
    )

    no_context_registry = AudioEventExpectationRegistry()
    no_context_omissions = 0
    no_context_novelty = 0.0
    for index, cues in enumerate(_event_sequence(missing=True)):
        result = no_context_registry.update(
            source_id="no-context",
            generation_id="synthetic-event-generation:no-context",
            consent_scope_id=_scope("event:no-context"),
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            cues=cues,
            finality="FINAL",
        )
        no_context_omissions += result.get("omission_detected") is True
        no_context_novelty = max(no_context_novelty, predictive_event_omission_novelty(result))
        no_context_registry.reset(source_id="no-context", generation_id="synthetic-event-generation:no-context")

    return {
        "source_isolation_equal": _event_source_isolation_probe(),
        "expected_on_time": {
            "status": expected["status"],
            "omission_detected": expected["omission_detected"],
            "attention_novelty": expected["attention_novelty"],
        },
        "missing_event": {
            "status": missing["status"],
            "omission_detected": missing["omission_detected"],
            "attention_novelty": missing["attention_novelty"],
            "omission_novelty": predictive_event_omission_novelty(missing),
            "timing_confidence_proxy": missing["timing_confidence_proxy"],
            "omissions": missing["omissions"],
        },
        "uncertain_control": {
            "status": uncertain["status"],
            "omission_detected": uncertain["omission_detected"],
            "attention_novelty": uncertain["attention_novelty"],
        },
        "provisional_control": {
            "status": provisional["status"],
            "state_retained": len(provisional_registry) == 1,
            "final_after_provisional_detected": after_provisional["omission_detected"],
            "final_after_provisional_novelty": after_provisional["attention_novelty"],
        },
        "consent_reset_control": {
            "status": consent_reset["status"],
            "omission_detected": consent_reset["omission_detected"],
            "attention_novelty": consent_reset["attention_novelty"],
            "interval_samples": consent_reset["interval_samples"],
        },
        "no_context_control": {
            "omissions": no_context_omissions,
            "max_omission_novelty": round(no_context_novelty, 8),
            "final_stream_count": len(no_context_registry),
        },
        "attention_gain_cap": EVENT_ATTENTION_GAIN,
    }


def run_experiment() -> dict:
    per_source = {
        source_id: _summarize(_feed(AudioTemporalPredictionRegistry(), source_id, sequence))
        for source_id, sequence in PATTERNS.items()
    }
    source_isolation_equal, source_isolation_max_difference = _source_isolation_probe()
    default_rate_parity = _default_rate_direct_registry_parity()
    learning_rate_sweep = _learning_rate_sweep()
    event_expectation = _event_expectation_ablation()
    no_context = _no_context_control(PATTERNS["speech-periodic"])
    provisional = _provisional_control()
    consent_reset = _consent_reset_control(PATTERNS["speech-periodic"])
    all_results = list(per_source.values())
    return {
        "schema": SCHEMA,
        "environment": "SYNTHETIC",
        "synthetic_benchmark": True,
        "device_benchmark": False,
        "input": "synthetic acoustic cue dictionaries only; no PCM, transcript or speaker identity",
        "raw_audio_persisted": False,
        "training_examples_persisted": False,
        "per_source": per_source,
        "default_rate_direct_registry_parity": default_rate_parity,
        "learning_rate_sweep": learning_rate_sweep,
        "event_expectation": event_expectation,
        "source_isolation": {
            "interleaved_equals_isolated": source_isolation_equal,
            "max_metric_difference": source_isolation_max_difference,
        },
        "no_context_control": no_context,
        "provisional_control": provisional,
        "consent_reset_control": consent_reset,
        "aggregate": {
            "parameter_delta_nonzero": any(item["max_weight_delta_l2"] > 0.0 for item in all_results),
            "max_attention_novelty": max(item["max_attention_novelty"] for item in all_results),
            "max_omission_attention_novelty": max(item["max_omission_attention_novelty"] for item in all_results),
            "attention_gain_cap": ATTENTION_GAIN,
        },
        "not_claimed": [
            "real microphone or Android execution",
            "semantic audio understanding or calibrated event probabilities",
            "cross-source weight sharing or generalization",
            "B1/B2/C3 master-weight learning",
            "trained JEPA or cross-organ latent coupling",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), sort_keys=True, separators=(",", ":"), allow_nan=False))
