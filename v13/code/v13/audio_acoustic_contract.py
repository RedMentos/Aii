"""Consent-bound, timestamped RAW EAR acoustic packet adapter (synthetic-tested).

No microphone acquisition, ASR, voice identity, or automatic persistence.
This is an A-plane input contract; learned A3 projector remains UNAVAILABLE.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt, isfinite
from typing import Sequence
import hashlib
import struct

MAX_SAMPLES = 48000 * 10
SUPPORTED_RATES = (8000, 16000, 24000, 48000)


@dataclass(frozen=True)
class AudioPercept:
    schema: str
    modality: str
    source_kind: str
    consent_scope: str
    start_ms: int
    end_ms: int
    sample_rate_hz: int
    sample_count: int
    rms: float
    peak: float
    zero_crossing_rate: float
    clipped_fraction: float
    signal_sha256: str
    provenance: str
    transcript: None
    speaker_identity: None
    a3_gate: str
    is_final: bool

    def to_dict(self):
        return asdict(self)


def acoustic_packet(samples: Sequence[float], *, sample_rate_hz: int,
                    start_ms: int, source_kind: str, consent_scope: str,
                    is_final: bool = False) -> AudioPercept:
    """Return nonverbal features without storing raw samples or inferring speech.

    The caller must validate Android OS capture permission separately. This
    function rejects absent explicit source consent, even for synthetic input.
    """
    if source_kind not in ("synthetic_fixture", "permissioned_microphone", "permissioned_app_audio"):
        raise ValueError("unsupported source")
    if consent_scope not in ("synthetic_test", "audio_capture_approved"):
        raise PermissionError("explicit audio consent required")
    if source_kind != "synthetic_fixture" and consent_scope != "audio_capture_approved":
        raise PermissionError("real audio needs capture approval")
    if type(start_ms) is not int or start_ms < 0:
        raise ValueError("invalid timestamp")
    if sample_rate_hz not in SUPPORTED_RATES:
        raise ValueError("unsupported rate")
    n = len(samples)
    if not 1 <= n <= MAX_SAMPLES:
        raise ValueError("invalid frame size")
    values = []
    digest = hashlib.sha256()
    for x in samples:
        if isinstance(x, bool) or not isinstance(x, (float, int)) or not isfinite(x) or abs(x) > 1.0:
            raise ValueError("PCM must be finite normalized mono samples")
        v = float(x)
        values.append(v)
        digest.update(struct.pack("<f", v))
    rms = sqrt(sum(x * x for x in values) / n)
    zcr = sum((a < 0) != (b < 0) for a, b in zip(values, values[1:])) / max(1, n - 1)
    return AudioPercept(
        schema="v13.a5.audio-acoustic/1", modality="audio",
        source_kind=source_kind, consent_scope=consent_scope,
        start_ms=start_ms, end_ms=start_ms + (n * 1000 + sample_rate_hz - 1) // sample_rate_hz,
        sample_rate_hz=sample_rate_hz, sample_count=n,
        rms=round(rms, 8), peak=round(max(abs(x) for x in values), 8),
        zero_crossing_rate=round(zcr, 8),
        clipped_fraction=round(sum(abs(x) >= 0.999 for x in values) / n, 8),
        signal_sha256=digest.hexdigest(), provenance="source_bound_acoustic_only",
        transcript=None, speaker_identity=None, a3_gate="UNAVAILABLE",
        is_final=bool(is_final))
