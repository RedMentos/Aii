"""Consent-bound, timestamped A-plane audio perception (synthetic/adapter input).

This module does not record microphone audio, perform ASR, or grant Android access.
Acoustic features remain distinct from optional teacher words. No learned A3 claim.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Optional
import hashlib
import struct


@dataclass(frozen=True)
class AudioPercept:
    source_id: str
    start_ms: int
    end_ms: int
    sample_rate_hz: int
    sample_count: int
    rms: float
    peak: float
    zero_crossing_rate: float
    provisional: bool
    consent_scope: str
    pcm_sha256: str
    teacher_text: Optional[str] = None
    teacher_provenance: Optional[str] = None
    speaker_id: Optional[str] = None
    modality: str = "audio_raw_ear"
    schema: str = "v13.a5.audio-percept/1"

    def packet(self):
        return dict(self.__dict__)


def from_pcm16(samples, *, source_id, start_ms, sample_rate_hz,
               consent_scope, provisional=True, teacher_text=None,
               teacher_provenance=None, speaker_id=None):
    """Compute bounded acoustic measurements from authorized signed PCM16 frames.

    The caller must obtain OS microphone/capture permission separately.
    Frames are not persisted or uploaded by this function.
    """
    if consent_scope not in ("local_microphone_granted", "authorized_fixture",
                             "authorized_audio_feed"):
        raise PermissionError("Explicit authorized audio source required")
    if not isinstance(source_id, str) or not source_id or len(source_id) > 128:
        raise ValueError("Invalid source identifier")
    if type(start_ms) is not int or start_ms < 0:
        raise ValueError("Invalid timestamp")
    if type(sample_rate_hz) is not int or not 8000 <= sample_rate_hz <= 48000:
        raise ValueError("Unsupported sample rate")
    if not isinstance(samples, (list, tuple)) or not 1 <= len(samples) <= sample_rate_hz * 2:
        raise ValueError("Frame must contain 1 ms to 2 seconds of PCM")
    if any(type(s) is not int or not -32768 <= s <= 32767 for s in samples):
        raise ValueError("Invalid signed PCM16 sample")
    if (teacher_text is None) != (teacher_provenance is None):
        raise ValueError("Teacher text requires independent provenance")
    if teacher_text is not None and (not isinstance(teacher_text, str)
                                     or len(teacher_text) > 4096
                                     or not isinstance(teacher_provenance, str)
                                     or not teacher_provenance.strip()):
        raise ValueError("Invalid teacher provenance")
    raw = struct.pack("<" + "h" * len(samples), *samples)
    normalized = [s / 32768.0 for s in samples]
    rms = sqrt(sum(s * s for s in normalized) / len(normalized))
    peak = max(abs(s) for s in normalized)
    zcr = sum((a < 0) != (b < 0) for a, b in zip(samples, samples[1:])) / max(1, len(samples)-1)
    end_ms = start_ms + (len(samples) * 1000 + sample_rate_hz - 1) // sample_rate_hz
    assert all(isfinite(x) for x in (rms, peak, zcr))
    return AudioPercept(source_id, start_ms, end_ms, sample_rate_hz, len(samples),
                        rms, peak, zcr, bool(provisional), consent_scope,
                        hashlib.sha256(raw).hexdigest(), teacher_text,
                        teacher_provenance, speaker_id)
