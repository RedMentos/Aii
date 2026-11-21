"""Additive timed RAW EAR voice/prosody cue adapter for A5, A4 and C3.

This module is deliberately separate from the Core-pinned A5 bridge. It uses
caller-supplied PCM16 only; it never opens a microphone, stores raw PCM, runs
ASR, identifies a speaker, or grants learning/action authority. The acoustic
classes and prosody-change score are deterministic heuristics, not a trained
VAD, speech classifier, or calibrated probability.
"""
from __future__ import annotations

import math
import struct
from contextlib import contextmanager
import threading
from statistics import median

from . import attention as attctl
from .audio_temporal_evidence import TemporalVoiceEvidence, TemporalVoiceEvidenceRegistry
from .audio_silero_vad import SileroVADStream, validate_vad_evidence
from .a5_audio_admission_bridge import audio_to_admission
from .audio_ear import observe_pcm16
from .audio_percept_contract import audio_percept_packet
from .audio_perception_bridge import _require_current_consent, _validate_runtime_binding
from .percept_admission import Percept, admit
from .common import dumps, now
from .contracts import validate


_ACTIVITY_HINTS = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}

# Protect first-use get/create/set on a shared Runtime during concurrent audio calls.
_RUNTIME_TEMPORAL_REGISTRY_INIT_LOCK = threading.Lock()


def _estimate_pitch(frame: list[float], sample_rate: float) -> tuple[float | None, float]:
    """Cheap normalized-autocorrelation F0 estimate over a 65..400 Hz range."""
    minimum_lag = max(2, int(sample_rate / 400))
    maximum_lag = min(len(frame) // 2, int(sample_rate / 65))
    correlations = []
    for lag in range(minimum_lag, maximum_lag + 1):
        left = frame[:-lag]
        right = frame[lag:]
        left_energy = sum(value * value for value in left)
        right_energy = sum(value * value for value in right)
        denominator = math.sqrt(left_energy * right_energy)
        if denominator <= 1e-9:
            continue
        correlation = sum(a * b for a, b in zip(left, right)) / denominator
        correlations.append((correlation, lag))
    if not correlations:
        return None, 0.0
    peak = max(item[0] for item in correlations)
    threshold = max(0.55, peak * 0.99)
    candidates = [(lag, corr) for corr, lag in correlations if corr >= threshold]
    if not candidates:
        return None, max(0.0, min(1.0, peak))
    lag, confidence = min(candidates, key=lambda item: item[0])
    return sample_rate / lag, max(0.0, min(1.0, confidence))


def _percentile(values: list[float], fraction: float) -> float | None:
    """Return a linearly interpolated percentile for a small bounded frame list."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def validate_voice_cues(cues: dict) -> dict:
    """Reject malformed/unbounded acoustic cues before they reach A4 or C3."""
    if type(cues) is not dict:
        raise ValueError("voice cues must be an object")
    required = {
        "method", "frame_ms", "hop_ms", "frame_count", "voiced_fraction",
        "voicing_confidence", "f0_median_hz", "f0_range_hz",
        "energy_range_db", "voiced_energy_range_db", "activity_hint", "activity_score",
        "prosody_change_score",
    }
    extra = set(cues) - required
    if (not required.issubset(cues) or not extra.issubset({"vad"})
            or cues.get("method") != "RAW_EAR_AUTOCORR_V3"):
        raise ValueError("voice cue fields or method are invalid")
    if cues.get("frame_ms") != 40 or cues.get("hop_ms") != 20:
        raise ValueError("voice cue timing is invalid")
    count = cues.get("frame_count")
    if type(count) is not int or not 0 <= count <= 50:
        raise ValueError("voice cue frame count is invalid")
    for key in ("voiced_fraction", "voicing_confidence", "activity_score", "prosody_change_score"):
        value = cues.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("voice cue score is invalid")
    for key, lower, upper in (("f0_median_hz", 65, 400), ("f0_range_hz", 0, 335),
                              ("energy_range_db", 0, 120),
                              ("voiced_energy_range_db", 0, 120)):
        value = cues.get(key)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                                  or not lower <= value <= upper):
            raise ValueError("voice cue range is invalid: " + key)
    if type(cues.get("activity_hint")) is not str or cues["activity_hint"] not in _ACTIVITY_HINTS:
        raise ValueError("voice activity hint is invalid")
    if count == 0 and (cues["f0_median_hz"] is not None or cues["f0_range_hz"] is not None
                       or cues["voiced_fraction"] != 0 or cues["voicing_confidence"] != 0):
        raise ValueError("voice cues cannot claim pitch or voicing without frames")
    if cues["f0_median_hz"] is None and cues["f0_range_hz"] is not None:
        raise ValueError("pitch range requires a median pitch")
    if cues["activity_hint"] != "VOICED" and cues["prosody_change_score"] != 0:
        raise ValueError("prosody change requires voiced activity")
    voiced_count = round(cues["voiced_fraction"] * count)
    if count and not math.isclose(cues["voiced_fraction"] * count, voiced_count, abs_tol=1e-3):
        raise ValueError("voice cue voiced fraction is inconsistent")
    if voiced_count == 0 and cues["voiced_energy_range_db"] is not None:
        raise ValueError("voiced energy range requires voiced frames")
    if voiced_count == 1 and (
        cues["f0_range_hz"] is not None
        or cues["voiced_energy_range_db"] != 0.0
        or cues["prosody_change_score"] != 0.0
    ):
        raise ValueError("a single voiced frame cannot establish prosody dynamics")
    if cues["activity_hint"] == "VOICED" and cues["voiced_energy_range_db"] is None:
        raise ValueError("voiced activity requires voiced energy range")
    if "vad" in cues:
        validate_vad_evidence(cues["vad"])
    return dict(cues)


def extract_voice_cues(pcm: bytes, sample_rate: int) -> dict:
    """Extract bounded pitch, voicing, energy and non-speech hints from mono PCM16."""
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("voice cue input must be complete PCM16 bytes")
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
        raise ValueError("voice cue sample rate must be 8000..48000")
    if len(pcm) > sample_rate * 2:
        raise ValueError("voice cue window is limited to one second")
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    overall_energy = sum(value * value for value in samples) / len(samples)
    overall_rms = math.sqrt(overall_energy) / 32768.0
    overall_peak = max(abs(value) for value in samples) / 32768.0

    # Block-average downsampling keeps the Python work bounded on ARM.
    factor = max(1, int(sample_rate // 8000))
    usable = (len(samples) // factor) * factor
    low_rate = [
        sum(samples[index:index + factor]) / factor
        for index in range(0, usable, factor)
    ]
    effective_rate = sample_rate / factor
    frame_ms, hop_ms = 40, 20
    frame_size = max(32, int(round(effective_rate * frame_ms / 1000.0)))
    hop_size = max(1, int(round(effective_rate * hop_ms / 1000.0)))
    frame_rms = []
    pitches = []
    voicing_scores = []
    voiced_frame_rms = []
    for start in range(0, max(0, len(low_rate) - frame_size + 1), hop_size):
        raw_frame = low_rate[start:start + frame_size]
        if len(raw_frame) != frame_size:
            continue
        mean = sum(raw_frame) / frame_size
        frame = [value - mean for value in raw_frame]
        rms = math.sqrt(sum(value * value for value in frame) / frame_size) / 32768.0
        frame_rms.append(rms)
        if rms < 0.002:
            continue
        pitch, confidence = _estimate_pitch(frame, effective_rate)
        if pitch is not None and confidence >= 0.55:
            pitches.append(pitch)
            voicing_scores.append(confidence)
            voiced_frame_rms.append(rms)

    voiced_fraction = len(pitches) / len(frame_rms) if frame_rms else 0.0
    voicing_confidence = median(voicing_scores) if voicing_scores else 0.0
    f0_median = median(pitches) if pitches else None
    f0_range = (max(pitches) - min(pitches)) if len(pitches) >= 2 else None
    if frame_rms:
        maximum_frame_rms = max(frame_rms)
        minimum_frame_rms = max(min(frame_rms), 1e-6)
        energy_range_db = (0.0 if maximum_frame_rms <= 1e-6 else min(
            120.0,
            max(0.0, 20.0 * math.log10(maximum_frame_rms / minimum_frame_rms)),
        ))
    else:
        energy_range_db = 0.0

    # Window energy includes silence; prosodic energy change must not.
    # Use the 10th–90th percentile of voiced frames to suppress pause/onset outliers.
    if len(voiced_frame_rms) >= 2:
        low_voiced_rms = _percentile(voiced_frame_rms, 0.10)
        high_voiced_rms = _percentile(voiced_frame_rms, 0.90)
        voiced_energy_range_db = min(
            120.0,
            max(0.0, 20.0 * math.log10(max(high_voiced_rms, 1e-6) / max(low_voiced_rms, 1e-6))),
        )
    elif len(voiced_frame_rms) == 1:
        # One observation has a zero range, but cannot establish a change.
        voiced_energy_range_db = 0.0
    else:
        voiced_energy_range_db = None

    crest = overall_peak / max(overall_rms, 1e-6)

    if overall_rms < 0.003:
        activity_hint = "SILENCE"
        activity_score = max(0.0, min(1.0, 1.0 - overall_rms / 0.003))
    elif voiced_fraction >= 0.25 and voicing_confidence >= 0.55:
        activity_hint = "VOICED"
        activity_score = min(1.0, 0.5 * voiced_fraction + 0.5 * voicing_confidence)
    elif crest >= 8.0 and voiced_fraction < 0.15:
        activity_hint = "IMPULSIVE"
        activity_score = min(1.0, crest / 16.0)
    elif overall_rms >= 0.01 and voiced_fraction < 0.15:
        activity_hint = "UNVOICED_NOISE"
        activity_score = min(1.0, overall_rms / 0.08)
    else:
        activity_hint = "UNCERTAIN"
        activity_score = 0.25

    # Relative salience only: pitch excursion or within-window energy dynamics.
    # This is not a speech probability and is emitted only for voiced activity.
    pitch_component = 0.0 if f0_range is None else min(1.0, f0_range / 100.0)
    voiced_energy_component = (0.0 if voiced_energy_range_db is None
                                else min(1.0, voiced_energy_range_db / 20.0))
    prosody_change_score = (max(pitch_component, voiced_energy_component)
                            if activity_hint == "VOICED" else 0.0)

    return validate_voice_cues({
        "method": "RAW_EAR_AUTOCORR_V3",
        "frame_ms": frame_ms,
        "hop_ms": hop_ms,
        "frame_count": len(frame_rms),
        "voiced_fraction": round(voiced_fraction, 6),
        "voicing_confidence": round(voicing_confidence, 6),
        "f0_median_hz": round(f0_median, 2) if f0_median is not None else None,
        "f0_range_hz": round(f0_range, 2) if f0_range is not None else None,
        "energy_range_db": round(energy_range_db, 2),
        "voiced_energy_range_db": (round(voiced_energy_range_db, 2)
                                    if voiced_energy_range_db is not None else None),
        "activity_hint": activity_hint,
        "activity_score": round(activity_score, 6),
        "prosody_change_score": round(prosody_change_score, 6),
    })




def reset_runtime_temporal_voice_states(runtime, *, source_id=None, generation_id=None):
    """Clear process-local A4 voice state after source revocation or stream teardown."""
    registry = getattr(runtime, "_raw_ear_temporal_registry", None)
    if registry is None:
        return 0
    if not isinstance(registry, TemporalVoiceEvidenceRegistry):
        raise ValueError("runtime RAW EAR temporal registry has an invalid type")
    return registry.reset(source_id=source_id, generation_id=generation_id)


def _runtime_temporal_voice_registry(runtime):
    registry = getattr(runtime, "_raw_ear_temporal_registry", None)
    if registry is None:
        with _RUNTIME_TEMPORAL_REGISTRY_INIT_LOCK:
            # Another audio worker may have initialized the shared Runtime while
            # this caller waited for the lock.
            registry = getattr(runtime, "_raw_ear_temporal_registry", None)
            if registry is None:
                registry = TemporalVoiceEvidenceRegistry()
                try:
                    setattr(runtime, "_raw_ear_temporal_registry", registry)
                except Exception as exc:
                    raise ValueError("runtime cannot retain bounded RAW EAR temporal state") from exc
    if not isinstance(registry, TemporalVoiceEvidenceRegistry):
        raise ValueError("runtime RAW EAR temporal registry has an invalid type")
    return registry


def _require_current_consent_and_reset(runtime, source_id, generation_id, consent_check, receipt, temporal_state=None, vad_stream=None):
    try:
        _require_current_consent(consent_check, source_id, receipt)
    except Exception:
        reset_runtime_temporal_voice_states(
            runtime, source_id=source_id, generation_id=generation_id
        )
        if isinstance(temporal_state, TemporalVoiceEvidence):
            temporal_state.reset()
        if isinstance(vad_stream, SileroVADStream):
            vad_stream.reset()
        raise


def _reset_audio_temporal_state(runtime, source_id, generation_id, temporal_state=None, vad_stream=None):
    reset_runtime_temporal_voice_states(
        runtime, source_id=source_id, generation_id=generation_id
    )
    if isinstance(temporal_state, TemporalVoiceEvidence):
        temporal_state.reset()
    if isinstance(vad_stream, SileroVADStream):
        vad_stream.reset()


@contextmanager
def _linearizable_audio_consent_lease(runtime, source_id, generation_id, receipt,
                                      consent_guard, temporal_state=None,
                                      vad_stream=None):
    """Hold the provider's revocation lease through persistence, A4 and C3.

    The provider lease is the authoritative linearization point. Its context
    manager must hold the same synchronization primitive used by every
    revocation path and yield the literal bool True only while consent is active.
    Do not call consent_check while the lease is held: a normal threading.Lock
    provider is intentionally allowed, and reacquiring it would deadlock.
    """
    if not callable(consent_guard):
        _reset_audio_temporal_state(
            runtime, source_id, generation_id, temporal_state, vad_stream,
        )
        raise PermissionError("a linearizable audio consent lease is required")
    try:
        manager = consent_guard(source_id, receipt)
    except Exception:
        _reset_audio_temporal_state(
            runtime, source_id, generation_id, temporal_state, vad_stream,
        )
        raise PermissionError("linearizable audio consent lease is unavailable") from None
    if not hasattr(manager, "__enter__") or not hasattr(manager, "__exit__"):
        _reset_audio_temporal_state(
            runtime, source_id, generation_id, temporal_state, vad_stream,
        )
        raise PermissionError("audio consent guard must return a context manager")
    try:
        with manager as active:
            if active is not True:
                raise PermissionError("current audio consent is not active")
            yield active
    except BaseException:
        _reset_audio_temporal_state(
            runtime, source_id, generation_id, temporal_state, vad_stream,
        )
        raise


def _persist_audio_packet_under_consent_lease(runtime, audio_packet, *, lease_active):
    """Persist atomically while the caller still owns the authoritative lease."""
    if lease_active is not True:
        raise PermissionError("audio packet persistence requires an active consent lease")
    validate("PerceptPacket", audio_packet)
    with runtime.store.tx() as connection:
        connection.execute(
            "INSERT INTO packets VALUES (?,?,?,?,?,?)",
            (
                audio_packet["packet_id"],
                "PerceptPacket",
                audio_packet["event_id"],
                audio_packet["brain_generation_id"],
                dumps(audio_packet),
                now(),
            ),
        )


def consume_pcm16_voice_window(runtime, pcm, *, sample_rate, start_ms, event_id,
                               generation_id, source_id, consent_receipt,
                               consent_check, finality, consent_guard=None, token_budget=512,
                               temporal_state: TemporalVoiceEvidence | None = None,
                               vad_stream: SileroVADStream | None = None):
    """Persist source-bound acoustic cues to A4/C3 under a linearizable consent lease."""
    if vad_stream is not None and not isinstance(vad_stream, SileroVADStream):
        raise ValueError("vad_stream must be a SileroVADStream instance")
    # This preflight check is metadata-only; the authoritative recheck happens
    # after the provider lease is acquired and before any PCM-derived work.
    _require_current_consent_and_reset(
        runtime, source_id, generation_id, consent_check, consent_receipt,
        temporal_state, vad_stream,
    )
    # Acquire the linearizable provider lease before any PCM-derived work.
    # Revocation must serialize with observe/extract/VAD as well as Store/A4/C3.
    lease_source_id = source_id
    lease_receipt = consent_receipt
    with _linearizable_audio_consent_lease(
        runtime, lease_source_id, generation_id, lease_receipt,
        consent_guard, temporal_state, vad_stream,
    ) as lease_active:
        raw = observe_pcm16(
            pcm, sample_rate, start_ms, consent=True, source_id=source_id, max_seconds=1
        )
        segment = raw["segments"][0]
        cues = extract_voice_cues(pcm, sample_rate)
        vad_evidence = None
        if vad_stream is not None:
            vad_evidence = vad_stream.push_pcm16(
                pcm, sample_rate=sample_rate,
                stream_id=f"{source_id}:{generation_id}", start_ms=start_ms,
            )
            cues["vad"] = validate_vad_evidence(vad_evidence)
            cues = validate_voice_cues(cues)
        audio_packet = audio_percept_packet(
            event_id=event_id,
            generation_id=generation_id,
            source_id=source_id,
            source_sha256=raw["source_ref"]["sha256"],
            start_ms=segment["start_ms"],
            end_ms=segment["end_ms"],
            rms=segment["acoustic"]["rms"],
            zcr=segment["acoustic"]["zero_crossing_rate"],
            finality=finality,
            consent_receipt=consent_receipt,
        )
        audio_segment = audio_packet["segments"][0]
        audio_segment["acoustic"]["voice_cues"] = cues
        audio_segment["unmeasured"] = [
            "speaker_identity", "speaker_timbre", "calibrated_speech_probability", "ASR"
        ]
        # Do not claim pitch/prosody were measured when the window had no usable
        # voiced frames. A single voiced frame estimates pitch, but not dynamics.
        if cues["f0_median_hz"] is None:
            audio_segment["unmeasured"].append("pitch")
        if round(cues["voiced_fraction"] * cues["frame_count"]) < 2:
            audio_segment["unmeasured"].append("prosody")

        source_id, receipt, rms, zcr, audio_segment = _validate_runtime_binding(
            runtime, event_id, audio_packet
        )
        if source_id != lease_source_id or receipt != lease_receipt:
            _reset_audio_temporal_state(
                runtime, lease_source_id, generation_id, temporal_state, vad_stream,
            )
            raise PermissionError("audio packet binding does not match active consent lease")

        _persist_audio_packet_under_consent_lease(
            runtime, audio_packet, lease_active=lease_active,
        )

        if temporal_state is None:
            temporal_voice = _runtime_temporal_voice_registry(runtime).update(
                source_id=source_id,
                generation_id=generation_id,
                start_ms=audio_segment["start_ms"],
                end_ms=audio_segment["end_ms"],
                cues=cues,
            )
        else:
            if not isinstance(temporal_state, TemporalVoiceEvidence):
                raise ValueError("temporal_state must be a TemporalVoiceEvidence instance")
            temporal_voice = temporal_state.update(
                source_id=source_id,
                generation_id=generation_id,
                start_ms=audio_segment["start_ms"],
                end_ms=audio_segment["end_ms"],
                cues=cues,
            )
        voice_novelty = max(
            0.35 * temporal_voice["voice_evidence"],
            0.9 * cues["prosody_change_score"] if temporal_voice["voice_active"] else 0.0,
        )
        prosody_interrupt = (0.25 * cues["prosody_change_score"]
                             if temporal_voice["voice_active"] else 0.0)
        onset_interrupt = 0.5 if temporal_voice["voice_onset"] else 0.0
        vad_speech_fraction = 0.0 if vad_evidence is None else vad_evidence["speech_fraction"]
        vad_interrupt = 0.25 * vad_speech_fraction
        voice_novelty = max(voice_novelty, 0.35 * vad_speech_fraction)
        if cues["activity_hint"] in {"UNVOICED_NOISE", "IMPULSIVE"}:
            # Preserve non-speech events as their own salience channel.
            voice_novelty = max(voice_novelty, 0.35 * cues["activity_score"])
        attention = attctl.controller(runtime)
        attention_result = attention.modulate(event_id, sal={
            "novelty": min(1.0, max(zcr, voice_novelty)),
            "external_interrupt": min(1.0, max(rms * 0.5, prosody_interrupt, onset_interrupt, vad_interrupt)),
        })
        a4 = {
            "packet_id": audio_packet["packet_id"],
            "source_id": source_id,
            "finality": audio_segment["finality"],
            "voice_activity_hint": cues["activity_hint"],
            "voice_cues": cues,
            "prosody_change_score": cues["prosody_change_score"],
            "temporal_voice": temporal_voice,
            "attention": attention_result,
            "learning_authority": False,
            "action_authority": False,
        }
        if vad_evidence is not None:
            a4["vad_evidence"] = vad_evidence

        # The provider lease remains authoritative through A4 and C3 admission.
        # Do not reacquire its lock through consent_check here.
        candidate = audio_to_admission(audio_packet, consent_active=True)
        summary = candidate.summary + (
            f" activity={cues['activity_hint']} voiced={cues['voiced_fraction']:.2f}"
        )
        if cues["f0_median_hz"] is not None:
            summary += f" f0_med_hz={cues['f0_median_hz']:.0f}"
        if cues["f0_range_hz"] is not None:
            summary += f" f0_range_hz={cues['f0_range_hz']:.0f}"
        summary += f" energy_range_db={cues['energy_range_db']:.1f}"
        if cues["voiced_energy_range_db"] is not None:
            summary += f" voiced_energy_range_db={cues['voiced_energy_range_db']:.1f}"
        summary += f" prosody_change={cues['prosody_change_score']:.2f}"
        if vad_evidence is not None:
            summary += f" vad_speech_fraction={vad_speech_fraction:.2f}"
        candidate = Percept(
            candidate.source_id, candidate.modality, candidate.start_ms, candidate.end_ms,
            summary[:256], candidate.consent, candidate.final, candidate.priority,
        )
        c3 = admit((candidate,), token_budget)
        result = {
            "status": "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION",
            "packet": audio_packet,
            "a4": a4,
            "c3_admission": c3,
            "temporal_voice": temporal_voice,
            "capture_authority": "CALLER_SUPPLIED_PCM16",
            "learning_authority": False,
            "action_authority": False,
        }
        if vad_evidence is not None:
            result["vad_evidence"] = vad_evidence
        return result
