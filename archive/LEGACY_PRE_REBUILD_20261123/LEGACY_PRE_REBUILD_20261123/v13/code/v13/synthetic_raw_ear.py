"""Synthetic normalized PCM -> existing consent-bound TimedAudioPercept.

Offline fixture only. No Android microphone access, ASR or speaker identity.
"""
from math import isfinite, sqrt
from typing import Sequence
from .timed_audio_percept import TimedAudioPercept


def synthetic_pcm_to_percept(samples: Sequence[float], *, source_id: str,
                            start_ms: int, sample_rate_hz: int,
                            consent_scope: str, status: str = "provisional"):
    if consent_scope != "audio_observation_granted":
        raise PermissionError("audio observation consent absent")
    if not isinstance(sample_rate_hz, int) or not 8000 <= sample_rate_hz <= 192000:
        raise ValueError("invalid sample rate")
    if not samples or len(samples) > sample_rate_hz * 10:
        raise ValueError("invalid frame length")
    values = [float(x) for x in samples]
    if any(not isfinite(x) or abs(x) > 1 for x in values):
        raise ValueError("invalid normalized PCM")
    duration_ms = max(1, (1000 * len(values) + sample_rate_hz - 1) // sample_rate_hz)
    rms = sqrt(sum(x*x for x in values) / len(values))
    return TimedAudioPercept(source_id=source_id, start_ms=start_ms,
        end_ms=start_ms+duration_ms, consent_scope=consent_scope,
        provenance="raw_ear_derived", status=status, rms=rms,
        pitch_hz=None, speech_probability=0.0, non_speech_probability=0.0,
        prosody_change=0.0, speaker_turn=False)
