"""Additive timed RAW EAR voice/prosody cue adapter for A5, A4 and C3.

This module is deliberately separate from the Core-pinned A5 bridge. It uses
caller-supplied PCM16 only; it never opens a microphone, stores raw PCM, runs
ASR, identifies a speaker, or grants learning/action authority. The acoustic
classes are deterministic heuristics, not a trained VAD or calibrated probability.
"""
from __future__ import annotations

import math
import struct
from statistics import median

from . import attention as attctl
from .a5_audio_admission_bridge import audio_to_admission
from .audio_ear import observe_pcm16
from .audio_percept_contract import audio_percept_packet
from .audio_perception_bridge import _require_current_consent, _validate_runtime_binding
from .percept_admission import Percept, admit


_ACTIVITY_HINTS = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}


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


def validate_voice_cues(cues: dict) -> dict:
    """Reject malformed/unbounded acoustic cues before they reach A4 or C3."""
    if type(cues) is not dict:
        raise ValueError("voice cues must be an object")
    required = {
        "method", "frame_ms", "hop_ms", "frame_count", "voiced_fraction",
        "voicing_confidence", "f0_median_hz", "f0_range_hz",
        "energy_range_db", "activity_hint", "activity_score",
    }
    if set(cues) != required or cues.get("method") != "RAW_EAR_AUTOCORR_V1":
        raise ValueError("voice cue fields or method are invalid")
    if cues.get("frame_ms") != 40 or cues.get("hop_ms") != 20:
        raise ValueError("voice cue timing is invalid")
    count = cues.get("frame_count")
    if type(count) is not int or not 0 <= count <= 50:
        raise ValueError("voice cue frame count is invalid")
    for key in ("voiced_fraction", "voicing_confidence", "activity_score"):
        value = cues.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("voice cue score is invalid")
    for key, lower, upper in (("f0_median_hz", 65, 400), ("f0_range_hz", 0, 335),
                              ("energy_range_db", 0, 120)):
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
    return dict(cues)


def extract_voice_cues(pcm: bytes, sample_rate: int) -> dict:
    """Extract bounded pitch, voicing, energy and non-speech hints from mono PCM16."""
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("voice cue input must be complete PCM16 bytes")
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
        raise ValueError("voice cue sample rate must be 8000..48000")
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    overall_energy = sum(value * value for value in samples) / len(samples)
    overall_rms = math.sqrt(overall_energy) / 32768.0
    overall_peak = max(abs(value) for value in samples) / 32768.0

    # Block-average downsampling keeps the Python work bounded on ARM.
    factor = max(1, int(round(sample_rate / 8000.0)))
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

    return validate_voice_cues({
        "method": "RAW_EAR_AUTOCORR_V1",
        "frame_ms": frame_ms,
        "hop_ms": hop_ms,
        "frame_count": len(frame_rms),
        "voiced_fraction": round(voiced_fraction, 6),
        "voicing_confidence": round(voicing_confidence, 6),
        "f0_median_hz": round(f0_median, 2) if f0_median is not None else None,
        "f0_range_hz": round(f0_range, 2) if f0_range is not None else None,
        "energy_range_db": round(energy_range_db, 2),
        "activity_hint": activity_hint,
        "activity_score": round(activity_score, 6),
    })


def consume_pcm16_voice_window(runtime, pcm, *, sample_rate, start_ms, event_id,
                               generation_id, source_id, consent_receipt,
                               consent_check, finality, token_budget=512):
    """Persist one source-bound acoustic packet and deliver cues to A4 and C3 admission."""
    _require_current_consent(consent_check, source_id, consent_receipt)
    raw = observe_pcm16(
        pcm, sample_rate, start_ms, consent=True, source_id=source_id, max_seconds=1
    )
    segment = raw["segments"][0]
    cues = extract_voice_cues(pcm, sample_rate)
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

    source_id, receipt, rms, zcr, audio_segment = _validate_runtime_binding(
        runtime, event_id, audio_packet
    )
    _require_current_consent(consent_check, source_id, receipt)
    runtime.store.add_packet("PerceptPacket", audio_packet)
    _require_current_consent(consent_check, source_id, receipt)

    voice_novelty = 0.0
    if cues["activity_hint"] != "SILENCE":
        voice_novelty = max(0.6 * cues["voiced_fraction"], 0.35 * cues["activity_score"])
    attention = attctl.controller(runtime)
    attention_result = attention.modulate(event_id, sal={
        "novelty": min(1.0, max(zcr, voice_novelty)),
        "external_interrupt": min(1.0, rms * 0.5),
    })
    a4 = {
        "packet_id": audio_packet["packet_id"],
        "source_id": source_id,
        "finality": audio_segment["finality"],
        "voice_activity_hint": cues["activity_hint"],
        "voice_cues": cues,
        "attention": attention_result,
        "learning_authority": False,
        "action_authority": False,
    }

    _require_current_consent(consent_check, source_id, receipt)
    candidate = audio_to_admission(audio_packet, consent_active=True)
    summary = candidate.summary + (
        f" activity={cues['activity_hint']} voiced={cues['voiced_fraction']:.2f}"
    )
    if cues["f0_median_hz"] is not None:
        summary += f" f0_med_hz={cues['f0_median_hz']:.0f}"
    if cues["f0_range_hz"] is not None:
        summary += f" f0_range_hz={cues['f0_range_hz']:.0f}"
    summary += f" energy_range_db={cues['energy_range_db']:.1f}"
    candidate = Percept(
        candidate.source_id, candidate.modality, candidate.start_ms, candidate.end_ms,
        summary[:256], candidate.consent, candidate.final, candidate.priority,
    )
    c3 = admit((candidate,), token_budget)
    return {
        "status": "SYNTHETIC_PCM16_A5_A4_C3_ADMISSION",
        "packet": audio_packet,
        "a4": a4,
        "c3_admission": c3,
        "capture_authority": "CALLER_SUPPLIED_PCM16",
        "learning_authority": False,
        "action_authority": False,
    }
