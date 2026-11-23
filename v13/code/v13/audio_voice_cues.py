"""Additive timed RAW EAR voice/prosody cue adapter for A5, A4 and C3.

This module is deliberately separate from the Core-pinned A5 bridge. It uses
caller-supplied PCM16 only; it never opens a microphone, stores raw PCM, runs
ASR, assigns speaker identity, or grants learning/action authority. An optional
caller-supplied frame-embedding batch may produce only a source-bound change-or-
overlap hint; no model is loaded here. Acoustic classes and prosody scores remain
deterministic heuristics, not a trained VAD, speech classifier, or calibrated probability.
"""
from __future__ import annotations

import math
import struct
from contextlib import contextmanager
from functools import lru_cache
import threading
from statistics import median

from . import attention as attctl
from .audio_temporal_evidence import TemporalVoiceEvidence, TemporalVoiceEvidenceRegistry
from .audio_speaker_evidence import SpeakerChangeEvidenceRegistry, SpeakerEvidenceError
from .audio_silero_vad import SileroVADStream, validate_vad_evidence
from .a5_audio_admission_bridge import audio_to_admission
from .audio_ear import observe_pcm16
from .audio_percept_contract import audio_percept_packet
from .audio_perception_bridge import _require_current_consent, _validate_runtime_binding
from .percept_admission import Percept, admit
from .common import dumps, now
from .contracts import validate


def _load_teacher_ear_validator():
    """Load the optional ASR teacher only when a source-bound result is supplied."""
    try:
        from .audio_teacher_ear import validate_teacher_ear_result
    except ModuleNotFoundError as exc:
        if exc.name not in {f"{__package__}.audio_teacher_ear", "audio_teacher_ear"}:
            raise
        return None
    return validate_teacher_ear_result


_ACTIVITY_HINTS = {"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"}

def _speaker_change_decision(evidence, cues):
    """Return a conservative A4 three-regime decision without assigning identity.

    Low similarity is only a candidate after a verified, model-bound calibration
    artifact is supplied. Caller labels and numeric thresholds are not calibration.
    Silence, noise, short windows, missing calibration, rejected embeddings and
    warm-up remain DEFER rather than false continuity.
    """
    if type(cues) is not dict or cues.get("activity_hint") != "VOICED":
        return "DEFER"
    frame_count = cues.get("frame_count")
    voiced_fraction = cues.get("voiced_fraction")
    # The PCM ingress contract bounds window size; do not impose a 1-second cap here.
    if (type(frame_count) is not int or frame_count < 2
            or type(voiced_fraction) not in (int, float)
            or not math.isfinite(float(voiced_fraction))
            or not 0.0 <= float(voiced_fraction) <= 1.0
            or int(frame_count * float(voiced_fraction)) < 2):
        return "DEFER"
    if type(evidence) is not dict or evidence.get("status") != "MEASURED":
        return "DEFER"
    # The current RAW EAR registry only accepts caller-asserted thresholds.
    # Until a separately reviewed calibration artifact is verified and pinned,
    # similarity remains diagnostic and cannot support continuity/change.
    if evidence.get("threshold_status") != "CALIBRATED_VERIFIED":
        return "DEFER"
    receipt_sha = evidence.get("calibration_receipt_sha256")
    if (type(receipt_sha) is not str or len(receipt_sha) != 64
            or any(char not in "0123456789abcdef" for char in receipt_sha)):
        return "DEFER"
    calibration_id = evidence.get("calibration_id")
    confidence_threshold = evidence.get("confidence_threshold")
    if (type(calibration_id) is not str or not calibration_id.strip()
            or type(confidence_threshold) not in (int, float)
            or not math.isfinite(float(confidence_threshold))
            or not -1.0 <= float(confidence_threshold) <= 1.0):
        return "DEFER"
    candidate = evidence.get("peak_speaker_change_candidate")
    if candidate is None:
        candidate = evidence.get("speaker_change_candidate")
    if candidate is True:
        return "CHANGE_OR_OVERLAP_CANDIDATE"
    if evidence.get("confidence_gate_passed") is True:
        return "CONTINUITY_SUPPORTED"
    return "DEFER"



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



def _load_numpy():
    """Load NumPy only when the explicitly requested accelerated backend is used."""
    try:
        import numpy as np
    except ImportError:
        return None
    return np


def _estimate_pitch_numpy(frame, sample_rate: float, np) -> tuple[float | None, float]:
    """NumPy autocorrelation equivalent of _estimate_pitch for short 40-ms frames."""
    values = np.asarray(frame, dtype=np.float64)
    count = int(values.size)
    minimum_lag = max(2, int(sample_rate / 400))
    maximum_lag = min(count // 2, int(sample_rate / 65))
    if maximum_lag < minimum_lag:
        return None, 0.0
    correlation = np.correlate(values, values, mode="full")[
        count - 1 + minimum_lag:count + maximum_lag
    ]
    prefix = np.concatenate(([0.0], np.cumsum(values * values)))
    lags = np.arange(minimum_lag, maximum_lag + 1)
    denominator = np.sqrt(prefix[count - lags] * (prefix[count] - prefix[lags]))
    valid = denominator > 1e-9
    if not np.any(valid):
        return None, 0.0
    normalized = np.full(lags.shape, -np.inf, dtype=np.float64)
    normalized[valid] = correlation[valid] / denominator[valid]
    peak = float(np.max(normalized))
    threshold = max(0.55, peak * 0.99)
    candidates = np.flatnonzero(normalized >= threshold)
    if not candidates.size:
        return None, max(0.0, min(1.0, peak))
    index = int(candidates[0])
    lag = int(lags[index])
    confidence = float(normalized[index])
    return sample_rate / lag, max(0.0, min(1.0, confidence))



@lru_cache(maxsize=32)
def _voice_decimator_coefficients(sample_rate: int, factor: int) -> tuple[float, ...]:
    """Return a cached centered Hamming-windowed low-pass FIR for RAW EAR cues."""
    taps = 25 if factor == 5 else 21
    target_rate = sample_rate / factor
    cutoff_hz = 0.45 * target_rate
    midpoint = (taps - 1) / 2
    coefficients = []
    for index in range(taps):
        offset = index - midpoint
        if offset == 0:
            ideal = 2.0 * cutoff_hz / sample_rate
        else:
            ideal = math.sin(2.0 * math.pi * cutoff_hz * offset / sample_rate) / (math.pi * offset)
        window = 0.54 - 0.46 * math.cos(2.0 * math.pi * index / (taps - 1))
        coefficients.append(ideal * window)
    total = sum(coefficients)
    if not math.isfinite(total) or abs(total) <= 1e-12:
        raise ValueError("invalid RAW EAR decimator filter")
    return tuple(value / total for value in coefficients)


def _anti_alias_decimate(samples, sample_rate: int, factor: int) -> tuple[list[float], float]:
    """Low-pass before integer decimation with odd endpoint reflection.

    The Hamming-windowed sinc coefficients are symmetric. Pairing samples
    around each output center preserves the centered zero-phase FIR result
    while nearly halving multiply operations on the pure-Python Android path.
    This is a RAW EAR feature decimator, not a speaker-model resampler.
    """
    if type(factor) is not int or factor < 1:
        raise ValueError("RAW EAR decimation factor must be a positive integer")
    if factor == 1:
        return [float(value) for value in samples], float(sample_rate)
    coefficients = _voice_decimator_coefficients(sample_rate, factor)
    half = len(coefficients) // 2
    sample_count = len(samples)
    output_count = sample_count // factor
    output = []
    for output_index in range(output_count):
        center = output_index * factor
        filtered = 0.0
        for offset in range(1, half + 1):
            left_index = center - offset
            right_index = center + offset
            if 0 <= left_index < sample_count:
                left_value = float(samples[left_index])
            elif sample_count <= half:
                left_value = float(samples[0] if left_index < 0 else samples[-1])
            elif left_index < 0:
                left_value = 2.0 * float(samples[0]) - float(samples[-left_index])
            else:
                mirror_index = 2 * sample_count - 2 - left_index
                left_value = 2.0 * float(samples[-1]) - float(samples[mirror_index])

            if 0 <= right_index < sample_count:
                right_value = float(samples[right_index])
            elif sample_count <= half:
                right_value = float(samples[0] if right_index < 0 else samples[-1])
            elif right_index < 0:
                right_value = 2.0 * float(samples[0]) - float(samples[-right_index])
            else:
                mirror_index = 2 * sample_count - 2 - right_index
                right_value = 2.0 * float(samples[-1]) - float(samples[mirror_index])

            filtered += coefficients[half - offset] * (left_value + right_value)

        filtered += coefficients[half] * float(samples[center])
        output.append(filtered)
    return output, sample_rate / factor

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


def extract_voice_cues(pcm: bytes, sample_rate: int, *, backend: str = "python") -> dict:
    """Extract bounded pitch, voicing, energy and non-speech hints from mono PCM16."""
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("voice cue input must be complete PCM16 bytes")
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 48000:
        raise ValueError("voice cue sample rate must be 8000..48000")
    if len(pcm) > sample_rate * 2:
        raise ValueError("voice cue window is limited to one second")
    if type(backend) is not str or backend not in {"python", "numpy"}:
        raise ValueError("voice cue backend must be 'python' or 'numpy'")
    numpy_module = _load_numpy() if backend == "numpy" else None
    if backend == "numpy" and numpy_module is None:
        raise RuntimeError("NumPy voice cue backend is unavailable")
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    overall_energy = sum(value * value for value in samples) / len(samples)
    overall_rms = math.sqrt(overall_energy) / 32768.0
    overall_peak = max(abs(value) for value in samples) / 32768.0

    # A boxcar average can alias high-frequency tones into the 65..400 Hz
    # pitch band. Keep RAW EAR self-contained and bounded with a small cached
    # centered FIR before integer decimation. This is not a model resampler.
    factor = max(1, int(sample_rate // 8000))
    low_rate, effective_rate = _anti_alias_decimate(samples, sample_rate, factor)
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
        if numpy_module is None:
            pitch, confidence = _estimate_pitch(frame, effective_rate)
        else:
            pitch, confidence = _estimate_pitch_numpy(frame, effective_rate, numpy_module)
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

    # Strong frame-level periodicity must not be overridden by the absolute window floor.
    # VOICED remains an acoustic cue, not a calibrated speech probability.
    if overall_rms < 0.003 and voiced_fraction < 0.25:
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
    """Clear process-local A4 voice and speaker-change state after revocation or teardown."""
    count = 0
    registry = getattr(runtime, "_raw_ear_temporal_registry", None)
    if registry is not None:
        if not isinstance(registry, TemporalVoiceEvidenceRegistry):
            raise ValueError("runtime RAW EAR temporal registry has an invalid type")
        count = registry.reset(source_id=source_id, generation_id=generation_id)
    speaker_registry = getattr(runtime, "_raw_ear_speaker_registry", None)
    if speaker_registry is not None:
        if not isinstance(speaker_registry, SpeakerChangeEvidenceRegistry):
            raise ValueError("runtime RAW EAR speaker registry has an invalid type")
        speaker_registry.reset(source_id=source_id, generation_id=generation_id)
    return count


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


def _runtime_speaker_evidence_registry(runtime):
    registry = getattr(runtime, "_raw_ear_speaker_registry", None)
    if registry is None:
        with _RUNTIME_TEMPORAL_REGISTRY_INIT_LOCK:
            registry = getattr(runtime, "_raw_ear_speaker_registry", None)
            if registry is None:
                registry = SpeakerChangeEvidenceRegistry()
                try:
                    setattr(runtime, "_raw_ear_speaker_registry", registry)
                except Exception as exc:
                    raise ValueError("runtime cannot retain bounded RAW EAR speaker state") from exc
    if not isinstance(registry, SpeakerChangeEvidenceRegistry):
        raise ValueError("runtime RAW EAR speaker registry has an invalid type")
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




_AUDIO_CONSENT_LEASE_TOKEN = object()


class AudioConsentLease:
    """Ephemeral, thread-bound handle for a provider lease already held by Runtime.

    The provider's synchronization primitive remains authoritative. This handle
    only prevents accidental callback re-entry and binds the held lease to one
    Runtime/source/generation/receipt scope. Never persist, copy or serialize it.
    """
    __slots__ = (
        "_token", "runtime", "source_id", "generation_id", "receipt",
        "temporal_state", "vad_stream", "_active", "_thread_id",
    )

    def __init__(self, runtime, source_id, generation_id, receipt,
                 temporal_state=None, vad_stream=None, *, _token=None):
        if _token is not _AUDIO_CONSENT_LEASE_TOKEN:
            raise PermissionError("AudioConsentLease must be created by audio_consent_lease")
        if type(receipt) is not str or not receipt:
            raise PermissionError("AudioConsentLease requires an opaque current receipt")
        self._token = _token
        self.runtime = runtime
        self.source_id = source_id
        self.generation_id = generation_id
        self.receipt = receipt
        self.temporal_state = temporal_state
        self.vad_stream = vad_stream
        self._active = True
        self._thread_id = threading.get_ident()

    @property
    def active(self):
        return self._active is True

    def matches(self, runtime, source_id, generation_id, receipt, *,
                temporal_state=None, vad_stream=None, require_state=False):
        if not (
            self._token is _AUDIO_CONSENT_LEASE_TOKEN
            and self._active is True
            and self._thread_id == threading.get_ident()
            and self.runtime is runtime
            and self.source_id == source_id
            and self.generation_id == generation_id
            and self.receipt == receipt
        ):
            return False
        if require_state and (
            self.temporal_state is not temporal_state
            or self.vad_stream is not vad_stream
        ):
            return False
        return True

    def __repr__(self):
        return f"<AudioConsentLease active={self.active}>"

    def __reduce__(self):
        raise TypeError("AudioConsentLease is ephemeral and cannot be serialized")

    def __copy__(self):
        raise TypeError("AudioConsentLease cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("AudioConsentLease cannot be copied")


@contextmanager
def audio_consent_lease(runtime, source_id, generation_id, receipt,
                        consent_check, consent_guard, temporal_state=None,
                        vad_stream=None):
    """Hold one provider lease for a complete Runtime audio/C3 generation scope.

    Keep this context open across audio-context reads and the complete
    runner.generate() iterator. Do not call consent_check while it is held.
    The provider must serialize this guard with every application-level revoke.
    """
    _require_current_consent_and_reset(
        runtime, source_id, generation_id, consent_check, receipt,
        temporal_state, vad_stream,
    )
    with _linearizable_audio_consent_lease(
        runtime, source_id, generation_id, receipt, consent_guard,
        temporal_state, vad_stream,
    ):
        lease = AudioConsentLease(
            runtime, source_id, generation_id, receipt,
            temporal_state, vad_stream, _token=_AUDIO_CONSENT_LEASE_TOKEN,
        )
        try:
            yield lease
        finally:
            lease._active = False


@contextmanager
def _audio_consent_scope(runtime, source_id, generation_id, receipt,
                         consent_check, consent_guard, consent_lease,
                         temporal_state=None, vad_stream=None):
    if consent_lease is None:
        _require_current_consent_and_reset(
            runtime, source_id, generation_id, consent_check, receipt,
            temporal_state, vad_stream,
        )
        with _linearizable_audio_consent_lease(
            runtime, source_id, generation_id, receipt, consent_guard,
            temporal_state, vad_stream,
        ) as active:
            yield active
        return

    if not isinstance(consent_lease, AudioConsentLease) or not consent_lease.matches(
        runtime, source_id, generation_id, receipt,
        temporal_state=temporal_state, vad_stream=vad_stream,
        require_state=True,
    ):
        _reset_audio_temporal_state(
            runtime, source_id, generation_id, temporal_state, vad_stream,
        )
        raise PermissionError("a live source-bound audio consent lease is required")

    # The caller already holds the same provider lease. Never re-enter its
    # consent_check or consent_guard here; the outer scope owns revocation.
    yield True


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
                               vad_stream: SileroVADStream | None = None,
                               consent_lease: AudioConsentLease | None = None,
                               voice_backend: str = "python",
                                speaker_embeddings: dict | None = None,
                                teacher_result: dict | None = None,
                                teacher_opt_in: bool = False,
                                teacher_transcript_consent: bool = False):
    """Persist source-bound acoustic cues under an owned or caller-held consent lease."""
    if type(voice_backend) is not str or voice_backend not in {"python", "numpy"}:
        raise ValueError("voice_backend must be 'python' or 'numpy'")
    if type(teacher_opt_in) is not bool or type(teacher_transcript_consent) is not bool:
        raise ValueError("teacher opt-in flags must be literal booleans")
    if vad_stream is not None and not isinstance(vad_stream, SileroVADStream):
        raise ValueError("vad_stream must be a SileroVADStream instance")
    # A Runtime-wide caller may already hold the same provider lease through
    # C3 generation. Reuse its bound handle without callback re-entry.
    with _audio_consent_scope(
        runtime, source_id, generation_id, consent_receipt,
        consent_check, consent_guard, consent_lease, temporal_state, vad_stream,
    ) as lease_active:
        raw = observe_pcm16(
            pcm, sample_rate, start_ms, consent=True, source_id=source_id, max_seconds=1
        )
        segment = raw["segments"][0]
        cues = extract_voice_cues(pcm, sample_rate, backend=voice_backend)
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
        teacher_ear = None
        teacher_ear_status = "NOT_SUPPLIED"
        if teacher_result is not None:
            teacher_validator = _load_teacher_ear_validator()
            if teacher_validator is None:
                # The teacher is an optional add-on. Keep the acoustic path alive,
                # but never admit unvalidated teacher text when its validator is absent.
                teacher_ear_status = "UNAVAILABLE_MODULE"
            else:
                teacher_ear = teacher_validator(
                    teacher_result,
                    source_id=source_id,
                    generation_id=generation_id,
                    source_sha256=raw["source_ref"]["sha256"],
                    start_ms=segment["start_ms"],
                    end_ms=segment["end_ms"],
                    finality=finality,
                    consent_active=lease_active,
                    teacher_opt_in=teacher_opt_in,
                    transcript_consent=teacher_transcript_consent,
                )
                teacher_ear_status = teacher_ear["status"]
        audio_segment["acoustic"]["voice_cues"] = cues
        speaker_evidence = None
        if speaker_embeddings is not None:
            try:
                speaker_evidence = _runtime_speaker_evidence_registry(runtime).update(
                    source_id=source_id, generation_id=generation_id,
                    start_ms=audio_segment["start_ms"], end_ms=audio_segment["end_ms"],
                    current_chunk_sha256=raw["source_ref"]["sha256"],
                    activity_hint=cues["activity_hint"], embeddings=speaker_embeddings,
                )
            except SpeakerEvidenceError as exc:
                runtime.store.log("speaker_embedding_rejected", event_id, {"error": type(exc).__name__})
                speaker_evidence = {
                    "method": "COSINE_LOOKBACK_DIAGNOSTIC_V1",
                    "status": "REJECTED",
                    "error": type(exc).__name__,
                    "speaker_label": None,
                    "identity_authority": False,
                    "learning_authority": False,
                    "action_authority": False,
                }
        speaker_change_decision = _speaker_change_decision(speaker_evidence, cues)
        if speaker_evidence is not None:
            speaker_evidence["decision"] = speaker_change_decision
            audio_segment["acoustic"]["speaker_change_evidence"] = speaker_evidence
        audio_segment["acoustic"]["speaker_change_decision"] = speaker_change_decision
        audio_segment["unmeasured"] = [
            "speaker_identity", "speaker_timbre", "calibrated_speech_probability", "ASR"
        ]
        if (speaker_evidence is None or speaker_evidence.get("status") != "MEASURED"
                or speaker_change_decision == "DEFER"):
            audio_segment["unmeasured"].append("speaker_change")
        # Do not claim pitch/prosody were measured when the window had no usable
        # voiced frames. A single voiced frame estimates pitch, but not dynamics.
        if cues["f0_median_hz"] is None:
            audio_segment["unmeasured"].append("pitch")
        if round(cues["voiced_fraction"] * cues["frame_count"]) < 2:
            audio_segment["unmeasured"].append("prosody")

        expected_source_id, expected_receipt = source_id, consent_receipt
        source_id, receipt, rms, zcr, audio_segment = _validate_runtime_binding(
            runtime, event_id, audio_packet
        )
        if source_id != expected_source_id or receipt != expected_receipt:
            _reset_audio_temporal_state(
                runtime, expected_source_id, generation_id, temporal_state, vad_stream,
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
        speaker_change_score = 0.0
        speaker_change_candidate = None
        if speaker_evidence is not None:
            speaker_change_candidate = speaker_evidence.get("peak_speaker_change_candidate")
            if speaker_change_candidate is None:
                speaker_change_candidate = speaker_evidence.get("speaker_change_candidate")
            if speaker_change_candidate is True:
                speaker_change_score = float(
                    speaker_evidence.get("peak_candidate_change_score")
                    or speaker_evidence.get("change_score")
                    or 0.0
                )
        voice_novelty = max(
            0.35 * temporal_voice["voice_evidence"],
            0.9 * cues["prosody_change_score"] if temporal_voice["voice_active"] else 0.0,
            0.35 * speaker_change_score,
        )
        prosody_interrupt = (0.25 * cues["prosody_change_score"]
                             if temporal_voice["voice_active"] else 0.0)
        speaker_interrupt = 0.25 * speaker_change_score
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
            "external_interrupt": min(1.0, max(rms * 0.5, prosody_interrupt, onset_interrupt, vad_interrupt, speaker_interrupt)),
        })
        a4 = {
            "packet_id": audio_packet["packet_id"],
            "source_id": source_id,
            "finality": audio_segment["finality"],
            "voice_activity_hint": cues["activity_hint"],
            "voice_cues": cues,
            "prosody_change_score": cues["prosody_change_score"],
            "temporal_voice": temporal_voice,
            "speaker_change_evidence": speaker_evidence,
            "speaker_change_decision": speaker_change_decision,
            "teacher_ear_status": teacher_ear_status,
            "teacher_ear_authority": teacher_ear["authority"] if teacher_ear else "NONE",
            "teacher_ear_word_count": teacher_ear["word_count"] if teacher_ear else 0,
            "attention": attention_result,
            "learning_authority": False,
            "action_authority": False,
        }
        if vad_evidence is not None:
            a4["vad_evidence"] = vad_evidence

        # The provider lease remains authoritative through A4 and C3 admission.
        # Do not reacquire its lock through consent_check here.
        candidate = audio_to_admission(audio_packet, consent_active=True)
        # Packet start/end already carry the interval; drop the duplicate text
        # field to preserve room for source-bound acoustic evidence below.
        base_summary = " ".join(
            token for token in candidate.summary.split()
            if not token.startswith(("zcr=", "interval_ms="))
        )
        summary = base_summary + (
            f" activity={cues['activity_hint']} v={cues['voiced_fraction']:.2f}"
        )
        if cues["f0_median_hz"] is not None:
            summary += f" f0_med_hz={cues['f0_median_hz']:.0f}"
        summary += f" energy_range_db={cues['energy_range_db']:.1f}"
        if cues["voiced_energy_range_db"] is not None:
            summary += f" voiced_energy_range_db={cues['voiced_energy_range_db']:.1f}"
        summary += f" prosody_change={cues['prosody_change_score']:.2f}"
        if vad_evidence is not None:
            summary += f" vad_speech_fraction={vad_speech_fraction:.2f}"
        if speaker_evidence is not None and speaker_evidence.get("status") == "MEASURED":
            if speaker_change_candidate is not None:
                summary += f" speaker_change_candidate={int(speaker_change_candidate)}"
                summary += f" speaker_change_score={speaker_change_score:.2f}"
                if speaker_change_candidate:
                    summary += " speaker_change_kind=CHANGE_OR_OVERLAP"
            else:
                summary += f" speaker_similarity_delta={speaker_evidence['change_score']:.2f}"
                summary += (
                    " spk_cal=UNVERIFIED"
                    if speaker_evidence.get("threshold_status") == "CALLER_ASSERTED_UNVERIFIED"
                    else " spk_cal=UNAVAILABLE"
                )
        # The structured packet retains every cue; reserve the bounded C3
        # summary tail for the speaker score/kind and explicit three-state decision.
        decision_suffix = f" spk_dec={speaker_change_decision}"
        summary = summary[:256-len(decision_suffix)] + decision_suffix
        candidate = Percept(
            candidate.source_id, candidate.modality, candidate.start_ms, candidate.end_ms,
            summary, candidate.consent, candidate.final, candidate.priority,
        )
        percepts = [candidate]
        if teacher_ear is not None:
            percepts.append(Percept(
                teacher_ear["teacher_source_id"], "audio",
                teacher_ear["start_ms"], teacher_ear["end_ms"],
                teacher_ear["summary"], True, teacher_ear["finality"] == "FINAL",
                candidate.priority,
            ))
        c3 = admit(tuple(percepts), token_budget)
        result = {
            "status": "CALLER_SUPPLIED_PCM16_A5_A4_C3_ADMISSION",
            "packet": audio_packet,
            "a4": a4,
            "c3_admission": c3,
            "temporal_voice": temporal_voice,
            "speaker_change_evidence": speaker_evidence,
            "teacher_ear": teacher_ear,
            "teacher_ear_status": teacher_ear_status,
            "capture_authority": "CALLER_SUPPLIED_PCM16",
            "learning_authority": False,
            "action_authority": False,
        }
        if vad_evidence is not None:
            result["vad_evidence"] = vad_evidence
        return result
